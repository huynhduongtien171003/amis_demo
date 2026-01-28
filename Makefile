# ==========================================
# AMIS OCR System - Makefile
# ==========================================
# Quản lý Docker commands dễ dàng

.PHONY: help install build up down restart logs shell clean status test backup

# ==========================================
# DEFAULT TARGET
# ==========================================
help:
	@echo "=================================================="
	@echo "  AMIS OCR System - Docker Management Commands"
	@echo "=================================================="
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make install      - Cài đặt lần đầu (tạo .env, directories)"
	@echo "  make build        - Build Docker image"
	@echo ""
	@echo "🚀 Running Services:"
	@echo "  make up           - Start containers (background)"
	@echo "  make down         - Stop containers"
	@echo "  make restart      - Restart containers"
	@echo "  make start        - Build + Start (shortcut)"
	@echo ""
	@echo "📊 Monitoring & Debugging:"
	@echo "  make logs         - Xem logs real-time"
	@echo "  make status       - Xem trạng thái containers"
	@echo "  make shell        - Mở shell trong container"
	@echo "  make stats        - Xem resource usage"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean        - Dọn dẹp containers & volumes"
	@echo "  make clean-all    - Dọn dẹp toàn bộ (bao gồm images)"
	@echo "  make backup       - Backup dữ liệu"
	@echo "  make test         - Chạy tests"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make dev          - Start ở development mode"
	@echo "  make prod         - Start ở production mode"
	@echo ""

# ==========================================
# INSTALLATION
# ==========================================
install:
	@echo "📦 Cài đặt AMIS OCR System..."
	@if [ ! -f .env ]; then \
		echo "   📄 Tạo file .env từ template..."; \
		cp .env.example .env; \
		echo "   ⚠️  LƯU Ý: Vui lòng sửa file .env và thêm ANTHROPIC_API_KEY"; \
		echo "   📖 Hướng dẫn: https://console.anthropic.com/"; \
	else \
		echo "   ✅ File .env đã tồn tại"; \
	fi
	@echo "   📁 Tạo directories..."
	@mkdir -p uploads outputs logs
	@echo ""
	@echo "✅ Cài đặt hoàn tất!"
	@echo ""
	@echo "📝 Bước tiếp theo:"
	@echo "   1. Sửa file .env và thêm ANTHROPIC_API_KEY"
	@echo "   2. Chạy: make build"
	@echo "   3. Chạy: make up"
	@echo ""

# ==========================================
# BUILD
# ==========================================
build:
	@echo "🔨 Building Docker image..."
	docker-compose build --no-cache
	@echo "✅ Build hoàn tất!"

build-quick:
	@echo "🔨 Building Docker image (with cache)..."
	docker-compose build
	@echo "✅ Build hoàn tất!"

# ==========================================
# RUN SERVICES
# ==========================================
up:
	@echo "🚀 Starting AMIS OCR System..."
	docker-compose up -d
	@echo ""
	@echo "✅ System đang chạy!"
	@echo "📡 API: http://localhost:8000"
	@echo "📖 API Docs: http://localhost:8000/docs"
	@echo "🌐 Frontend: Mở file frontend/index.html"
	@echo ""
	@echo "💡 Tips:"
	@echo "   - Xem logs: make logs"
	@echo "   - Xem status: make status"
	@echo "   - Stop: make down"
	@echo ""

down:
	@echo "🛑 Stopping containers..."
	docker-compose down
	@echo "✅ Đã dừng containers"

restart:
	@echo "🔄 Restarting containers..."
	docker-compose restart
	@echo "✅ Đã restart"

# Quick start (build + up)
start: build-quick up

# ==========================================
# DEVELOPMENT MODE
# ==========================================
dev:
	@echo "🔧 Starting in DEVELOPMENT mode..."
	@echo "   - Hot reload enabled"
	@echo "   - Debug mode ON"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
	
# ==========================================
# PRODUCTION MODE
# ==========================================
prod:
	@echo "🚀 Starting in PRODUCTION mode..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✅ Production mode started"

# ==========================================
# MONITORING
# ==========================================
logs:
	@echo "📋 Viewing logs (Ctrl+C to exit)..."
	docker-compose logs -f --tail=100

logs-app:
	@echo "📋 Viewing application logs..."
	docker-compose logs -f amis-ocr

status:
	@echo "📊 Container status:"
	@docker-compose ps
	@echo ""
	@echo "🔍 Detailed info:"
	@docker ps -a --filter "name=amis-ocr"

stats:
	@echo "📈 Resource usage (Ctrl+C to exit):"
	docker stats amis-ocr-backend

health:
	@echo "🏥 Health check:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Service not responding"

# ==========================================
# SHELL ACCESS
# ==========================================
shell:
	@echo "🐚 Opening shell in container..."
	docker-compose exec amis-ocr /bin/bash

shell-root:
	@echo "🐚 Opening root shell..."
	docker-compose exec -u root amis-ocr /bin/bash

# ==========================================
# TESTING
# ==========================================
test:
	@echo "🧪 Running tests..."
	docker-compose exec amis-ocr pytest tests/ -v

test-api:
	@echo "🧪 Testing API endpoints..."
	@echo "Testing /health..."
	@curl -s http://localhost:8000/health
	@echo ""
	@echo "Testing /..."
	@curl -s http://localhost:8000/ | python -m json.tool

# ==========================================
# BACKUP
# ==========================================
backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@tar -czf backups/amis-ocr-backup-$$(date +%Y%m%d_%H%M%S).tar.gz uploads outputs logs .env
	@echo "✅ Backup created in backups/"

# ==========================================
# CLEANUP
# ==========================================
clean:
	@echo "🧹 Cleaning up..."
	@echo "   - Stopping containers..."
	docker-compose down -v
	@echo "   - Removing dangling images..."
	docker image prune -f
	@echo "✅ Cleanup hoàn tất"

clean-all:
	@echo "🧹 Deep cleaning (removing everything)..."
	@echo "   ⚠️  This will remove ALL containers, images, and volumes"
	@read -p "   Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		docker system prune -af --volumes; \
		echo "✅ Deep clean hoàn tất"; \
	else \
		echo "❌ Cancelled"; \
	fi

clean-data:
	@echo "🧹 Cleaning data directories..."
	@echo "   ⚠️  This will delete all uploaded files and outputs"
	@read -p "   Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf uploads/* outputs/* logs/*; \
		echo "✅ Data cleaned"; \
	else \
		echo "❌ Cancelled"; \
	fi

# ==========================================
# UTILITIES
# ==========================================
ps:
	docker-compose ps

images:
	docker-compose images

top:
	docker-compose top

# ==========================================
# UPDATE & REBUILD
# ==========================================
update:
	@echo "🔄 Updating system..."
	git pull
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Update hoàn tất"

# ==========================================
# QUICK COMMANDS
# ==========================================
# Aliases
run: up
stop: down
rebuild: clean build up
