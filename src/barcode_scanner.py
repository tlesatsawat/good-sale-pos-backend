import cv2
import numpy as np
from pyzbar import pyzbar
import logging
from typing import Optional, Dict, List
import base64
import io
from PIL import Image

class BarcodeScanner:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def scan_from_camera(self, camera_index: int = 0, timeout: int = 30) -> Optional[str]:
        """สแกนบาร์โค้ดจากกล้อง"""
        try:
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                self.logger.error(f"Cannot open camera {camera_index}")
                return None
            
            start_time = cv2.getTickCount()
            timeout_ticks = timeout * cv2.getTickFrequency()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # สแกนบาร์โค้ดในเฟรม
                barcodes = pyzbar.decode(frame)
                
                for barcode in barcodes:
                    # แปลงข้อมูลบาร์โค้ดเป็น string
                    barcode_data = barcode.data.decode('utf-8')
                    barcode_type = barcode.type
                    
                    self.logger.info(f"Barcode detected: {barcode_data} (Type: {barcode_type})")
                    
                    cap.release()
                    cv2.destroyAllWindows()
                    return barcode_data
                
                # ตรวจสอบ timeout
                current_time = cv2.getTickCount()
                if (current_time - start_time) > timeout_ticks:
                    break
                
                # แสดงเฟรมสำหรับการดีบัก (ถ้าต้องการ)
                # cv2.imshow('Barcode Scanner', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
            
            cap.release()
            cv2.destroyAllWindows()
            return None
            
        except Exception as e:
            self.logger.error(f"Error scanning from camera: {e}")
            return None
    
    def scan_from_image(self, image_data: str) -> List[Dict]:
        """สแกนบาร์โค้ดจากรูปภาพ (base64)"""
        try:
            # แปลง base64 เป็นรูปภาพ
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # แปลงเป็น numpy array สำหรับ OpenCV
            image_array = np.array(image)
            
            # แปลงเป็น BGR ถ้าเป็น RGB
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            
            # สแกนบาร์โค้ด
            barcodes = pyzbar.decode(image_array)
            
            results = []
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                
                # ดึงตำแหน่งของบาร์โค้ด
                points = barcode.polygon
                if len(points) == 4:
                    x = min([p.x for p in points])
                    y = min([p.y for p in points])
                    w = max([p.x for p in points]) - x
                    h = max([p.y for p in points]) - y
                else:
                    x, y, w, h = barcode.rect
                
                results.append({
                    'data': barcode_data,
                    'type': barcode_type,
                    'position': {
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h
                    }
                })
                
                self.logger.info(f"Barcode detected in image: {barcode_data} (Type: {barcode_type})")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error scanning from image: {e}")
            return []
    
    def scan_from_file(self, file_path: str) -> List[Dict]:
        """สแกนบาร์โค้ดจากไฟล์รูปภาพ"""
        try:
            # อ่านรูปภาพ
            image = cv2.imread(file_path)
            if image is None:
                self.logger.error(f"Cannot read image file: {file_path}")
                return []
            
            # สแกนบาร์โค้ด
            barcodes = pyzbar.decode(image)
            
            results = []
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                
                # ดึงตำแหน่งของบาร์โค้ด
                x, y, w, h = barcode.rect
                
                results.append({
                    'data': barcode_data,
                    'type': barcode_type,
                    'position': {
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h
                    }
                })
                
                self.logger.info(f"Barcode detected in file: {barcode_data} (Type: {barcode_type})")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error scanning from file: {e}")
            return []
    
    def validate_barcode(self, barcode_data: str, barcode_type: str = None) -> Dict:
        """ตรวจสอบความถูกต้องของบาร์โค้ด"""
        try:
            result = {
                'valid': False,
                'data': barcode_data,
                'type': barcode_type,
                'format': 'unknown',
                'check_digit_valid': False
            }
            
            # ตรวจสอบรูปแบบบาร์โค้ด
            if barcode_type:
                result['format'] = barcode_type.lower()
            
            # ตรวจสอบ EAN-13
            if len(barcode_data) == 13 and barcode_data.isdigit():
                result['format'] = 'ean13'
                result['check_digit_valid'] = self._validate_ean13(barcode_data)
                result['valid'] = result['check_digit_valid']
            
            # ตรวจสอบ EAN-8
            elif len(barcode_data) == 8 and barcode_data.isdigit():
                result['format'] = 'ean8'
                result['check_digit_valid'] = self._validate_ean8(barcode_data)
                result['valid'] = result['check_digit_valid']
            
            # ตรวจสอบ UPC-A
            elif len(barcode_data) == 12 and barcode_data.isdigit():
                result['format'] = 'upca'
                result['check_digit_valid'] = self._validate_upca(barcode_data)
                result['valid'] = result['check_digit_valid']
            
            # บาร์โค้ดอื่นๆ ถือว่าถูกต้อง
            else:
                result['valid'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating barcode: {e}")
            return {
                'valid': False,
                'data': barcode_data,
                'error': str(e)
            }
    
    def _validate_ean13(self, barcode: str) -> bool:
        """ตรวจสอบ check digit ของ EAN-13"""
        try:
            if len(barcode) != 13 or not barcode.isdigit():
                return False
            
            # คำนวณ check digit
            odd_sum = sum(int(barcode[i]) for i in range(0, 12, 2))
            even_sum = sum(int(barcode[i]) for i in range(1, 12, 2))
            total = odd_sum + (even_sum * 3)
            check_digit = (10 - (total % 10)) % 10
            
            return check_digit == int(barcode[12])
            
        except Exception:
            return False
    
    def _validate_ean8(self, barcode: str) -> bool:
        """ตรวจสอบ check digit ของ EAN-8"""
        try:
            if len(barcode) != 8 or not barcode.isdigit():
                return False
            
            # คำนวณ check digit
            odd_sum = sum(int(barcode[i]) for i in range(0, 7, 2))
            even_sum = sum(int(barcode[i]) for i in range(1, 7, 2))
            total = (odd_sum * 3) + even_sum
            check_digit = (10 - (total % 10)) % 10
            
            return check_digit == int(barcode[7])
            
        except Exception:
            return False
    
    def _validate_upca(self, barcode: str) -> bool:
        """ตรวจสอบ check digit ของ UPC-A"""
        try:
            if len(barcode) != 12 or not barcode.isdigit():
                return False
            
            # คำนวณ check digit
            odd_sum = sum(int(barcode[i]) for i in range(0, 11, 2))
            even_sum = sum(int(barcode[i]) for i in range(1, 11, 2))
            total = (odd_sum * 3) + even_sum
            check_digit = (10 - (total % 10)) % 10
            
            return check_digit == int(barcode[11])
            
        except Exception:
            return False
    
    def get_product_info(self, barcode: str) -> Optional[Dict]:
        """ดึงข้อมูลสินค้าจากบาร์โค้ด (จากฐานข้อมูลภายใน)"""
        try:
            # ในการใช้งานจริง ควรเชื่อมต่อกับฐานข้อมูลสินค้า
            # ที่นี่จะใช้ข้อมูลจำลองเพื่อการทดสอบ
            
            sample_products = {
                '8851019001234': {
                    'name': 'น้ำดื่ม 600ml',
                    'price': 7.00,
                    'category': 'เครื่องดื่ม',
                    'brand': 'Crystal',
                    'unit': 'ขวด'
                },
                '8851234567890': {
                    'name': 'ขนมปัง 350g',
                    'price': 25.00,
                    'category': 'อาหาร',
                    'brand': 'Farmhouse',
                    'unit': 'ถุง'
                },
                '1234567890123': {
                    'name': 'สินค้าทดสอบ',
                    'price': 10.00,
                    'category': 'ทั่วไป',
                    'brand': 'Test Brand',
                    'unit': 'ชิ้น'
                }
            }
            
            return sample_products.get(barcode)
            
        except Exception as e:
            self.logger.error(f"Error getting product info: {e}")
            return None


