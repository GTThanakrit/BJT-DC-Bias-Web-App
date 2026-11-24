"""Adapter for the single CE voltage-divider circuit simulated by ngspice.

Only validated numbers reach the netlist. This module knows nothing about
HTTP or HTML; Flask passes in a CEParams value and receives a netlist path.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

NETLIST_MODES = ("dc", "ac", "tran")

_NUMERIC_FIELDS = (
    "vcc", "r1", "r2", "rc", "re", "rl", "cin_uf", "cout_uf",
    "source_peak_v", "source_freq_hz", "beta", "vbe",
)
_RESISTANCE_FIELDS = ("r1", "r2", "rc", "re", "rl")
_CAPACITANCE_FIELDS = ("cin_uf", "cout_uf")
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
_NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")
_OP_IC_RE = re.compile(
    r"^\s*ic\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_RAD_TO_DEG = 180.0 / math.pi


@dataclass(frozen=True)
class CEParams:
    """Validated circuit and source parameters in volts, ohms and farads."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin_uf: float
    cout_uf: float
    source_peak_v: float
    source_freq_hz: float
    beta: float
    vbe: float
    model_name: str = "CE_UNVERIFIED"


def validate_sim_params(values: dict[str, str]) -> dict[str, str]:
    """Return Thai error messages keyed by field name for invalid input."""

    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}

    for key in _NUMERIC_FIELDS:
        try:
            number = float(values.get(key, ""))
        except (TypeError, ValueError):
            errors[key] = "ต้องเป็นตัวเลข"
            continue
        if not math.isfinite(number):
            errors[key] = "ต้องเป็นตัวเลขที่จำกัด"
            continue
        numbers[key] = number

    for key in _RESISTANCE_FIELDS:
        if key not in numbers:
            continue
        if numbers[key] <= 0:
            errors[key] = "ต้องมากกว่า 0"
        elif numbers[key] > 1e9:
            errors[key] = "ต้องไม่เกิน 1 000 000 000 Ω"

    for key in _CAPACITANCE_FIELDS:
        if key not in numbers:
            continue
        if numbers[key] <= 0:
            errors[key] = "ต้องมากกว่า 0"
        elif numbers[key] > 1000:
            errors[key] = "ต้องไม่เกิน 1000 µF"

    if "vcc" in numbers and numbers["vcc"] <= 0:
        errors.setdefault("vcc", "ต้องมากกว่า 0")
    if "source_peak_v" in numbers:
        peak = numbers["source_peak_v"]
        if peak <= 0 or peak > 1:
            errors.setdefault("source_peak_v", "ต้องอยู่ระหว่าง 0 และ 1 V")
    if "source_freq_hz" in numbers:
        freq = numbers["source_freq_hz"]
        if freq < 1 or freq > 1e7:
            errors.setdefault("source_freq_hz", "ต้องอยู่ระหว่าง 1 Hz และ 10 MHz")
    if "beta" in numbers:
        beta = numbers["beta"]
        if beta < 1 or beta > 1e6:
            errors.setdefault("beta", "ต้องอยู่ระหว่าง 1 และ 1 000 000")
    if "vbe" in numbers:
        vbe = numbers["vbe"]
        if vbe <= 0:
            errors.setdefault("vbe", "ต้องมากกว่า 0")
        elif "vcc" in numbers and vbe >= numbers["vcc"]:
            errors.setdefault("vbe", "ต้องน้อยกว่า VCC")

    model_name = str(values.get("model_name", "CE_UNVERIFIED")).strip()
    if not _MODEL_NAME_RE.fullmatch(model_name):
        errors["model_name"] = "ใช้ได้เฉพาะตัวอักษร ตัวเลข และ _"

    return errors


@dataclass
class RunResult:
    """Outcome of one external ngspice batch run."""

    ok: bool
    log_text: str
    raw_path: Path | None
    engine_version: str
    error: str


@dataclass
class OpResult:
    """DC operating point values in volts and milliamperes."""

    vb_v: float
    ve_v: float
    vc_v: float
    vce_v: float
    ic_ma: float


@dataclass
class AcResult:
    """AC sweep arrays; gain and phase are relative to vin."""

    freq_hz: list[float]
    gain_db: list[float]
    phase_deg: list[float]
    cutoff_hz: float | None


@dataclass
class TranResult:
    """Time-domain arrays parsed from a .print tran table."""

    time_s: list[float]
    vin_v: list[float]
    vout_v: list[float]
    phase_relation: str


@dataclass
class SimulationResult:
    """Complete outcome of one requested analysis."""

    mode: str
    ok: bool
    status: str
    message: str
    op: OpResult | None
    ac: AcResult | None
    tran: TranResult | None
    provenance: dict[str, str]


def _engine_executable() -> str:
    """Prefer the Windows console binary; keep ngspice on other platforms."""

    resolved = shutil.which("ngspice_con") or shutil.which("ngspice")
    if resolved:
        return resolved
    if sys.platform.startswith("win"):
        # The flask process may not inherit a shell's temporary PATH change.
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            candidate = (
                Path(local_app_data)
                / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe"
            )
            if candidate.exists():
                return str(candidate)
        return "ngspice_con"
    return "ngspice"


def get_engine_version(timeout: int = 5) -> str:
    """Return the ngspice version banner or 'not available'."""

    try:
        completed = subprocess.run(
            [_engine_executable(), "-v"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "not available"

    for line in (completed.stdout + "\n" + completed.stderr).splitlines():
        if "ngspice-" in line.lower():
            return line.strip()
    return "not available"


def run_ngspice(
    mode: str, netlist: Path, workdir: Path, timeout: int = 30
) -> RunResult:
    """Run one netlist in batch mode and classify the outcome."""

    version = get_engine_version()
    # ngspice 47 suppresses .print tables and the .op summary when -r is used,
    # so the human-inspectable log is the only evidence source for v1.
    command = [
        _engine_executable(),
        "-b",
        "-o",
        "run.log",
        netlist.name,
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return RunResult(False, "", None, version, "ENGINE NOT AVAILABLE")
    except subprocess.TimeoutExpired:
        return RunResult(False, "", None, version, f"TIMEOUT after {timeout} s")

    log_path = workdir / "run.log"
    log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else completed.stdout
    raw_path = workdir / "run.raw" if (workdir / "run.raw").exists() else None

    if completed.returncode != 0 or "Fatal error" in log_text:
        return RunResult(False, log_text, raw_path, version, "RUN FAILED")
    if not log_text.strip():
        return RunResult(False, log_text, raw_path, version, "EMPTY OUTPUT")
    return RunResult(True, log_text, raw_path, version, "")


def _fmt(value: float) -> str:
    """Format a validated float for a SPICE deck without trailing .0."""

    return f"{value:g}"


def _tables(log_text: str) -> list[tuple[list[str], list[list[float]]]]:
    """Read named .print tables from a real ngspice batch log.

    ngspice 47 writes one table per printed vector group, repeating the
    header on each page. A leading ``Index`` column is dropped; simple
    header-plus-rows fixtures are accepted as well.
    """

    tables: list[tuple[list[str], list[list[float]]]] = []
    headers: list[str] | None = None
    rows: list[list[float]] = []

    def close() -> None:
        if headers is not None and rows:
            tables.append((headers, rows))

    for raw_line in log_text.splitlines():
        line = raw_line.strip().strip("\f").strip()
        if not line:
            close()
            headers, rows = None, []
            continue
        tokens = line.replace(",", " ").split()
        if tokens[0].lower() == "index" and len(tokens) > 1:
            close()
            headers, rows = [token.lower() for token in tokens[1:]], []
            continue
        numbers: list[float] = []
        for token in tokens:
            if not _NUMBER_RE.fullmatch(token):
                break
            numbers.append(float(token))
        if headers is None:
            if not numbers:
                headers, rows = [token.lower() for token in tokens], []
            continue
        if not numbers:
            continue
        if len(numbers) > len(headers):
            numbers = numbers[-len(headers):]
        if len(numbers) == len(headers):
            rows.append(numbers)
        elif rows:
            close()
            headers, rows = None, []
    close()
    return tables


def _column(headers: list[str], *names: str) -> int | None:
    for name in names:
        if name.lower() in headers:
            return headers.index(name.lower())
    return None


def _op_ic_amperes(log_text: str, tables: list[tuple[list[str], list[list[float]]]]) -> float:
    """Read collector current from the real .op BJT block or a fixture column."""

    match = _OP_IC_RE.search(log_text)
    if match:
        return float(match.group(1))
    for headers, rows in tables:
        index = _column(headers, "i(q1)", "i(q1#branch)", "ic")
        if index is not None and rows:
            return rows[0][index]
    raise ValueError("no operating-point collector current found")


def parse_op(log_text: str) -> OpResult:
    """Parse .print op voltages and the .op collector current with units."""

    tables = _tables(log_text)
    for headers, rows in tables:
        vb = _column(headers, "v(vb)", "vb")
        ve = _column(headers, "v(ve)", "ve")
        vc = _column(headers, "v(vc)", "vc")
        if None in (vb, ve, vc) or not rows:
            continue
        row = rows[0]
        vce_column = _column(headers, "v(vc)-v(ve)", "v(vc,ve)", "vce")
        vce = row[vce_column] if vce_column is not None else row[vc] - row[ve]
        return OpResult(row[vb], row[ve], row[vc], vce, _op_ic_amperes(log_text, tables) * 1000.0)
    raise ValueError("no .print op table found")


def _ac_series(
    table: tuple[list[str], list[list[float]]], role: str
) -> dict[float, tuple[float, float]]:
    headers, rows = table
    freq = _column(headers, "frequency", "freq")
    if role == "out":
        db = _column(headers, "vdb(vout)", "vdb(out)")
        phase = _column(headers, "vp(vout)", "vp(out)")
    else:
        db = _column(headers, "vdb(vin)", "vdb(in)")
        phase = _column(headers, "vp(vin)", "vp(in)")
    if None in (freq, db, phase):
        raise ValueError("missing .print ac columns")
    return {row[freq]: (row[db], row[phase]) for row in rows}


def parse_ac(log_text: str) -> AcResult:
    """Parse .print ac tables and compute gain/phase relative to vin.

    ngspice 47 prints vout and vin in separate tables and reports vp() in
    radians, so the two tables are merged by frequency and phase converted
    to degrees.
    """

    out_tables: list[tuple[list[str], list[list[float]]]] = []
    in_tables: list[tuple[list[str], list[list[float]]]] = []
    for table in _tables(log_text):
        headers = table[0]
        if _column(headers, "frequency", "freq") is None:
            continue
        if _column(headers, "vdb(vout)", "vdb(out)") is not None:
            out_tables.append(table)
        if _column(headers, "vdb(vin)", "vdb(in)") is not None:
            in_tables.append(table)
    if not out_tables or not in_tables:
        raise ValueError("no .print ac table found")

    out: dict[float, tuple[float, float]] = {}
    reference: dict[float, tuple[float, float]] = {}
    for table in out_tables:
        out.update(_ac_series(table, "out"))
    for table in in_tables:
        reference.update(_ac_series(table, "in"))
    freq_hz: list[float] = []
    gain_db: list[float] = []
    phase_deg: list[float] = []
    for frequency in sorted(out):
        if frequency not in reference:
            continue
        out_db, out_phase = out[frequency]
        in_db, in_phase = reference[frequency]
        freq_hz.append(frequency)
        gain_db.append(out_db - in_db)
        phase_deg.append((out_phase - in_phase) * _RAD_TO_DEG)

    if not freq_hz:
        raise ValueError("no .print ac table found")

    cutoff_hz: float | None = None
    for index in range(1, len(gain_db)):
        if gain_db[index - 1] >= -3.0 and gain_db[index] < -3.0:
            cutoff_hz = freq_hz[index]
            break

    return AcResult(freq_hz, gain_db, phase_deg, cutoff_hz)


def parse_tran(log_text: str) -> TranResult:
    """Parse .print tran tables and classify vin/vout phase relation."""

    time_s: list[float] = []
    vin_v: list[float] = []
    vout_v: list[float] = []
    for headers, rows in _tables(log_text):
        time = _column(headers, "time")
        vin = _column(headers, "v(vin)", "vin")
        vout = _column(headers, "v(vout)", "vout")
        if None in (time, vin, vout):
            continue
        for row in rows:
            time_s.append(row[time])
            vin_v.append(row[vin])
            vout_v.append(row[vout])
    if not time_s:
        raise ValueError("no .print tran table found")

    phase_relation = "non-inverted"
    if len(vin_v) > 1:
        mean_in = sum(vin_v) / len(vin_v)
        mean_out = sum(vout_v) / len(vout_v)
        covariance = sum(
            (vin - mean_in) * (vout - mean_out)
            for vin, vout in zip(vin_v, vout_v)
        )
        if covariance < 0:
            phase_relation = "inverted"

    return TranResult(time_s, vin_v, vout_v, phase_relation)


def simulate(mode: str, params: CEParams) -> SimulationResult:
    """Build, run and parse one analysis, returning provenance with the result."""

    with tempfile.TemporaryDirectory(prefix="ce-run-") as temporary:
        workdir = Path(temporary)
        netlist = build_netlist(mode, params, workdir)
        run = run_ngspice(mode, netlist, workdir)
        provenance = {
            "engine": run.engine_version,
            "model": params.model_name,
            "log": "run.log (.print)",
            "status": run.error or "OK",
        }

        if not run.ok:
            return SimulationResult(
                mode, False, run.error or "RUN FAILED", run.error,
                None, None, None, provenance,
            )

        try:
            if mode == "dc":
                op, ac, tran = parse_op(run.log_text), None, None
            elif mode == "ac":
                op, ac, tran = None, parse_ac(run.log_text), None
            else:
                op, ac, tran = None, None, parse_tran(run.log_text)
        except (ValueError, IndexError, TypeError) as exc:
            provenance["status"] = "PARSE FAILED"
            return SimulationResult(
                mode, False, "PARSE FAILED", str(exc),
                None, None, None, provenance,
            )

        provenance["status"] = "SUCCESS"
        return SimulationResult(mode, True, "SUCCESS", "", op, ac, tran, provenance)


def build_netlist(mode: str, params: CEParams, workdir: Path) -> Path:
    """Write a batch-mode netlist for one analysis and return its path."""

    if mode not in NETLIST_MODES:
        raise ValueError(f"unknown analysis mode: {mode}")

    model_path = (
        Path(__file__).resolve().parent / "spice_models" / "ce_generic.mod"
    ).as_posix()

    lines = [
        f"* CE voltage divider reference - {mode} - UNVERIFIED model",
        f'.include "{model_path}"',
        f"VCC vcc 0 DC {_fmt(params.vcc)}",
        f"R1 vcc vb {_fmt(params.r1)}",
        f"R2 vb 0 {_fmt(params.r2)}",
        f"RC vcc vc {_fmt(params.rc)}",
        f"RE ve 0 {_fmt(params.re)}",
        f"Q1 vc vb ve {params.model_name}",
        (
            f"Vs vin 0 AC 1 SIN(0 {_fmt(params.source_peak_v)} "
            f"{_fmt(params.source_freq_hz)})"
        ),
        f"Cin vin vb {_fmt(params.cin_uf)}u",
        f"Cout vc vout {_fmt(params.cout_uf)}u",
        f"RL vout 0 {_fmt(params.rl)}",
    ]

    if mode == "dc":
        lines.append(".op")
        lines.append(".print op v(vb) v(ve) v(vc) v(vc)-v(ve)")
    elif mode == "ac":
        lines.append(".ac dec 20 1 10Meg")
        lines.append(".print ac vdb(vout) vp(vout) vdb(vin) vp(vin)")
    else:
        tstop = 5.0 / params.source_freq_hz
        tmax = 1.0 / (100.0 * params.source_freq_hz)
        lines.append(f".tran {_fmt(tmax)} {_fmt(tstop)} 0 {_fmt(tmax)}")
        lines.append(".print tran v(vin) v(vout)")

    lines.append(".end")

    path = workdir / f"{mode}.cir"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
