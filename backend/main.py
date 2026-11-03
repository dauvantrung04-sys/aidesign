"""AI DESIGN STUDIO PRO - local hybrid image backend.

Run from backend/: uvicorn main:app --reload --host 127.0.0.1 --port 8000
AI background removal uses rembg (model downloaded on first use).
Layer separation returns aligned foreground/background RGBA PNGs.
PSD export uses psd-tools and preserves each submitted layer as a PSD layer.
"""
from __future__ import annotations

import base64
import io
import os
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageChops

APP_VERSION = "0.2.0"
MAX_UPLOAD = 40 * 1024 * 1024
MAX_SIDE = 12000

app = FastAPI(title="AI DESIGN STUDIO PRO API", version=APP_VERSION)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.webmanifest"), media_type="application/manifest+json")

@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"), media_type="application/javascript", headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})

@app.get("/icons/{icon_name}", include_in_schema=False)
def app_icon(icon_name: str):
    if icon_name not in {"icon-192.png", "icon-512.png", "icon-maskable-512.png"}:
        raise HTTPException(404, "Không tìm thấy biểu tượng.")
    return FileResponse(os.path.join(FRONTEND_DIR, "icons", icon_name), media_type="image/png")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def read_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.width > MAX_SIDE or image.height > MAX_SIDE:
            raise HTTPException(413, f"Ảnh vượt giới hạn {MAX_SIDE}px mỗi chiều.")
        return image.convert("RGBA")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(415, "Tệp không phải ảnh hợp lệ hoặc định dạng không được hỗ trợ.") from exc


def run_rembg(image: Image.Image) -> Image.Image:
    try:
        from rembg import remove
    except ImportError as exc:
        raise HTTPException(503, "Chưa cài rembg. Hãy chạy: pip install -r requirements.txt") from exc
    try:
        result = remove(image)
        if isinstance(result, bytes):
            result = Image.open(io.BytesIO(result)).convert("RGBA")
        else:
            result = result.convert("RGBA")
        return result
    except Exception as exc:
        raise HTTPException(500, f"Không thể chạy mô hình tách nền: {exc}") from exc


def png_bytes(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        import rembg  # noqa: F401
        rembg_ready = True
    except Exception:
        rembg_ready = False
    try:
        import psd_tools  # noqa: F401
        psd_ready = True
    except Exception:
        psd_ready = False
    return {
        "ok": True,
        "app": "AI DESIGN STUDIO PRO",
        "version": APP_VERSION,
        "background_removal": "ready" if rembg_ready else "install_required",
        "psd_export": "ready" if psd_ready else "install_required",
        "layer_separation": "foreground_background",
        "mode": os.getenv("AI_MODE", "cloud"),
    }


@app.post("/api/remove-background")
async def remove_background(file: UploadFile = File(...)) -> Response:
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Dung lượng ảnh tối đa 40 MB.")
    image = read_image(data)
    result = run_rembg(image)
    return Response(png_bytes(result), media_type="image/png", headers={"X-AI-Operation": "remove-background"})


@app.post("/api/separate-layers")
async def separate_layers(file: UploadFile = File(...)) -> dict[str, Any]:
    """Split a photo into aligned foreground and background transparent PNG layers."""
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Dung lượng ảnh tối đa 40 MB.")
    original = read_image(data)
    foreground = run_rembg(original)
    if foreground.size != original.size:
        foreground = foreground.resize(original.size, Image.Resampling.LANCZOS)
    alpha = foreground.getchannel("A")
    # Keep the original RGB values; the inverse alpha makes the subject area transparent.
    inverse = ImageChops.invert(alpha)
    background = original.copy()
    background.putalpha(inverse)
    return {
        "width": original.width,
        "height": original.height,
        "method": "rembg foreground/background segmentation",
        "layers": [
            {"name": "02 - Đối tượng đã tách", "role": "foreground", "png_base64": base64.b64encode(png_bytes(foreground)).decode("ascii")},
            {"name": "01 - Phông nền", "role": "background", "png_base64": base64.b64encode(png_bytes(background)).decode("ascii")},
        ],
        "note": "Bản MVP tách chủ thể chính và phần nền. Tách nhiều chủ thể độc lập bằng SAM 2 là module nâng cấp tiếp theo.",
    }


class PSDLayer(BaseModel):
    name: str = Field(default="Layer", max_length=120)
    visible: bool = True
    opacity: float = Field(default=1.0, ge=0, le=1)
    x: int = 0
    y: int = 0
    png_data_url: str


class PSDRequest(BaseModel):
    width: int = Field(ge=1, le=12000)
    height: int = Field(ge=1, le=12000)
    layers: list[PSDLayer] = Field(min_length=1, max_length=100)


@app.post("/api/export/psd")
def export_psd(req: PSDRequest) -> Response:
    try:
        from psd_tools import PSDImage
        from psd_tools.api.layers import PixelLayer
    except ImportError as exc:
        raise HTTPException(503, "Chưa cài psd-tools. Hãy chạy pip install -r requirements.txt") from exc

    psd = PSDImage.new(mode="RGB", size=(req.width, req.height))
    # PSD stack order follows the editor's bottom-to-top layer order.
    for item in req.layers:
        if not item.visible:
            continue
        try:
            header, encoded = item.png_data_url.split(",", 1)
            if "base64" not in header:
                raise ValueError("Expected base64 data URL")
            raw = base64.b64decode(encoded, validate=True)
            source = Image.open(io.BytesIO(raw)).convert("RGBA")
            full = Image.new("RGBA", (req.width, req.height), (0, 0, 0, 0))
            if item.opacity < 1:
                a = source.getchannel("A").point(lambda value: round(value * item.opacity))
                source.putalpha(a)
            full.alpha_composite(source, dest=(item.x, item.y))
            layer = PixelLayer.frompil(full, psd, name=item.name)
            psd.append(layer)
        except Exception as exc:
            raise HTTPException(400, f"Layer '{item.name}' không hợp lệ: {exc}") from exc
    output = io.BytesIO()
    try:
        psd.save(output)
    except Exception as exc:
        raise HTTPException(500, f"Không thể ghi PSD: {exc}") from exc
    return Response(
        output.getvalue(),
        media_type="image/vnd.adobe.photoshop",
        headers={"Content-Disposition": 'attachment; filename="ai-design-studio-pro.psd"'},
    )
