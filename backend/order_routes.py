"""
API endpoints cho Order Recognition System - Công cụ cho NGƯỜI BÁN

Giúp người bán/shop nhận diện thông tin KHÁCH HÀNG từ tin nhắn đặt hàng
- Tự động trích xuất: tên KH, SĐT, địa chỉ, sản phẩm, số lượng, giá
- Hỗ trợ cả text và ảnh screenshot (Zalo, Messenger, Email)
- Lọc nhiễu tự động (lời chào, emoji, câu hỏi không liên quan)
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from loguru import logger

from backend.config import settings
from backend.order import (
    OrderRequest,
    OrderResponse,
    TextOrderInput,
    OrderUpdateRequest,
    OrderData
)
from backend.order_service import order_recognition_service


# Router
router = APIRouter(prefix="/api/order", tags=["Order Recognition"])

# In-memory storage (trong production nên dùng database)
order_jobs_storage = {}


def generate_job_id() -> str:
    """Tạo job ID unique"""
    return f"order_{uuid.uuid4().hex[:12]}"


def save_uploaded_file(upload_file: UploadFile, job_id: str) -> str:
    """
    Lưu file upload vào thư mục uploads

    Args:
        upload_file: File được upload
        job_id: ID của job

    Returns:
        Đường dẫn đến file đã lưu
    """
    # Tạo thư mục upload nếu chưa có
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Tạo tên file
    file_extension = Path(upload_file.filename).suffix
    filename = f"{job_id}{file_extension}"
    file_path = upload_dir / filename

    # Lưu file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return str(file_path)


@router.post("/upload", response_model=OrderResponse)
async def upload_and_process_order_image(
    file: UploadFile = File(...)
):
    """
    [NGƯỜI BÁN] Upload ảnh screenshot tin nhắn khách hàng và nhận diện thông tin đặt hàng

    - **file**: File ảnh screenshot tin nhắn từ khách hàng (JPG, PNG, WebP)

    **Công cụ giúp người bán:**
    - Screenshot từ Zalo, Messenger, Email, SMS
    - Tự động trích xuất thông tin KHÁCH HÀNG: tên, SĐT, địa chỉ
    - Nhận diện sản phẩm, số lượng, giá từ tin nhắn
    - Lọc nhiễu tự động (lời chào, emoji, câu hỏi không liên quan)
    """
    try:
        # Kiểm tra file extension
        file_ext = Path(file.filename).suffix.lower().replace('.', '')
        if file_ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"File extension không được hỗ trợ. Chỉ chấp nhận: {settings.allowed_extensions}"
            )

        # Kiểm tra file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File quá lớn. Kích thước tối đa: {settings.max_file_size / 1024 / 1024}MB"
            )

        # Tạo job ID
        job_id = generate_job_id()

        # Lưu file
        file_path = save_uploaded_file(file, job_id)
        logger.info(f"📸 File screenshot đã lưu: {file_path}")

        # Xử lý nhận diện đơn hàng
        result = await order_recognition_service.process_image_order(file_path)

        if not result["success"]:
            return OrderResponse(
                success=False,
                job_id=job_id,
                status="error",
                error_message=result.get("error", "Unknown error"),
                processing_time=result.get("processing_time", 0)
            )

        # Lấy order data
        order_data = result["data"]

        # Lưu vào storage
        order_jobs_storage[job_id] = {
            "job_id": job_id,
            "created_at": datetime.now(),
            "file_path": file_path,
            "input_type": "file",
            "status": "completed",
            "order_data": order_data,
            "raw_response": result.get("raw_response")
        }

        return OrderResponse(
            success=True,
            job_id=job_id,
            status="completed",
            data=order_data,
            processing_time=result["processing_time"],
            raw_response=result.get("raw_response")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi khi xử lý upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=OrderResponse)
async def process_text_order(
    message_text: str = Form(...),
    additional_context: Optional[str] = Form(default=None)
):
    """
    [NGƯỜI BÁN] Nhận diện thông tin khách hàng từ text tin nhắn (không cần upload ảnh)

    - **message_text**: Nội dung text tin nhắn từ khách hàng
    - **additional_context**: Thông tin bổ sung (optional)

    **Công cụ giúp người bán:**
    - Copy/paste text tin nhắn từ khách hàng
    - Tự động trích xuất thông tin KHÁCH HÀNG: tên, SĐT, địa chỉ
    - Nhận diện sản phẩm, số lượng, giá
    - Lọc nhiễu tự động

    **Ví dụ tin nhắn từ khách hàng:**
    ```
    Tên: Nguyễn Văn A
    SĐT: 0901234567
    Địa chỉ: 123 Nguyễn Huệ, Q1, HCM

    Đặt hàng:
    1. Laptop Dell XPS - 2 cái - 25tr/cái
    2. Chuột Logitech - 1 cái - 500k

    Thanh toán: COD
    ```
    """
    try:
        # Tạo job ID
        job_id = generate_job_id()

        # Tạo TextOrderInput
        text_input = TextOrderInput(
            message_text=message_text,
            additional_context=additional_context
        )

        # Xử lý parsing
        result = await order_recognition_service.process_text_order(text_input)

        if not result["success"]:
            return OrderResponse(
                success=False,
                job_id=job_id,
                status="error",
                error_message=result.get("error", "Unknown error"),
                processing_time=result.get("processing_time", 0)
            )

        # Lấy order data
        order_data = result["data"]

        # Lưu vào storage
        order_jobs_storage[job_id] = {
            "job_id": job_id,
            "created_at": datetime.now(),
            "input_type": "text",
            "input_text": message_text,
            "status": "completed",
            "order_data": order_data,
            "raw_response": result.get("raw_response")
        }

        return OrderResponse(
            success=True,
            job_id=job_id,
            status="completed",
            data=order_data,
            processing_time=result["processing_time"],
            raw_response=result.get("raw_response")
        )

    except Exception as e:
        logger.error(f"❌ Lỗi khi xử lý text input: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{job_id}", response_model=OrderResponse)
async def get_order_result(job_id: str):
    """
    Lấy kết quả nhận diện đơn hàng theo job ID

    - **job_id**: ID của job cần lấy kết quả
    """
    if job_id not in order_jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    job_data = order_jobs_storage[job_id]

    return OrderResponse(
        success=True,
        job_id=job_id,
        status=job_data["status"],
        data=job_data.get("order_data"),
        raw_response=job_data.get("raw_response"),
        processing_time=0
    )


@router.put("/update/{job_id}")
async def update_order_data(job_id: str, update_request: OrderUpdateRequest):
    """
    Cập nhật dữ liệu đơn hàng sau khi người dùng chỉnh sửa

    - **job_id**: ID của job
    - **update_request**: Dữ liệu đã chỉnh sửa
    """
    if job_id not in order_jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    # Cập nhật data
    order_jobs_storage[job_id]["order_data"] = update_request.updated_data
    order_jobs_storage[job_id]["updated_at"] = datetime.now()
    order_jobs_storage[job_id]["update_notes"] = update_request.update_notes

    return {
        "success": True,
        "message": "Đã cập nhật đơn hàng thành công",
        "job_id": job_id
    }


@router.get("/jobs")
async def list_order_jobs(limit: int = 50, offset: int = 0):
    """
    Liệt kê danh sách jobs nhận diện đơn hàng

    - **limit**: Số lượng jobs trả về (mặc định 50)
    - **offset**: Bỏ qua bao nhiêu jobs (phân trang)
    """
    jobs_list = []

    for job_id, job_data in list(order_jobs_storage.items())[offset:offset+limit]:
        order_data = job_data.get("order_data")
        jobs_list.append({
            "job_id": job_id,
            "created_at": job_data["created_at"],
            "input_type": job_data["input_type"],
            "status": job_data["status"],
            "customer_name": order_data.customer_name if order_data else None,
            "customer_phone": order_data.customer_phone if order_data else None,
            "total_items": len(order_data.items) if order_data else 0,
            "needs_review": order_data.needs_review if order_data else False
        })

    return {
        "total": len(order_jobs_storage),
        "limit": limit,
        "offset": offset,
        "jobs": jobs_list
    }


@router.delete("/job/{job_id}")
async def delete_order_job(job_id: str):
    """
    Xóa job và dữ liệu liên quan

    - **job_id**: ID của job cần xóa
    """
    if job_id not in order_jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")

    # Xóa file nếu có
    job_data = order_jobs_storage[job_id]
    if "file_path" in job_data:
        try:
            Path(job_data["file_path"]).unlink(missing_ok=True)
            logger.info(f"🗑️ Đã xóa file: {job_data['file_path']}")
        except Exception as e:
            logger.warning(f"⚠️ Không thể xóa file: {str(e)}")

    # Xóa khỏi storage
    del order_jobs_storage[job_id]

    return {
        "success": True,
        "message": "Đã xóa job thành công",
        "job_id": job_id
    }


@router.get("/stats")
async def get_order_stats():
    """
    Thống kê các đơn hàng đã xử lý
    """
    total_jobs = len(order_jobs_storage)
    total_needs_review = sum(
        1 for job in order_jobs_storage.values()
        if job.get("order_data") and job["order_data"].needs_review
    )
    total_text_input = sum(
        1 for job in order_jobs_storage.values()
        if job.get("input_type") == "text"
    )
    total_image_input = sum(
        1 for job in order_jobs_storage.values()
        if job.get("input_type") == "file"
    )

    return {
        "total_jobs": total_jobs,
        "needs_review": total_needs_review,
        "text_input": total_text_input,
        "image_input": total_image_input
    }
