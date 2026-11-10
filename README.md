# BJT DC Bias Simulator — ENG29 2121 Lab 02

เว็บแอป Flask สำหรับคำนวณจุดทำงานกระแสตรง (DC Operating Point) ของทรานซิสเตอร์
NPN แบบ Common-Emitter ที่ไบอัสด้วยวงจรแบ่งแรงดัน (Voltage-Divider Bias)
โดยใช้สมมติฐาน Forward-Active Approximation

การคำนวณทั้งหมดเกิดใน Python ฝั่ง Server หน้า HTML ไม่ได้คำนวณเองและไม่ได้ฝัง
ตัวเลขคำตอบไว้

## ขอบเขตงาน (Week 2)

| อยู่ในขอบเขต | ไม่อยู่ในขอบเขต |
|---|---|
| รับค่า VCC, R1, R2, RC, RE, β, VBE | AC small-signal, gain, Bode plot |
| แสดง VTH, RTH, IB, IC, IE, VB, VE, VC, VCE | Transient / signal generator |
| ตรวจสอบข้อมูลเข้า + เตือนเมื่อออกนอกย่าน | SPICE solver, load line |
| Unit tests + Flask HTTP tests | FET, bias topology อื่น |

## ความต้องการของระบบ

- Python 3.10 ขึ้นไป
- Flask 3.x (ติดตั้งจาก `requirements.txt`)

## ติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # Linux / macOS
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิด <http://127.0.0.1:5000/> ใน Browser

> ต้องเปิดผ่าน Flask Server เท่านั้น ไม่ใช่ double-click ไฟล์ `index.html`
> เพราะตัวเลขต้องถูกคำนวณจาก Python

## เทสต์

```powershell
python -m unittest discover -s tests -v
```

มี 2 ชุด: `tests/test_dc_bias.py` (สมการวิศวกรรม 13 เทสต์) และ
`tests/test_web.py` (HTTP ผ่าน Flask test client 8 เทสต์) รวม **21 เทสต์**
ให้รันจากโฟลเดอร์รากของ repository เพราะเทสต์ import `app` จากโฟลเดอร์ปัจจุบัน

## หน่วยของข้อมูลเข้า

- `VCC`, `VBE` หน่วยโวลต์ (V)
- `R1`, `R2`, `RC`, `RE` หน่วยโอห์ม (Ω) เช่น 100 kΩ ให้กรอก `100000`
- `β` คือ DC current gain (hFE) ไม่มีหน่วย และต้องมากกว่า 0

ช่วงที่รับได้: `VCC ≤ 10 kV`, `R ≤ 1 TΩ`, `β ≤ 1 000 000` และ `0 < VBE < VCC`
ค่าที่เกินขอบเขตจะถูกปฏิเสธ ไม่ปล่อยให้แสดงเป็น `inf`/`nan`

## ตัวอย่างอ้างอิง

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100,
VBE = 0.70 V

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.03 kΩ |
| IB | 12.30 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VB | 1.942 V |
| VE | 1.242 V |
| VC | 9.294 V |
| VCE | 8.052 V |

ย่านการทำงาน: **Forward-Active**

ตัวเลขข้างบนคำนวณด้วยมือจากสมการใน `docs/validation.md` ไม่ได้คัดลอกมาจากผลของโปรแกรม

## แบบจำลองและข้อจำกัด

สมการที่ใช้ (forward-active, β และ VBE คงที่):

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β·IB
IE  = (β + 1)·IB
VE  = IE·RE
VB  = VE + VBE
VC  = VCC − IC·RC
VCE = VC − VE
```

โปรแกรมจะแจ้งเตือนและไม่รายงานผลว่าเชื่อถือได้ เมื่อสมมติฐาน forward-active ใช้ไม่ได้:

- `VTH ≤ VBE` → **Cutoff** (ไม่มีกระแสฐาน กระแสที่แสดงเป็น 0)
- `VCE ≤ 0.3 V` → **Saturation** (ตัวเลขมาจากสมการที่อธิบายวงจรจริงไม่ได้แล้ว
  และถูกขีดฆ่าในหน้าจอ)
- `0.3 V < VCE < 1.0 V` → ยังเป็น active แต่เตือนว่า **ใกล้ Saturation**
- `0 < VTH − VBE < 10 mV` → ยังเป็น active แต่เตือนว่า **ใกล้ Cutoff**

ผลกระทบที่ยังไม่คิด: Early effect, กระแสรั่ว, การเปลี่ยนแปลงตามอุณหภูมิ,
ความต้านทานของแหล่งจ่าย และค่าคลาดเคลื่อนของอุปกรณ์

## โครงสร้างโปรเจกต์

```
BJT-DC-Bias-Web-App/
├── app.py                  # Flask routes, parse ฟอร์ม, จัดรูปแบบหน่วย
├── dc_bias.py              # สมการวิศวกรรมล้วน ๆ (ไม่รู้จัก Flask/HTML)
├── templates/index.html    # ฟอร์ม + ตารางผลลัพธ์ (Jinja)
├── static/style.css        # responsive layout
├── tests/
│   ├── test_dc_bias.py
│   └── test_web.py
├── docs/
│   ├── design-note.md
│   ├── validation.md
│   ├── reflection.md
│   └── screenshots/
├── requirements.txt
├── AGENTS.md
└── README.md
```

## เกณฑ์ตรวจรับ (A1–A7)

- [x] A1 `GET /` คืนหน้าฟอร์มด้วย HTTP 200
- [x] A2 `POST /` คำนวณใน Python แล้วแสดงผล
- [x] A3 ผลตรงกับการคำนวณมือภายใต้แบบจำลองเดียวกัน
- [x] A4 ข้อมูลผิด (R≤0, β≤0, ไม่ใช่ตัวเลข, ไม่กรอก) แจ้ง error ที่อ่านได้
- [x] A5 เตือนกรณี Cutoff / Saturation
- [x] A6 เทสต์อัตโนมัติ 21 ตัว (13 engineering + 8 HTTP)
- [x] A7 push ขึ้น GitHub แล้วและทำซ้ำได้: clone จาก
      `https://github.com/GTThanakrit/BJT-DC-Bias-Web-App.git`
      แล้ว `pip install -r requirements.txt` + รันเทสต์ผ่านทั้ง 21 ตัว
