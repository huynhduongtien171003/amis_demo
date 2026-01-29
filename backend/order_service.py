"""
Order Recognition Service - Công cụ nhận diện thông tin KHÁCH HÀNG cho NGƯỜI BÁN

Giúp người bán/shop tự động trích xuất thông tin khách hàng từ tin nhắn đặt hàng
- Sử dụng OpenAI GPT-4 Vision API
- Hỗ trợ cả OCR từ ảnh screenshot và parsing từ text tin nhắn
- Tự động lọc nhiễu (lời chào, emoji, câu hỏi không liên quan)
- CHỈ trích xuất thông tin KHÁCH HÀNG, KHÔNG trích xuất thông tin người bán
"""

import base64
import json
import time
import re
from typing import Optional, Dict, Any, List
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date

from openai import OpenAI
from loguru import logger

from backend.config import settings
from backend.order import OrderData, OrderItemData, TextOrderInput


class OrderRecognitionService:
    """
    Service nhận diện thông tin KHÁCH HÀNG từ tin nhắn/email đặt hàng

    Công cụ cho NGƯỜI BÁN/SHOP:
    - Tự động trích xuất thông tin khách hàng (tên, SĐT, địa chỉ)
    - Nhận diện sản phẩm, số lượng, giá từ tin nhắn
    - Lọc nhiễu tự động (lời chào, emoji, câu hỏi)
    - Sử dụng OpenAI GPT-4 Vision API để xử lý cả ảnh và text
    """

    def __init__(self):
        """Khởi tạo OpenAI client"""
        try:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            self.max_tokens = settings.openai_max_tokens
            logger.info(f"✅ Khởi tạo Order Recognition Service - Model: {self.model}")
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

    def _build_order_extraction_prompt_from_image(self) -> str:
        """
        Xây dựng prompt cho OpenAI Vision để trích xuất đơn hàng từ ảnh screenshot

        Returns:
            Prompt string
        """
        return """
BẠN LÀ CHUYÊN GIA NHẬN DIỆN ĐƠN ĐẶT HÀNG TỪ TIN NHẮN/EMAIL
CÔNG CỤ NÀY DÀNH CHO NGƯỜI BÁN/SHOP để nhận diện thông tin KHÁCH HÀNG từ tin nhắn đặt hàng

NHIỆM VỤ: Trích xuất thông tin KHÁCH HÀNG và đơn đặt hàng từ ảnh tin nhắn, BỎ QUA thông tin nhiễu

⚠️ QUAN TRỌNG: CHỈ trích xuất thông tin KHÁCH HÀNG (người đặt hàng), KHÔNG trích xuất thông tin người bán/shop

═══════════════════════════════════════════════
⚠️ XỬ LÝ NHIỄU - CỰC KỲ QUAN TRỌNG:
═══════════════════════════════════════════════
Tin nhắn có thể chứa nhiều thông tin KHÔNG LIÊN QUAN:

❌ BỎ QUA các thông tin này:
   - Lời chào hỏi: "Chào anh", "Hi em", "Hello", "Xin chào", "Chào shop"
   - Câu hỏi: "Có hàng không?", "Bao giờ ship?", "Còn hàng không?"
   - Emoji/sticker: 😊, 👍, ❤️, 🙏, 😀
   - Lời cảm ơn: "Cảm ơn", "Thank you", "Thanks"
   - Tin nhắn thăm hỏi: "Hôm nay thế nào?", "Khỏe không?"
   - UI elements: Tên app, thời gian tin nhắn, nút bấm

✅ CHỈ TRÍCH XUẤT thông tin liên quan đến đơn hàng:
   - Thông tin người đặt: Tên, số điện thoại, địa chỉ giao hàng, email
   - Danh sách sản phẩm: Tên sản phẩm, số lượng, giá (nếu có)
   - Thông tin đơn: Mã đơn, ngày đặt, phương thức thanh toán, ghi chú

═══════════════════════════════════════════════
🔍 PATTERN NHẬN DIỆN THÔNG TIN QUAN TRỌNG:
═══════════════════════════════════════════════

📌 LOẠI KHÁCH HÀNG (customer_type):
   - "individual" nếu là cá nhân
   - "business" nếu là công ty/hộ kinh doanh/doanh nghiệp

📌 TÊN KHÁCH HÀNG (customer_name):
   Pattern cá nhân:
   - "Tên: Nguyễn Văn A"
   - "Họ tên: ..."
   - "Người nhận: ..."
   - "Anh/Chị/Em: ..."

📌 TÊN DOANH NGHIỆP (business_name):
   Pattern doanh nghiệp:
   - "Công ty: ABC Corp"
   - "Công ty TNHH ..."
   - "Hộ kinh doanh: ..."
   - "Cửa hàng: ..."
   - "Shop: ..."

📌 MÃ SỐ THUẾ (customer_tax_code):
   Pattern thường gặp:
   - "MST: 0123456789"
   - "Mã số thuế: ..."
   - "Tax code: ..."
   - Dãy 10-13 chữ số

   Chỉ trích xuất nếu khách hàng cung cấp (thường là doanh nghiệp)

📌 SỐ ĐIỆN THOẠI (customer_phone):
   Pattern thường gặp:
   - "SĐT: 0901234567"
   - "Điện thoại: 090.123.4567"
   - "Liên hệ: 090-123-4567"
   - "Phone: 0901234567"
   - Dãy số 10-11 chữ số bắt đầu bằng 0

   Format chuẩn: Chỉ giữ số, bỏ dấu chấm/gạch ngang

📌 ĐỊA CHỈ GIAO HÀNG (customer_address):
   Pattern thường gặp:
   - "Địa chỉ: ..."
   - "Giao hàng: ..."
   - "Địa chỉ nhận hàng: ..."
   - "Ship về: ..."
   - "Giao tới: ..."
   - "Nhận hàng tại: ..."
   - "Gửi về: ..."

   ⚠️ QUAN TRỌNG: Đây là địa chỉ NHẬN HÀNG, không phải địa chỉ công ty
   Đặc điểm: Thường dài, có số nhà, tên đường, phường/xã, quận/huyện, tỉnh/thành phố

📌 ĐỊA CHỈ CÔNG TY/TRỤ SỞ (business_address):
   CHỈ trích xuất nếu khách hàng là DOANH NGHIỆP và cung cấp địa chỉ công ty riêng
   Pattern thường gặp:
   - "Địa chỉ công ty: ..."
   - "Trụ sở: ..."
   - "Văn phòng: ..."
   - "Địa chỉ kinh doanh: ..."

   ⚠️ Nếu chỉ có MỘT địa chỉ → đặt vào customer_address (ưu tiên địa chỉ giao hàng)
   ⚠️ Nếu có HAI địa chỉ khác nhau → phân biệt địa chỉ giao hàng vs địa chỉ công ty

📌 EMAIL (customer_email):
   Pattern: xxx@yyy.zzz
   - "Email: example@gmail.com"
   - "Mail: ..."

📌 SẢN PHẨM (items):
   Pattern thường gặp:
   - "1. Laptop Dell XPS - 2 cái"
   - "Áo thun trắng x 5"
   - "- Điện thoại iPhone 15 (1 cái) - 20tr"
   - "Laptop Dell x2 - 25 triệu/cái"
   - "2 cái laptop"

   Cấu trúc: [STT/Bullet] [Tên sản phẩm] [số lượng] [giá - optional]

   Số lượng có thể là:
   - "2 cái", "x 2", "×2", "(2)", "- 2"
   - "5 chiếc", "10 kg"

📌 MÃ ĐƠN HÀNG (order_id):
   Pattern: "Mã đơn:", "Order ID:", "ĐH123456"

📌 NGÀY ĐẶT (order_date):
   Pattern: DD/MM/YYYY, DD-MM-YYYY
   Chuyển sang format: YYYY-MM-DD

📌 THANH TOÁN (payment_method):
   Pattern: "COD", "Chuyển khoản", "Tiền mặt", "ATM", "Ship COD"

═══════════════════════════════════════════════
🧹 LỌC NHIỄU - DANH SÁCH ĐẦY ĐỦ:
═══════════════════════════════════════════════

❌ KHÔNG TRÍCH XUẤT các cụm từ này:
   - "Chào anh/chị/em/shop/bạn"
   - "Hi", "Hello", "Xin chào"
   - "Cảm ơn", "Thank you", "Thanks"
   - "Dạ", "Vâng", "Ạ", "Ơi"
   - Emoji đơn lẻ: 😊, 👍, ❤️, 🙏
   - "Shop có hàng không?"
   - "Khi nào giao được?"
   - "Còn hàng không?"
   - "Hôm nay thế nào?"
   - "Bao nhiêu tiền?"
   - Timestamp: "10:30 AM", "Hôm qua"
   - Tên app: "Zalo", "Messenger"

✅ LƯU TRỮ NHIỄU vào noise_detected array để report lại cho user

═══════════════════════════════════════════════
💰 XỬ LÝ GIÁ TIỀN:
═══════════════════════════════════════════════

Các format giá tiền thường gặp:
- "20 triệu" → 20000000
- "20tr" → 20000000
- "20 tr" → 20000000
- "2.5 triệu" → 2500000
- "500k" → 500000
- "500 nghìn" → 500000
- "1.000.000đ" → 1000000
- "1,000,000 VNĐ" → 1000000

CHỈ GHI SỐ THUẦN TÚY, bỏ dấu phẩy, chấm, ký tự đơn vị

═══════════════════════════════════════════════
FORMAT JSON TRẢ VỀ:
═══════════════════════════════════════════════

{
  "customer_type": "individual",
  "customer_name": "Nguyễn Văn A",
  "business_name": null,
  "customer_tax_code": null,
  "customer_phone": "0901234567",
  "customer_address": "123 Nguyễn Huệ, Quận 1, TP.HCM",
  "business_address": null,
  "customer_email": null,

  "order_id": null,
  "order_date": "2024-01-27",
  "payment_method": "COD",
  "notes": null,

  "items": [
    {
      "line_number": 1,
      "product_name": "Laptop Dell XPS 13",
      "quantity": 2,
      "unit_price": 25000000,
      "total_price": 50000000,
      "notes": null
    },
    {
      "line_number": 2,
      "product_name": "Chuột Logitech",
      "quantity": 1,
      "unit_price": 500000,
      "total_price": 500000,
      "notes": null
    }
  ],

  "total_amount": 50500000,
  "needs_review": false,
  "review_notes": null,
  "noise_detected": ["Chào shop!", "Có hàng không?", "😊"]
}

═══════════════════════════════════════════════
⚠️ QUAN TRỌNG:
═══════════════════════════════════════════════

1. Nếu KHÔNG THẤY thông tin → đặt là null
2. KHÔNG bịa đặt, KHÔNG đoán
3. Lưu tất cả thông tin nhiễu vào noise_detected
4. Nếu thiếu thông tin quan trọng → đặt needs_review = true
5. CHỈ TRẢ VỀ JSON, KHÔNG TEXT KHÁC

CHỈ TRẢ VỀ JSON, KHÔNG CÓ TEXT GIẢI THÍCH, KHÔNG CÓ MARKDOWN.
"""

    def _build_order_extraction_prompt_from_text(self, text_content: str, additional_context: Optional[str] = None) -> str:
        """
        Xây dựng prompt cho text parsing

        Args:
            text_content: Nội dung text tin nhắn
            additional_context: Thông tin bổ sung từ user

        Returns:
            Prompt string
        """
        context_str = f"\n\nTHÔNG TIN BỔ SUNG TỪ USER:\n{additional_context}" if additional_context else ""

        return f"""
BẠN LÀ CHUYÊN GIA NHẬN DIỆN ĐƠN ĐẶT HÀNG TỪ TIN NHẮN
CÔNG CỤ NÀY DÀNH CHO NGƯỜI BÁN/SHOP để nhận diện thông tin KHÁCH HÀNG từ tin nhắn đặt hàng

NHIỆM VỤ: Trích xuất thông tin KHÁCH HÀNG và đơn đặt hàng từ text dưới đây, BỎ QUA thông tin nhiễu

⚠️ QUAN TRỌNG: CHỈ trích xuất thông tin KHÁCH HÀNG (người đặt hàng), KHÔNG trích xuất thông tin người bán/shop

═══════════════════════════════════════════════
TEXT TIN NHẮN:
═══════════════════════════════════════════════

{text_content}

{context_str}

═══════════════════════════════════════════════
HƯỚNG DẪN XỬ LÝ:
═══════════════════════════════════════════════

1. ĐỌC KỸ text trên và PHÂN BIỆT:
   ✅ Thông tin đơn hàng (tên, SĐT, địa chỉ, sản phẩm, số lượng, giá)
   ❌ Thông tin nhiễu (lời chào, câu hỏi, emoji, sticker text)

2. TRÍCH XUẤT:
   - customer_type: "individual" (cá nhân) hoặc "business" (doanh nghiệp)
   - customer_name: Tên người đặt (nếu là cá nhân) hoặc người liên hệ (nếu là doanh nghiệp)
   - business_name: Tên công ty/hộ kinh doanh (CHỈ nếu là doanh nghiệp)
   - customer_tax_code: Mã số thuế (nếu có)
   - customer_phone: Số điện thoại (10-11 số)
   - customer_address: Địa chỉ GIAO HÀNG (địa chỉ nhận sản phẩm)
   - business_address: Địa chỉ công ty/trụ sở (CHỈ nếu khác địa chỉ giao hàng)
   - customer_email: Email (nếu có)
   - order_id: Mã đơn hàng (nếu có)
   - order_date: Ngày đặt (format YYYY-MM-DD)
   - payment_method: COD/Chuyển khoản/Tiền mặt
   - items: Danh sách sản phẩm với quantity, price

3. LƯU NHIỄU vào noise_detected array

4. Nếu thiếu thông tin quan trọng → needs_review = true

═══════════════════════════════════════════════
FORMAT JSON TRẢ VỀ:
═══════════════════════════════════════════════

{{
  "customer_type": null,
  "customer_name": null,
  "business_name": null,
  "customer_tax_code": null,
  "customer_phone": null,
  "customer_address": null,
  "business_address": null,
  "customer_email": null,
  "order_id": null,
  "order_date": null,
  "payment_method": null,
  "notes": null,
  "items": [],
  "total_amount": null,
  "needs_review": false,
  "review_notes": null,
  "noise_detected": []
}}

CHỈ TRẢ VỀ JSON, KHÔNG TEXT KHÁC.
"""

    async def process_image_order(self, image_path: str) -> Dict[str, Any]:
        """
        Nhận diện đơn hàng từ ảnh screenshot tin nhắn

        Args:
            image_path: Đường dẫn ảnh

        Returns:
            Dict kết quả nhận diện
        """
        start_time = time.time()

        try:
            logger.info(f"🔍 Bắt đầu nhận diện đơn hàng từ ảnh: {image_path}")

            # Encode ảnh
            image_data_uri = self._encode_image_to_base64(image_path)

            # Build prompt
            prompt = self._build_order_extraction_prompt_from_image()

            # Gọi OpenAI Vision API
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
                                    "detail": "high"  # High detail cho OCR tốt hơn
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.1  # Low temperature cho kết quả nhất quán
            )

            # Extract response
            response_text = response.choices[0].message.content
            processing_time = time.time() - start_time

            logger.info(f"✅ Nhận diện hoàn thành trong {processing_time:.2f}s")
            logger.debug(f"Response: {response_text[:200]}...")

            # Parse JSON
            parsed_data = self._extract_json_from_response(response_text)

            if not parsed_data:
                return {
                    "success": False,
                    "error": "Không parse được JSON từ response",
                    "raw_response": response_text,
                    "processing_time": processing_time
                }

            # Validate và fix
            validated_data = self._validate_order_data(parsed_data)

            # Convert to OrderData
            order_data = self._convert_to_order_data(validated_data, processing_time)

            return {
                "success": True,
                "data": order_data,
                "raw_response": response_text,
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(f"❌ Lỗi nhận diện đơn hàng: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time
            }

    async def process_text_order(self, text_input: TextOrderInput) -> Dict[str, Any]:
        """
        Nhận diện đơn hàng từ text tin nhắn

        Args:
            text_input: Text input data

        Returns:
            Dict kết quả nhận diện
        """
        start_time = time.time()

        try:
            logger.info("⌨️  Bắt đầu nhận diện đơn hàng từ text")

            # Build prompt
            prompt = self._build_order_extraction_prompt_from_text(
                text_input.message_text,
                text_input.additional_context
            )

            # Gọi OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.1
            )

            # Extract response
            response_text = response.choices[0].message.content
            processing_time = time.time() - start_time

            logger.info(f"✅ Nhận diện hoàn thành trong {processing_time:.2f}s")

            # Parse JSON
            parsed_data = self._extract_json_from_response(response_text)

            if not parsed_data:
                return {
                    "success": False,
                    "error": "Không parse được JSON từ response",
                    "raw_response": response_text,
                    "processing_time": processing_time
                }

            # Validate và fix
            validated_data = self._validate_order_data(parsed_data)

            # Convert to OrderData
            order_data = self._convert_to_order_data(validated_data, processing_time)

            return {
                "success": True,
                "data": order_data,
                "raw_response": response_text,
                "processing_time": processing_time
            }

        except Exception as e:
            logger.error(f"❌ Lỗi nhận diện đơn hàng: {str(e)}")
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
                logger.debug("✅ Parsed JSON successfully")
                return parsed

            logger.warning("⚠️ Không tìm thấy JSON object trong response")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"❌ Không parse được JSON: {str(e)}")
            logger.error(f"Raw text: {response_text[:500]}")
            return None

    def _validate_order_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate và sửa các lỗi thường gặp trong order data

        Args:
            raw_data: Dữ liệu thô

        Returns:
            Dữ liệu đã được validate
        """
        warnings = []

        # 1. Validate phone number
        phone = raw_data.get("customer_phone")
        if phone:
            # Clean phone: chỉ giữ số
            cleaned_phone = ''.join(c for c in str(phone) if c.isdigit())
            if len(cleaned_phone) < 10 or len(cleaned_phone) > 11:
                warnings.append(f"SĐT không hợp lệ: {phone} (độ dài: {len(cleaned_phone)})")
                raw_data["needs_review"] = True
            raw_data["customer_phone"] = cleaned_phone if cleaned_phone else None

        # 2. Validate items
        for idx, item in enumerate(raw_data.get("items", []), 1):
            try:
                # Validate quantity
                quantity = Decimal(str(item.get("quantity", 0)))
                if quantity <= 0:
                    warnings.append(f"Item {idx}: Số lượng <= 0")
                    raw_data["needs_review"] = True

                # Validate price
                unit_price = item.get("unit_price")
                total_price = item.get("total_price")

                if unit_price and total_price:
                    expected_total = quantity * Decimal(str(unit_price))
                    actual_total = Decimal(str(total_price))
                    if abs(expected_total - actual_total) > Decimal("1"):
                        warnings.append(f"Item {idx}: {quantity} × {unit_price} ≠ {total_price}")
                        # Auto fix
                        item["total_price"] = str(expected_total)

            except Exception as e:
                warnings.append(f"Item {idx}: Lỗi validate: {str(e)}")

        # 3. Check if missing important info
        if not raw_data.get("customer_name") or not raw_data.get("customer_phone"):
            raw_data["needs_review"] = True
            review_notes = []
            if not raw_data.get("customer_name"):
                review_notes.append("Thiếu tên khách hàng")
            if not raw_data.get("customer_phone"):
                review_notes.append("Thiếu số điện thoại")
            raw_data["review_notes"] = "; ".join(review_notes)

        if warnings:
            logger.warning(f"⚠️ Validation warnings: {warnings}")

        return raw_data

    def _convert_to_order_data(self, raw_data: Dict[str, Any], processing_time: float) -> OrderData:
        """
        Convert raw dict sang OrderData model

        Args:
            raw_data: Raw dictionary
            processing_time: Thời gian xử lý

        Returns:
            OrderData object
        """
        # Parse items
        items = []
        for item_dict in raw_data.get("items", []):
            try:
                item = OrderItemData(
                    line_number=item_dict.get("line_number", 0),
                    product_name=item_dict.get("product_name", ""),
                    quantity=Decimal(str(item_dict.get("quantity", 0))),
                    unit_price=Decimal(str(item_dict.get("unit_price", 0))) if item_dict.get("unit_price") else None,
                    total_price=Decimal(str(item_dict.get("total_price", 0))) if item_dict.get("total_price") else None,
                    notes=item_dict.get("notes")
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi parse item: {str(e)}")

        # Parse date
        order_date = None
        if raw_data.get("order_date"):
            try:
                if isinstance(raw_data["order_date"], str):
                    order_date = datetime.strptime(raw_data["order_date"], "%Y-%m-%d").date()
                elif isinstance(raw_data["order_date"], date):
                    order_date = raw_data["order_date"]
            except Exception as e:
                logger.warning(f"⚠️ Lỗi parse date: {str(e)}")

        # Create OrderData
        order_data = OrderData(
            customer_type=raw_data.get("customer_type"),
            customer_name=raw_data.get("customer_name"),
            business_name=raw_data.get("business_name"),
            customer_tax_code=raw_data.get("customer_tax_code"),
            customer_phone=raw_data.get("customer_phone"),
            customer_address=raw_data.get("customer_address"),
            business_address=raw_data.get("business_address"),
            customer_email=raw_data.get("customer_email"),
            order_id=raw_data.get("order_id"),
            order_date=order_date,
            payment_method=raw_data.get("payment_method"),
            notes=raw_data.get("notes"),
            items=items,
            total_amount=Decimal(str(raw_data.get("total_amount", 0))) if raw_data.get("total_amount") else None,
            processing_time=processing_time,
            needs_review=raw_data.get("needs_review", False),
            review_notes=raw_data.get("review_notes"),
            noise_detected=raw_data.get("noise_detected", [])
        )

        return order_data


# Khởi tạo service instance
order_recognition_service = OrderRecognitionService()
