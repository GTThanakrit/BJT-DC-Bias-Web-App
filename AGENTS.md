# AGENTS.md — conventions for this repository

## Stack

- Python 3.10+ , Flask 3.x, Jinja templates, plain CSS. No JavaScript required.
- No build step, no Node tooling, no database.

## Structure rules

- `dc_bias.py` is pure Python: no Flask import, no HTML, no I/O. It takes
  numbers and returns numbers (dataclasses).
- `app.py` owns HTTP: form parsing, error mapping, display formatting.
- `templates/` renders only what it is given; never compute physics in Jinja
  (a static formula reference panel is display-only and allowed).
- `static/style.css` for presentation only.

## Engineering rules

- Forward-active model only: constant β and VBE.
- Always report units and keep one consistent convention: ohms in, volts and
  amperes internally, V / mA / µA out.
- Any result outside forward-active must carry a warning; never present a
  saturated or cut-off value as trustworthy.
- Validation lives in `dc_bias.validate_inputs` (physics) and `app.py`
  (parsing), not in the template.

## Workflow

- Run tests before every commit:
  `python -m unittest discover -s tests -v`
- Keep changes small and commit messages descriptive.
- Never commit `.venv/`, `.env`, API keys, or captured credentials.
- Update `docs/validation.md` when equations, thresholds, or reference values
  change.

## Language

UI text is Thai with English engineering terms (VCC, VBE, β, Forward-Active).
Code comments and documentation are English.
