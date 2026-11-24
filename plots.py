"""Pure SVG renderers for parsed ngspice AC and transient arrays.

No plotting library and no hidden dataset: every coordinate is derived only
from the sequences supplied by the caller.
"""

from __future__ import annotations

import math
from typing import Sequence

_WIDTH = 640
_HEIGHT = 360
_LEFT = 64
_RIGHT = 56
_TOP = 36
_BOTTOM = 56
_PLOT_W = _WIDTH - _LEFT - _RIGHT
_PLOT_H = _HEIGHT - _TOP - _BOTTOM
_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _fmt(value: float) -> str:
    """Format a tick label compactly without losing small or large values."""

    if value == 0:
        return "0"
    if abs(value) >= 1000 or abs(value) < 0.01:
        return f"{value:.2e}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _span(values: Sequence[float]) -> tuple[float, float]:
    """Return the supplied minimum and maximum; equal values stay equal."""

    return min(values), max(values)


def _y(value: float, low: float, high: float) -> float:
    if high <= low:
        return _TOP + _PLOT_H / 2
    return _TOP + _PLOT_H - (value - low) / (high - low) * _PLOT_H


def _x_log(value: float, low: float, high: float) -> float:
    log_low = math.log10(max(low, 1e-12))
    log_high = math.log10(max(high, 1e-12))
    if log_high <= log_low:
        return _LEFT + _PLOT_W / 2
    log_value = math.log10(max(value, 1e-12))
    return _LEFT + (log_value - log_low) / (log_high - log_low) * _PLOT_W


def _x_linear(value: float, low: float, high: float) -> float:
    if high <= low:
        return _LEFT + _PLOT_W / 2
    return _LEFT + (value - low) / (high - low) * _PLOT_W


def _svg_open(title: str) -> str:
    slug = "".join(character if character.isalnum() else "-" for character in title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        f'role="img" aria-labelledby="{slug}-title {slug}-desc">'
        f'<title id="{slug}-title">{title}</title>'
        f'<desc id="{slug}-desc">Data-driven plot from parsed ngspice output</desc>'
    )


def _grid() -> list[str]:
    parts: list[str] = []
    for fraction in _FRACTIONS:
        y = _TOP + fraction * _PLOT_H
        parts.append(
            f'<line class="grid" x1="{_LEFT}" y1="{y:.1f}" '
            f'x2="{_LEFT + _PLOT_W}" y2="{y:.1f}" />'
        )
    for fraction in _FRACTIONS:
        x = _LEFT + fraction * _PLOT_W
        parts.append(
            f'<line class="grid" x1="{x:.1f}" y1="{_TOP}" '
            f'x2="{x:.1f}" y2="{_TOP + _PLOT_H}" />'
        )
    parts.append(
        f'<line class="axis" x1="{_LEFT}" y1="{_TOP}" x2="{_LEFT}" '
        f'y2="{_TOP + _PLOT_H}" />'
    )
    parts.append(
        f'<line class="axis" x1="{_LEFT}" y1="{_TOP + _PLOT_H}" '
        f'x2="{_LEFT + _PLOT_W}" y2="{_TOP + _PLOT_H}" />'
    )
    return parts


def _legend(entries: tuple[tuple[str, str], ...]) -> list[str]:
    parts = [f'<g class="legend" transform="translate({_LEFT + 8},{_TOP + 10})">']
    for index, (label, colour) in enumerate(entries):
        y = index * 18
        parts.append(
            f'<line x1="0" y1="{y}" x2="18" y2="{y}" '
            f'stroke="{colour}" stroke-width="3" />'
        )
        parts.append(f'<text x="24" y="{y + 4}">{label}</text>')
    parts.append("</g>")
    return parts


def bode_svg(
    freq_hz: Sequence[float],
    gain_db: Sequence[float],
    phase_deg: Sequence[float],
) -> str:
    """Render magnitude and phase against a logarithmic frequency axis."""

    if not (len(freq_hz) == len(gain_db) == len(phase_deg)):
        raise ValueError("bode_svg requires equal-length sequences")

    low_f, high_f = _span(freq_hz) if freq_hz else (1.0, 10.0)
    low_g, high_g = _span(gain_db) if gain_db else (0.0, 1.0)
    low_p, high_p = _span(phase_deg) if phase_deg else (-180.0, -179.0)

    parts = [_svg_open("CE Bode plot")]
    parts.extend(_grid())

    for fraction in _FRACTIONS:
        y = _TOP + fraction * _PLOT_H
        gain_tick = high_g - fraction * (high_g - low_g)
        phase_tick = high_p - fraction * (high_p - low_p)
        parts.append(
            f'<text class="tick" x="{_LEFT - 6}" y="{y + 4:.1f}" '
            f'text-anchor="end">{_fmt(gain_tick)}</text>'
        )
        parts.append(
            f'<text class="tick" x="{_LEFT + _PLOT_W + 6}" y="{y + 4:.1f}" '
            f'text-anchor="start">{_fmt(phase_tick)}</text>'
        )

    log_low = math.log10(max(low_f, 1e-12))
    log_high = math.log10(max(high_f, 1e-12))
    for fraction in _FRACTIONS:
        x = _LEFT + fraction * _PLOT_W
        if log_high > log_low:
            tick = 10 ** (log_low + fraction * (log_high - log_low))
        else:
            tick = low_f
        parts.append(
            f'<text class="tick" x="{x:.1f}" y="{_TOP + _PLOT_H + 18}" '
            f'text-anchor="middle">{_fmt(tick)}</text>'
        )

    if freq_hz:
        gain_points = " ".join(
            f"{_x_log(freq, low_f, high_f):.1f},{_y(gain, low_g, high_g):.1f}"
            for freq, gain in zip(freq_hz, gain_db)
        )
        phase_points = " ".join(
            f"{_x_log(freq, low_f, high_f):.1f},{_y(phase, low_p, high_p):.1f}"
            for freq, phase in zip(freq_hz, phase_deg)
        )
        parts.append(
            f'<polyline class="series gain" points="{gain_points}" fill="none" '
            f'stroke="#2b6cb0" stroke-width="2" />'
        )
        parts.append(
            f'<polyline class="series phase" points="{phase_points}" fill="none" '
            f'stroke="#dd6b20" stroke-width="2" />'
        )

    parts.append(
        f'<text x="{_LEFT + _PLOT_W / 2:.1f}" y="{_HEIGHT - 12}" '
        f'text-anchor="middle">Frequency (Hz)</text>'
    )
    parts.append(
        f'<text transform="rotate(-90 18 {_TOP + _PLOT_H / 2:.1f})" '
        f'x="18" y="{_TOP + _PLOT_H / 2:.1f}" text-anchor="middle">Gain (dB)</text>'
    )
    parts.append(
        f'<text transform="rotate(90 {_WIDTH - 18} {_TOP + _PLOT_H / 2:.1f})" '
        f'x="{_WIDTH - 18}" y="{_TOP + _PLOT_H / 2:.1f}" '
        f'text-anchor="middle">Phase (deg)</text>'
    )
    parts.extend(_legend((("Gain (dB)", "#2b6cb0"), ("Phase (deg)", "#dd6b20"))))
    parts.append("</svg>")
    return "\n".join(parts)


def waveform_svg(
    time_s: Sequence[float],
    vin_v: Sequence[float],
    vout_v: Sequence[float],
) -> str:
    """Render Vin and Vout against time in milliseconds."""

    if not (len(time_s) == len(vin_v) == len(vout_v)):
        raise ValueError("waveform_svg requires equal-length sequences")

    times_ms = [value * 1000.0 for value in time_s]
    low_t, high_t = _span(times_ms) if times_ms else (0.0, 1.0)
    voltages = [*vin_v, *vout_v]
    low_v, high_v = _span(voltages) if voltages else (-1.0, 1.0)

    parts = [_svg_open("CE waveform")]
    parts.extend(_grid())

    for fraction in _FRACTIONS:
        y = _TOP + fraction * _PLOT_H
        voltage_tick = high_v - fraction * (high_v - low_v)
        parts.append(
            f'<text class="tick" x="{_LEFT - 6}" y="{y + 4:.1f}" '
            f'text-anchor="end">{_fmt(voltage_tick)}</text>'
        )
    for fraction in _FRACTIONS:
        x = _LEFT + fraction * _PLOT_W
        time_tick = low_t + fraction * (high_t - low_t)
        parts.append(
            f'<text class="tick" x="{x:.1f}" y="{_TOP + _PLOT_H + 18}" '
            f'text-anchor="middle">{_fmt(time_tick)}</text>'
        )

    if time_s:
        vin_points = " ".join(
            f"{_x_linear(time, low_t, high_t):.1f},{_y(vin, low_v, high_v):.1f}"
            for time, vin in zip(times_ms, vin_v)
        )
        vout_points = " ".join(
            f"{_x_linear(time, low_t, high_t):.1f},{_y(vout, low_v, high_v):.1f}"
            for time, vout in zip(times_ms, vout_v)
        )
        parts.append(
            f'<polyline class="series vin" points="{vin_points}" fill="none" '
            f'stroke="#2b6cb0" stroke-width="2" />'
        )
        parts.append(
            f'<polyline class="series vout" points="{vout_points}" fill="none" '
            f'stroke="#dd6b20" stroke-width="2" />'
        )

    parts.append(
        f'<text x="{_LEFT + _PLOT_W / 2:.1f}" y="{_HEIGHT - 12}" '
        f'text-anchor="middle">Time (ms)</text>'
    )
    parts.append(
        f'<text transform="rotate(-90 18 {_TOP + _PLOT_H / 2:.1f})" '
        f'x="18" y="{_TOP + _PLOT_H / 2:.1f}" text-anchor="middle">Voltage (V)</text>'
    )
    parts.extend(_legend((("Vin", "#2b6cb0"), ("Vout", "#dd6b20"))))
    parts.append("</svg>")
    return "\n".join(parts)
