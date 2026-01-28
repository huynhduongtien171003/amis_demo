# 🚀 Hướng dẫn Deploy lên Railway.com

Hướng dẫn chi tiết để deploy **AMIS OCR System** lên Railway.com và tạo một web động chạy 24/7.

---

## 📋 Yêu cầu trước khi bắt đầu

1. **Tài khoản Railway**: Đăng ký tại [railway.app](https://railway.app)
2. **GitHub Account**: Để kết nối repository
3. **OpenAI API Key**: Lấy tại [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

---

## 🎯 Bước 1: Chuẩn bị Repository

### 1.1. Tạo GitHub Repository

```bash
# Khởi tạo git (nếu chưa có)
git init

# Thêm tất cả files
git add .

# Commit
git commit -m "Initial commit for Railway deployment"

# Tạo repository trên GitHub và thêm remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push code
git push -u origin main
```

### 1.2. Kiểm tra các file cần thiết

Đảm bảo repository có các file sau:

- ✅ `requirements.txt` - Dependencies Python
- ✅ `railway.toml` - Cấu hình Railway
- ✅ `.railwayignore` - File bỏ qua khi deploy
- ✅ `.env.example` - Mẫu biến môi trường
- ✅ `backend/main.py` - FastAPI application
- ✅ `frontend/index.html` - Giao diện web

---

## 🚂 Bước 2: Deploy lên Railway

### 2.1. Tạo Project mới trên Railway

1. Truy cập [railway.app](https://railway.app)
2. Click **"New Project"**
3. Chọn **"Deploy from GitHub repo"**
4. Authorize Railway truy cập GitHub
5. Chọn repository **amis-ocr-system** (hoặc tên repo của bạn)

### 2.2. Railway sẽ tự động:

- ✅ Detect Python project
- ✅ Install dependencies từ `requirements.txt`
- ✅ Đọc cấu hình từ `railway.toml`
- ✅ Build và deploy application

---

## ⚙️ Bước 3: Cấu hình Biến Môi trường

### 3.1. Thêm Variables trên Railway Dashboard

1. Trong Railway Dashboard, chọn service vừa tạo
2. Mở tab **"Variables"**
3. Thêm các biến môi trường sau:

#### Biến bắt buộc:

```
OPENAI_API_KEY=sk-proj-xxx...xxx
```

#### Biến tùy chọn (có giá trị mặc định):

```
APP_NAME=AMIS OCR System
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False

OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=4096

UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs

MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf

SECRET_KEY=your-random-secret-key-here

CORS_ORIGINS=*

LOG_LEVEL=INFO
```

### 3.2. Tạo SECRET_KEY ngẫu nhiên

Chạy lệnh sau để tạo secret key:

```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy kết quả và thêm vào biến `SECRET_KEY` trên Railway.

---

## 🌐 Bước 4: Lấy Domain và Truy cập

### 4.1. Railway tự động tạo domain

Sau khi deploy thành công, Railway sẽ tạo domain dạng:

```
https://your-project-name.up.railway.app
```

### 4.2. Custom Domain (Tùy chọn)

1. Trong Railway Dashboard, mở tab **"Settings"**
2. Scroll xuống **"Domains"**
3. Click **"Generate Domain"** hoặc thêm custom domain

### 4.3. Truy cập ứng dụng

```
🌐 Frontend:  https://your-domain.railway.app/
📚 API Docs:  https://your-domain.railway.app/docs
❤️ Health:    https://your-domain.railway.app/health
```

---

## ✅ Bước 5: Kiểm tra Deployment

### 5.1. Kiểm tra Health Check

Truy cập endpoint health check:

```
GET https://your-domain.railway.app/health
```

Kết quả mong đợi:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### 5.2. Kiểm tra Frontend

1. Mở trình duyệt
2. Truy cập `https://your-domain.railway.app/`
3. Kiểm tra giao diện OCR hiển thị đúng

### 5.3. Test OCR

1. Upload một ảnh hóa đơn
2. Click **"Xử lý hóa đơn"**
3. Kiểm tra kết quả OCR

---

## 📊 Bước 6: Giám sát và Logs

### 6.1. Xem Logs

1. Trong Railway Dashboard
2. Mở tab **"Deployments"**
3. Click vào deployment mới nhất
4. Xem **Logs** real-time

### 6.2. Theo dõi Metrics

Railway cung cấp metrics về:

- 📈 CPU Usage
- 💾 Memory Usage
- 🌐 Network Traffic
- ⚡ Request Rate

---

## 🔄 Cập nhật Code

### Tự động deploy khi push code

Railway tự động redeploy khi có thay đổi trên GitHub:

```bash
# Sửa code
git add .
git commit -m "Update OCR prompt"
git push

# Railway tự động detect và redeploy
```

### Rollback nếu cần

1. Trong Railway Dashboard → **Deployments**
2. Click vào deployment cũ
3. Click **"Redeploy"**

---

## 🛠️ Troubleshooting

### ❌ Lỗi: Build failed

**Nguyên nhân**: Missing dependencies

**Giải pháp**:

- Kiểm tra `requirements.txt` có đầy đủ không
- Xem logs để tìm package bị thiếu

### ❌ Lỗi: Application crashed

**Nguyên nhân**: Thiếu biến môi trường

**Giải pháp**:

- Kiểm tra `OPENAI_API_KEY` đã được set chưa
- Xem logs chi tiết trong tab **Deployments**

### ❌ Lỗi: OpenAI API quota exceeded

**Nguyên nhân**: Hết quota OpenAI

**Giải pháp**:

- Kiểm tra billing tại [platform.openai.com/account/billing](https://platform.openai.com/account/billing)
- Nâng cấp plan hoặc thêm credit

### ❌ Lỗi: CORS

**Nguyên nhân**: Frontend không call được API

**Giải pháp**:

- Set `CORS_ORIGINS=*` trong Railway Variables
- Hoặc chỉ định domain cụ thể

---

## 💰 Chi phí

### Railway Pricing

- **Free Tier**: $5 credit/tháng (miễn phí)
  - Đủ cho demo và test
  - Auto-sleep khi không dùng

- **Starter Plan**: $5/tháng
  - Không auto-sleep
  - Uptime 24/7

### OpenAI API Pricing (gpt-4o)

- **Input**: ~$2.5/1M tokens
- **Output**: ~$10/1M tokens

**Ước tính**:

- 1 hóa đơn ≈ 1,000 tokens input + 500 tokens output
- 1,000 hóa đơn/tháng ≈ $7-10

---

## 🔐 Bảo mật

### Khuyến nghị:

1. ✅ **Không commit** file `.env` lên GitHub
2. ✅ Sử dụng **Railway Variables** cho sensitive data
3. ✅ Tạo **SECRET_KEY** ngẫu nhiên cho mỗi environment
4. ✅ Giới hạn **CORS_ORIGINS** nếu có thể
5. ✅ Enable **rate limiting** nếu cần (xem FastAPI docs)

---

## 📚 Tài liệu tham khảo

- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [OpenAI API](https://platform.openai.com/docs)

---

## ✨ Tính năng nâng cao

### 1. Thêm Database (PostgreSQL)

Railway cung cấp PostgreSQL miễn phí:

1. Trong project Railway, click **"New"** → **"Database"** → **"PostgreSQL"**
2. Railway tự động tạo `DATABASE_URL`
3. Sử dụng SQLAlchemy để kết nối

### 2. Thêm Redis cho Caching

1. Add Redis service trong Railway
2. Sử dụng redis-py để cache OCR results

### 3. Webhook cho tự động xử lý

- Tạo endpoint nhận webhook từ email/file storage
- Tự động OCR khi có file mới

---

## 🎉 Kết luận

Bạn đã deploy thành công **AMIS OCR System** lên Railway!

Web app của bạn giờ đã:

- ✅ Chạy 24/7 trên cloud
- ✅ Có HTTPS tự động
- ✅ Tự động scale
- ✅ Logs và metrics đầy đủ

**URL ứng dụng của bạn**:

```
🌐 https://YOUR-APP-NAME.up.railway.app
```

Enjoy! 🚀
