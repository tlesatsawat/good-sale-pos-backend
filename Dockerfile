# ใช้ Python เวอร์ชัน 3.11 เป็นพื้นฐาน
FROM python:3.11-slim

# ตั้งค่า Working Directory ภายใน Container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt เข้าไปก่อน
COPY requirements.txt .

# ติดตั้งไลบรารี
RUN pip install -r requirements.txt

# คัดลอกไฟล์โปรเจคที่เหลือทั้งหมดเข้าไป
COPY . .

# *** คำสั่งที่ถูกต้องสำหรับ Application Factory ***
# บอกให้ Gunicorn เรียกใช้ฟังก์ชัน create_app() ที่อยู่ในโมดูล src.main
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "src.main:create_app()"]
