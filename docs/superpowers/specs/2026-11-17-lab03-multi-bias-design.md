# Lab 03 design — one Flask app, three BJT bias circuits

Date: 2026-11-17

## Intent

Extend the existing Lab 02 Flask app so the same page can solve three NPN
common-emitter DC bias circuits: the existing voltage-divider circuit plus
fixed bias and single-supply emitter bias. The point of the lab is not just
more equations: the student must check the AI-written math, see the mode
selection happen in Flask, and verify the real page in a browser against
independently calculated reference values.

## Goals

- Select `divider` (default), `fixed`, or `emitter` on the form.
- Show only the inputs the selected circuit needs; reject an unknown mode.
- Keep every existing Lab 02 result bit-for-bit identical.
- Add `compute_fixed_bias()` and `compute_emitter_bias()` in `dc_bias.py`,
  returning a `dict` with the same keys and units as the other circuit.
- Warn when the forward-active model is invalid (`IB <= 0` or `VCE <= 0.2 V`),
  in addition to the existing tiered warnings.
- Record browser acceptance cases A1–A5 with expected values, units, observed
  values, method and status.

## Non-goals

- AC, transient, SPICE, load line, bypass capacitors, FET, other topologies.
- New `unittest` cases (Lab 03 explicitly says to keep the Lab 02 suite).
- JavaScript, a new project, a database, or a deployment.

## Anti-goals

- Numbers or equations computed in Jinja.
- Silently treating an unknown mode as `divider`.
- Showing stale results from a previous submission after an input error.
- Presenting a saturation/cut-off value as trustworthy.

## Constraints

- Python 3.10+, Flask 3.x, Jinja templates, plain CSS, no build step.
- `dc_bias.py` stays pure: numbers in, data out, no Flask/HTML/I/O.
- Units: ohms in, volts and amperes internally, V / mA / µA out. Source
  resistances are entered in ohms (1 MΩ = 1000000).
- UI text in Thai with English engineering symbols; code and docs in English.
- Existing `compute_dc_bias()` and `DcBiasResult` must not change.

## Approaches considered

1. **Dropdown + form reload (chosen).** A `<select name="mode">` submits with
   GET (`/?mode=fixed`); `app.py` rebuilds `FIELD_SPECS` for that mode and the
   existing Jinja loop renders only those fields. POST carries a hidden `mode`
   field. Cost: one page reload when changing mode. Benefit: no JavaScript,
   accessible labels kept, no stale field values, matches the no-JS stack.
2. **Always show all seven/eight fields, disable irrelevant ones.** No reload,
   but A2 ("works without RE") and A3 ("uses RE") become hard to demonstrate,
   and disabled inputs still carry old values that are easy to submit by
   accident. Rejected.
3. **JavaScript toggles fields in place.** Nicer interaction, but the project
   declares no JavaScript required; rejected as unnecessary for a 180-minute
   lab and for browser-based grading.

For the result shape: all three circuit functions return a shared `dict`
(`vb_v, ve_v, vc_v, vce_v, ic_ma, ib_ua, ie_ma, vth_v, rth_kohm, region,
warning, trustworthy`). `compute_dc_bias()` keeps its dataclass so the 21
existing tests stay valid; a small adapter converts its result to the shared
dict. Returning dataclasses from the new functions was rejected because the
rubric explicitly asks for `dict`; hard-coding values in HTML was rejected as
an anti-goal.

## Decisions

- Mode keys: `divider`, `fixed`, `emitter`; default `divider`.
- Common inputs: `vcc`, `rc`, `beta`, `vbe`.
  `fixed` adds `rb`; `emitter` adds `rb`, `re`; `divider` keeps `r1`, `r2`, `re`.
- Equations (forward-active, constant β and VBE), with Ω and A internally:
  - Fixed: `IB = (VCC - VBE) / RB`, `VE = 0`
  - Emitter: `IB = (VCC - VBE) / (RB + (β+1)·RE)`, `VE = IE·RE`
  - Divider: unchanged
  - Shared: `IC = β·IB`, `IE = (β+1)·IB`, `VB = VE + VBE`,
    `VC = VCC - IC·RC`, `VCE = VC - VE`
- Validation is mode-aware: parse only the fields shown, require them all,
  apply the existing finite/positive/upper-bound rules, and reject an
  unrecognised mode with a readable Thai error. `validate_inputs()` stays as
  the divider-facing wrapper so the old tests keep passing.
- Warnings: keep the Lab 02 tiered rules for every mode and add the Lab 03
  conditions (`IB <= 0` → cutoff warning, `VCE <= 0.2 V` → model-invalid
  warning) so the stricter rule wins. Saturation values remain struck through.
- Reference values for A1–A5 are derived by hand from the equations above,
  written into `docs/validation.md`, and the student must check and own them
  before submission. Browser method is recorded as OpenCode Browser (the
  Playwright MCP path is not configured on this machine); grading gives equal
  credit to either method.

## Left to the builder

- Exact Thai wording of validation and warning sentences.
- CSS for the mode selector; keep the existing two-panel responsive layout.
- Where to place the A1–A5 table (existing `docs/validation.md` is the choice).
