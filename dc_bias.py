"""DC bias calculations for an NPN BJT common-emitter amplifier
with voltage-divider bias, using the forward-active approximation.

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
    "rc": MAX_RESISTANCE,
    "re": MAX_RESISTANCE,
    "beta": MAX_BETA,
}


def validate_inputs(values: Mapping[str, float]) -> dict[str, str]:
    """Return field -> Thai error message for invalid circuit parameters."""

    errors: dict[str, str] = {}

    for key in _FIELDS:
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
