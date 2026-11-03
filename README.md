# AI DESIGN STUDIO PRO — Android PWA MVP 0.3

This package contains the responsive web editor, PWA manifest/icons/service worker, FastAPI backend, Dockerfile and Render Blueprint.

## Android installation
Deploy the app to a public HTTPS URL first. On Android Chrome, open the URL, tap ⋮, then choose **Install app** or **Add to Home screen**. It is a PWA, not an APK.

## Local run
Python 3.11 is recommended:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000. PWA install is allowed on localhost for testing; remote installation requires HTTPS.

## Cloud deployment
See `DEPLOY-ANDROID.md`. The included Docker/Render configuration is a cloud-hosted CPU starter. `rembg` runs on the server; first inference may download its model and be slow. A GPU cloud endpoint is not provisioned by this source package and must be connected separately for production-speed AI.

## Endpoints
- `GET /api/health`
- `POST /api/remove-background`
- `POST /api/separate-layers`
- `POST /api/export/psd`

## Known limitations
PWA shell can load offline after first visit, but AI endpoints require Internet. Current segmentation separates primary foreground/background, not multiple independent objects. Upscale is not yet AI super-resolution. No user accounts, cloud project sync, text-to-image generation, inpainting, GPU inference, or print-grade CMYK/PDF-X pipeline is included yet.
