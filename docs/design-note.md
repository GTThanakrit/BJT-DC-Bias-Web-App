# Design note — BJT DC Bias Web App (Lab 02)

## Problem

Students need a working multi-file Flask application that computes the DC
operating point of an NPN common-emitter amplifier with voltage-divider bias.
Opening an HTML file directly is not acceptable: the numbers must come from a
Python calculation triggered by an HTTP request.

## Goals

- Accept seven circuit parameters and return a complete DC operating point.
- Keep the engineering math in a module that knows nothing about HTTP or HTML.
- Show units, the operating region, and an explicit warning when the
  forward-active model stops being valid.
- Be verifiable: automated tests plus an independent hand calculation.
- Fit inside one 180-minute lab and leave a structure that can grow in W3–W11.

## Non-goals

- AC analysis, gain, Bode plots, transient simulation, load line.
- Writing a SPICE solver or integrating ngspice.
- Bias topologies other than voltage divider; FET support.
- User accounts, database, deployment.

## Anti-goals

- Numbers hard-coded in the template.
- Reporting a saturated or cut-off result as if the model were valid.
- A single-file script with HTML strings inside the Python code.

## Architecture

```
Browser form ──POST──▶ app.py ──▶ dc_bias.py (pure functions)
                          │
                          └──▶ templates/index.html (Jinja) ──▶ HTML response
```

| File | Responsibility |
|---|---|
| `app.py` | Routes, form parsing, error mapping, display formatting |
| `dc_bias.py` | `validate_inputs`, `compute_dc_bias`, dataclasses, region rules |
| `templates/index.html` | Form and results markup, no physics |
| `static/style.css` | Presentation only |
| `tests/` | Engineering math and HTTP behaviour |

## Decisions

1. **One route, two methods.** `GET /` renders an empty form, `POST /`
   re-renders the same template with results or errors. Simpler than a JSON API
   and matches the "form → server → HTML" flow the course teaches.
2. **Ohms only.** Resistances are entered in ohms rather than accepting `k`
   suffixes. It removes an ambiguous parsing rule and matches the unit shown
   next to each field. The UI states the convention.
3. **Thevenin equivalent of the base divider.** Standard textbook method, so the
   reference numbers can be reproduced by hand.
4. **Region policy.**
   - `VTH ≤ VBE` → Cutoff; currents reported as zero, VCE ≈ VCC, warning shown.
   - `VCE ≤ 0.3 V` → Saturation; the forward-active values are still displayed
     but struck through and labeled invalid.
   - `0.3 V < VCE < 1.0 V` → active with a near-saturation warning.
   - `0 < VTH − VBE < 10 mV` → active with a near-cutoff warning, because the
     operating point is indistinguishable from cutoff at display resolution.
5. **Input bounds.** `VCC ≤ 10 kV`, `R ≤ 1 TΩ`, `β ≤ 1e6`, plus `math.isfinite`
   on every parsed value. The engineering module also re-checks that every
   computed number is finite and raises `ValueError` rather than rendering
   `inf`/`nan` as a valid operating point.
5. **Validation in two layers.** `app.py` converts text to floats (catching
   non-numeric and missing values); `dc_bias.validate_inputs` enforces the
   physics constraints (`R > 0`, `β > 0`, `VCC > 0`, `0 < VBE < VCC`).
6. **Thai interface, English engineering terms.** Matches the handout language
   while keeping symbol names (`VCE`, `β`) conventional.

## Left to the builder

- Exact wording of warnings and help text.
- Visual design beyond the two-panel responsive layout.
- Whether to add persistence or history in later weeks.

## Risks

- The model is only valid in forward-active; the UI must keep saying so.
- β is treated as constant, so real hardware will differ, especially at low
  VCE.
- Python 3.15 and Flask 3.1 were used; older Python versions are untested.
