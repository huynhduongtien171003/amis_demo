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

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        Trích xuất text từ file PDF

        Args:
            file_path: Đường dẫn file PDF

        Returns:
            Text đã trích xuất
        """
        try:
            import pdfplumber
            
            text_content = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            
            full_text = "\n\n".join(text_content)
            logger.info(f"✅ Đã trích xuất {len(full_text)} ký tự từ PDF")
            return full_text

        except Exception as e:
            logger.error(f"❌ Lỗi trích xuất text từ PDF: {str(e)}")
            raise

    def _extract_text_from_html(self, file_path: str) -> str:
        """
        Trích xuất text từ file HTML

        Args:
            file_path: Đường dẫn file HTML

        Returns:
            Text đã trích xuất
        """
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script và style tags
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Lấy text
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = '\n'.join(lines)
            
            logger.info(f"✅ Đã trích xuất {len(clean_text)} ký tự từ HTML")
            return clean_text

        except Exception as e:
            logger.error(f"❌ Lỗi trích xuất text từ HTML: {str(e)}")
            raise

    def _build_order_extraction_prompt_from_image(self) -> str:
        """Build a detailed prompt for vision-based order/invoice extraction."""
        return (
            "You are an expert system for extracting structured order/invoice data "
            "from images of invoices, purchase orders, receipts, or chat screenshots.\n\n"
            "CRITICAL RULES:\n"
            "1. Return ONLY a single valid JSON object — no markdown, no explanation.\n"
            "2. Support both Vietnamese and English text.\n"
            "3. Numbers MUST be plain numeric values: strip all currency symbols "
            "(đ, ₫, VND, $, USD), thousand separators (dots or commas used as grouping), "
            "and whitespace. Example: 'd1,250,000.0000' → 1250000, '575,000.0000' → 575000.\n"
            "4. For tabular invoices look for columns like: Item SKU / Code, Product Description, "
            "Qty, UOM/Unit, Unit Price, Price Extension/Total. Map them to the JSON fields below.\n"
            "5. If a row has '*' or 'Non catalog item', still extract it.\n"
            "6. Extract summary lines: Sub Total, Freight, Tax Amount, Discount, Total amount due.\n"
            "7. Use null for unknown fields, [] for empty items.\n"
            "8. Set needs_review=true when data is ambiguous.\n\n"
            "CUSTOMER NAME RULE:\n"
            "- customer_name is the PRIMARY name of the customer — this can be a person name "
            "(individual) OR an organization/company name (business).\n"
            "- Set customer_type='individual' if customer is a person, 'business' if it is "
            "a company/organization.\n"
            "- business_name is OPTIONAL — only use it for a short/trade name if different "
            "from customer_name.\n\n"
            "JSON schema to return:\n"
            '{\n'
            '  "customer_type": null,\n'
            '  "customer_name": null,\n'
            '  "business_name": null,\n'
            '  "customer_tax_code": null,\n'
            '  "customer_phone": null,\n'
            '  "customer_address": null,\n'
            '  "business_address": null,\n'
            '  "customer_email": null,\n'
            '  "order_id": null,\n'
            '  "order_date": null,\n'
            '  "payment_method": null,\n'
            '  "notes": null,\n'
            '  "items": [\n'
            '    {\n'
            '      "product_name": "string",\n'
            '      "product_code": "string or null",\n'
            '      "quantity": 0,\n'
            '      "unit": "string or null",\n'
            '      "unit_price": 0,\n'
            '      "total_price": 0\n'
            '    }\n'
            '  ],\n'
            '  "subtotal": null,\n'
            '  "shipping": null,\n'
            '  "tax": null,\n'
            '  "discount": null,\n'
            '  "total_amount": null,\n'
            '  "currency": "VND",\n'
            '  "needs_review": false,\n'
            '  "review_notes": null,\n'
            '  "noise_detected": []\n'
            '}\n\n'
            "Respond with ONLY the JSON object."
        )

    def _build_order_extraction_prompt_from_text(self, text_content: str, additional_context: Optional[str] = None) -> str:
        """
        Xây dựng prompt cho text parsing

        Args:
            text_content: Nội dung text tin nhắn
            additional_context: Thông tin bổ sung từ user

        Returns:
            Prompt string
        """
        context_str = (
            f"\n\nAdditional context from user:\n{additional_context}"
            if additional_context
            else ""
        )

        schema = (
            '{\n'
            '  "customer_type": null,\n'
            '  "customer_name": null,\n'
            '  "business_name": null,\n'
            '  "customer_tax_code": null,\n'
            '  "customer_phone": null,\n'
            '  "customer_address": null,\n'
            '  "business_address": null,\n'
            '  "customer_email": null,\n'
            '  "order_id": null,\n'
            '  "order_date": null,\n'
            '  "payment_method": null,\n'
            '  "notes": null,\n'
            '  "items": [\n'
            '    {\n'
            '      "product_name": "string",\n'
            '      "product_code": "string or null",\n'
            '      "quantity": 0,\n'
            '      "unit": "string or null",\n'
            '      "unit_price": 0,\n'
            '      "total_price": 0\n'
            '    }\n'
            '  ],\n'
            '  "subtotal": null,\n'
            '  "shipping": null,\n'
            '  "tax": null,\n'
            '  "discount": null,\n'
            '  "total_amount": null,\n'
            '  "currency": "VND",\n'
            '  "needs_review": false,\n'
            '  "review_notes": null,\n'
            '  "noise_detected": []\n'
            '}'
        )

        return (
            f"You are an expert system for extracting structured order/invoice data "
            f"from free-text messages, emails, or pasted receipt/invoice text.\n\n"
            f"CRITICAL RULES:\n"
            f"1. Return ONLY a single valid JSON object — no markdown, no explanation.\n"
            f"2. Support both Vietnamese and English text.\n"
            f"3. Numbers MUST be plain numeric values: strip all currency symbols "
            f"(đ, ₫, VND, $, USD), thousand separators, and whitespace. "
            f"Example: 'd1,250,000.0000' → 1250000.\n"
            f"4. For tabular data look for columns: Item SKU/Code, Product Description, "
            f"Qty, UOM/Unit, Unit Price, Total. Map them to the items array.\n"
            f"5. Extract summary: Sub Total, Freight, Tax, Discount, Total amount due.\n"
            f"6. Use null for unknown fields, [] for empty items.\n"
            f"7. Set needs_review=true when data is ambiguous.\n\n"
            f"CUSTOMER NAME RULE:\n"
            f"- customer_name is the PRIMARY name — person name (individual) OR "
            f"organization/company name (business).\n"
            f"- Set customer_type='individual' or 'business' accordingly.\n"
            f"- business_name is OPTIONAL — only for short/trade name if different from customer_name.\n\n"
            f"--- SOURCE TEXT ---\n{text_content}\n--- END TEXT ---\n"
            f"{context_str}\n\n"
            f"JSON schema:\n{schema}\n\n"
            f"Respond with ONLY the JSON object."
        )

    async def process_image_order(self, image_path: str, model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Nhận diện đơn hàng từ ảnh screenshot tin nhắn hoặc file PDF/HTML

        Args:
            image_path: Đường dẫn ảnh hoặc file

        Returns:
            Dict kết quả nhận diện
        """
        start_time = time.time()

        try:
            file_extension = Path(image_path).suffix.lower()
            
            # Kiểm tra loại file
            if file_extension in ['.pdf']:
                logger.info(f"🔍 Bắt đầu nhận diện đơn hàng từ PDF: {image_path}")
                # Trích xuất text từ PDF và xử lý như text
                text_content = self._extract_text_from_pdf(image_path)
                from backend.order import TextOrderInput
                text_input = TextOrderInput(message_text=text_content)
                return await self.process_text_order(text_input, model_override=model_override)
                
            elif file_extension in ['.html', '.htm']:
                logger.info(f"🔍 Bắt đầu nhận diện đơn hàng từ HTML: {image_path}")
                # Trích xuất text từ HTML và xử lý như text
                text_content = self._extract_text_from_html(image_path)
                from backend.order import TextOrderInput
                text_input = TextOrderInput(message_text=text_content)
                return await self.process_text_order(text_input, model_override=model_override)
            
            else:
                # Xử lý như ảnh
                logger.info(f"🔍 Bắt đầu nhận diện đơn hàng từ ảnh: {image_path}")

            # Encode ảnh
            image_data_uri = self._encode_image_to_base64(image_path)

            # Build prompt
            prompt = self._build_order_extraction_prompt_from_image()

            # Gọi OpenAI Vision API
            model_to_use = model_override or self.model
            response = self.client.chat.completions.create(
                model=model_to_use,
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

    async def process_text_order(self, text_input: TextOrderInput, model_override: Optional[str] = None) -> Dict[str, Any]:
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
            model_to_use = model_override or self.model
            response = self.client.chat.completions.create(
                model=model_to_use,
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
                # Helper to safely get decimal
                def get_safe_decimal(value):
                    if value is None or value == "" or value == "null":
                        return None
                    try:
                        clean_val = str(value).replace(",", "").replace(" ", "").strip()
                        if not clean_val or clean_val.lower() in ['none', 'null', 'n/a']:
                            return None
                        return Decimal(clean_val)
                    except:
                        return None
                
                # Validate quantity
                quantity = get_safe_decimal(item.get("quantity", 0))
                if quantity and quantity <= 0:
                    warnings.append(f"Item {idx}: Số lượng <= 0")
                    raw_data["needs_review"] = True

                # Validate price
                unit_price = get_safe_decimal(item.get("unit_price"))
                total_price = get_safe_decimal(item.get("total_price"))

                if quantity and unit_price and total_price:
                    expected_total = quantity * unit_price
                    if abs(expected_total - total_price) > Decimal("1"):
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
        for idx, item_dict in enumerate(raw_data.get("items", []), 1):
            try:
                # Helper function to safely convert to Decimal
                def safe_decimal(value, default=None):
                    if value is None or value == "" or value == "null":
                        return default
                    try:
                        # Remove commas and spaces
                        clean_value = str(value).replace(",", "").replace(" ", "").strip()
                        if not clean_value or clean_value.lower() in ['none', 'null', 'n/a']:
                            return default
                        return Decimal(clean_value)
                    except:
                        return default
                
                quantity_val = safe_decimal(item_dict.get("quantity"), Decimal('0'))
                unit_price_val = safe_decimal(item_dict.get("unit_price"), None)
                total_price_val = safe_decimal(item_dict.get("total_price"), None)
                
                # Handle both 'name'/'product_name' and 'code'/'product_code' from AI
                product_name = item_dict.get("product_name") or item_dict.get("name") or ""
                product_code = item_dict.get("product_code") or item_dict.get("code")
                unit = item_dict.get("unit") or item_dict.get("uom")

                item = OrderItemData(
                    line_number=item_dict.get("line_number", idx),
                    product_code=product_code,
                    product_name=product_name,
                    quantity=quantity_val,
                    unit=unit,
                    unit_price=unit_price_val,
                    total_price=total_price_val,
                    notes=item_dict.get("notes")
                )
                items.append(item)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi parse item {idx}: {str(e)} - Data: {item_dict}")

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

        # Helper function to safely convert to Decimal
        def safe_decimal(value, default=None):
            if value is None or value == "" or value == "null":
                return default
            try:
                clean_value = str(value).replace(",", "").replace(" ", "").strip()
                if not clean_value or clean_value.lower() in ['none', 'null', 'n/a']:
                    return default
                return Decimal(clean_value)
            except:
                return default

        # Create OrderData
        order_data = OrderData(
            customer_id=raw_data.get("customer_id"),
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
            status=raw_data.get("status"),
            payment_method=raw_data.get("payment_method"),
            notes=raw_data.get("notes"),
            items=items,
            total_amount=safe_decimal(raw_data.get("total_amount"), None),
            processing_time=processing_time,
            needs_review=raw_data.get("needs_review", False),
            review_notes=raw_data.get("review_notes"),
            noise_detected=raw_data.get("noise_detected", [])
        )

        return order_data


# Khởi tạo service instance
order_recognition_service = OrderRecognitionService()
