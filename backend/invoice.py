"""
Pydantic schemas cho dữ liệu hóa đơn AMIS
Định nghĩa cấu trúc dữ liệu input/output
"""

from typing import List, Optional, Literal
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class InvoiceDetailItem(BaseModel):
    """Chi tiết dòng hàng hóa/dịch vụ trong hóa đơn"""
    
    item_type: int = Field(default=1, description="Loại hàng hóa: 1=Thường, 2=Khuyến mại")
    sort_order: Optional[int] = Field(None, description="STT dòng hàng")
    line_number: int = Field(default=1, description="Vị trí dòng hàng (bắt đầu từ 1)")
    
    # Thông tin hàng hóa
    item_code: Optional[str] = Field(None, description="Mã hàng hóa")
    item_name: Optional[str] = Field(None, description="Tên hàng hóa/dịch vụ")
    unit_name: Optional[str] = Field(None, description="Đơn vị tính")

    # Thông tin giá
    quantity: Decimal = Field(default=Decimal('0'), description="Số lượng")
    unit_price: Decimal = Field(default=Decimal('0'), description="Đơn giá")
    amount_oc: Decimal = Field(default=Decimal('0'), description="Thành tiền trước thuế, trước CK")
    amount: Decimal = Field(default=Decimal('0'), description="Thành tiền quy đổi")
    
    # Chiết khấu
    discount_rate: Decimal = Field(default=Decimal('0'), description="Tỷ lệ chiết khấu (%)")
    discount_amount_oc: Decimal = Field(default=Decimal('0'), description="Tiền chiết khấu")
    discount_amount: Decimal = Field(default=Decimal('0'), description="Tiền chiết khấu quy đổi")
    
    # Tiền sau chiết khấu
    amount_without_vat_oc: Decimal = Field(default=Decimal('0'), description="Thành tiền sau CK - nguyên tệ")
    amount_without_vat: Decimal = Field(default=Decimal('0'), description="Thành tiền sau CK - quy đổi")

    # Thuế VAT
    vat_rate_name: Optional[str] = Field(default="10%", description="Thuế suất: KCT, 0%, 5%, 8%, 10%, KHAC:x%")
    vat_amount_oc: Decimal = Field(default=Decimal('0'), description="Tiền thuế - nguyên tệ")
    vat_amount: Decimal = Field(default=Decimal('0'), description="Tiền thuế - quy đổi")
    
    # Các trường bổ sung
    confidence: Optional[float] = Field(None, description="Độ tin cậy của OCR (0-1)")
    needs_review: bool = Field(default=False, description="Cần review thủ công")


class TaxRateInfo(BaseModel):
    """Thông tin tổng hợp theo thuế suất"""

    vat_rate_name: str = Field(default="10%", description="Thuế suất: KCT, 0%, 5%, 8%, 10%, KHAC:x%")
    amount_without_vat_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền trước thuế")
    vat_amount_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền thuế")


class InvoiceData(BaseModel):
    """
    Dữ liệu hóa đơn AMIS đầy đủ
    Mapping với cấu trúc InvoiceData của AMIS API
    """
    
    # ===== Dữ liệu chung =====
    ref_id: Optional[str] = Field(None, description="Mã tham chiếu (GUID)")
    inv_series: Optional[str] = Field(None, description="Ký hiệu hóa đơn (VD: C24MAA)")
    inv_date: Optional[date] = Field(None, description="Ngày phát hành hóa đơn")
    currency_code: str = Field(default="VND", description="Mã tiền tệ")
    exchange_rate: Decimal = Field(default=Decimal('1'), description="Tỷ giá")
    payment_method_name: Optional[str] = Field(default="TM/CK", description="Hình thức thanh toán")

    # ===== Thông tin người bán =====
    seller_legal_name: Optional[str] = Field(None, description="Tên đơn vị người bán")
    seller_tax_code: Optional[str] = Field(None, description="Mã số thuế người bán")
    seller_address: Optional[str] = Field(None, description="Địa chỉ người bán")

    # ===== Thông tin người mua =====
    buyer_code: Optional[str] = Field(None, description="Mã người mua")
    buyer_legal_name: Optional[str] = Field(None, description="Tên đơn vị người mua")
    buyer_tax_code: Optional[str] = Field(None, description="Mã số thuế người mua")
    buyer_address: Optional[str] = Field(None, description="Địa chỉ người mua")
    buyer_full_name: Optional[str] = Field(None, description="Họ tên người mua")
    buyer_phone_number: Optional[str] = Field(None, description="Số điện thoại")
    buyer_email: Optional[str] = Field(None, description="Email người mua")
    
    # ===== Tổng tiền =====
    total_sale_amount_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền bán hàng chưa thuế")
    total_sale_amount: Decimal = Field(default=Decimal('0'), description="Tổng tiền bán hàng quy đổi")
    total_discount_amount_oc: Decimal = Field(default=Decimal('0'), description="Tổng chiết khấu")
    total_discount_amount: Decimal = Field(default=Decimal('0'), description="Tổng CK quy đổi")
    total_amount_without_vat_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền chưa thuế")
    total_amount_without_vat: Decimal = Field(default=Decimal('0'), description="Tổng tiền chưa thuế QĐ")
    total_vat_amount_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền thuế")
    total_vat_amount: Decimal = Field(default=Decimal('0'), description="Tổng tiền thuế quy đổi")
    total_amount_oc: Decimal = Field(default=Decimal('0'), description="Tổng tiền thanh toán")
    total_amount: Decimal = Field(default=Decimal('0'), description="Tổng tiền thanh toán quy đổi")
    total_amount_in_words: Optional[str] = Field(None, description="Tổng tiền bằng chữ")
    
    # ===== Danh sách hàng hóa =====
    original_invoice_detail: List[InvoiceDetailItem] = Field(
        default_factory=list,
        description="Danh sách hàng hóa/dịch vụ"
    )
    
    # ===== Tổng hợp thuế suất =====
    tax_rate_info: List[TaxRateInfo] = Field(
        default_factory=list,
        description="Danh sách tổng hợp thuế suất"
    )
    
    # ===== Metadata từ OCR =====
    ocr_confidence: Optional[float] = Field(None, description="Độ tin cậy tổng thể của OCR")
    processing_time: Optional[float] = Field(None, description="Thời gian xử lý (giây)")
    needs_review: bool = Field(default=False, description="Cần review thủ công không")
    review_notes: Optional[str] = Field(None, description="Ghi chú cần review")


class TextInvoiceInput(BaseModel):
    """
    Schema cho input nhập text thủ công
    Người dùng có thể nhập text của hóa đơn thay vì upload ảnh
    """
    
    invoice_text: str = Field(..., description="Nội dung text của hóa đơn")
    document_type: Literal["invoice", "receipt", "delivery_note"] = Field(
        default="invoice",
        description="Loại chứng từ"
    )
    additional_context: Optional[str] = Field(
        None,
        description="Thông tin bổ sung (VD: đây là hóa đơn VAT, công ty ABC...)"
    )


class OCRRequest(BaseModel):
    """
    Request cho API OCR
    Hỗ trợ cả upload file và nhập text
    """
    
    # Có thể là file upload hoặc text input
    input_type: Literal["file", "text"] = Field(..., description="Loại input: file hoặc text")
    
    # Cho text input
    text_data: Optional[TextInvoiceInput] = Field(None, description="Dữ liệu text (nếu input_type=text)")
    
    # Các options chung
    document_type: Literal["invoice", "receipt", "delivery_note", "auto"] = Field(
        default="auto",
        description="Loại chứng từ (auto để tự động phát hiện)"
    )
    language: Literal["vi", "en"] = Field(default="vi", description="Ngôn ngữ")
    auto_map_amis: bool = Field(default=True, description="Tự động map sang cấu trúc AMIS")
    confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Ngưỡng confidence (0-1)"
    )


class OCRResponse(BaseModel):
    """Response từ API OCR"""
    
    success: bool = Field(..., description="Trạng thái xử lý")
    job_id: str = Field(..., description="ID của job xử lý")
    status: Literal["processing", "completed", "failed"] = Field(..., description="Trạng thái")
    
    # Dữ liệu đã trích xuất
    data: Optional[InvoiceData] = Field(None, description="Dữ liệu hóa đơn")
    
    # Metadata
    processing_time: Optional[float] = Field(None, description="Thời gian xử lý (giây)")
    error_message: Optional[str] = Field(None, description="Thông báo lỗi (nếu có)")
    
    # Raw data từ Claude (để debug)
    raw_claude_response: Optional[str] = Field(None, description="Response gốc từ Claude")


class InvoiceUpdateRequest(BaseModel):
    """Request để update dữ liệu đã chỉnh sửa"""
    
    job_id: str = Field(..., description="ID của job")
    updated_data: InvoiceData = Field(..., description="Dữ liệu đã chỉnh sửa")
    notes: Optional[str] = Field(None, description="Ghi chú về các thay đổi")


class ExportRequest(BaseModel):
    """Request để export dữ liệu sang định dạng AMIS"""
    
    job_id: str = Field(..., description="ID của job")
    export_format: Literal["excel", "xml", "json"] = Field(
        default="excel",
        description="Định dạng export"
    )
    template_type: Literal["purchase_invoice", "sales_invoice", "general"] = Field(
        default="general",
        description="Loại template AMIS"
    )


class ExportResponse(BaseModel):
    """Response cho export"""
    
    success: bool = Field(..., description="Trạng thái export")
    download_url: Optional[str] = Field(None, description="URL download file")
    filename: str = Field(..., description="Tên file")
    expires_at: Optional[datetime] = Field(None, description="Thời gian hết hạn link")