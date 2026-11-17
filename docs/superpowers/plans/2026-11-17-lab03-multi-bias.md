# Lab 03 Multi-Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fixed-bias and emitter-bias modes to the existing Lab 02 Flask app, keep the divider result unchanged, and verify A1–A5 in a real browser.

**Architecture:** `dc_bias.py` gains two pure circuit functions and a mode-aware validator, all returning a shared `dict` shape; `app.py` parses a `mode` field, rebuilds the field list for that mode, and dispatches with `if/elif`; Jinja renders only the fields it is given. Mode changes use a GET form reload, so no JavaScript is needed. The existing `compute_dc_bias()`/`DcBiasResult` stay untouched.

**Tech Stack:** Python 3.10+, Flask 3.x, Jinja, plain CSS, `unittest`, OpenCode Browser (or Playwright MCP if configured).

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

## Global Constraints

- Python 3.10+, Flask 3.x, Jinja templates, plain CSS, no build step.
- `dc_bias.py` stays pure: numbers in, data out, no Flask/HTML/I/O.
- Units: ohms in, volts and amperes internally, V / mA / µA out. Resistances are entered in ohms (1 MΩ = 1000000).
- UI text in Thai with English engineering symbols; code comments and docs in English.
- `compute_dc_bias()` and `DcBiasResult` must not be modified.
- No JavaScript. No new dependencies. No `.venv`, `.env`, or credentials committed.
- Run `python -m unittest discover -s tests -v` from the repository root before every commit.

## Review Focus

- `mode=bogus` must produce a readable error, never fall back to divider — pinned by Task 2 HTTP test `test_unknown_mode_is_rejected`.
- POST with `mode=fixed` but missing `rb` must show an error and no result — pinned by Task 2 `test_fixed_missing_rb_has_no_result`.
- After an error, the previous result must not remain on the page — pinned by Task 2 `test_invalid_input_does_not_show_stale_result`.
- Changing only `RE` from 1 kΩ to 2 kΩ in emitter mode must change `IC` (1.026 → 0.940 mA, decreasing) — pinned by Task 4 A4 browser case and Task 1 `test_emitter_ic_falls_when_re_increases`.
- Divider inputs must keep giving `IC = 1.230 mA`, `VCE = 8.052 V` after the refactor — pinned by Task 1 `test_divider_result_unchanged` and Task 4 A1 browser case.

---

### Task 1: Pure engineering functions and mode-aware validation

**Files:**
- Modify: `dc_bias.py`
- Create: `tests/test_lab03.py`

**Interfaces:**
- Consumes: existing `DcBiasInputs`, `compute_dc_bias`, `DcBiasResult`, `validate_inputs`, `WARNING_*`, `REGION_*` from `dc_bias.py`.
- Produces: `MODE_DIVIDER = "divider"`, `MODE_FIXED = "fixed"`, `MODE_EMITTER = "emitter"`, `MODES`, `MODE_FIELDS` (mapping mode → field keys in display order), `COMMON_FIELDS = ("vcc", "rc", "beta", "vbe")`, `RESULT_KEYS`; `fields_for_mode(mode) -> tuple[str, ...] | None`; `validate_mode(mode, values: Mapping[str, float]) -> dict[str, str]`; `compute_fixed_bias(values) -> dict`, `compute_emitter_bias(values) -> dict`, `compute_divider_bias(values) -> dict`; `result_to_dict(result: DcBiasResult) -> dict`. Every compute function returns keys `vth_v, rth_kohm, ib_ua, ic_ma, ie_ma, vb_v, ve_v, vc_v, vce_v, region, warning, trustworthy`; `vth_v` and `rth_kohm` are `None` when the circuit has no Thevenin equivalent.

- [ ] **Step 1: Write failing tests in `tests/test_lab03.py`** for fixed bias `VCC=12, RB=1e6, RC=2200, β=100, VBE=0.70` expecting `ib_ua=11.300`, `ic_ma=1.130`, `ve_v=0.0`, `vb_v=0.700`, `vc_v=9.514`, `vce_v=9.514`; for emitter bias `RB=1e6, RE=1000` expecting `ib_ua=10.2634`, `ic_ma=1.02634`, `ve_v=1.03660`, `vce_v=8.70545`; for emitter `RE=2000` expecting `ic_ma=0.94010` and `ic_ma` strictly less than the 1 kΩ case; for `compute_divider_bias` with the Lab 02 reference inputs expecting `ic_ma=1.22986`, `vce_v=8.05216` and all `RESULT_KEYS` present; for `fields_for_mode("bogus") is None`; and for `validate_mode("fixed", {"vcc": 12.0, "rc": 2200.0, "beta": 100.0, "vbe": 0.7})` reporting `rb` as missing.
- [ ] **Step 2: Run `python -m unittest tests.test_lab03 -v` from the repo root; confirm it fails with import/attribute errors.**
- [ ] **Step 3: Implement the constants and `fields_for_mode` in `dc_bias.py`.** Field order follows the spec: common fields first, then `rb`/`re`/`r1`,`r2`,`re`.
- [ ] **Step 4: Implement `validate_mode`.** Reuse the existing finite/positive/upper-bound rules; return `{"mode": "โหมดวงจรไม่ถูกต้อง"}` when the mode is unknown, and a missing-field error for each required field absent from `values`.
- [ ] **Step 5: Implement `result_to_dict`, `compute_fixed_bias`, `compute_emitter_bias`, `compute_divider_bias`.** Equations come verbatim from the design doc. Reuse the Lab 02 warning codes; for `IB <= 0` return `region="cutoff"` with a warning, and mark `trustworthy=False` whenever Lab 02 would mark saturation. Convert amperes to `ib_ua`/`ic_ma`/`ie_ma` and ohms to `rth_kohm` inside these functions.
- [ ] **Step 6: Run `python -m unittest discover -s tests -v`; expect the original 21 tests plus the new ones to pass.**
- [ ] **Step 7: Commit** with message `Add fixed and emitter bias engineering functions`.

### Task 2: Flask mode dispatch and validation

**Files:**
- Modify: `app.py`
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: `MODES`, `MODE_FIELDS`, `COMMON_FIELDS`, `fields_for_mode`, `validate_mode`, `compute_*_bias`, `RESULT_KEYS` from Task 1.
- Produces: `index()` accepts optional `?mode=...`; `calculate()` reads hidden `mode`; template receives `mode`, `modes`, `mode_label`, `fields`, `result`, `errors`, `form_error`. `result` is the shared dict plus display-only `rows` and `region_label`/`region_tone`.

- [ ] **Step 1: Add HTTP tests to `tests/test_web.py`** for: GET `/?mode=fixed` showing `name="rb"` and not `name="r1"`; GET `/?mode=emitter` showing `name="re"` and not `name="r1"`; POST `mode=fixed` with `rb=1000000` yielding `9.514 V` and `1.130 mA`; POST `mode=emitter` with `rb=1000000, re=1000` yielding `8.705 V`; POST `mode=bogus` yielding a mode error and no result; POST `mode=fixed` with `rb=0` yielding `ต้องมากกว่า 0` and no result; POST with a valid case followed by an invalid case yielding no result in the second response.
- [ ] **Step 2: Run `python -m unittest tests.test_web -v`; confirm the new tests fail.**
- [ ] **Step 3: Refactor `FIELD_SPECS` into a mode-keyed spec mapping** while keeping the existing `divider` specs and defaults exactly as-is; add `rb` (default `1000000`, help `VCC → Base`) and reuse the `re` spec for emitter.
- [ ] **Step 4: Update `index()`** to read `request.args.get("mode", MODE_DIVIDER)`, fall back to divider with an error for an unknown mode, and pass `mode`, `modes`, `mode_label`, and the fields for that mode to the template.
- [ ] **Step 5: Update `_read_form()` / `calculate()`** to parse only `fields_for_mode(mode)`, call `validate_mode`, dispatch via `if/elif` to the three `compute_*_bias` functions, and set `result=None` whenever `errors` or `form_error` is present. Build `rows` from the shared dict, omitting `vth_v`/`rth_kohm` rows when their value is `None`.
- [ ] **Step 6: Run the full suite; expect all tests green and the original divider POST test still asserting `9.294 V` / `1.230 mA` / `8.052 V`.**
- [ ] **Step 7: Commit** with message `Select bias circuit by mode in Flask`.

### Task 3: Template and styling

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`

**Interfaces:**
- Consumes: `mode`, `modes`, `mode_label`, `fields`, `result`, `errors`, `form_error` from Task 2.
- Produces: a mode selector that reloads the form by GET and a results section that names the selected mode.

- [ ] **Step 1: Add a mode `<form method="get">` with `<select name="mode">` and an `onchange`-free submit button** (`เลือกวงจร`) above the main form; mark the current mode `selected`. Add a hidden `<input name="mode">` inside the POST form.
- [ ] **Step 2: Show the selected mode in the results heading** and keep the results/warning/table markup unchanged otherwise, including the `untrusted` strikethrough for invalid regions.
- [ ] **Step 3: Replace the static formula list with three short, static per-mode lists** chosen by `mode` in Jinja; these are display-only and must not compute anything.
- [ ] **Step 4: Add minimal CSS for the selector row;** verify the two-panel responsive layout still works at a narrow viewport.
- [ ] **Step 5: Run the full test suite and reload `http://127.0.0.1:5000/` in the browser; commit** with message `Add circuit mode selector to bias form`.

### Task 4: Hand-calculated references and documentation

**Files:**
- Modify: `docs/validation.md`
- Modify: `docs/design-note.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: A1–A5 expected values listed below, derived by hand from the design-doc equations with `VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V`.
- Produces: a completed A1–A5 table with expected values, units, observed values, method `OpenCode Browser`, and `PASS`; a Thai README run guide for all three modes.

Hand-derived expectations (student must check and own these before submission):
- A1 divider (R1=100 kΩ, R2=22 kΩ, RE=1 kΩ): `IC = 1.2299 mA`, `VCE = 8.0522 V`
- A2 fixed (RB=1 MΩ): `IC = 1.1300 mA`, `VCE = 9.5140 V`
- A3 emitter (RB=1 MΩ, RE=1 kΩ): `IC = 1.02634 mA`, `VCE = 8.70545 V`
- A4 emitter (RE=2 kΩ): `IC = 0.94010 mA`, `VCE = 8.03278 V`; `IC` decreases vs A3 because the denominator gains another 100 kΩ of reflected emitter resistance
- A5 fixed (RB=0): validation error `ต้องมากกว่า 0`, no result

- [ ] **Step 1: Replace the A1–A5 table in `docs/validation.md`** with the cases above, leaving observed/status blank until Task 5; state tolerance `±0.01 mA` for `IC` and `±0.02 V` for `VCE`.
- [ ] **Step 2: Add the two new circuits' hand derivations** to `docs/validation.md`, including `RB + (β+1)RE` and `VE = 0` for fixed bias, and note that the Lab 02 divider value is unchanged.
- [ ] **Step 3: Update `docs/design-note.md`** with the new functions, shared dict keys, and the reason the mode reload needs no JavaScript.
- [ ] **Step 4: Update the Thai `README.md`** with the three modes, the `?mode=` URL examples, the ohm convention (1 MΩ = 1000000), a pointer to the A1–A5 table, and a short section explaining MCP: OpenCode is the MCP client, Playwright MCP is the MCP server, the browser talks to Flask over HTTP, and this run used OpenCode Browser because Playwright MCP is not configured. State clearly that browser tools only report results and never replace the student's own hand calculation.
- [ ] **Step 5: Commit** with message `Document Lab 03 modes and acceptance references`.

### Task 5: Browser acceptance, self-review and submission record

**Files:**
- Modify: `docs/validation.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the A1–A5 table from Task 4 and the running Flask server at `http://127.0.0.1:5000/`.
- Produces: observed values filled in, at least one screenshot committed, final README with GitHub URL and commit SHA.

- [ ] **Step 1: Start the server** with `.venv\Scripts\python.exe -m flask --app app run --port 5000` and confirm HTTP 200.
- [ ] **Step 2: Run A1–A5 in the browser with OpenCode Browser tools.** For each case, open the page, select the mode, fill the values, submit, read the post-submit snapshot, and record the exact `IC`/`VCE` or error message with units. Use a fresh snapshot after every mode change or submit. Mark `PASS`/`FAIL` against the Task 4 tolerance.
- [ ] **Step 3: Save a screenshot of at least one successful case** to `docs/screenshots/lab03-emitter.jpeg` and embed it in `docs/validation.md`.
- [ ] **Step 4: Re-run one case yourself in the browser** (recommended A4) and write a short note in `docs/validation.md` explaining how `RE` travels from the form field to `compute_emitter_bias`, per the spec's closing question.
- [ ] **Step 5: Run `python -m unittest discover -s tests -v`** from the repo root; expect green, then update `docs/test-log.txt`.
- [ ] **Step 6: Fill the final commit SHA and repository URL in `README.md`, commit, and push to `origin/main`.**
- [ ] **Step 7: Verify with an anonymous clone** (`git -c credential.helper= clone ...`) that `pip install -r requirements.txt` and the full test suite pass; record the result in `README.md` and push the follow-up commit.
