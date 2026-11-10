"""Flask entry point for the BJT DC bias web application.

HTTP handling and presentation formatting live here; the engineering math
lives in dc_bias.py.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import (
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
    DcBiasInputs,
    DcBiasResult,
    compute_dc_bias,
    validate_inputs,
)

app = Flask(__name__)

FIELD_SPECS = (
    {"key": "vcc", "label": "VCC", "unit": "V", "default": "12", "help": "แรงดันไฟเลี้ยง"},
    {"key": "r1", "label": "R1", "unit": "Ω", "default": "100000", "help": "VCC → Base"},
    {"key": "r2", "label": "R2", "unit": "Ω", "default": "22000", "help": "Base → GND"},
    {"key": "rc", "label": "RC", "unit": "Ω", "default": "2200", "help": "VCC → Collector"},
    {"key": "re", "label": "RE", "unit": "Ω", "default": "1000", "help": "Emitter → GND"},
    {"key": "beta", "label": "β (hFE)", "unit": "", "default": "100", "help": "อัตราขยายกระแส"},
    {"key": "vbe", "label": "VBE", "unit": "V", "default": "0.7", "help": "Base → Emitter"},
)

REGION_LABELS = {
    REGION_ACTIVE: ("Forward-Active", "ok"),
    REGION_CUTOFF: ("Cutoff", "warn"),
    REGION_SATURATION: ("Saturation", "bad"),
}


def _blank_fields() -> list[dict[str, str]]:
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
        for spec in FIELD_SPECS
    ]


def _read_form() -> tuple[dict[str, float], list[dict[str, str]], dict[str, str]]:
    """Parse the submitted form into floats, returning values, fields, errors."""

    fields = _blank_fields()
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

    errors.update({k: v for k, v in validate_inputs(values).items() if k not in errors})
    return values, fields, errors


def _warning_text(code: str | None, result: DcBiasResult) -> str | None:
    """Turn the engineering warning code into a sentence for the page."""

    if code == WARNING_CUTOFF:
        return (
            "VTH ≤ VBE: ทรานซิสเตอร์อยู่ในย่าน Cutoff สมการ forward-active "
            "ใช้ไม่ได้ ค่ากระแสที่แสดงจึงเป็นศูนย์โดยประมาณ"
        )
    if code == WARNING_NEAR_CUTOFF:
        return (
            f"VTH = {result.vth:.3f} V ใกล้ VBE มาก (ต่างกันน้อยกว่า "
            f"{VBE_NEAR_CUTOFF_MARGIN * 1000:.0f} mV) กระแสอาจไวต่ออุณหภูมิและ "
            "ค่าอุปกรณ์จริงมาก"
        )
    if code == WARNING_NEAR_SATURATION:
        return (
            f"VCE = {result.vce:.3f} V ใกล้ Saturation มาก (< {VCE_NEAR_SATURATION:.1f} V) "
            "ผลจากแบบจำลอง forward-active อาจคลาดเคลื่อนจากวงจรจริง"
        )
    if code == WARNING_SATURATION:
        return (
            f"VCE = {result.vce:.3f} V ≤ {VCE_SATURATION_MAX:.1f} V: ทรานซิสเตอร์อิ่มตัว "
            "(Saturation) สมการ forward-active ใช้ไม่ได้ ตัวเลขที่แสดงด้านล่างเป็นเพียง "
            "ผลของสมการที่ไม่สอดคล้องกับวงจรจริง ห้ามนำไปใช้"
        )
    return None


def _format_result(result: DcBiasResult) -> dict[str, object]:
    label, tone = REGION_LABELS[result.region]
    rows = [
        ("VTH", "แรงดันเทียบเท่า Thevenin", f"{result.vth:.3f} V"),
        ("RTH", "ความต้านทานเทียบเท่า Thevenin", f"{result.rth / 1000:.2f} kΩ"),
        ("IB", "กระแสฐาน", f"{result.ib * 1e6:.2f} µA"),
        ("IC", "กระแสคอลเล็กเตอร์", f"{result.ic * 1e3:.3f} mA"),
        ("IE", "กระแสอิมิตเตอร์", f"{result.ie * 1e3:.3f} mA"),
        ("VB", "แรงดันฐาน", f"{result.vb:.3f} V"),
        ("VE", "แรงดันอิมิตเตอร์", f"{result.ve:.3f} V"),
        ("VC", "แรงดันคอลเล็กเตอร์", f"{result.vc:.3f} V"),
        ("VCE", "แรงดันคอลเล็กเตอร์–อิมิตเตอร์", f"{result.vce:.3f} V"),
    ]
    return {
        "region": result.region,
        "region_label": label,
        "region_tone": tone,
        "trustworthy": result.region != REGION_SATURATION,
        "rows": rows,
        "warning": _warning_text(result.warning, result),
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        fields=_blank_fields(),
        errors={},
        form_error=None,
        result=None,
    )


@app.post("/")
def calculate():
    values, fields, errors = _read_form()

    for field in fields:
        if field["key"] in errors:
            field["error"] = errors[field["key"]]

    result = None
    form_error = None
    if not errors:
        params = DcBiasInputs(
            vcc=values["vcc"],
            r1=values["r1"],
            r2=values["r2"],
            rc=values["rc"],
            re=values["re"],
            beta=values["beta"],
            vbe=values["vbe"],
        )
        try:
            result = _format_result(compute_dc_bias(params))
        except ValueError as exc:
            form_error = f"คำนวณไม่ได้: {exc}"

    return render_template(
        "index.html",
        fields=fields,
        errors=errors,
        form_error=form_error,
        result=result,
    )


if __name__ == "__main__":
    app.run()
