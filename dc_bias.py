"""DC bias calculations for NPN BJT common-emitter amplifiers using the
forward-active approximation: voltage-divider, fixed, and emitter bias.

This module must stay independent of Flask/HTML: it only knows numbers and
returns data, never rendered text.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

# Model limits (volts). The forward-active equations stop being trustworthy
# once the collector-emitter voltage gets close to the saturation knee.
VCE_SATURATION_MAX = 0.3
VCE_NEAR_SATURATION = 1.0
# If the Thevenin base voltage only just clears VBE, IB is vanishingly small
# and the operating point is effectively cut off.
VBE_NEAR_CUTOFF_MARGIN = 0.01

# Input bounds. They keep the arithmetic finite and the result meaningful.
MAX_VCC = 1e4
MAX_RESISTANCE = 1e12
MAX_BETA = 1e6

REGION_ACTIVE = "active"
REGION_CUTOFF = "cutoff"
REGION_SATURATION = "saturation"

WARNING_CUTOFF = "cutoff"
WARNING_NEAR_CUTOFF = "near_cutoff"
WARNING_NEAR_SATURATION = "near_saturation"
WARNING_SATURATION = "saturation"

# Circuit modes. The divider is the default so Lab 02 behaviour is preserved.
MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

# Inputs shared by every circuit; mode-specific fields follow these in order.
COMMON_FIELDS = ("vcc", "rc", "beta", "vbe")
MODE_FIELDS = {
    MODE_DIVIDER: COMMON_FIELDS + ("r1", "r2", "re"),
    MODE_FIXED: COMMON_FIELDS + ("rb",),
    MODE_EMITTER: COMMON_FIELDS + ("rb", "re"),
}

# Shared result shape for all three modes. vth_v/rth_kohm are None when the
# circuit has no Thevenin equivalent (fixed and emitter bias).
RESULT_KEYS = (
    "vth_v", "rth_kohm", "ib_ua", "ic_ma", "ie_ma",
    "vb_v", "ve_v", "vc_v", "vce_v",
    "region", "warning", "trustworthy",
)


@dataclass(frozen=True)
class DcBiasInputs:
    """Circuit parameters in SI units (volts, ohms)."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class DcBiasResult:
    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warning: str | None


_FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
_UPPER_BOUNDS = {
    "vcc": MAX_VCC,
    "r1": MAX_RESISTANCE,
    "r2": MAX_RESISTANCE,
    "rb": MAX_RESISTANCE,
    "rc": MAX_RESISTANCE,
    "re": MAX_RESISTANCE,
    "beta": MAX_BETA,
}


def _validate_fields(fields, values: Mapping[str, float]) -> dict[str, str]:
    """Validate exactly the given fields; shared by both validators."""

    errors: dict[str, str] = {}

    for key in fields:
        value = values.get(key)
        if value is None or not math.isfinite(value):
            errors[key] = "ต้องเป็นตัวเลขที่ใช้ได้"
        elif value <= 0:
            errors[key] = "ต้องมากกว่า 0"
        elif key in _UPPER_BOUNDS and value > _UPPER_BOUNDS[key]:
            errors[key] = "ค่าสูงเกินขอบเขตที่แบบจำลองรองรับ"

    if not errors and values["vbe"] >= values["vcc"]:
        errors["vbe"] = "ต้องน้อยกว่า VCC"

    return errors


def validate_inputs(values: Mapping[str, float]) -> dict[str, str]:
    """Return field -> Thai error message for invalid divider parameters."""

    return _validate_fields(_FIELDS, values)


def fields_for_mode(mode: str) -> tuple[str, ...] | None:
    """Return the ordered fields for a mode, or None for an unknown mode."""

    return MODE_FIELDS.get(mode)


def validate_mode(mode: str, values: Mapping[str, float]) -> dict[str, str]:
    """Validate only the inputs the selected circuit actually uses."""

    fields = fields_for_mode(mode)
    if fields is None:
        return {"mode": "โหมดวงจรไม่ถูกต้อง"}

    return _validate_fields(fields, values)


def compute_dc_bias(params: DcBiasInputs) -> DcBiasResult:
    """Solve the DC operating point (Thevenin equivalent of the base divider).

    Raises ValueError if the result cannot be represented as finite numbers;
    callers are expected to have run validate_inputs first.
    """

    vth = params.vcc * params.r2 / (params.r1 + params.r2)
    # Reciprocal form: r1*r2 overflows long before the real RTH does.
    rth = 1.0 / (1.0 / params.r1 + 1.0 / params.r2)

    if vth <= params.vbe:
        # No base current can flow: the device is cut off and the
        # forward-active equations do not describe the circuit.
        return DcBiasResult(
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=params.vcc,
            vce=params.vcc,
            region=REGION_CUTOFF,
            warning=WARNING_CUTOFF,
        )

    ib = (vth - params.vbe) / (rth + (params.beta + 1.0) * params.re)
    ic = params.beta * ib
    ie = (params.beta + 1.0) * ib
    ve = ie * params.re
    vb = ve + params.vbe
    vc = params.vcc - ic * params.rc
    vce = vc - ve

    numbers = (vth, rth, ib, ic, ie, vb, ve, vc, vce)
    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("ผลลัพธ์ไม่สามารถแทนด้วยจำนวนจริงจำกัดได้")

    if vce <= VCE_SATURATION_MAX:
        region = REGION_SATURATION
        warning = WARNING_SATURATION
    elif vce < VCE_NEAR_SATURATION:
        region = REGION_ACTIVE
        warning = WARNING_NEAR_SATURATION
    elif vth - params.vbe < VBE_NEAR_CUTOFF_MARGIN:
        region = REGION_ACTIVE
        warning = WARNING_NEAR_CUTOFF
    else:
        region = REGION_ACTIVE
        warning = None

    return DcBiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warning=warning,
    )


def result_to_dict(result: DcBiasResult) -> dict:
    """Convert the untouched Lab 02 dataclass into the shared Lab 03 dict."""

    return {
        "vth_v": result.vth,
        "rth_kohm": result.rth / 1000.0,
        "ib_ua": result.ib * 1e6,
        "ic_ma": result.ic * 1e3,
        "ie_ma": result.ie * 1e3,
        "vb_v": result.vb,
        "ve_v": result.ve,
        "vc_v": result.vc,
        "vce_v": result.vce,
        "region": result.region,
        "warning": result.warning,
        "trustworthy": result.region == REGION_ACTIVE,
    }


def _build_result(vth, rth, ib, ic, ie, vb, ve, vc, vce, drive_v) -> dict:
    """Apply the shared finite check, region, warning and unit conversion."""

    numeric = [ib, ic, ie, vb, ve, vc, vce]
    if vth is not None:
        numeric.append(vth)
    if rth is not None:
        numeric.append(rth)
    if not all(math.isfinite(value) for value in numeric):
        raise ValueError("ผลลัพธ์ไม่สามารถแทนด้วยจำนวนจริงจำกัดได้")

    if ib <= 0:
        region, warning = REGION_CUTOFF, WARNING_CUTOFF
    elif vce <= VCE_SATURATION_MAX:
        region, warning = REGION_SATURATION, WARNING_SATURATION
    elif vce < VCE_NEAR_SATURATION:
        region, warning = REGION_ACTIVE, WARNING_NEAR_SATURATION
    elif drive_v < VBE_NEAR_CUTOFF_MARGIN:
        region, warning = REGION_ACTIVE, WARNING_NEAR_CUTOFF
    else:
        region, warning = REGION_ACTIVE, None

    return {
        "vth_v": vth,
        "rth_kohm": None if rth is None else rth / 1000.0,
        "ib_ua": ib * 1e6,
        "ic_ma": ic * 1e3,
        "ie_ma": ie * 1e3,
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vce,
        "region": region,
        "warning": warning,
        "trustworthy": region == REGION_ACTIVE,
    }


def compute_divider_bias(values: Mapping[str, float]) -> dict:
    """Solve the divider circuit by adapting the unchanged Lab 02 function."""

    params = DcBiasInputs(
        vcc=values["vcc"],
        r1=values["r1"],
        r2=values["r2"],
        rc=values["rc"],
        re=values["re"],
        beta=values["beta"],
        vbe=values["vbe"],
    )
    return result_to_dict(compute_dc_bias(params))


def compute_fixed_bias(values: Mapping[str, float]) -> dict:
    """Solve fixed bias: IB = (VCC - VBE) / RB, with VE = 0."""

    vcc = values["vcc"]
    rb = values["rb"]
    rc = values["rc"]
    beta = values["beta"]
    vbe = values["vbe"]

    drive_v = vcc - vbe
    if drive_v <= 0:
        return _build_result(
            None, None, 0.0, 0.0, 0.0, vbe, 0.0, vcc, vcc, drive_v
        )

    ib = drive_v / rb
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = 0.0
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    return _build_result(None, None, ib, ic, ie, vb, ve, vc, vce, drive_v)


def compute_emitter_bias(values: Mapping[str, float]) -> dict:
    """Solve emitter bias: IB = (VCC - VBE) / (RB + (beta+1) RE)."""

    vcc = values["vcc"]
    rb = values["rb"]
    rc = values["rc"]
    re = values["re"]
    beta = values["beta"]
    vbe = values["vbe"]

    drive_v = vcc - vbe
    if drive_v <= 0:
        return _build_result(
            None, None, 0.0, 0.0, 0.0, vbe, 0.0, vcc, vcc, drive_v
        )

    ib = drive_v / (rb + (beta + 1.0) * re)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - ic * rc
    vce = vc - ve

    return _build_result(None, None, ib, ic, ie, vb, ve, vc, vce, drive_v)
