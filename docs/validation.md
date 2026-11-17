# Validation — engineering check

## Independent hand calculation

Inputs: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ,
β = 100, VBE = 0.70 V.

Step by step, without using the application:

1. `VTH = 12 × 22 000 / (100 000 + 22 000) = 2.1639 V`
2. `RTH = 100 000 × 22 000 / 122 000 = 18 032.79 Ω`
3. `IB = (2.1639 − 0.70) / (18 032.79 + 101 × 1 000) = 12.2986 µA`
4. `IC = 100 × 12.2986 µA = 1.22986 mA`
5. `IE = 101 × 12.2986 µA = 1.24216 mA`
6. `VE = 1.24216 mA × 1 kΩ = 1.2422 V`
7. `VB = 1.2422 + 0.70 = 1.9422 V`
8. `VC = 12 − 1.22986 mA × 2.2 kΩ = 9.2943 V`
9. `VCE = 9.2943 − 1.2422 = 8.0522 V`

Sanity checks: `IE = IB + IC` (1.2422 = 0.0123 + 1.2299 mA), `VTH > VBE`
(2.164 > 0.7, so not cut off), `VCE = 8.05 V` (far from saturation).

## Application output

| Quantity | Hand calculation | App output |
|---|---|---|
| VTH | 2.1639 V | 2.164 V |
| RTH | 18 032.79 Ω | 18.03 kΩ |
| IB | 12.2986 µA | 12.30 µA |
| IC | 1.22986 mA | 1.230 mA |
| IE | 1.24216 mA | 1.242 mA |
| VB | 1.9422 V | 1.942 V |
| VE | 1.24216 V | 1.242 V |
| VC | 9.2943 V | 9.294 V |
| VCE | 8.0522 V | 8.052 V |

Agreement is within display rounding (3 decimals). Region reported:
Forward-Active.

## Boundary behaviour

| Case | Input | Expected | Observed |
|---|---|---|---|
| Cutoff | R2 = 1 kΩ → VTH = 0.119 V ≤ VBE | region Cutoff, IC = 0, VCE = VCC, warning | matches |
| Cutoff boundary | R1 = 7.5 kΩ, R2 = 500 Ω, VBE = 0.75 V → VTH = VBE | treated as Cutoff (`<=`) | matches |
| Near cutoff | R2 = 6.242 kΩ → VTH − VBE = 5 mV | active + near-cutoff warning | matches |
| Saturation | R1 = R2 = 10 kΩ, RC = 20 kΩ → VCE < 0 | region Saturation, values struck through, warning | matches |
| Near saturation | RC = 8.2 kΩ → VCE ≈ 0.67 V | active + near-saturation warning | matches |
| R1 = 0 | invalid | "ต้องมากกว่า 0", no result | matches |
| VCC = "abc" | non-numeric | "ต้องเป็นตัวเลข", no result | matches |
| Missing field | empty input | "กรุณากรอกค่านี้" | matches |
| NaN / inf / 1e300 | out of range | rejected by the finite/bounds check, no `inf` cell | matches |
| Huge but valid | R1 = 1e12 Ω | computes finite values | matches |

## Second, independent circuit

VCC = 15 V, R1 = 47 kΩ, R2 = 10 kΩ, RC = 3.3 kΩ, RE = 1 kΩ, β = 150,
VBE = 0.70 V.

Hand calculation: VTH = 2.6316 V, RTH = 8 245.6 Ω, IB = 12.1296 µA,
IC = 1.81943 mA, IE = 1.83156 mA, VE = 1.8316 V, VB = 2.5316 V,
VC = 8.9959 V, VCE = 7.1643 V. The application matches, which shows the result
is genuinely computed rather than copied from the first case.

## Lab 03 — hand derivation for the two new circuits

Common to A2–A5: VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V.

### Fixed bias (A2: RB = 1 MΩ)

1. `IB = (VCC − VBE) / RB = (12 − 0.70) / 1 000 000 = 11.30 µA`
2. `IC = β·IB = 100 × 11.30 µA = 1.1300 mA`
3. `IE = (β + 1)·IB = 101 × 11.30 µA = 1.1413 mA`
4. `VE = 0 V` — the emitter is tied directly to ground; there is no RE
5. `VB = VE + VBE = 0.7000 V`
6. `VC = VCC − IC·RC = 12 − 1.1300 mA × 2.2 kΩ = 9.5140 V`
7. `VCE = VC − VE = 9.5140 V`

### Emitter bias (A3: RB = 1 MΩ, RE = 1 kΩ)

1. `RB + (β + 1)·RE = 1 000 000 + 101 × 1 000 = 1 101 000 Ω`
2. `IB = (VCC − VBE) / 1 101 000 = 11.30 / 1 101 000 = 10.2634 µA`
3. `IC = 100 × 10.2634 µA = 1.02634 mA`
4. `IE = 101 × 10.2634 µA = 1.03660 mA`
5. `VE = IE·RE = 1.03660 mA × 1 kΩ = 1.03660 V`
6. `VB = VE + VBE = 1.73660 V`
7. `VC = 12 − 1.02634 mA × 2.2 kΩ = 9.74205 V`
8. `VCE = VC − VE = 8.70545 V`

### Emitter bias with RE doubled (A4: RE = 2 kΩ)

1. `RB + (β + 1)·RE = 1 000 000 + 101 × 2 000 = 1 202 000 Ω`
2. `IB = 11.30 / 1 202 000 = 9.4010 µA`
3. `IC = 0.94010 mA`, `IE = 0.94950 mA`
4. `VE = 0.94950 mA × 2 kΩ = 1.8990 V`, `VB = 2.5990 V`
5. `VC = 12 − 0.94010 mA × 2.2 kΩ = 9.93178 V`
6. `VCE = 9.93178 − 1.8990 = 8.03278 V`

`IC` falls from 1.02634 mA to 0.94010 mA when RE doubles: the denominator gains
another `(β + 1)·1 kΩ = 101 kΩ` of reflected emitter resistance, so base current
and therefore collector current decrease.

The divider value (A1) is unchanged from Lab 02: `compute_divider_bias()` adapts
the untouched `compute_dc_bias()` result to the shared dict, so all nine rows
stay identical.

## Lab 03 — browser acceptance cases A1–A5

Tolerance: `±0.01 mA` for IC and `±0.02 V` for VCE. Method: OpenCode Browser
(Playwright MCP is not configured on this machine). Observed values and status
are filled in after the cases have actually been run.

| Case | Mode | Inputs (Ω unless noted) | Expected IC | Expected VCE / message | Observed | Status |
|---|---|---|---|---|---|---|
| A1 | Divider | R1=100000, R2=22000, RE=1000; VCC=12 V, RC=2200, β=100, VBE=0.7 V | 1.2299 mA | 8.0522 V | — | NOT RUN |
| A2 | Fixed | RB=1000000; VCC=12 V, RC=2200, β=100, VBE=0.7 V | 1.1300 mA | 9.5140 V | — | NOT RUN |
| A3 | Emitter | RB=1000000, RE=1000; VCC=12 V, RC=2200, β=100, VBE=0.7 V | 1.02634 mA | 8.70545 V | — | NOT RUN |
| A4 | Emitter | RB=1000000, RE=2000; VCC=12 V, RC=2200, β=100, VBE=0.7 V | 0.94010 mA | 8.03278 V | — | NOT RUN |
| A5 | Fixed | RB=0; VCC=12 V, RC=2200, β=100, VBE=0.7 V | n/a (rejected) | `ต้องมากกว่า 0`, no result | — | NOT RUN |

## Automated tests

```
python -m unittest discover -s tests -v
Ran 38 tests — OK
```

- `tests/test_dc_bias.py` — 13 tests: two hand-calculated operating points,
  Kirchhoff/Ohm consistency, cutoff, cutoff boundary (`VTH == VBE`),
  near-cutoff, saturation, near-saturation, and five validation rules
  (zero/negative, non-positive β and VCC, VBE ≥ VCC, NaN/inf/out-of-range).
- `tests/test_lab03.py` — 7 tests: fixed bias hand calculation, emitter bias
  hand calculation, IC falling when RE increases, divider adapter keeping the
  shared result keys, unknown mode returning no fields, common fields present
  in every mode, and missing `rb` reported by `validate_mode`.
- `tests/test_web.py` — 18 tests: the original 8 (GET form, POST calculation,
  recomputation for a different circuit, zero resistance, non-numeric, missing
  field, cutoff, saturation) plus 10 mode tests (per-mode field lists, selector,
  hidden mode, fixed/emitter POST values, unknown mode, invalid/zero RB, and no
  stale result after an error).

![Forward-active result](screenshots/forward-active.jpeg)

Screenshot of the reference case computed by the running Flask app.

## Limitations acknowledged

The model assumes constant β and VBE and ignores Early effect, leakage,
temperature and source resistance. Results in cutoff or saturation are not
physical predictions of this model, and the UI says so rather than presenting
them as valid.
