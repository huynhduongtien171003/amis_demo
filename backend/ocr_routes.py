"""
API endpoints cho AMIS OCR System
Hỗ trợ cả OCR từ ảnh và nhập text thủ công
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
from backend.invoice import (
    OCRRequest,
    OCRResponse,
    TextInvoiceInput,
    InvoiceUpdateRequest,
    InvoiceData
)
from backend.ocr_service import openai_ocr_service


# Router
router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# In-memory storage (trong production nên dùng database)
jobs_storage = {}


def generate_job_id() -> str:
    """Tạo job ID unique"""
    return f"job_{uuid.uuid4().hex[:12]}"


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


@router.post("/upload", response_model=OCRResponse)
async def upload_and_process_image(
    file: UploadFile = File(...),
    document_type: str = Form(default="auto"),
    language: str = Form(default="vi"),
    auto_map_amis: bool = Form(default=True)
):
    """
    Upload ảnh hóa đơn và xử lý OCR
    
    - **file**: File ảnh (JPG, PNG, PDF)
    - **document_type**: Loại chứng từ (invoice, receipt, delivery_note, auto)
    - **language**: Ngôn ngữ (vi, en)
    - **auto_map_amis**: Tự động map sang cấu trúc AMIS
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
        file.file.seek(0, 2)  # Đi đến cuối file
        file_size = file.file.tell()  # Lấy vị trí = size
        file.file.seek(0)  # Reset về đầu
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File quá lớn. Kích thước tối đa: {settings.max_file_size / 1024 / 1024}MB"
            )
        
        # Tạo job ID
        job_id = generate_job_id()
        
        # Lưu file
        file_path = save_uploaded_file(file, job_id)
        logger.info(f"File đã lưu: {file_path}")
        
        # Xử lý OCR
        result = await openai_ocr_service.process_image_ocr(
            image_path=file_path,
            document_type=document_type if document_type != "auto" else "invoice"
        )
        
        if not result["success"]:
            return OCRResponse(
                success=False,
                job_id=job_id,
                status="failed",
                error_message=result.get("error", "Unknown error"),
                processing_time=result.get("processing_time")
            )
        
        # Parse JSON từ response
        raw_response = result["raw_response"]
        parsed_data = openai_ocr_service._extract_json_from_response(raw_response)
        
        if not parsed_data:
            return OCRResponse(
                success=False,
                job_id=job_id,
                status="failed",
                error_message="Không thể parse JSON từ Claude response",
                raw_claude_response=raw_response
            )
        
        # Validate và fix dữ liệu
        validated_data = openai_ocr_service._validate_and_fix_numbers(parsed_data)

        # Convert sang InvoiceData
        invoice_data = openai_ocr_service._convert_to_invoice_data(
            validated_data,
            result["processing_time"]
        )
        
        # Lưu vào storage
        jobs_storage[job_id] = {
            "job_id": job_id,
            "created_at": datetime.now(),
            "file_path": file_path,
            "input_type": "file",
            "status": "completed",
            "invoice_data": invoice_data,
            "raw_response": raw_response
        }
        
        return OCRResponse(
            success=True,
            job_id=job_id,
            status="completed",
            data=invoice_data,
            processing_time=result["processing_time"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi xử lý upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=OCRResponse)
async def process_text_input(
    invoice_text: str = Form(...),
    document_type: str = Form(default="invoice"),
    additional_context: Optional[str] = Form(default=None),
    language: str = Form(default="vi"),
    auto_map_amis: bool = Form(default=True)
):
    """
    Xử lý text đầu vào thủ công (không cần upload ảnh)
    
    - **invoice_text**: Nội dung text của hóa đơn
    - **document_type**: Loại chứng từ (invoice, receipt, delivery_note)
    - **additional_context**: Thông tin bổ sung (optional)
    - **language**: Ngôn ngữ (vi, en)
    - **auto_map_amis**: Tự động map sang cấu trúc AMIS
    """
    try:
        # Tạo job ID
        job_id = generate_job_id()
        
        # Tạo TextInvoiceInput
        text_input = TextInvoiceInput(
            invoice_text=invoice_text,
            document_type=document_type,
            additional_context=additional_context
        )
        
        # Xử lý parsing
        result = await openai_ocr_service.process_text_input(text_input)
        
        if not result["success"]:
            return OCRResponse(
                success=False,
                job_id=job_id,
                status="failed",
                error_message=result.get("error", "Unknown error"),
                processing_time=result.get("processing_time")
            )
        
        # Parse JSON từ response
        raw_response = result["raw_response"]
        parsed_data = openai_ocr_service._extract_json_from_response(raw_response)
        
        if not parsed_data:
            return OCRResponse(
                success=False,
                job_id=job_id,
                status="failed",
                error_message="Không thể parse JSON từ Claude response",
                raw_claude_response=raw_response
            )
        
        # Validate và fix dữ liệu
        validated_data = openai_ocr_service._validate_and_fix_numbers(parsed_data)

        # Convert sang InvoiceData
        invoice_data = openai_ocr_service._convert_to_invoice_data(
            validated_data,
            result["processing_time"]
        )
        
        # Lưu vào storage
        jobs_storage[job_id] = {
            "job_id": job_id,
            "created_at": datetime.now(),
            "input_type": "text",
            "input_text": invoice_text,
            "status": "completed",
            "invoice_data": invoice_data,
            "raw_response": raw_response
        }
        
        return OCRResponse(
            success=True,
            job_id=job_id,
            status="completed",
            data=invoice_data,
            processing_time=result["processing_time"]
        )
        
    except Exception as e:
        logger.error(f"Lỗi khi xử lý text input: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{job_id}", response_model=OCRResponse)
async def get_ocr_result(job_id: str):
    """
    Lấy kết quả OCR theo job ID
    
    - **job_id**: ID của job cần lấy kết quả
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    job_data = jobs_storage[job_id]
    
    return OCRResponse(
        success=True,
        job_id=job_id,
        status=job_data["status"],
        data=job_data.get("invoice_data"),
        raw_claude_response=job_data.get("raw_response")
    )


@router.put("/update/{job_id}")
async def update_invoice_data(job_id: str, update_request: InvoiceUpdateRequest):
    """
    Cập nhật dữ liệu hóa đơn sau khi người dùng chỉnh sửa
    
    - **job_id**: ID của job
    - **update_request**: Dữ liệu đã chỉnh sửa
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    # Cập nhật data
    jobs_storage[job_id]["invoice_data"] = update_request.updated_data
    jobs_storage[job_id]["updated_at"] = datetime.now()
    jobs_storage[job_id]["update_notes"] = update_request.notes
    
    return {
        "success": True,
        "message": "Đã cập nhật dữ liệu thành công",
        "job_id": job_id
    }


@router.get("/jobs")
async def list_jobs(limit: int = 50, offset: int = 0):
    """
    Liệt kê danh sách jobs
    
    - **limit**: Số lượng jobs trả về (mặc định 50)
    - **offset**: Bỏ qua bao nhiêu jobs (phân trang)
    """
    jobs_list = []
    
    for job_id, job_data in list(jobs_storage.items())[offset:offset+limit]:
        jobs_list.append({
            "job_id": job_id,
            "created_at": job_data["created_at"],
            "input_type": job_data["input_type"],
            "status": job_data["status"],
            "buyer_name": job_data.get("invoice_data", {}).buyer_legal_name if job_data.get("invoice_data") else None
        })
    
    return {
        "total": len(jobs_storage),
        "limit": limit,
        "offset": offset,
        "jobs": jobs_list
    }


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Xóa job và dữ liệu liên quan
    
    - **job_id**: ID của job cần xóa
    """
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    
    # Xóa file nếu có
    job_data = jobs_storage[job_id]
    if "file_path" in job_data:
        try:
            Path(job_data["file_path"]).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Không thể xóa file: {str(e)}")
    
    # Xóa khỏi storage
    del jobs_storage[job_id]
    
    return {
        "success": True,
        "message": "Đã xóa job thành công",
        "job_id": job_id
    }