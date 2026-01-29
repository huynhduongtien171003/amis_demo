"""
AMIS OCR System - Main Application
FastAPI application chính - Hỗ trợ cả OCR và nhập text thủ công
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from backend.config import settings
from backend import ocr_routes, export_routes, order_routes


# Khởi tạo FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AMIS OCR & Order Recognition System

    **Tính năng:**

    📄 **OCR Hóa đơn:**
    - ✅ OCR từ ảnh hóa đơn (JPG, PNG, PDF)
    - ✅ Nhập text thủ công (không cần ảnh)
    - ✅ Trích xuất thông tin tự động với OpenAI GPT-4
    - ✅ Export sang Excel/JSON theo định dạng AMIS

    📦 **Nhận diện Đơn hàng:**
    - ✅ Nhận diện từ screenshot tin nhắn (Zalo, Messenger, Email)
    - ✅ Nhập text đơn hàng thủ công
    - ✅ Tự động lọc nhiễu (lời chào, emoji, thông tin không liên quan)
    - ✅ Trích xuất: KH, SĐT, địa chỉ, sản phẩm, số lượng, giá

    **Workflow:**
    1. Upload ảnh/screenshot HOẶC nhập text
    2. OpenAI GPT-4 tự động trích xuất thông tin
    3. Review và sửa dữ liệu nếu cần
    4. Export/Lưu dữ liệu
    """,
    debug=settings.debug
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(ocr_routes.router)
app.include_router(export_routes.router)
app.include_router(order_routes.router)


# Static files
try:
    # Tạo thư mục nếu chưa tồn tại
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

    app.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir),
        name="uploads"
    )
    app.mount(
        "/outputs",
        StaticFiles(directory=settings.output_dir),
        name="outputs"
    )
except Exception as e:
    logger.warning(f"Không thể mount static files: {e}")


@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi app start"""
    logger.info("🚀 Starting AMIS OCR System...")
    logger.info(f"📝 Environment: {settings.environment}")
    logger.info(f"🤖 OpenAI Model: {settings.openai_model}")
    
    # Tạo các thư mục cần thiết
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    
    logger.info("✅ AMIS OCR System started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi app shutdown"""
    logger.info("👋 Shutting down AMIS OCR System...")


@app.get("/api")
async def api_info():
    """API info endpoint"""
    return {
        "message": "AMIS OCR & Order Recognition System API",
        "version": settings.app_version,
        "docs": "/docs",
        "features": [
            "OCR từ ảnh hóa đơn",
            "Nhận diện đơn hàng từ tin nhắn/screenshot",
            "Nhập text thủ công",
            "Trích xuất thông tin tự động với AI",
            "Lọc nhiễu và validate dữ liệu",
            "Export sang AMIS"
        ]
    }


@app.get("/")
async def root():
    """Serve frontend - Root page"""
    from fastapi.responses import FileResponse
    frontend_file = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_file.exists():
        return FileResponse(
            str(frontend_file),
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Frontend not found", "status": "error"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )