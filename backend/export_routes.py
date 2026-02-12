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


# ==================== ORDER EXPORT ENDPOINTS ====================

@router.post("/order/{job_id}/json")
async def export_order_to_json(job_id: str):
    """
    Export dữ liệu đơn hàng ra file JSON

    - **job_id**: ID của job cần export
    
    Returns:
        File JSON để download
    """
    try:
        # Import order_jobs_storage
        from backend.order_routes import order_jobs_storage
        
        # Kiểm tra job tồn tại
        if job_id not in order_jobs_storage:
            raise HTTPException(status_code=404, detail="Job không tồn tại")
        
        job_data = order_jobs_storage[job_id]
        order_data = job_data.get("order_data")
        
        if not order_data:
            raise HTTPException(status_code=400, detail="Job chưa có dữ liệu đơn hàng")
        
        # Export JSON
        file_path = amis_export_service.export_order_to_json(order_data, job_id)
        
        # Return file
        from pathlib import Path
        filename = Path(file_path).name
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/json'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi export order JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order/{job_id}/excel")
async def export_order_to_excel(job_id: str):
    """
    Export dữ liệu đơn hàng ra file Excel

    - **job_id**: ID của job cần export
    
    Returns:
        File Excel để download với 3 sheets:
        - Order Information: Thông tin đơn hàng
        - Order Items: Chi tiết sản phẩm
        - Metadata: Thông tin xử lý
    """
    try:
        # Import order_jobs_storage
        from backend.order_routes import order_jobs_storage
        
        # Kiểm tra job tồn tại
        if job_id not in order_jobs_storage:
            raise HTTPException(status_code=404, detail="Job không tồn tại")
        
        job_data = order_jobs_storage[job_id]
        order_data = job_data.get("order_data")
        
        if not order_data:
            raise HTTPException(status_code=400, detail="Job chưa có dữ liệu đơn hàng")
        
        # Export Excel
        file_path = amis_export_service.export_order_to_excel(order_data, job_id)
        
        # Return file
        from pathlib import Path
        filename = Path(file_path).name
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi export order Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/order/{job_id}/both")
async def export_order_both_formats(job_id: str):
    """
    Export dữ liệu đơn hàng ra cả JSON và Excel

    - **job_id**: ID của job cần export
    
    Returns:
        URLs để download cả 2 files
    """
    try:
        # Import order_jobs_storage
        from backend.order_routes import order_jobs_storage
        
        # Kiểm tra job tồn tại
        if job_id not in order_jobs_storage:
            raise HTTPException(status_code=404, detail="Job không tồn tại")
        
        job_data = order_jobs_storage[job_id]
        order_data = job_data.get("order_data")
        
        if not order_data:
            raise HTTPException(status_code=400, detail="Job chưa có dữ liệu đơn hàng")
        
        # Export cả 2 formats
        json_path = amis_export_service.export_order_to_json(order_data, job_id)
        excel_path = amis_export_service.export_order_to_excel(order_data, job_id)
        
        # Tạo response
        from pathlib import Path
        json_filename = Path(json_path).name
        excel_filename = Path(excel_path).name
        
        return {
            "success": True,
            "files": {
                "json": {
                    "filename": json_filename,
                    "download_url": f"/api/export/download/{json_filename}"
                },
                "excel": {
                    "filename": excel_filename,
                    "download_url": f"/api/export/download/{excel_filename}"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Lỗi export order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))