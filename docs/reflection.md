# Reflection — Lab 02 + Lab 03

> เขียนส่วน "สิ่งที่ได้เรียนรู้", "ปัญหาที่เจอและวิธีแก้" และ "สิ่งที่ยังไม่แน่ใจ"
> ด้วยคำของคุณเอง ส่วนสรุปงานด้านล่างเป็นข้อเท็จจริงของสิ่งที่สร้างและตรวจแล้ว

## สิ่งที่สร้าง

Flask Web App หลายไฟล์สำหรับคำนวณ DC Bias ของ NPN BJT แบบ Common-Emitter
3 วงจรที่เลือกได้: Voltage-Divider (Lab 02), Fixed และ Emitter (Lab 03)
ฟอร์มรับ VCC, RC, β, VBE ร่วมกับพารามิเตอร์ของโหมดที่เลือก
แล้วให้ Python คำนวณ IB, IC, IE, VB, VE, VC, VCE
(และ VTH, RTH เฉพาะ Divider) พร้อมหน่วยและ Operating Region

## สิ่งที่ตรวจสอบแล้ว

- Divider ตรงกับการคำนวณมือ (VCE = 8.052 V, IC = 1.230 mA) ตาม `docs/validation.md`
- Fixed (A2): IC = 1.130 mA, VCE = 9.514 V
- Emitter (A3): IC = 1.026 mA, VCE = 8.705 V
- Emitter (A4, RE=2 kΩ): IC = 0.940 mA, VCE = 8.033 V — IC ลดลงเมื่อ RE เพิ่ม
- A5 (RB=0) ถูกปฏิเสธด้วย `ต้องมากกว่า 0` และไม่แสดงผลลัพธ์
- Automated tests 38 ตัวผ่านทั้งหมด (13 engineering + 7 Lab 03 + 18 HTTP)
- Browser A1–A5 ผ่านทั้งหมด และมี screenshot ของ A3 ใน `docs/screenshots/`
- clone จาก GitHub แบบไม่ใช้ credential แล้วติดตั้งและรันเทสต์ผ่าน (38 tests)

## สิ่งที่ได้เรียนรู้

- ...
- ...
- ...

## ปัญหาที่เจอและวิธีแก้

- ...
- ...

## สิ่งที่ยังไม่แน่ใจ / อยากทำต่อ

- ...
- ...

## การใช้ AI

- ใช้ OpenCode + Superpowers ในขั้นใด (brainstorm / plan / implement / test)
- ส่วนใดที่ตรวจโค้ดเองและแก้เอง
- ส่วนใดที่ยังไม่เข้าใจและต้องการทบทวน
- แนะนำให้ระบุด้วยว่าค่า A1–A5 คำนวณมือและตรวจเองแล้ว ก่อนนำส่ง
