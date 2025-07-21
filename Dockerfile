# ใช้ Python เวอร์ชัน 3.11 เป็นพื้นฐาน
FROM python:3.11-slim

# ตั้งค่า Working Directory ภายใน Container
WORKDIR /app

# อัปเกรดเครื่องมือติดตั้งให้เป็นเวอร์ชันล่าสุด (สำคัญมาก)
RUN pip install --upgrade pip setuptools wheel

# คัดลอกไฟล์ requirements.txt เข้าไปก่อน
COPY requirements.txt .

# ติดตั้งไลบรารีทั้งหมด
RUN pip install -r requirements.txt

# คัดลอกไฟล์โปรเจคที่เหลือทั้งหมดเข้าไป
COPY . .

# คำสั่งที่จะรันเมื่อแอปพลิเคชันเริ่มทำงาน
# Render จะกำหนด PORT ให้เอง เราแค่ต้อง bind ไปที่ 0.0.0.0
CMD ["gunicorn", "src.app:app", "--bind", "0.0.0.0:10000"]
