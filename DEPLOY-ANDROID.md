# AI DESIGN STUDIO PRO — Android PWA + Cloud

## Mục tiêu
- Dùng mọi nơi qua Internet.
- Cài lên Android như ứng dụng (PWA), không cần APK.
- Giao diện được host cùng FastAPI; AI inference chạy ở backend cloud.

## Chạy thử trên máy tính
Yêu cầu Python 3.11. Từ thư mục `app`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Mở `http://localhost:8000`. PWA install chỉ hoạt động đầy đủ trên localhost hoặc HTTPS.

## Đưa lên Internet bằng Render (Docker)
1. Tạo tài khoản GitHub và Render.
2. Tạo repository mới, tải toàn bộ nội dung thư mục `app` lên repository.
3. Trên Render chọn **New → Blueprint**, kết nối repository và chọn file `render.yaml`.
4. Render build Docker image, cài Python dependencies và khởi chạy FastAPI.
5. Chờ deploy xong, mở URL HTTPS do Render cấp; kiểm tra `/api/health`.
6. Trên Android, mở URL HTTPS bằng Chrome → menu ⋮ → **Cài đặt ứng dụng** hoặc **Thêm vào màn hình chính**.

## Cloud AI và chi phí
- Endpoint `/api/remove-background` và `/api/separate-layers` dùng `rembg` ở backend. Render Starter chạy CPU; model có thể tải ở lần chạy đầu và xử lý chậm với ảnh lớn.
- Đây là bản cloud-hosted CPU, chưa phải GPU cloud. Để chạy inference GPU thực sự, cần triển khai backend AI lên máy chủ GPU (ví dụ GPU VM hoặc dịch vụ inference tương thích) và cấu hình endpoint/secret ở server. Không đặt API key trong JavaScript/frontend.
- Render filesystem mặc định không nên dùng làm nơi lưu dự án lâu dài. Bản này chưa có tài khoản, thư viện dự án cloud hay object storage; hãy bổ sung S3-compatible storage và database trước khi mở cho nhiều người dùng.
- Bảo vệ dịch vụ bằng xác thực, giới hạn dung lượng/tần suất, quota và giám sát chi phí trước khi public.

## PWA hoạt động thế nào
- `manifest.webmanifest`: tên, biểu tượng, chế độ standalone.
- `sw.js`: cache vỏ ứng dụng để tải giao diện nhanh và hiển thị shell khi offline.
- API AI không được cache; tách nền/xuất PSD cần Internet.
- Cần HTTPS để cài PWA từ xa. Service worker không thể thay thế máy chủ AI.

## Giới hạn chức năng hiện tại
- Tách nền rembg; tách lớp chủ thể/nền, chưa phải tách nhiều đối tượng bằng SAM 2.
- Nút upscale hiện là nội suy 2x, chưa phải super-resolution AI.
- PSD xuất layer ảnh; chữ có thể được rasterize tùy pipeline.
- Chưa có AI text-to-image, inpainting cloud, CMYK/ICC, PDF/X, lưu dự án đồng bộ.

## Kiểm tra sau deploy
- `https://YOUR-DOMAIN/` tải giao diện.
- `https://YOUR-DOMAIN/manifest.webmanifest` trả JSON manifest.
- `https://YOUR-DOMAIN/api/health` trả JSON `ok: true`.
- Trên Chrome Android, menu có mục Cài đặt ứng dụng.
