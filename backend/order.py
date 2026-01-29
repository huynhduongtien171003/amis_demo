"""
Pydantic schemas cho dữ liệu đơn đặt hàng
Định nghĩa cấu trúc dữ liệu input/output cho Order Recognition System
"""

from typing import List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class OrderItemData(BaseModel):
    """Chi tiết sản phẩm trong đơn hàng"""

    line_number: int = Field(description="Số thứ tự dòng sản phẩm")
    product_name: str = Field(description="Tên sản phẩm")
    quantity: Decimal = Field(default=Decimal('0'), description="Số lượng")
    unit_price: Optional[Decimal] = Field(None, description="Đơn giá")
    total_price: Optional[Decimal] = Field(None, description="Thành tiền")
    notes: Optional[str] = Field(None, description="Ghi chú cho sản phẩm")


class OrderData(BaseModel):
    """
    Dữ liệu đơn đặt hàng từ tin nhắn/email KHÁCH HÀNG

    Công cụ dành cho NGƯỜI BÁN/SHOP để nhận diện thông tin KHÁCH HÀNG
    từ tin nhắn đặt hàng (Zalo, Messenger, Email, SMS, etc.)

    Trích xuất từ text hoặc ảnh screenshot tin nhắn
    """

    # ===== Thông tin khách hàng =====
    customer_type: Optional[str] = Field(None, description="Loại khách hàng: 'individual' (cá nhân) hoặc 'business' (doanh nghiệp/hộ kinh doanh)")
    customer_name: Optional[str] = Field(None, description="Tên khách hàng cá nhân")
    business_name: Optional[str] = Field(None, description="Tên công ty/hộ kinh doanh (nếu là doanh nghiệp)")
    customer_tax_code: Optional[str] = Field(None, description="Mã số thuế (MST) của khách hàng/doanh nghiệp")
    customer_phone: Optional[str] = Field(None, description="Số điện thoại liên hệ")
    customer_address: Optional[str] = Field(None, description="Địa chỉ giao hàng (địa chỉ nhận sản phẩm)")
    business_address: Optional[str] = Field(None, description="Địa chỉ trụ sở công ty/hộ kinh doanh (nếu khác địa chỉ giao hàng)")
    customer_email: Optional[str] = Field(None, description="Email khách hàng")

    # ===== Thông tin đơn hàng =====
    order_id: Optional[str] = Field(None, description="Mã đơn hàng")
    order_date: Optional[date] = Field(None, description="Ngày đặt hàng")
    payment_method: Optional[str] = Field(None, description="Phương thức thanh toán (COD, Chuyển khoản...)")
    notes: Optional[str] = Field(None, description="Ghi chú đơn hàng")

    # ===== Danh sách sản phẩm =====
    items: List[OrderItemData] = Field(
        default_factory=list,
        description="Danh sách sản phẩm trong đơn hàng"
    )

    # ===== Tổng tiền =====
    total_amount: Optional[Decimal] = Field(None, description="Tổng thanh toán")

    # ===== Metadata =====
    processing_time: Optional[float] = Field(None, description="Thời gian xử lý (giây)")
    needs_review: bool = Field(default=False, description="Cần review thủ công")
    review_notes: Optional[str] = Field(None, description="Ghi chú review")
    noise_detected: List[str] = Field(
        default_factory=list,
        description="Danh sách thông tin nhiễu đã phát hiện và bỏ qua"
    )


class TextOrderInput(BaseModel):
    """Input text từ tin nhắn chat"""

    message_text: str = Field(description="Nội dung text tin nhắn")
    additional_context: Optional[str] = Field(None, description="Thông tin bổ sung từ user")


class OrderRequest(BaseModel):
    """Request nhận diện đơn hàng"""

    input_type: str = Field(description="Loại input: 'file' hoặc 'text'")
    text_data: Optional[TextOrderInput] = Field(None, description="Dữ liệu text nếu input_type='text'")


class OrderResponse(BaseModel):
    """Response trả về từ API"""

    success: bool = Field(description="Trạng thái xử lý thành công hay không")
    job_id: Optional[str] = Field(None, description="ID công việc để tra cứu sau")
    status: str = Field(description="Trạng thái: 'completed', 'processing', 'error'")
    data: Optional[OrderData] = Field(None, description="Dữ liệu đơn hàng đã trích xuất")
    processing_time: float = Field(description="Thời gian xử lý (giây)")
    error_message: Optional[str] = Field(None, description="Thông báo lỗi nếu có")
    raw_response: Optional[str] = Field(None, description="Response gốc từ AI (for debugging)")


class OrderUpdateRequest(BaseModel):
    """Request cập nhật đơn hàng sau khi user chỉnh sửa"""

    job_id: str = Field(description="ID công việc cần cập nhật")
    updated_data: OrderData = Field(description="Dữ liệu đã được chỉnh sửa")
    update_notes: Optional[str] = Field(None, description="Ghi chú về việc cập nhật")
