# 🐳 AMIS OCR System - Docker Guide

Hướng dẫn chi tiết sử dụng Docker để deploy AMIS OCR System

## 📋 Mục lục

1. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
2. [Cài đặt nhanh](#cài-đặt-nhanh)
3. [Các lệnh thường dùng](#các-lệnh-thường-dùng)
4. [Cấu hình](#cấu-hình)
5. [Troubleshooting](#troubleshooting)
6. [Production Deployment](#production-deployment)

---

## 🔧 Yêu cầu hệ thống

### Phần mềm cần thiết:

- **Docker Desktop** (Windows/Mac) hoặc **Docker Engine** (Linux)
  - Phiên bản: 20.10+
  - Download: https://www.docker.com/products/docker-desktop/

- **Docker Compose**
  - Phiên bản: 2.0+
  - Thường đi kèm Docker Desktop

### Tài nguyên:

- RAM: Tối thiểu 4GB (khuyến nghị 8GB+)
- Disk: 5GB trống
- CPU: 2 cores

---

## 🚀 Cài đặt nhanh

### Bước 1: Tải code

```bash
# Clone hoặc giải nén code
cd amis_ocr_complete
```

### Bước 2: Cấu hình

```bash
# Sử dụng Makefile
make install

# Hoặc thủ công
cp .env.example .env
mkdir -p uploads outputs logs
```

### Bước 3: Thêm API key

Mở file `.env` và thêm API key:

```bash
# Mở file .env bằng editor
nano .env

# Hoặc
vim .env

# Hoặc
code .env
```

Sửa dòng:
```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_ACTUAL_API_KEY_HERE
```

**Lấy API key tại:** https://console.anthropic.com/

### Bước 4: Chạy

```bash
# Cách 1: Sử dụng Makefile (khuyến nghị)
make start

# Cách 2: Docker Compose trực tiếp
docker-compose up -d
```

### Bước 5: Kiểm tra

```bash
# Xem logs
make logs

# Kiểm tra health
make health

# Hoặc mở trình duyệt
# http://localhost:8000
```

✅ **Xong!** Hệ thống đã chạy tại http://localhost:8000

---

## 📖 Các lệnh thường dùng

### Quản lý cơ bản

```bash
# Xem tất cả lệnh
make help

# Khởi động
make up

# Dừng
make down

# Restart
make restart

# Build lại
make build

# Build + Start
make start
```

### Monitoring & Logs

```bash
# Xem logs real-time
make logs

# Xem logs của app only
make logs-app

# Xem trạng thái
make status

# Xem resource usage
make stats

# Health check
make health
```

### Debug & Shell

```bash
# Mở shell trong container
make shell

# Mở root shell
make shell-root

# Chạy tests
make test

# Test API
make test-api
```

### Cleanup

```bash
# Dọn dẹp containers & images
make clean

# Dọn dẹp toàn bộ (bao gồm volumes)
make clean-all

# Chỉ xóa data
make clean-data
```

### Backup & Restore

```bash
# Backup dữ liệu
make backup

# Restore (thủ công)
tar -xzf backups/amis-ocr-backup-YYYYMMDD_HHMMSS.tar.gz
```

---

## ⚙️ Cấu hình

### 1. Thay đổi Port

Trong file `.env`:

```env
PORT=8001  # Thay vì 8000
```

Sau đó:

```bash
make restart
```

### 2. Environment Variables

File `.env` chứa tất cả config:

```env
# Application
APP_NAME=AMIS OCR System
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False

# Server
HOST=0.0.0.0
PORT=8000

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# File Storage
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
MAX_FILE_SIZE=10485760

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### 3. Resource Limits

Trong `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Tăng CPU
      memory: 4G       # Tăng RAM
    reservations:
      cpus: '2.0'
      memory: 2G
```

### 4. Volumes (Persistent Data)

```yaml
volumes:
  - ./uploads:/app/uploads    # Upload files
  - ./outputs:/app/outputs    # Export files
  - ./logs:/app/logs          # Application logs
```

---

## 🔧 Troubleshooting

### 1. Port đã được sử dụng

**Lỗi:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Giải pháp:**

```bash
# Tìm process đang dùng port
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Giải pháp 1: Kill process đó
kill -9 <PID>

# Giải pháp 2: Đổi port trong .env
PORT=8001
```

### 2. API key không hợp lệ

**Lỗi:** `anthropic.APIError: Invalid API key`

**Giải pháp:**

```bash
# Kiểm tra .env
cat .env | grep ANTHROPIC_API_KEY

# Đảm bảo format đúng:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# Restart container
make restart
```

### 3. Container không start

**Kiểm tra logs:**

```bash
make logs

# Hoặc
docker-compose logs amis-ocr
```

**Kiểm tra trạng thái:**

```bash
make status
docker ps -a
```

### 4. Out of memory

**Tăng memory limit:**

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G  # Tăng từ 2G
```

### 5. Build lỗi

```bash
# Clean và rebuild
make clean
make build

# Hoặc build không cache
docker-compose build --no-cache
```

### 6. Permission denied

**Lỗi:** `Permission denied: /app/uploads`

**Giải pháp:**

```bash
# Tạo lại directories với quyền đúng
mkdir -p uploads outputs logs
chmod 755 uploads outputs logs

# Hoặc chạy với root
make shell-root
```

---

## 🚀 Production Deployment

### 1. Build Production Image

```bash
# Build với production settings
ENVIRONMENT=production DEBUG=False make build
```

### 2. Security Checklist

- [ ] Đổi `SECRET_KEY` trong `.env`
- [ ] Đặt `DEBUG=False`
- [ ] Giới hạn CORS origins
- [ ] Sử dụng HTTPS
- [ ] Backup định kỳ
- [ ] Monitor logs

### 3. Sử dụng Nginx Reverse Proxy

**Tạo file `nginx/nginx.conf`:**

```nginx
upstream amis_ocr {
    server amis-ocr:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://amis_ocr;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /app/frontend;
    }
}
```

**Uncomment nginx service trong `docker-compose.yml`**

### 4. SSL/HTTPS với Let's Encrypt

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Tạo certificate
certbot --nginx -d yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

### 5. Monitoring & Logging

**Tích hợp Sentry (optional):**

```env
# .env
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

**Centralized logging với ELK Stack:**

```yaml
# docker-compose.yml
logging:
  driver: "syslog"
  options:
    syslog-address: "tcp://logstash:5000"
```

### 6. Backup Strategy

```bash
# Cron job hàng ngày
0 2 * * * cd /path/to/amis_ocr && make backup

# Backup to S3
aws s3 sync ./backups s3://your-bucket/amis-ocr-backups/
```

### 7. High Availability

**Sử dụng Docker Swarm:**

```bash
# Init swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml amis_ocr

# Scale
docker service scale amis_ocr_amis-ocr=3
```

**Hoặc Kubernetes:**

```bash
# Tạo k8s deployment
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## 📊 Resource Monitoring

### Xem resource usage:

```bash
# Real-time stats
make stats

# Hoặc
docker stats amis-ocr-backend
```

### Expected Usage:

- **CPU**: 5-20% (idle), 50-80% (processing)
- **Memory**: 500MB-1.5GB
- **Disk**: Tùy vào số file upload/export

---

## 🔄 Update & Maintenance

### Update code:

```bash
# Pull code mới
git pull

# Rebuild và restart
make update
```

### Update dependencies:

```bash
# Sửa requirements.txt
# Rebuild image
make clean
make build
make up
```

### Database migrations (nếu có):

```bash
make shell
python manage.py migrate
```

---

## 💡 Tips & Best Practices

### 1. Development vs Production

**Development:**
```bash
# Hot reload, debug mode
DEBUG=True make dev
```

**Production:**
```bash
# Optimized, no debug
DEBUG=False make prod
```

### 2. Tối ưu build time

```yaml
# Sử dụng .dockerignore
# Sắp xếp lệnh COPY theo thứ tự thay đổi ít nhất
COPY requirements.txt .    # Ít thay đổi
RUN pip install ...
COPY backend/ .           # Thay đổi nhiều
```

### 3. Multi-stage builds

Dockerfile đã sử dụng multi-stage để giảm kích thước image:

- Stage 1 (builder): Build dependencies
- Stage 2 (runtime): Chỉ copy artifacts cần thiết

### 4. Health checks

```bash
# Auto health check mỗi 30s
# Restart container nếu unhealthy
```

### 5. Logs rotation

```yaml
logging:
  options:
    max-size: "10m"    # Max 10MB per file
    max-file: "3"      # Keep 3 files
```

---

## 📚 Tài liệu thêm

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI + Docker](https://fastapi.tiangolo.com/deployment/docker/)

---

## ❓ FAQ

**Q: Docker Desktop có miễn phí không?**  
A: Có, miễn phí cho cá nhân và công ty nhỏ (<250 nhân viên, <$10M doanh thu).

**Q: Image size bao nhiêu?**  
A: ~500MB (Python slim) + ~300MB (dependencies) = ~800MB.

**Q: Có thể chạy trên Raspberry Pi không?**  
A: Có, cần build cho ARM architecture.

**Q: Scale như thế nào?**  
A: Sử dụng `docker-compose up --scale amis-ocr=3`

**Q: Backup tự động?**  
A: Dùng cron job: `0 2 * * * make backup`

**Q: Chạy multiple instances?**  
A: Thay đổi port trong .env hoặc dùng Docker Swarm/K8s.

---

**Happy Dockerizing! 🐳**

*Last updated: January 2026*
