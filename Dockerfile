# ใช้ Python เวอร์ชัน 3.11 เป็นพื้นฐาน
FROM python:3.11-slim

# ตั้งค่า Working Directory ภายใน Container
WORKDIR /app

# อัปเกรดเครื่องมือติดตั้ง
RUN pip install --upgrade pip

# คัดลอกไฟล์ requirements.txt เข้าไปก่อน
COPY requirements.txt .

# ติดตั้งไลบรารี
RUN pip install -r requirements.txt

# คัดลอกไฟล์โปรเจคที่เหลือทั้งหมดเข้าไป
COPY . .

# *** บรรทัดสำคัญที่เพิ่มเข้ามา ***
# บอกให้ Python รู้จักโฟลเดอร์รากของโปรเจค
ENV PYTHONPATH "${PYTHONPATH}:/app"

# คำสั่งที่จะรันเมื่อแอปพลิเคชันเริ่มทำงาน
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
