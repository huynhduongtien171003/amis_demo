"""
API endpoints cho export dữ liệu
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from backend.invoice import ExportRequest, ExportResponse
from backend.export_service import amis_export_service


# Router
router = APIRouter(prefix="/api/export", tags=["Export"])

# Import jobs_storage từ ocr_routes
from backend.ocr_routes import jobs_storage


@router.post("/amis/{job_id}", response_model=ExportResponse)
async def export_to_amis(job_id: str, export_request: ExportRequest):
    """
    Export dữ liệu hóa đơn sang định dạng AMIS
    
    - **job_id**: ID của job
    - **export_format**: Định dạng export (excel, json, xml)
    - **template_type**: Loại template AMIS
    """
    try:
        # Kiểm tra job tồn tại
        if job_id not in jobs_storage:
            raise HTTPException(status_code=404, detail="Job không tồn tại")
        
        job_data = jobs_storage[job_id]
        invoice_data = job_data.get("invoice_data")
        
        if not invoice_data:
            raise HTTPException(status_code=400, detail="Job chưa có dữ liệu hóa đơn")
        
        # Export theo format
        if export_request.export_format == "excel":
            file_path = amis_export_service.export_to_excel(
                invoice_data,
                job_id,
                export_request.template_type
            )
        elif export_request.export_format == "json":
            file_path = amis_export_service.export_to_json(invoice_data, job_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Format {export_request.export_format} chưa được hỗ trợ"
            )
        
        # Tạo download URL (giả định)
        from pathlib import Path
        filename = Path(file_path).name
        download_url = f"/api/export/download/{filename}"
        
        return ExportResponse(
            success=True,
            download_url=download_url,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi khi export: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download file đã export
    
    - **filename**: Tên file cần download
    """
    from pathlib import Path
    from backend.config import settings
    
    file_path = Path(settings.output_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/octet-stream'
    )