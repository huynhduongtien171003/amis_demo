"""
Configuration module for AMIS OCR System
Quản lý tất cả cấu hình của ứng dụng - Hỗ trợ cả OCR và nhập text thủ công
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Settings class sử dụng Pydantic để validate và load cấu hình từ .env file"""
    
    # Application settings
    app_name: str = Field(default="AMIS OCR System", description="Tên ứng dụng")
    app_version: str = Field(default="1.0.0", description="Phiên bản")
    debug: bool = Field(default=False, description="Chế độ debug")
    environment: str = Field(default="production", description="Môi trường")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Host của server")
    port: int = Field(default=8000, description="Port của server (Railway sẽ tự động set)")
    
    # OpenAI API settings
    openai_api_key: str = Field(..., description="API key của OpenAI")
    openai_model: str = Field(default="gpt-4o", description="Model OpenAI")
    openai_max_tokens: int = Field(default=4096, description="Số token tối đa")
    
    # File storage settings
    upload_dir: str = Field(default="./uploads", description="Thư mục upload")
    output_dir: str = Field(default="./outputs", description="Thư mục output")
    max_file_size: int = Field(default=10485760, description="Kích thước file tối đa (bytes)")
    allowed_extensions: str = Field(default="jpg,jpeg,png,pdf", description="Định dạng cho phép")
    
    # Security settings
    secret_key: str = Field(default="change-me-in-production", description="Secret key")
    
    # CORS settings
    cors_origins: str = Field(default="http://localhost:3000", description="CORS origins")
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Mức độ logging")
    log_dir: str = Field(default="./logs", description="Thư mục log")
    log_file: str = Field(default="./logs/app.log", description="File log")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Trả về danh sách các extension được phép"""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Trả về danh sách CORS origins"""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Khởi tạo settings instance
settings = Settings()