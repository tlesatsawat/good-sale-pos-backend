import logging
import json
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Optional

class HardwareManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected_devices = {}
        self.printer_settings = {}
        self.cash_drawer_settings = {}
        
    def detect_printers(self) -> List[Dict]:
        """ตรวจหาเครื่องพิมพ์ที่เชื่อมต่อ"""
        try:
            printers = []
            
            # สำหรับ Windows
            if platform.system() == "Windows":
                try:
                    import win32print
                    printer_names = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
                    for name in printer_names:
                        printers.append({
                            'name': name,
                            'type': 'thermal' if 'thermal' in name.lower() or 'pos' in name.lower() else 'standard',
                            'status': 'available',
                            'connection': 'usb'
                        })
                except ImportError:
                    self.logger.warning("win32print not available")
            
            # สำหรับ Linux/Unix
            elif platform.system() in ["Linux", "Darwin"]:
                try:
                    result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if line.startswith('printer'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    name = parts[1]
                                    printers.append({
                                        'name': name,
                                        'type': 'thermal' if 'thermal' in name.lower() or 'pos' in name.lower() else 'standard',
                                        'status': 'available',
                                        'connection': 'usb'
                                    })
                except subprocess.SubprocessError:
                    self.logger.warning("lpstat command failed")
            
            # เพิ่มเครื่องพิมพ์จำลองสำหรับการทดสอบ
            if not printers:
                printers.append({
                    'name': 'Virtual POS Printer',
                    'type': 'thermal',
                    'status': 'available',
                    'connection': 'virtual'
                })
            
            self.connected_devices['printers'] = printers
            return printers
            
        except Exception as e:
            self.logger.error(f"Error detecting printers: {e}")
            return []
    
    def configure_printer(self, printer_name: str, settings: Dict) -> bool:
        """ตั้งค่าเครื่องพิมพ์"""
        try:
            self.printer_settings[printer_name] = {
                'paper_width': settings.get('paper_width', 80),  # mm
                'paper_height': settings.get('paper_height', 0),  # 0 = continuous
                'font_size': settings.get('font_size', 12),
                'encoding': settings.get('encoding', 'utf-8'),
                'cut_paper': settings.get('cut_paper', True),
                'open_drawer': settings.get('open_drawer', False),
                'copies': settings.get('copies', 1),
                'configured_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Printer {printer_name} configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error configuring printer {printer_name}: {e}")
            return False
    
    def print_receipt(self, printer_name: str, receipt_data: Dict) -> bool:
        """พิมพ์ใบเสร็จ"""
        try:
            if printer_name not in self.printer_settings:
                self.logger.error(f"Printer {printer_name} not configured")
                return False
            
            settings = self.printer_settings[printer_name]
            
            # สร้างเนื้อหาใบเสร็จ
            receipt_content = self._format_receipt(receipt_data, settings)
            
            # สำหรับการทดสอบ - บันทึกลงไฟล์
            if printer_name == 'Virtual POS Printer':
                return self._print_to_file(receipt_content, receipt_data.get('order_id', 'unknown'))
            
            # พิมพ์จริงสำหรับเครื่องพิมพ์จริง
            return self._send_to_printer(printer_name, receipt_content, settings)
            
        except Exception as e:
            self.logger.error(f"Error printing receipt: {e}")
            return False
    
    def _format_receipt(self, receipt_data: Dict, settings: Dict) -> str:
        """จัดรูปแบบใบเสร็จ"""
        width = settings.get('paper_width', 80) // 2  # ประมาณ characters per line
        
        lines = []
        
        # Header
        store_name = receipt_data.get('store_name', 'GOOD SALE POS')
        lines.append(store_name.center(width))
        lines.append('=' * width)
        
        # Order info
        lines.append(f"Order ID: {receipt_data.get('order_id', 'N/A')}")
        lines.append(f"Date: {receipt_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        lines.append(f"Table: {receipt_data.get('table_number', 'N/A')}")
        lines.append('-' * width)
        
        # Items
        items = receipt_data.get('items', [])
        for item in items:
            name = item.get('name', 'Unknown Item')
            qty = item.get('quantity', 1)
            price = item.get('price', 0)
            total = qty * price
            
            lines.append(f"{name}")
            lines.append(f"  {qty} x {price:.2f} = {total:.2f}")
            
            # Customizations
            if item.get('customizations'):
                for custom in item['customizations']:
                    lines.append(f"  + {custom}")
        
        lines.append('-' * width)
        
        # Totals
        subtotal = receipt_data.get('subtotal', 0)
        tax = receipt_data.get('tax', 0)
        total = receipt_data.get('total', 0)
        
        lines.append(f"Subtotal: {subtotal:.2f}")
        if tax > 0:
            lines.append(f"Tax: {tax:.2f}")
        lines.append(f"TOTAL: {total:.2f}")
        
        # Payment
        payment_method = receipt_data.get('payment_method', 'Cash')
        lines.append(f"Payment: {payment_method}")
        
        if payment_method == 'Cash':
            paid = receipt_data.get('amount_paid', total)
            change = paid - total
            lines.append(f"Paid: {paid:.2f}")
            if change > 0:
                lines.append(f"Change: {change:.2f}")
        
        lines.append('=' * width)
        lines.append("Thank you for your visit!")
        lines.append("Please come again!")
        
        return '\n'.join(lines)
    
    def _print_to_file(self, content: str, order_id: str) -> bool:
        """บันทึกใบเสร็จลงไฟล์ (สำหรับการทดสอบ)"""
        try:
            filename = f"receipt_{order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Receipt saved to file: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving receipt to file: {e}")
            return False
    
    def _send_to_printer(self, printer_name: str, content: str, settings: Dict) -> bool:
        """ส่งข้อมูลไปยังเครื่องพิมพ์จริง"""
        try:
            # สำหรับ Windows
            if platform.system() == "Windows":
                try:
                    import win32print
                    hPrinter = win32print.OpenPrinter(printer_name)
                    try:
                        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Receipt", None, "RAW"))
                        try:
                            win32print.StartPagePrinter(hPrinter)
                            win32print.WritePrinter(hPrinter, content.encode('utf-8'))
                            win32print.EndPagePrinter(hPrinter)
                        finally:
                            win32print.EndDocPrinter(hPrinter)
                    finally:
                        win32print.ClosePrinter(hPrinter)
                    return True
                except ImportError:
                    self.logger.warning("win32print not available, using alternative method")
            
            # สำหรับ Linux/Unix
            elif platform.system() in ["Linux", "Darwin"]:
                try:
                    process = subprocess.Popen(['lp', '-d', printer_name], stdin=subprocess.PIPE)
                    process.communicate(content.encode('utf-8'))
                    return process.returncode == 0
                except subprocess.SubprocessError as e:
                    self.logger.error(f"Error using lp command: {e}")
            
            # Fallback - บันทึกลงไฟล์
            return self._print_to_file(content, "fallback")
            
        except Exception as e:
            self.logger.error(f"Error sending to printer: {e}")
            return False
    
    def open_cash_drawer(self, printer_name: str = None) -> bool:
        """เปิดลิ้นชักเงิน"""
        try:
            # ESC/POS command สำหรับเปิดลิ้นชัก
            # ESC p m t1 t2 (0x1B 0x70 0x00 0x19 0x19)
            drawer_command = b'\x1B\x70\x00\x19\x19'
            
            if printer_name and printer_name != 'Virtual POS Printer':
                # ส่งคำสั่งไปยังเครื่องพิมพ์จริง
                if platform.system() == "Windows":
                    try:
                        import win32print
                        hPrinter = win32print.OpenPrinter(printer_name)
                        try:
                            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Cash Drawer", None, "RAW"))
                            try:
                                win32print.StartPagePrinter(hPrinter)
                                win32print.WritePrinter(hPrinter, drawer_command)
                                win32print.EndPagePrinter(hPrinter)
                            finally:
                                win32print.EndDocPrinter(hPrinter)
                        finally:
                            win32print.ClosePrinter(hPrinter)
                        return True
                    except ImportError:
                        pass
                
                elif platform.system() in ["Linux", "Darwin"]:
                    try:
                        process = subprocess.Popen(['lp', '-d', printer_name, '-o', 'raw'], stdin=subprocess.PIPE)
                        process.communicate(drawer_command)
                        return process.returncode == 0
                    except subprocess.SubprocessError:
                        pass
            
            # สำหรับการทดสอบ
            self.logger.info("Cash drawer opened (simulated)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening cash drawer: {e}")
            return False
    
    def test_printer(self, printer_name: str) -> Dict:
        """ทดสอบเครื่องพิมพ์"""
        try:
            test_receipt = {
                'store_name': 'GOOD SALE POS',
                'order_id': 'TEST-001',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'table_number': 'TEST',
                'items': [
                    {
                        'name': 'Test Item',
                        'quantity': 1,
                        'price': 10.00,
                        'customizations': ['Test Customization']
                    }
                ],
                'subtotal': 10.00,
                'tax': 0.70,
                'total': 10.70,
                'payment_method': 'Cash',
                'amount_paid': 20.00
            }
            
            success = self.print_receipt(printer_name, test_receipt)
            
            return {
                'printer_name': printer_name,
                'test_successful': success,
                'test_time': datetime.now().isoformat(),
                'message': 'Test print successful' if success else 'Test print failed'
            }
            
        except Exception as e:
            self.logger.error(f"Error testing printer: {e}")
            return {
                'printer_name': printer_name,
                'test_successful': False,
                'test_time': datetime.now().isoformat(),
                'message': f'Test failed: {str(e)}'
            }
    
    def get_device_status(self) -> Dict:
        """ดึงสถานะอุปกรณ์ทั้งหมด"""
        try:
            printers = self.detect_printers()
            
            status = {
                'printers': printers,
                'printer_settings': self.printer_settings,
                'cash_drawer_settings': self.cash_drawer_settings,
                'last_updated': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting device status: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }

