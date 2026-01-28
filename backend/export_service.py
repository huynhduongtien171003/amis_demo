"""
Service export dữ liệu sang định dạng AMIS
Hỗ trợ export Excel, XML, JSON
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
from decimal import Decimal

import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from loguru import logger

from backend.config import settings
from backend.invoice import InvoiceData, ExportRequest


class AMISExportService:
    """Service export dữ liệu sang định dạng AMIS"""
    
    def __init__(self):
        """Khởi tạo service"""
        self.output_dir = Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_to_excel(
        self,
        invoice_data: InvoiceData,
        job_id: str,
        template_type: str = "general"
    ) -> str:
        """
        Export dữ liệu hóa đơn sang file Excel theo định dạng AMIS

        Args:
            invoice_data: Dữ liệu hóa đơn
            job_id: ID của job
            template_type: Loại template

        Returns:
            Đường dẫn đến file Excel đã tạo
        """
        try:
            logger.info(f"Bắt đầu export Excel cho job {job_id}")

            # Tạo workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Hóa đơn GTGT"

            # ========== STYLES ==========
            # Title style
            title_font = Font(bold=True, size=16, color="1F4E78")
            subtitle_font = Font(bold=True, size=11, color="1F4E78")

            # Header styles
            header_font = Font(bold=True, size=11, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

            # Info section styles
            label_font = Font(bold=True, size=10)
            value_font = Font(size=10)

            # Border styles
            thin_border = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )
            thick_border = Border(
                left=Side(style='medium', color='000000'),
                right=Side(style='medium', color='000000'),
                top=Side(style='medium', color='000000'),
                bottom=Side(style='medium', color='000000')
            )

            # Total row styles
            total_font = Font(bold=True, size=11)
            total_fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")

            current_row = 1

            # ========== HEADER - TIÊU ĐỀ ==========
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="HÓA ĐƠN GIÁ TRỊ GIA TĂNG")
            cell.font = title_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            current_row += 1

            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="VAT INVOICE")
            cell.font = Font(bold=True, size=10, italic=True, color="666666")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            current_row += 2

            # ========== THÔNG TIN NGƯỜI BÁN ==========
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="THÔNG TIN NGƯỜI BÁN")
            cell.font = subtitle_font
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            current_row += 1

            seller_info = [
                ["Tên đơn vị:", invoice_data.seller_legal_name or ""],
                ["Mã số thuế:", invoice_data.seller_tax_code or ""],
                ["Địa chỉ:", invoice_data.seller_address or ""],
            ]

            for label, value in seller_info:
                ws.cell(row=current_row, column=1, value=label).font = label_font
                ws.merge_cells(f'B{current_row}:J{current_row}')
                ws.cell(row=current_row, column=2, value=value).font = value_font
                current_row += 1

            current_row += 1

            # ========== THÔNG TIN HÓA ĐƠN ==========
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="THÔNG TIN HÓA ĐƠN")
            cell.font = subtitle_font
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            current_row += 1

            invoice_info = [
                ["Ký hiệu hóa đơn:", invoice_data.inv_series or ""],
                ["Ngày hóa đơn:", invoice_data.inv_date.strftime("%d/%m/%Y") if invoice_data.inv_date else ""],
                ["Hình thức thanh toán:", invoice_data.payment_method_name or "TM/CK"],
            ]

            for label, value in invoice_info:
                ws.cell(row=current_row, column=1, value=label).font = label_font
                ws.merge_cells(f'B{current_row}:J{current_row}')
                ws.cell(row=current_row, column=2, value=value).font = value_font
                current_row += 1

            current_row += 1

            # ========== THÔNG TIN NGƯỜI MUA ==========
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="THÔNG TIN NGƯỜI MUA")
            cell.font = subtitle_font
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            current_row += 1

            buyer_info = [
                ["Tên đơn vị:", invoice_data.buyer_legal_name or ""],
                ["Mã số thuế:", invoice_data.buyer_tax_code or ""],
                ["Địa chỉ:", invoice_data.buyer_address or ""],
                ["Số điện thoại:", invoice_data.buyer_phone_number or ""],
                ["Email:", invoice_data.buyer_email or ""],
            ]

            for label, value in buyer_info:
                ws.cell(row=current_row, column=1, value=label).font = label_font
                ws.merge_cells(f'B{current_row}:J{current_row}')
                ws.cell(row=current_row, column=2, value=value).font = value_font
                current_row += 1

            current_row += 2

            # ========== BẢNG CHI TIẾT HÀNG HÓA ==========
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value="CHI TIẾT HÀNG HÓA / DỊCH VỤ")
            cell.font = subtitle_font
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
            current_row += 1

            # Header bảng
            headers = [
                ("STT", 5),
                ("Mã hàng", 15),
                ("Tên hàng hóa/dịch vụ", 35),
                ("ĐVT", 10),
                ("Số lượng", 10),
                ("Đơn giá", 15),
                ("Thành tiền", 15),
                ("Thuế suất", 10),
                ("Tiền thuế", 15),
                ("Tổng tiền", 15)
            ]

            for col_idx, (header, width) in enumerate(headers, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border
                ws.column_dimensions[get_column_letter(col_idx)].width = width

            current_row += 1
            detail_start_row = current_row

            # Dữ liệu chi tiết
            for item in invoice_data.original_invoice_detail:
                row_data = [
                    item.sort_order or item.line_number,
                    item.item_code or "",
                    item.item_name or "",
                    item.unit_name or "",
                    float(item.quantity),
                    float(item.unit_price),
                    float(item.amount_without_vat),
                    item.vat_rate_name or "10%",
                    float(item.vat_amount),
                    float(item.amount_without_vat + item.vat_amount)
                ]

                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=current_row, column=col_idx, value=value)
                    cell.border = thin_border
                    cell.font = value_font

                    # Alignment
                    if col_idx == 1:  # STT
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif col_idx in [3]:  # Tên hàng
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                    elif col_idx in [5, 6, 7, 9, 10]:  # Các cột số tiền
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        cell.number_format = '#,##0'
                    elif col_idx == 4:  # Số lượng
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        cell.number_format = '#,##0.##'
                    else:
                        cell.alignment = Alignment(horizontal="center", vertical="center")

                ws.row_dimensions[current_row].height = 25
                current_row += 1

            # ========== TỔNG CỘNG ==========
            ws.merge_cells(f'A{current_row}:F{current_row}')
            cell = ws.cell(row=current_row, column=1, value="TỔNG CỘNG")
            cell.font = total_font
            cell.fill = total_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thick_border

            # Tổng thành tiền
            cell = ws.cell(row=current_row, column=7, value=float(invoice_data.total_amount_without_vat))
            cell.font = total_font
            cell.fill = total_fill
            cell.number_format = '#,##0'
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.border = thick_border

            # Cột thuế suất (trống)
            cell = ws.cell(row=current_row, column=8, value="")
            cell.fill = total_fill
            cell.border = thick_border

            # Tổng tiền thuế
            cell = ws.cell(row=current_row, column=9, value=float(invoice_data.total_vat_amount))
            cell.font = total_font
            cell.fill = total_fill
            cell.number_format = '#,##0'
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.border = thick_border

            # Tổng thanh toán
            cell = ws.cell(row=current_row, column=10, value=float(invoice_data.total_amount))
            cell.font = total_font
            cell.fill = total_fill
            cell.number_format = '#,##0'
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.border = thick_border

            current_row += 2

            # ========== TỔNG TIỀN BẰNG CHỮ ==========
            ws.cell(row=current_row, column=1, value="Tổng tiền bằng chữ:").font = label_font
            ws.merge_cells(f'B{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=2, value=invoice_data.total_amount_in_words or "")
            cell.font = Font(size=10, italic=True)
            current_row += 2

            # ========== CHỮ KÝ ==========
            signature_row = current_row

            # Người mua
            ws.merge_cells(f'A{signature_row}:C{signature_row}')
            cell = ws.cell(row=signature_row, column=1, value="NGƯỜI MUA HÀNG")
            cell.font = Font(bold=True, size=10)
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Người bán
            ws.merge_cells(f'H{signature_row}:J{signature_row}')
            cell = ws.cell(row=signature_row, column=8, value="NGƯỜI BÁN HÀNG")
            cell.font = Font(bold=True, size=10)
            cell.alignment = Alignment(horizontal="center", vertical="center")

            current_row += 1
            ws.merge_cells(f'A{current_row}:C{current_row}')
            cell = ws.cell(row=current_row, column=1, value="(Ký, ghi rõ họ tên)")
            cell.font = Font(size=9, italic=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")

            ws.merge_cells(f'H{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=8, value="(Ký, đóng dấu, ghi rõ họ tên)")
            cell.font = Font(size=9, italic=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # ========== FOOTER ==========
            current_row += 6
            ws.merge_cells(f'A{current_row}:J{current_row}')
            cell = ws.cell(row=current_row, column=1, value=f"Xuất bởi AMIS OCR System - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            cell.font = Font(size=8, italic=True, color="999999")
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Lưu file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"HoaDon_GTGT_{job_id}_{timestamp}.xlsx"
            file_path = self.output_dir / filename

            wb.save(file_path)
            logger.info(f"Đã export Excel: {file_path}")

            return str(file_path)

        except Exception as e:
            logger.error(f"Lỗi khi export Excel: {str(e)}")
            raise
    
    def export_to_json(
        self,
        invoice_data: InvoiceData,
        job_id: str
    ) -> str:
        """
        Export dữ liệu sang JSON
        
        Args:
            invoice_data: Dữ liệu hóa đơn
            job_id: ID của job
            
        Returns:
            Đường dẫn đến file JSON
        """
        try:
            import json
            from decimal import Decimal
            
            # Custom JSON encoder cho Decimal và date
            class CustomEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return float(obj)
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    if hasattr(obj, '__dict__'):
                        return obj.__dict__
                    return super().default(obj)
            
            # Convert sang dict
            data_dict = invoice_data.model_dump()
            
            # Lưu file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"amis_invoice_{job_id}_{timestamp}.json"
            file_path = self.output_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2, cls=CustomEncoder)
            
            logger.info(f"Đã export JSON: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Lỗi khi export JSON: {str(e)}")
            raise


# Singleton instance
amis_export_service = AMISExportService()