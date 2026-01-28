# ⚡ AMIS OCR - Quick Start Guide

## 🚀 Cài đặt & Chạy (3 phút)

### Bước 1: Setup

```bash
# Tạo .env
cp .env.example .env

# Hoặc dùng Makefile
make install
```

### Bước 2: Config

Mở `.env` và sửa:

```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
```

### Bước 3: Chạy

```bash
# Khởi động
make start

# Hoặc
docker-compose up -d
```

### Bước 4: Truy cập

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: Mở `frontend/index.html`

---

## 📋 Commands Copy-Paste

### Makefile Commands

```bash
# Xem tất cả lệnh
make help

# Cài đặt
make install

# Build
make build

# Start
make up

# Stop
make down

# Restart
make restart

# Logs
make logs

# Status
make status

# Shell
make shell

# Clean
make clean
```

### Docker Compose Commands

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Exec shell
docker-compose exec amis-ocr /bin/bash

# Restart
docker-compose restart
```

---

## 🔧 File .env Template

Copy & paste vào file `.env`:

```env
# Application
APP_NAME=AMIS OCR System
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False

# Server
HOST=0.0.0.0
PORT=8000

# Anthropic API (BẮT BUỘC - thay YOUR_KEY_HERE)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=4096

# Storage
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
LOG_DIR=./logs
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf

# Security
SECRET_KEY=your-secret-key-change-in-production

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://localhost:5500

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

---

## 🧪 Test Commands

```bash
# Test health
curl http://localhost:8000/health

# Test root
curl http://localhost:8000/

# Upload ảnh
curl -X POST http://localhost:8000/api/ocr/upload \
  -F "file=@invoice.jpg" \
  -F "document_type=auto"

# Parse text
curl -X POST http://localhost:8000/api/ocr/text \
  -F "invoice_text=Nội dung hóa đơn..." \
  -F "document_type=invoice"
```

---

## 🐛 Troubleshooting Quick Fix

### Port bị chiếm

```bash
# Đổi port trong .env
PORT=8001

# Restart
make restart
```

### Container không start

```bash
# Xem logs
make logs

# Rebuild
make clean
make build
make up
```

### Permission issues

```bash
# Fix permissions
chmod 755 uploads outputs logs

# Hoặc chạy với root
make shell-root
```

---

## 📦 One-liner Installation

```bash
# Clone > Setup > Start
git clone <repo> amis_ocr && \
cd amis_ocr && \
cp .env.example .env && \
echo "Sửa .env và thêm API key, sau đó chạy: make start"
```

---

## 🎯 Common Use Cases

### Development Mode

```bash
# Hot reload code
DEBUG=True docker-compose up
```

### Production Mode

```bash
# Optimized, no debug
DEBUG=False make prod
```

### Backup Data

```bash
make backup

# Manual backup
tar -czf backup.tar.gz uploads outputs logs .env
```

### Update System

```bash
git pull
make update
```

---

## 💡 Pro Tips

### Alias trong ~/.bashrc

```bash
# Thêm vào ~/.bashrc
alias amis-start='make up'
alias amis-stop='make down'
alias amis-logs='make logs'
alias amis-shell='make shell'
```

### Watch logs real-time

```bash
watch -n 2 'docker-compose logs --tail=50 amis-ocr'
```

### Auto-restart on crash

```yaml
# Đã có sẵn trong docker-compose.yml
restart: unless-stopped
```

---

## 📞 Support

- GitHub Issues: [link]
- Documentation: `README.md`, `DOCKER.md`
- API Docs: http://localhost:8000/docs

---

**Happy coding! 🚀**
