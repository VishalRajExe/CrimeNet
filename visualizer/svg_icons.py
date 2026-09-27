"""CrimeNet Professional Monochrome SVG Icon System.

Provides consistent, lightweight, scalable SVG icons across the CrimeNet
investigation workstation, replacing all emoji-based iconography.
"""

from __future__ import annotations
import urllib.parse
from typing import Optional
from dash import html


def _make_svg_icon(
    inner_svg: str,
    size: int = 16,
    color: str = "#475569",
    viewBox: str = "0 0 24 24",
    stroke_width: float = 2.0,
    class_name: str = "",
    extra_style: Optional[dict] = None,
) -> html.Img:
    """Helper to render an inline SVG as an accessible Dash html.Img."""
    svg_str = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="{viewBox}" fill="none" stroke="{color}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">{inner_svg}</svg>'
    )
    uri = f"data:image/svg+xml;utf8,{urllib.parse.quote(svg_str)}"
    style = {
        "width": f"{size}px",
        "height": f"{size}px",
        "display": "inline-block",
        "verticalAlign": "-2px",
        "flexShrink": "0",
    }
    if extra_style:
        style.update(extra_style)
    return html.Img(src=uri, className=f"cn-icon {class_name}".strip(), style=style, alt="")


def icon_shield(color: str = "#2563eb", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        size=size, color=color
    )


def icon_search(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
        size=size, color=color
    )


def icon_more_dots(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="12" cy="12" r="1.5" fill="currentColor"/><circle cx="12" cy="5" r="1.5" fill="currentColor"/><circle cx="12" cy="19" r="1.5" fill="currentColor"/>',
        size=size, color=color, stroke_width=0
    )


def icon_filter(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
        size=size, color=color
    )


def icon_nodes(color: str = "#2563eb", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
        size=size, color=color
    )


def icon_edges(color: str = "#2563eb", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        size=size, color=color
    )


def icon_labels(color: str = "#2563eb", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',
        size=size, color=color
    )


def icon_expand(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>',
        size=size, color=color
    )


def icon_focus(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
        size=size, color=color
    )


def icon_fit(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>',
        size=size, color=color
    )


def icon_reset(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
        size=size, color=color
    )


def icon_sparkles(color: str = "#2563eb", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>',
        size=size, color=color
    )


def icon_case(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
        size=size, color=color
    )


def icon_folder(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        size=size, color=color
    )


def icon_plus(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
        size=size, color=color
    )


def icon_close(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
        size=size, color=color
    )


def icon_check(color: str = "#10b981", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polyline points="20 6 9 17 4 12"/>',
        size=size, color=color
    )


def icon_alert(color: str = "#f59e0b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
        size=size, color=color
    )


def icon_eye(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
        size=size, color=color
    )


def icon_trash(color: str = "#ef4444", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
        size=size, color=color
    )


def icon_edit(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
        size=size, color=color
    )


def icon_download(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
        size=size, color=color
    )


def icon_upload(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
        size=size, color=color
    )


def icon_refresh(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
        size=size, color=color
    )


def icon_zoom_in(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>',
        size=size, color=color
    )


def icon_zoom_out(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/>',
        size=size, color=color
    )


def icon_file(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>',
        size=size, color=color
    )


def icon_link(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        size=size, color=color
    )


def icon_timeline(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
        size=size, color=color
    )


def icon_user(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        size=size, color=color
    )


def icon_phone(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
        size=size, color=color
    )


def icon_car(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="2" y="8" width="20" height="9" rx="2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/><path d="M5 8l2-4h10l2 4"/>',
        size=size, color=color
    )


def icon_location(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
        size=size, color=color
    )


def icon_building(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="9" y1="22" x2="9" y2="2"/><line x1="8" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="16" y2="14"/><line x1="8" y1="18" x2="10" y2="18"/><line x1="14" y1="18" x2="16" y2="18"/>',
        size=size, color=color
    )


def icon_card(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
        size=size, color=color
    )


def icon_network(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><line x1="12" y1="12" x2="12" y2="8"/>',
        size=size, color=color
    )


def icon_audit(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
        size=size, color=color
    )


def icon_report(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        size=size, color=color
    )


def icon_money(color: str = "#64748b", size: int = 16) -> html.Img:
    return _make_svg_icon(
        '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
        size=size, color=color
    )
