# BJT DC Bias Simulator — ENG29 2121 Lab 02

Flask web application that computes the DC operating point of an NPN BJT
common-emitter amplifier with **voltage-divider bias**, using the
forward-active approximation.

The calculations run in Python on the server. The HTML page never computes or
hard-codes a result.

## Scope (Week 2)

| In scope | Out of scope |
|---|---|
| Input: VCC, R1, R2, RC, RE, β, VBE | AC small-signal, gain, Bode plot |
| Output: VTH, RTH, IB, IC, IE, VB, VE, VC, VCE | Transient / signal generator |
| Input validation and region warnings | SPICE solver, load line |
| Unit tests + Flask HTTP tests | FET, other bias topologies |

## Requirements

- Python 3.10 or newer
- Flask 3.x (installed from `requirements.txt`)

## Install and run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate         # Linux / macOS
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

Open <http://127.0.0.1:5000/> in a browser.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Two suites run: `tests/test_dc_bias.py` (engineering math, 13 tests) and
`tests/test_web.py` (HTTP routes through Flask's test client, 8 tests).
Run both commands from the repository root: the tests import `app` from the
current directory.

## Input units

- `VCC`, `VBE` in volts.
- `R1`, `R2`, `RC`, `RE` in ohms. Enter `100000` for 100 kΩ.
- `β` is the DC current gain hFE (dimensionless, > 0).

Accepted range: `VCC ≤ 10 kV`, `R ≤ 1 TΩ`, `β ≤ 1 000 000`, and `0 < VBE < VCC`.
Values outside these bounds are rejected instead of producing `inf`/`nan`.

## Reference case

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100,
VBE = 0.70 V.

| Quantity | Value |
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

Region: **Forward-Active**.

The numbers above are derived by hand from the equations in
`docs/validation.md`, not copied from the app output.

## Model and limitations

Equations used (forward-active, constant β and VBE):

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

The app reports a warning and refuses to present the result as trustworthy when
the forward-active assumption fails:

- `VTH ≤ VBE` → **Cutoff** (no base current; the currents are reported as 0).
- `VCE ≤ 0.3 V` → **Saturation** (values shown come from equations that no
  longer describe the circuit).
- `0.3 V < VCE < 1.0 V` → still active, but flagged as **near saturation**.
- `0 < VTH − VBE < 10 mV` → still active, but flagged as **near cutoff**.

Ignored effects: Early effect, leakage currents, temperature drift, source
resistance, component tolerance.

## Project layout

```
transistor-simulator/
├── app.py                  # Flask routes, form parsing, display formatting
├── dc_bias.py              # engineering calculations (no Flask/HTML)
├── templates/index.html    # Jinja form + results
├── static/style.css        # responsive layout
├── tests/
│   ├── test_dc_bias.py
│   └── test_web.py
├── docs/
│   ├── design-note.md
│   ├── validation.md
│   └── reflection.md
├── requirements.txt
├── AGENTS.md
└── README.md
```

## Submission checklist (handout A1–A7)

- [x] A1 `GET /` returns the form with HTTP 200
- [x] A2 `POST /` computes in Python and renders results
- [x] A3 results agree with an independent hand calculation
- [x] A4 invalid input (R≤0, β≤0, non-numeric, missing) shows readable errors
- [x] A5 cutoff / saturation warnings
- [x] A6 21 automated tests (13 engineering + 8 HTTP)
- [x] A7 repository pushed and reproducible: a fresh clone of
      `https://github.com/GTThanakrit/BJT-DC-Bias-Web-App.git` installs with
      `pip install -r requirements.txt` and passes all 21 tests
