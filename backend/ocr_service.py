"""
OCR Service
Xử lý OCR và parsing hóa đơn sử dụng OpenAI GPT-4 Vision API
Hỗ trợ cả OCR từ ảnh và parsing từ text
"""

import base64
import json
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from decimal import Decimal
from datetime import datetime

from openai import OpenAI
from loguru import logger

from backend.config import settings
from backend.invoice import InvoiceData, InvoiceDetailItem, TextInvoiceInput


class OpenAIOCRService:
    """
    Service xử lý OCR và parsing hóa đơn
    Sử dụng OpenAI GPT-4 Vision API
    """
    
    def __init__(self):
        """Khởi tạo OpenAI client"""
        try:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            self.max_tokens = settings.openai_max_tokens
            logger.info(f"✅ Khởi tạo OpenAI client thành công - Model: {self.model}")
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo OpenAI client: {str(e)}")
            raise
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Encode ảnh sang base64 cho OpenAI
        
        Args:
            image_path: Đường dẫn file ảnh
            
        Returns:
            Base64 string với data URI format
        """
        path = Path(image_path)
        extension = path.suffix.lower()
        
        # Map extension -> media type
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_type_map.get(extension, 'image/jpeg')
        
        # Đọc và encode
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_string = base64.b64encode(image_data).decode('utf-8')
        
        # OpenAI format: data:image/jpeg;base64,{base64_string}
        data_uri = f"data:{media_type};base64,{base64_string}"
        
        logger.debug(f"Đã encode ảnh: {image_path} -> {media_type}")
        return data_uri
    
    def _build_ocr_prompt(self, document_type: str = "invoice") -> str:
        """
        Xây dựng prompt cho OpenAI để OCR hóa đơn

        Args:
            document_type: Loại chứng từ

        Returns:
            Prompt string
        """
        return """
Bạn là chuyên gia phân tích hóa đơn Việt Nam. Nhiệm vụ: trích xuất CHÍNH XÁC mọi thông tin từ ảnh hóa đơn.

═══════════════════════════════════════════════
⚠️ NGUYÊN TẮC QUAN TRỌNG:
═══════════════════════════════════════════════
✓ CHỈ trích xuất thông tin THẤY RÕ trong ảnh
✓ Nếu KHÔNG THẤY thông tin → đặt giá trị là null
✓ KHÔNG bịa đặt, KHÔNG đoán, KHÔNG thêm thông tin không có
✓ KIỂM TRA KỸ TỪNG CHỮ SỐ để tránh nhầm lẫn OCR

═══════════════════════════════════════════════
🔢 ĐỌC SỐ CHÍNH XÁC (tránh nhầm lẫn OCR):
═══════════════════════════════════════════════
- Số 0 (không) ≠ chữ O
- Số 1 (một) ≠ chữ I hoặc l
- Số 5 (năm) ≠ chữ S
- Số 8 (tám) ≠ chữ B
- Số 6 (sáu) ≠ số 0
- Số 9 (chín) ≠ số 4
- Số 2 (hai) ≠ chữ Z
✅ KIỂM TRA LẠI TỪNG CHỮ SỐ trong giá tiền và MST

═══════════════════════════════════════════════
🏢 PHÂN BIỆT MÃ SỐ THUẾ:
═══════════════════════════════════════════════
Trong hóa đơn có 2 MST KHÁC NHAU, TUYỆT ĐỐI KHÔNG ĐƯỢC NHẦM:

📌 MST NGƯỜI BÁN (seller_tax_code):
   - Ở PHẦN ĐẦU hóa đơn (header/top)
   - Gần logo, tên công ty phát hành hóa đơn
   - Gần các từ: "Người bán", "Bên bán", "Đơn vị bán hàng"
   - Thường xuất hiện TRƯỚC thông tin người mua

📌 MST NGƯỜI MUA (buyer_tax_code):
   - Ở PHẦN THÂN hóa đơn (body/middle)
   - Dưới thông tin người bán
   - Gần các từ: "Người mua", "Khách hàng", "Bên mua", "Đơn vị mua hàng"
   - Thường xuất hiện SAU thông tin người bán

⚠️ KIỂM TRA: seller_tax_code PHẢI KHÁC buyer_tax_code!

═══════════════════════════════════════════════
💰 ĐỊNH DẠNG SỐ TIỀN:
═══════════════════════════════════════════════
- CHỈ GHI CÁC CHỮ SỐ, không dấu phẩy, chấm, ký tự đơn vị
- "1.000.000đ" → 1000000
- "500,000 VNĐ" → 500000
- "2.500.000,50" → 2500000.5

═══════════════════════════════════════════════
THÔNG TIN CẦN TRÍCH XUẤT:
═══════════════════════════════════════════════

1. THÔNG TIN CHUNG:
   - inv_series: Ký hiệu HĐ (VD: "C24MAA", "AA/24E") → null nếu không có
   - inv_date: Ngày HĐ format "YYYY-MM-DD" → null nếu không có
   - payment_method_name: Hình thức TT → "TM/CK" nếu không thấy

2. THÔNG TIN NGƯỜI BÁN (Ở PHẦN ĐẦU):
   - seller_legal_name: Tên công ty bán → null nếu không thấy
   - seller_tax_code: MST người bán (10-13 số) → null nếu không thấy
   - seller_address: Địa chỉ người bán → null nếu không thấy

3. THÔNG TIN NGƯỜI MUA (Ở PHẦN THÂN):
   - buyer_legal_name: Tên công ty mua → null nếu không thấy
   - buyer_tax_code: MST người mua (10-13 số) → null nếu không thấy
   - buyer_address: Địa chỉ người mua → null nếu không thấy
   - buyer_phone_number: SĐT → null nếu không có
   - buyer_email: Email → null nếu không có

4. CHI TIẾT HÀNG HÓA (items):
   - line_number: STT (1, 2, 3...)
   - item_name: Tên hàng hóa → null nếu không rõ
   - unit_name: Đơn vị tính (Cái, kg...) → null nếu không có
   - quantity: Số lượng (CHỈ SỐ)
   - unit_price: Đơn giá (CHỈ SỐ, bỏ dấu phẩy)
   - amount: Thành tiền (CHỈ SỐ)
   - vat_rate: Thuế suất ("10%", "8%", "5%", "0%", "KCT") → "10%" nếu không rõ
   - vat_amount: Tiền thuế (CHỈ SỐ)

5. TỔNG CỘNG:
   - total_amount_without_vat: Tổng tiền chưa thuế (CHỈ SỐ)
   - total_vat_amount: Tổng tiền thuế (CHỈ SỐ)
   - total_amount: Tổng thanh toán (CHỈ SỐ)
   - total_amount_in_words: Tiền bằng chữ → null nếu không có

═══════════════════════════════════════════════
✅ KIỂM TRA CUỐI CÙNG:
═══════════════════════════════════════════════
- unit_price × quantity = amount (sai lệch nhỏ OK)
- Tổng các amount ≈ total_amount_without_vat
- seller_tax_code ≠ buyer_tax_code
- Tất cả số tiền chỉ chứa chữ số (không có dấu phẩy, chấm, chữ)

═══════════════════════════════════════════════
FORMAT JSON TRẢ VỀ:
═══════════════════════════════════════════════

{
  "seller_legal_name": null,
  "seller_tax_code": null,
  "seller_address": null,
  "inv_series": null,
  "inv_date": null,
  "payment_method_name": "TM/CK",
  "buyer_legal_name": null,
  "buyer_tax_code": null,
  "buyer_address": null,
  "buyer_phone_number": null,
  "buyer_email": null,
  "items": [
    {
      "line_number": 1,
      "item_name": null,
      "unit_name": null,
      "quantity": 0,
      "unit_price": 0,
      "amount": 0,
      "vat_rate": "10%",
      "vat_amount": 0
    }
  ],
  "total_amount_without_vat": 0,
  "total_vat_amount": 0,
  "total_amount": 0,
  "total_amount_in_words": null
}

CHỈ TRẢ VỀ JSON, KHÔNG CÓ TEXT GIẢI THÍCH, KHÔNG CÓ MARKDOWN ```

CHỈ TRẢ VỀ JSON thuần túy, KHÔNG text khác.
"""
    
    def _build_text_parsing_prompt(
        self,
        text_content: str,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Xây dựng prompt cho parsing text

        Args:
            text_content: Nội dung text hóa đơn
            additional_context: Thông tin bổ sung

        Returns:
            Prompt string
        """
        context = f"\n\nBỐI CẢNH BỔ SUNG:\n{additional_context}" if additional_context else ""

        return f"""
Bạn là chuyên gia phân tích hóa đơn Việt Nam. Hãy trích xuất CHÍNH XÁC thông tin từ text hóa đơn dưới đây.{context}

═══════════════════════════════════════════════
NỘI DUNG HÓA ĐƠN:
═══════════════════════════════════════════════
{text_content}

═══════════════════════════════════════════════
NGUYÊN TẮC QUAN TRỌNG:
═══════════════════════════════════════════════
✓ CHỈ trích xuất thông tin CÓ SẴN trong text
✓ Nếu KHÔNG TÌM THẤY thông tin → đặt giá trị là null
✓ KHÔNG bịa đặt, KHÔNG đoán, KHÔNG thêm thông tin không có
✓ Số tiền: Loại bỏ dấu phẩy, chấm phân cách → chỉ giữ số (VD: "30,000,000" → 30000000)
✓ Ngày tháng: Format "YYYY-MM-DD" (VD: 27/01/2024 → "2024-01-27")
✓ MST: Chỉ số, 10-13 chữ số (VD: "MST: 0123456789" → "0123456789")

═══════════════════════════════════════════════
FORMAT JSON CẦN TRẢ VỀ:
═══════════════════════════════════════════════

{{
  "seller_legal_name": null,        // Tên công ty người BÁN (tìm ở đầu hóa đơn)
  "seller_tax_code": null,          // MST người bán (10-13 số)
  "seller_address": null,           // Địa chỉ người bán

  "inv_series": null,               // Ký hiệu HĐ (VD: "C24MAA", "AA/24E")
  "inv_date": null,                 // Ngày HĐ format "YYYY-MM-DD"
  "payment_method_name": "TM/CK",   // Hình thức thanh toán (mặc định "TM/CK" nếu không có)

  "buyer_legal_name": null,         // Tên công ty/khách hàng MUA
  "buyer_tax_code": null,           // MST người mua (10-13 số)
  "buyer_address": null,            // Địa chỉ người mua
  "buyer_phone_number": null,       // SĐT (nếu có)
  "buyer_email": null,              // Email (nếu có)

  "items": [                        // Danh sách hàng hóa/dịch vụ
    {{
      "line_number": 1,             // STT dòng (1, 2, 3...)
      "item_name": "Laptop Dell",   // Tên hàng hóa
      "unit_name": "Cái",           // Đơn vị tính (Cái, Hộp, Cái, kg...)
      "quantity": 2,                // Số lượng (CHỈ SỐ, không có đơn vị)
      "unit_price": 15000000,       // Đơn giá (CHỈ SỐ, bỏ dấu phẩy)
      "amount": 30000000,           // Thành tiền = quantity × unit_price
      "vat_rate": "10%",            // Thuế suất (10%, 8%, 5%, 0%, KCT)
      "vat_amount": 3000000         // Tiền thuế (CHỈ SỐ)
    }}
  ],

  "total_amount_without_vat": 32500000,  // Tổng tiền CHƯA thuế (CHỈ SỐ)
  "total_vat_amount": 3250000,           // Tổng tiền thuế VAT (CHỈ SỐ)
  "total_amount": 35750000,              // Tổng cộng thanh toán (CHỈ SỐ)
  "total_amount_in_words": null,         // Tổng tiền bằng chữ (nếu có)

  "needs_review": false,                 // true nếu thiếu thông tin quan trọng
  "review_notes": null                   // Ghi chú lý do cần review
}}

═══════════════════════════════════════════════
LƯU Ý ĐẶC BIỆT:
═══════════════════════════════════════════════
- Nếu không tìm thấy thông tin → ĐỂ null (KHÔNG để "", KHÔNG để "N/A")
- Số tiền CHỈ là số, KHÔNG có dấu phẩy, chấm, chữ "đ" (VD: 30000000)
- Thuế suất phải có ký hiệu % (VD: "10%", không phải "10")
- Tính toán: amount = quantity × unit_price
- Tính toán: vat_amount = amount × (vat_rate/100)
- Tổng cộng = total_amount_without_vat + total_vat_amount

CHỈ TRẢ VỀ JSON, KHÔNG CÓ TEXT GIẢI THÍCH, KHÔNG CÓ MARKDOWN.
"""
    
    async def process_image_ocr(
        self,
        image_path: str,
        document_type: str = "invoice"
    ) -> Dict[str, Any]:
        """
        Xử lý OCR từ ảnh sử dụng OpenAI GPT-4 Vision
        
        Args:
            image_path: Đường dẫn ảnh
            document_type: Loại chứng từ
            
        Returns:
            Dict kết quả OCR
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Bắt đầu OCR với OpenAI: {image_path}")
            
            # Encode ảnh
            image_data_uri = self._encode_image_to_base64(image_path)
            
            # Build prompt
            prompt = self._build_ocr_prompt(document_type)
            
            # Gọi OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_uri,
                                    "detail": "high"  # high detail for better OCR
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Low temperature for consistent results
            )
            
            # Extract response
            response_text = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            logger.info(f"✅ OCR hoàn thành trong {processing_time:.2f}s")
            logger.debug(f"Response: {response_text[:200]}...")
            
            return {
                "success": True,
                "raw_response": response_text,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ Lỗi OCR: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def process_text_input(
        self,
        text_input: TextInvoiceInput
    ) -> Dict[str, Any]:
        """
        Xử lý parsing từ text sử dụng OpenAI
        
        Args:
            text_input: Text input data
            
        Returns:
            Dict kết quả parsing
        """
        start_time = time.time()
        
        try:
            logger.info("⌨️  Bắt đầu parsing text với OpenAI")
            
            # Build prompt
            prompt = self._build_text_parsing_prompt(
                text_input.invoice_text,
                text_input.additional_context
            )
            
            # Gọi OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1
            )
            
            # Extract response
            response_text = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Parsing hoàn thành trong {processing_time:.2f}s")
            logger.debug(f"Response: {response_text[:200]}...")
            
            return {
                "success": True,
                "raw_response": response_text,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"❌ Lỗi parsing: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        Trích xuất JSON từ OpenAI response
        
        Args:
            response_text: Response text
            
        Returns:
            Dict JSON hoặc None
        """
        try:
            # Remove markdown code blocks nếu có
            text = response_text.strip()
            
            # Remove ```json and ```
            if text.startswith('```'):
                lines = text.split('\n')
                # Remove first line (```json) and last line (```)
                text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
            
            # Tìm JSON object
            start = text.find('{')
            end = text.rfind('}')
            
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                parsed = json.loads(json_str)
                logger.debug(f"✅ Parsed JSON successfully")
                return parsed
            
            logger.warning("⚠️ Không tìm thấy JSON object trong response")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Không parse được JSON: {str(e)}")
            logger.error(f"Raw text: {response_text[:500]}")
            return None
    
    def _validate_and_fix_numbers(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate và sửa các lỗi thường gặp trong số tiền và MST

        Args:
            raw_data: Dữ liệu thô

        Returns:
            Dữ liệu đã được validate và fix
        """
        warnings = []

        # 1. Validate MST (Mã số thuế)
        def clean_tax_code(tax_code):
            """Làm sạch MST - chỉ giữ lại chữ số"""
            if not tax_code:
                return None
            # Remove all non-digit characters
            cleaned = ''.join(c for c in str(tax_code) if c.isdigit())
            if len(cleaned) < 10 or len(cleaned) > 13:
                warnings.append(f"MST không hợp lệ: {tax_code} (độ dài: {len(cleaned)})")
            return cleaned if cleaned else None

        seller_tax = clean_tax_code(raw_data.get("seller_tax_code"))
        buyer_tax = clean_tax_code(raw_data.get("buyer_tax_code"))

        # Kiểm tra MST người bán và người mua PHẢI khác nhau
        if seller_tax and buyer_tax and seller_tax == buyer_tax:
            warnings.append(f"⚠️ MST người bán = MST người mua ({seller_tax}) - CẦN KIỂM TRA!")
            raw_data["needs_review"] = True
            raw_data["review_notes"] = "MST người bán và người mua giống nhau"

        raw_data["seller_tax_code"] = seller_tax
        raw_data["buyer_tax_code"] = buyer_tax

        # 2. Validate số tiền trong items
        for idx, item in enumerate(raw_data.get("items", []), 1):
            try:
                quantity = Decimal(str(item.get("quantity", 0)).replace(",", ""))
                unit_price = Decimal(str(item.get("unit_price", 0)).replace(",", ""))
                amount = Decimal(str(item.get("amount", 0)).replace(",", ""))

                # Kiểm tra: quantity × unit_price = amount
                expected_amount = quantity * unit_price
                if abs(expected_amount - amount) > Decimal("0.01"):
                    warnings.append(f"Item {idx}: {quantity} × {unit_price} ≠ {amount} (expected: {expected_amount})")
                    # Tự động sửa
                    item["amount"] = str(expected_amount)

            except Exception as e:
                warnings.append(f"Item {idx}: Lỗi validate số: {str(e)}")

        # 3. Validate tổng tiền
        try:
            total_without_vat = Decimal(str(raw_data.get("total_amount_without_vat", 0)).replace(",", ""))
            total_vat = Decimal(str(raw_data.get("total_vat_amount", 0)).replace(",", ""))
            total_amount = Decimal(str(raw_data.get("total_amount", 0)).replace(",", ""))

            expected_total = total_without_vat + total_vat
            if abs(expected_total - total_amount) > Decimal("0.01"):
                warnings.append(f"Tổng tiền: {total_without_vat} + {total_vat} ≠ {total_amount}")

        except Exception as e:
            warnings.append(f"Lỗi validate tổng tiền: {str(e)}")

        if warnings:
            logger.warning(f"⚠️ Validation warnings: {'; '.join(warnings)}")

        return raw_data

    def _convert_to_invoice_data(
        self,
        raw_data: Dict[str, Any],
        processing_time: float
    ) -> InvoiceData:
        """
        Convert raw data sang InvoiceData
        
        Args:
            raw_data: Dữ liệu thô từ OpenAI
            processing_time: Thời gian xử lý
            
        Returns:
            InvoiceData object
        """
        # Parse items
        items = []
        for idx, item_data in enumerate(raw_data.get("items", []), start=1):
            try:
                # Safely convert to Decimal
                quantity = Decimal(str(item_data.get("quantity", 0)).replace(",", ""))
                unit_price = Decimal(str(item_data.get("unit_price", 0)).replace(",", ""))
                amount = Decimal(str(item_data.get("amount", 0)).replace(",", ""))
                vat_amount = Decimal(str(item_data.get("vat_amount", 0)).replace(",", ""))
                
                item = InvoiceDetailItem(
                    item_type=1,
                    sort_order=idx,
                    line_number=idx,
                    item_code=item_data.get("item_code"),
                    item_name=item_data.get("item_name", ""),
                    unit_name=item_data.get("unit_name"),
                    quantity=quantity,
                    unit_price=unit_price,
                    amount_oc=amount,
                    amount=amount,
                    discount_rate=Decimal(str(item_data.get("discount_rate", 0))),
                    discount_amount_oc=Decimal(str(item_data.get("discount_amount", 0))),
                    discount_amount=Decimal(str(item_data.get("discount_amount", 0))),
                    amount_without_vat_oc=amount,
                    amount_without_vat=amount,
                    vat_rate_name=item_data.get("vat_rate", "10%"),
                    vat_amount_oc=vat_amount,
                    vat_amount=vat_amount
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi parse item {idx}: {str(e)}")
                continue
        
        # Parse date
        inv_date_str = raw_data.get("inv_date", "")
        try:
            inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d").date()
        except:
            logger.warning(f"⚠️ Không parse được ngày: {inv_date_str}, dùng ngày hiện tại")
            inv_date = datetime.now().date()
        
        # Parse totals
        def safe_decimal(value, default=0):
            try:
                return Decimal(str(value).replace(",", ""))
            except:
                return Decimal(str(default))
        
        total_without_vat = safe_decimal(raw_data.get("total_amount_without_vat", 0))
        total_vat = safe_decimal(raw_data.get("total_vat_amount", 0))
        total_amount = safe_decimal(raw_data.get("total_amount", 0))
        
        # Build InvoiceData
        invoice_data = InvoiceData(
            inv_series=raw_data.get("inv_series", ""),
            inv_date=inv_date,
            payment_method_name=raw_data.get("payment_method_name", "TM/CK"),
            # Thông tin người bán
            seller_legal_name=raw_data.get("seller_legal_name"),
            seller_tax_code=raw_data.get("seller_tax_code"),
            seller_address=raw_data.get("seller_address"),
            # Thông tin người mua
            buyer_legal_name=raw_data.get("buyer_legal_name", ""),
            buyer_tax_code=raw_data.get("buyer_tax_code"),
            buyer_address=raw_data.get("buyer_address", ""),
            buyer_full_name=raw_data.get("buyer_full_name"),
            buyer_phone_number=raw_data.get("buyer_phone_number"),
            buyer_email=raw_data.get("buyer_email"),
            # Tổng tiền
            total_sale_amount_oc=total_without_vat,
            total_sale_amount=total_without_vat,
            total_amount_without_vat_oc=total_without_vat,
            total_amount_without_vat=total_without_vat,
            total_vat_amount_oc=total_vat,
            total_vat_amount=total_vat,
            total_amount_oc=total_amount,
            total_amount=total_amount,
            total_amount_in_words=raw_data.get("total_amount_in_words"),
            original_invoice_detail=items,
            processing_time=processing_time,
            needs_review=raw_data.get("needs_review", False),
            review_notes=raw_data.get("review_notes")
        )
        
        logger.info(f"✅ Converted to InvoiceData: {len(items)} items")
        return invoice_data


# ===== Singleton Instance =====
openai_ocr_service = OpenAIOCRService()