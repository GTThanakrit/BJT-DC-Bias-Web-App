# Design note — BJT DC Bias Web App (Lab 02, extended in Lab 03)

## Problem

Students need a working multi-file Flask application that computes the DC
operating point of an NPN common-emitter amplifier. Lab 02 used voltage-divider
bias; Lab 03 adds fixed bias and single-supply emitter bias to the same app.
Opening an HTML file directly is not acceptable: the numbers must come from a
Python calculation triggered by an HTTP request, and the student must verify
the AI-written equations independently.

## Goals

- Accept the parameters of three selectable circuits and return a complete DC
  operating point in a shared result shape.
- Keep the engineering math in a module that knows nothing about HTTP or HTML.
- Show units, the operating region, and an explicit warning when the
  forward-active model stops being valid.
- Be verifiable: automated tests plus an independent hand calculation and
  browser acceptance cases A1–A5.
- Fit inside one 180-minute lab and leave a structure that can grow in W3–W11.

## Non-goals

- AC analysis, gain, Bode plots, transient simulation, load line.
- Writing a SPICE solver or integrating ngspice.
- Bias topologies other than divider, fixed, and emitter; FET support.
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
| `app.py` | Routes, mode dispatch, form parsing, error mapping, display formatting |
| `dc_bias.py` | `validate_inputs`, `validate_mode`, `compute_dc_bias`, `compute_divider_bias`, `compute_fixed_bias`, `compute_emitter_bias`, `result_to_dict`, dataclasses, region rules |
| `templates/index.html` | Mode selector, per-mode form and results markup, no physics |
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

## Lab 03 additions

### Three modes, one result shape

`MODE_DIVIDER` (default), `MODE_FIXED`, and `MODE_EMITTER` are selected with a
`<select name="mode">`. `MODE_FIELDS` lists the fields each circuit uses;
`fields_for_mode()` returns that tuple or `None` for an unknown mode.
`validate_mode()` checks only the selected fields and returns
`{"mode": "โหมดวงจรไม่ถูกต้อง"}` for an unrecognised mode, so a bad mode can
never silently fall back to the divider.

Every `compute_*_bias()` function returns the same dict keys:
`vth_v, rth_kohm, ib_ua, ic_ma, ie_ma, vb_v, ve_v, vc_v, vce_v, region,
warning, trustworthy`. `vth_v` and `rth_kohm` are `None` for fixed and emitter
bias because those circuits have no Thevenin base divider, and the template
omits those two rows. The original `compute_dc_bias()` and `DcBiasResult` are
untouched: `result_to_dict()` adapts them, which is why all nine Lab 02 divider
values remain identical.

Equations: fixed bias uses `IB = (VCC − VBE)/RB` with `VE = 0`; emitter bias
uses `IB = (VCC − VBE)/(RB + (β + 1)·RE)` with `VE = IE·RE`. Both share
`IC = β·IB`, `IE = (β + 1)·IB`, `VB = VE + VBE`, `VC = VCC − IC·RC`, and
`VCE = VC − VE`. Internally ohms and amperes; at the boundary volts,
milliamperes and microamperes.

### Why the mode change needs no JavaScript

Changing mode submits a small `GET /?mode=...` form. Flask rebuilds
`FIELD_SPECS` for that mode and renders only its inputs; the POST form carries
the mode in a hidden field. A full page reload is sufficient for a form with
four to seven text inputs, keeps the project's "no JavaScript required" stack,
avoids stale values from a previously selected circuit, and leaves every value
readable in an accessibility snapshot for browser verification.

## Left to the builder

- Exact wording of warnings and help text.
- Visual design beyond the two-panel responsive layout.
- Whether to add persistence or history in later weeks.

## Risks

- The model is only valid in forward-active; the UI must keep saying so.
- β is treated as constant, so real hardware will differ, especially at low
  VCE.
- Python 3.15 and Flask 3.1 were used; older Python versions are untested.
