"""Flask entry point for the BJT DC bias web application.

HTTP handling and presentation formatting live here; the engineering math
lives in dc_bias.py.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
    MODES,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIXED,
    MODE_FIELDS,
    REGION_ACTIVE,
    REGION_CUTOFF,
    REGION_SATURATION,
    VBE_NEAR_CUTOFF_MARGIN,
    VCE_NEAR_SATURATION,
    VCE_SATURATION_MAX,
    WARNING_CUTOFF,
    WARNING_NEAR_CUTOFF,
    WARNING_NEAR_SATURATION,
    WARNING_SATURATION,
    compute_divider_bias,
    compute_emitter_bias,
    compute_fixed_bias,
    fields_for_mode,
    validate_mode,
)

app = Flask(__name__)

# Divider specs/defaults are unchanged from Lab 02; the new rb spec is added
# for the fixed and emitter circuits.
_INPUT_SPECS = {
    "vcc": {"key": "vcc", "label": "VCC", "unit": "V", "default": "12", "help": "แรงดันไฟเลี้ยง"},
    "r1": {"key": "r1", "label": "R1", "unit": "Ω", "default": "100000", "help": "VCC → Base"},
    "r2": {"key": "r2", "label": "R2", "unit": "Ω", "default": "22000", "help": "Base → GND"},
    "rb": {"key": "rb", "label": "RB", "unit": "Ω", "default": "1000000", "help": "VCC → Base"},
    "rc": {"key": "rc", "label": "RC", "unit": "Ω", "default": "2200", "help": "VCC → Collector"},
    "re": {"key": "re", "label": "RE", "unit": "Ω", "default": "1000", "help": "Emitter → GND"},
    "beta": {"key": "beta", "label": "β (hFE)", "unit": "", "default": "100", "help": "อัตราขยายกระแส"},
    "vbe": {"key": "vbe", "label": "VBE", "unit": "V", "default": "0.7", "help": "Base → Emitter"},
}

FIELD_SPECS = {
    mode: tuple(_INPUT_SPECS[key] for key in fields)
    for mode, fields in MODE_FIELDS.items()
}

MODE_LABELS = {
    MODE_DIVIDER: "Voltage-Divider Bias",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias",
}

REGION_LABELS = {
    REGION_ACTIVE: ("Forward-Active", "ok"),
    REGION_CUTOFF: ("Cutoff", "warn"),
    REGION_SATURATION: ("Saturation", "bad"),
}


def _blank_fields(mode: str) -> list[dict[str, str]]:
    specs = FIELD_SPECS[mode]
    return [
        {
            "key": spec["key"],
            "label": spec["label"],
            "unit": spec["unit"],
            "default": spec["default"],
            "help": spec["help"],
            "value": spec["default"],
            "error": "",
        }
        for spec in specs
    ]


def _read_form(mode: str) -> tuple[dict[str, float], list[dict[str, str]], dict[str, str]]:
    """Parse only the selected mode's fields into floats, values, errors."""

    fields = _blank_fields(mode)
    values: dict[str, float] = {}
    errors: dict[str, str] = {}

    for field in fields:
        raw = (request.form.get(field["key"]) or "").strip()
        field["value"] = raw
        if not raw:
            errors[field["key"]] = "กรุณากรอกค่านี้"
            continue
        try:
            values[field["key"]] = float(raw)
        except ValueError:
            errors[field["key"]] = "ต้องเป็นตัวเลข"

    errors.update({k: v for k, v in validate_mode(mode, values).items() if k not in errors})
    return values, fields, errors


def _warning_text(code: str | None, result: dict) -> str | None:
    """Turn the engineering warning code into a sentence for the page."""

    if code == WARNING_CUTOFF:
        return (
            "IB ≤ 0: ทรานซิสเตอร์อยู่ในย่าน Cutoff สมการ forward-active "
            "ใช้ไม่ได้ ค่ากระแสที่แสดงจึงเป็นศูนย์โดยประมาณ"
        )
    if code == WARNING_NEAR_CUTOFF:
        vth = result["vth_v"]
        if vth is None:
            return (
                "IB มีค่าน้อยมากจนอาจไวต่ออุณหภูมิและค่าอุปกรณ์จริงมาก "
                "ผลจากแบบจำลอง forward-active อาจคลาดเคลื่อนจากวงจรจริง"
            )
        return (
            f"VTH = {vth:.3f} V ใกล้ VBE มาก (ต่างกันน้อยกว่า "
            f"{VBE_NEAR_CUTOFF_MARGIN * 1000:.0f} mV) กระแสอาจไวต่ออุณหภูมิและ "
            "ค่าอุปกรณ์จริงมาก"
        )
    if code == WARNING_NEAR_SATURATION:
        return (
            f"VCE = {result['vce_v']:.3f} V ใกล้ Saturation มาก (< {VCE_NEAR_SATURATION:.1f} V) "
            "ผลจากแบบจำลอง forward-active อาจคลาดเคลื่อนจากวงจรจริง"
        )
    if code == WARNING_SATURATION:
        return (
            f"VCE = {result['vce_v']:.3f} V ≤ {VCE_SATURATION_MAX:.1f} V: ทรานซิสเตอร์อิ่มตัว "
            "(Saturation) สมการ forward-active ใช้ไม่ได้ ตัวเลขที่แสดงด้านล่างเป็นเพียง "
            "ผลของสมการที่ไม่สอดคล้องกับวงจรจริง ห้ามนำไปใช้"
        )
    return None


def _format_result(result: dict) -> dict[str, object]:
    label, tone = REGION_LABELS[result["region"]]
    rows = []
    if result["vth_v"] is not None:
        rows.append(("VTH", "แรงดันเทียบเท่า Thevenin", f"{result['vth_v']:.3f} V"))
    if result["rth_kohm"] is not None:
        rows.append(("RTH", "ความต้านทานเทียบเท่า Thevenin", f"{result['rth_kohm']:.2f} kΩ"))
    rows.extend(
        [
            ("IB", "กระแสฐาน", f"{result['ib_ua']:.2f} µA"),
            ("IC", "กระแสคอลเล็กเตอร์", f"{result['ic_ma']:.3f} mA"),
            ("IE", "กระแสอิมิตเตอร์", f"{result['ie_ma']:.3f} mA"),
            ("VB", "แรงดันฐาน", f"{result['vb_v']:.3f} V"),
            ("VE", "แรงดันอิมิตเตอร์", f"{result['ve_v']:.3f} V"),
            ("VC", "แรงดันคอลเล็กเตอร์", f"{result['vc_v']:.3f} V"),
            ("VCE", "แรงดันคอลเล็กเตอร์–อิมิตเตอร์", f"{result['vce_v']:.3f} V"),
        ]
    )
    return {
        "region": result["region"],
        "region_label": label,
        "region_tone": tone,
        "trustworthy": result["trustworthy"],
        "rows": rows,
        "warning": _warning_text(result["warning"], result),
    }


def _render(mode, fields, errors, form_error, result):
    return render_template(
        "index.html",
        mode=mode,
        modes=MODES,
        mode_label=MODE_LABELS[mode],
        fields=fields,
        errors=errors,
        form_error=form_error,
        result=result,
    )


@app.get("/")
def index():
    mode = request.args.get("mode", MODE_DIVIDER)
    if fields_for_mode(mode) is None:
        return _render(MODE_DIVIDER, _blank_fields(MODE_DIVIDER), {}, "โหมดวงจรไม่ถูกต้อง", None)
    return _render(mode, _blank_fields(mode), {}, None, None)


@app.post("/")
def calculate():
    mode = request.form.get("mode", MODE_DIVIDER)
    if fields_for_mode(mode) is None:
        return _render(MODE_DIVIDER, _blank_fields(MODE_DIVIDER), {}, "โหมดวงจรไม่ถูกต้อง", None)

    values, fields, errors = _read_form(mode)
    for field in fields:
        if field["key"] in errors:
            field["error"] = errors[field["key"]]

    result = None
    form_error = None
    if not errors:
        try:
            if mode == MODE_FIXED:
                raw = compute_fixed_bias(values)
            elif mode == MODE_EMITTER:
                raw = compute_emitter_bias(values)
            else:
                raw = compute_divider_bias(values)
            result = _format_result(raw)
        except ValueError as exc:
            form_error = f"คำนวณไม่ได้: {exc}"

    return _render(mode, fields, errors, form_error, result)


if __name__ == "__main__":
    app.run()
