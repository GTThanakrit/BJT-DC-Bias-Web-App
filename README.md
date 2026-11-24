# BJT DC Bias Simulator — ENG29 2121 Lab 02 + Lab 03

เว็บแอป Flask สำหรับคำนวณจุดทำงานกระแสตรง (DC Operating Point) ของทรานซิสเตอร์
NPN แบบ Common-Emitter 3 วงจรที่เลือกได้ในหน้าเดียว:

- **Voltage-Divider Bias** (Lab 02 — ผลเหมือนเดิมทุกตัวเลข)
- **Fixed Bias** (RB, RC)
- **Emitter Bias** (RB, RC, RE)

ใช้สมมติฐาน Forward-Active Approximation (β และ VBE คงที่) การคำนวณทั้งหมดเกิดใน
Python ฝั่ง Server หน้า HTML ไม่ได้คำนวณเองและไม่ได้ฝังตัวเลขคำตอบไว้

## ขอบเขตงาน

| อยู่ในขอบเขต | ไม่อยู่ในขอบเขต |
|---|---|
| เลือกโหมด Divider / Fixed / Emitter | AC small-signal, gain, Bode plot |
| รับ VCC, RC, β, VBE ร่วมกัน + ช่องของโหมดนั้น | Transient / signal generator |
| แสดง IB, IC, IE, VB, VE, VC, VCE (และ VTH, RTH เฉพาะ Divider) | SPICE solver, load line |
| ตรวจข้อมูลเข้า + เตือนเมื่อ IB ≤ 0 หรือ VCE ≤ 0.2 V | FET, bias topology อื่น |
| ตรวจ A1–A5 ผ่าน Browser + Unit/HTTP tests | JavaScript, database, deployment |

## ความต้องการของระบบ

- Python 3.10 ขึ้นไป
- Flask 3.x (ติดตั้งจาก `requirements.txt`)
- ngspice 47 (สำหรับ Lab 04 CE simulator) — เป็นโปรแกรมภายนอก ไม่ใช่แพ็กเกจ `pip`

### ngspice และ BJT model สำหรับ Lab 04

ตรวจว่าเรียกได้จาก Terminal ก่อนรัน Flask (บน Windows ให้ใช้ `ngspice_con.exe`
ซึ่งเป็นรุ่น Console; `ngspice.exe` เป็นรุ่น GUI และไม่พิมพ์เวอร์ชัน):

```powershell
ngspice_con -v
```

ผลต้องเป็นสายเวอร์ชันของ ngspice ถ้าไม่พบให้ติดตั้ง 7-Zip แล้วดาวน์โหลด
`ngspice-47_64.7z` จาก <https://ngspice.sourceforge.io/download.html> แตกไฟล์แล้วเพิ่ม
โฟลเดอร์ที่ contain `ngspice_con.exe` ลงใน `PATH` ของ Session นั้น

ในเครื่องที่ใช้พัฒนา Lab 04 ติดตั้งจริงที่
`%LOCALAPPDATA%\ngspice\Spice64\bin` และได้เวอร์ชัน `ngspice-47` (สร้าง 11 ส.ค. 2026)
แม้ Flask จะเริ่มโดยไม่ได้เพิ่ม PATH ก็ตาม adapter จะลองตำแหน่งมาตรฐานนี้เองก่อน
รายงาน `ENGINE NOT AVAILABLE`

ngspice 47 เขียนตาราง `.print` ลง log เฉพาะตอนที่ไม่ใช้ `-r` ดังนั้น adapter จึงรัน
แบบไม่สร้าง `.raw` และอ่าน `run.log` ที่เป็นข้อความเท่านั้น ตัวอย่าง log จริงจากเครื่อง
เก็บไว้ใน `tests/fixtures/ngspice_*_real.log` เพื่อทดสอบ parser (ไม่ใช่ค่าที่แอปใช้รัน)

โมเดลที่แนบมา `spice_models/ce_generic.mod` คือ **UNVERIFIED** generic teaching
NPN ใช้เพื่อทดสอบ adapter เท่านั้น ต้องแทนที่ด้วยโมเดลที่อาจารย์ตรวจก่อนอ้างผลว่า
ถูกต้องตามหลักวิศวกรรม หน้าเว็บจะแสดงป้าย `UNVERIFIED` ทุกครั้งที่ใช้โมเดลนี้

## ติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # Linux / macOS
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิด <http://127.0.0.1:5000/> ใน Browser แล้วเลือกวงจรจาก dropdown **โหมดวงจร**
**แล้วกดปุ่ม "เลือกวงจร" ทุกครั้ง** ฟอร์มถึงจะสลับช่องกรอก (โหลดใหม่แบบ GET ไม่ใช้ JavaScript)
ถ้าเลือกใน dropdown อย่างเดียวโดยยังไม่กดปุ่ม ช่องจะยังเป็นของโหมดเก่าอยู่ — นี่เป็นสาเหตุที่
ช่อง RB ดูเหมือนหายไป RB จะปรากฏเฉพาะโหมด Fixed / Emitter

ตัวอย่าง URL ที่เลือกโหมดได้โดยตรง:

- <http://127.0.0.1:5000/?mode=divider> — วงจรแบ่งแรงดัน (ค่าเริ่มต้น)
- <http://127.0.0.1:5000/?mode=fixed> — Fixed Bias (ช่อง RB)
- <http://127.0.0.1:5000/?mode=emitter> — Emitter Bias (ช่อง RB, RE)

> ต้องเปิดผ่าน Flask Server เท่านั้น ไม่ใช่ double-click ไฟล์ `index.html`
> เพราะตัวเลขต้องถูกคำนวณจาก Python

## เทสต์

```powershell
python -m unittest discover -s tests -v
```

มี 3 ชุด รวม **39 เทสต์**:

| ไฟล์ | จำนวน | ตรวจอะไร |
|---|---|---|
| `tests/test_dc_bias.py` | 13 | สมการ Divider เดิม, Kirchhoff, ขอบเขตย่าน, validation |
| `tests/test_lab03.py` | 7 | สมการ Fixed/Emitter, RE เปลี่ยนแล้ว IC ลด, adapter ของ Divider, mode helper |
| `tests/test_web.py` | 19 | HTTP ทุกโหมด, dropdown, error, กันผลเก่าค้าง, คำอธิบายปุ่มเปลี่ยนโหมด |

ให้รันจากโฟลเดอร์รากของ repository เพราะเทสต์ import `app` จากโฟลเดอร์ปัจจุบัน

ผลที่รันจริงบันทึกไว้ที่ [`docs/test-log.txt`](docs/test-log.txt) ผลเทียบค่าคำนวณมือ
และตาราง A1–A5 อยู่ที่ [`docs/validation.md`](docs/validation.md)

## หน่วยของข้อมูลเข้า

- `VCC`, `VBE` หน่วยโวลต์ (V)
- `R1`, `R2`, `RB`, `RC`, `RE` หน่วยโอห์ม (Ω) เช่น 100 kΩ ให้กรอก `100000`,
  **1 MΩ ให้กรอก `1000000`**
- `β` คือ DC current gain (hFE) ไม่มีหน่วย และต้องมากกว่า 0

ช่วงที่รับได้: `VCC ≤ 10 kV`, `R ≤ 1 TΩ`, `β ≤ 1 000 000` และ `0 < VBE < VCC`
โหมดที่เลือกจะถูกตรวจเฉพาะช่องที่ใช้จริง เช่น Fixed ไม่ต้องกรอก R1/R2/RE
ค่าที่เกินขอบเขตจะถูกปฏิเสธ ไม่ปล่อยให้แสดงเป็น `inf`/`nan`

## ตัวอย่างอ้างอิง (คำนวณด้วยมือ)

ร่วมกัน: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

| วงจร | อินพุตเพิ่ม | IC | VCE |
|---|---|---|---|
| Divider (A1) | R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 1.2299 mA | 8.0522 V |
| Fixed (A2) | RB=1 MΩ | 1.1300 mA | 9.5140 V |
| Emitter (A3) | RB=1 MΩ, RE=1 kΩ | 1.02634 mA | 8.70545 V |
| Emitter (A4) | RB=1 MΩ, RE=2 kΩ | 0.94010 mA | 8.03278 V |

ย่านการทำงานทั้ง 4 กรณี: **Forward-Active** ตัวเลขข้างบนคำนวณด้วยมือจากสมการใน
[`docs/validation.md`](docs/validation.md) ไม่ได้คัดลอกมาจากผลของโปรแกรม
กรณี A5 (Fixed, RB=0) ต้องได้ error `ต้องมากกว่า 0` และไม่แสดงผลลัพธ์

## แบบจำลองและข้อจำกัด

สมการที่ใช้ (forward-active, β และ VBE คงที่):

```
Divider : VTH = VCC·R2/(R1+R2),  RTH = R1·R2/(R1+R2)
          IB = (VTH − VBE)/(RTH + (β+1)·RE)
Fixed   : IB = (VCC − VBE)/RB,  VE = 0
Emitter : IB = (VCC − VBE)/(RB + (β+1)·RE)
ร่วมกัน  : IC = β·IB,  IE = (β+1)·IB,  VE = IE·RE
          VB = VE + VBE,  VC = VCC − IC·RC,  VCE = VC − VE
```

โปรแกรมจะแจ้งเตือนและไม่รายงานผลว่าเชื่อถือได้ เมื่อสมมติฐาน forward-active ใช้ไม่ได้:

- `IB ≤ 0` → **Cutoff** (ไม่มีกระแสฐาน กระแสที่แสดงเป็น 0)
- `VCE ≤ 0.3 V` (ครอบคลุมเงื่อนไข `≤ 0.2 V` ที่ใบงานกำหนด) → **Saturation**
  ตัวเลขมาจากสมการที่อธิบายวงจรจริงไม่ได้แล้วและถูกขีดฆ่าในหน้าจอ
- `0.3 V < VCE < 1.0 V` → ยังเป็น active แต่เตือนว่า **ใกล้ Saturation**
- drive voltage ใกล้ VBE มาก → ยังเป็น active แต่เตือนว่า **ใกล้ Cutoff**

ผลกระทบที่ยังไม่คิด: Early effect, กระแสรั่ว, การเปลี่ยนแปลงตามอุณหภูมิ,
ความต้านทานของแหล่งจ่าย และค่าคลาดเคลื่อนของอุปกรณ์

## MCP คืออะไร (ตรวจผ่าน Browser)

- **MCP (Model Context Protocol)** คือมาตรฐานที่ให้ AI (MCP client) เรียกใช้
  เครื่องมือภายนอก (MCP server) ผ่านข้อความที่มีโครงสร้าง
- ในงานนี้ **OpenCode เป็น MCP client** และ **Playwright MCP คือ MCP server**
  ที่เปิดให้ AI สั่ง browser ได้ (เปิดหน้า, เลือก dropdown, กรอกฟอร์ม, กดปุ่ม,
  อ่าน snapshot, ถ่าย screenshot)
- **Browser สื่อสารกับ Flask ผ่าน HTTP** ปกติ: browser ส่ง GET/POST ไปที่
  `127.0.0.1:5000` แล้ว Flask คืนหน้า HTML ที่มีตัวเลขจาก Python
- เครื่องนี้ไม่ได้ configure Playwright MCP ไว้ จึงใช้ **OpenCode Browser**
  แทน (เป็น browser tool ในตัวของ harness) — ใบงานให้เครดิตเท่ากัน
- **เครื่องมือ browser รายงานสิ่งที่เห็นเท่านั้น** ไม่ได้พิสูจน์ว่าสมการถูกต้อง
  และไม่แทนที่การคำนวณด้วยมือของนักศึกษา ค่าคาดหมาย A1–A5 ต้องตรวจและรับรอง
  โดยนักศึกษาก่อนใช้ส่งงาน

## โครงสร้างโปรเจกต์

```
BJT-DC-Bias-Web-App/
├── app.py                  # Flask routes, เลือกโหมด, parse ฟอร์ม, จัดรูปแบบหน่วย
├── dc_bias.py              # สมการวิศวกรรมล้วน ๆ (ไม่รู้จัก Flask/HTML)
├── templates/index.html    # dropdown + ฟอร์ม + ตารางผลลัพธ์ (Jinja)
├── static/style.css        # responsive layout
├── tests/
│   ├── test_dc_bias.py
│   ├── test_lab03.py
│   └── test_web.py
├── docs/
│   ├── design-note.md
│   ├── validation.md       # คำนวณมือ + ตาราง A1–A5
│   ├── reflection.md
│   ├── test-log.txt
│   ├── superpowers/        # spec + plan
│   └── screenshots/
├── requirements.txt
├── AGENTS.md
└── README.md
```

## เกณฑ์ตรวจรับ

### Lab 02 (A1–A7)

- [x] A1 `GET /` คืนหน้าฟอร์มด้วย HTTP 200
- [x] A2 `POST /` คำนวณใน Python แล้วแสดงผล
- [x] A3 ผลตรงกับการคำนวณมือภายใต้แบบจำลองเดียวกัน
- [x] A4 ข้อมูลผิด (R≤0, β≤0, ไม่ใช่ตัวเลข, ไม่กรอก) แจ้ง error ที่อ่านได้
- [x] A5 เตือนกรณี Cutoff / Saturation
- [x] A6 เทสต์อัตโนมัติ (13 engineering + 8 HTTP เดิม)
- [x] A7 push ขึ้น GitHub แล้วทำซ้ำได้: clone จาก
      `https://github.com/GTThanakrit/BJT-DC-Bias-Web-App.git`
      แล้ว `pip install -r requirements.txt` + รันเทสต์ผ่าน

### Lab 03 (A1–A5)

ดูตารางผลจริง ค่าคาดหมาย หน่วย วิธีตรวจ และ status ได้ที่
[`docs/validation.md`](docs/validation.md#lab-03--browser-acceptance-cases-a1a5)
— รันจริงใน OpenCode Browser ครบทั้ง 5 กรณี **PASS ทั้งหมด**
(A1 Divider, A2 Fixed, A3/A4 Emitter, A5 RB=0 ถูกปฏิเสธ)
และมี screenshot ของ A3 อยู่ที่
[`docs/screenshots/lab03-emitter.jpeg`](docs/screenshots/lab03-emitter.jpeg)

## บันทึกการส่งงาน / Submission record

- **Repository:** <https://github.com/GTThanakrit/BJT-DC-Bias-Web-App>
- **Commit ที่เป็นโค้ด Lab 03 ครบถ้วน (38 tests):**
  `e94ff7a6e6bdf3b427269c2506d26f7e5c62fc89`
- **Commit URL:**
  <https://github.com/GTThanakrit/BJT-DC-Bias-Web-App/commit/e94ff7a6e6bdf3b427269c2506d26f7e5c62fc89>
- หมายเหตุ: commit ด้านบนคือจุดที่โค้ดและผลตรวจรับครบ ส่วน README นี้ถูกอัปเดตใน
  commit ถัดไปเพื่อบันทึก URL/SHA และผล clone verify (เป็นเอกสารเท่านั้น โค้ดไม่เปลี่ยน)
  และ `docs/reflection.md` ต้องเขียนความเห็นส่วนตัวเพิ่มก่อนส่ง

### ตรวจความสามารถในการทำซ้ำจาก anonymous clone

รันจริงเมื่อ 2026-11-17 จากเครื่องเดียวกันโดยไม่ใช้ credential ที่เก็บไว้:

```powershell
git -c credential.helper= clone https://github.com/GTThanakrit/BJT-DC-Bias-Web-App.git
cd BJT-DC-Bias-Web-App
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลที่ได้:

| ขั้นตอน | ผล |
|---|---|
| clone จาก URL สาธารณะโดยไม่ใช้ credential | สำเร็จ HEAD = `e94ff7a` และมีไฟล์ครบรวม screenshot |
| `pip install -r requirements.txt` (Flask 3.1.3) | สำเร็จ ไม่มี error |
| `python -m unittest discover -s tests -v` | **Ran 38 tests — OK** ที่ commit `e94ff7a` (exit code 0); หลังเพิ่มคำอธิบายปุ่มเปลี่ยนโหมดเป็น **Ran 39 tests — OK** |

### ใครเขียนอะไร / AI-written vs student-checked

| ส่วน | ผู้เขียน | สิ่งที่ต้องตรวจเองก่อนส่ง |
|---|---|---|
| โค้ด Flask, สมการ, เทสต์, เอกสารภาษาไทย และ plan | AI (OpenCode + Superpowers) ช่วยเขียน | อ่านและอธิบายสมการ `IB`, `IC`, `VCE` ให้ได้ด้วยตนเอง |
| spec, plan, ตัวเลขคาดหมาย A1–A5, ตาราง validation | AI ร่างจากสมการ | **นักศึกษาต้องคำนวณมือและรับรองตัวเลข A1–A5 ว่าเป็นของตนเอง** |
| ผล browser A1–A5, screenshot, clone verify | ดำเนินการด้วยเครื่องมือจริง | เปิด URL ใน browser ของตนแล้วเทียบผลอีกครั้ง |
| `docs/reflection.md` ส่วนความเห็น/ปัญหา/สิ่งที่ไม่แน่ใจ | **เว้นไว้ให้เติมเอง** | เขียนด้วยคำของนักศึกษา (ห้ามปล่อย `...`) |

MCP (Model Context Protocol) คือมาตรฐานที่ให้ AI เรียกใช้เครื่องมือภายนอกผ่านข้อความที่มี
โครงสร้าง: ในงานนี้ OpenCode เป็น MCP client และ Playwright MCP คือ MCP server ที่ให้ AI
สั่ง browser ได้ แต่เครื่องนี้ไม่ได้ configure ไว้ จึงใช้ OpenCode Browser แทนตามที่ใบงาน
อนุญาต (ได้เครดิตเท่ากัน) รายละเอียดอยู่ในหัวข้อ **MCP คืออะไร** ด้านบน
