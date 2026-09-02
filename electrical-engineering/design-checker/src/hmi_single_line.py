"""Compact single-line SVG renderer for the HMI Board Planner preview.

This is a presentation layer only. It visualizes the existing board graph with
conventional single-line motifs (busbars, breaker marks, feeder lines and load
terminations) without changing or inferring engineering data.
"""
from __future__ import annotations

from html import escape

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph


_LINE = "#9bb0c8"
_LINE_DIM = "#57708d"
_TEXT = "#e8f2ff"
_TEXT_DIM = "#7891ad"
_ACCENT = "#39aef7"
_GOOD = "#54d99a"


def _children(graph: BoardElectricalGraph, node: ElectricalNode, kind: str) -> tuple[ElectricalNode, ...]:
    return tuple(child for child in graph.children_of(node.node_id) if child.kind == kind)


def _first_child(graph: BoardElectricalGraph, node: ElectricalNode, kind: str) -> ElectricalNode | None:
    return next((child for child in graph.children_of(node.node_id) if child.kind == kind), None)


def _branch_endpoint(graph: BoardElectricalGraph, protective: ElectricalNode) -> tuple[ElectricalNode | None, ElectricalNode | None]:
    cable = _first_child(graph, protective, "cable")
    if cable is None:
        return None, None
    endpoint = next(
        (child for child in graph.children_of(cable.node_id) if child.kind in ("load", "field", "sub_board")),
        None,
    )
    return cable, endpoint


def _downstream_busbar(graph: BoardElectricalGraph, endpoint: ElectricalNode | None) -> ElectricalNode | None:
    if endpoint is None:
        return None
    if endpoint.kind == "field":
        return _first_child(graph, endpoint, "busbar")
    if endpoint.kind == "sub_board":
        incomer = _first_child(graph, endpoint, "incomer")
        return _first_child(graph, incomer, "busbar") if incomer is not None else None
    return None


def _leaf_count(graph: BoardElectricalGraph, busbar: ElectricalNode) -> int:
    protective = _children(graph, busbar, "protective_device")
    if not protective:
        return 1
    total = 0
    for device in protective:
        _, endpoint = _branch_endpoint(graph, device)
        child_busbar = _downstream_busbar(graph, endpoint)
        total += _leaf_count(graph, child_busbar) if child_busbar is not None else 1
    return max(1, total)


def _rating(node: ElectricalNode | None) -> str:
    return "" if node is None or node.rating_a is None else f"{node.rating_a:g} A"


def _cable(node: ElectricalNode | None) -> str:
    if node is None or node.cable_mm2 is None:
        return ""
    runs = node.cable_runs or 1
    return f"{runs}×{node.cable_mm2:g} mm²" if runs > 1 else f"{node.cable_mm2:g} mm²"


def _text(x: float, y: float, value: str, *, anchor: str = "middle", size: int = 11, fill: str = _TEXT, weight: int = 600) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="Inter,Segoe UI,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(value)}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, *, active: bool = False, width: float = 2.0) -> str:
    stroke = _ACCENT if active else _LINE_DIM
    glow = ' filter="url(#glow)"' if active else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width:g}"{glow}/>'


def _breaker_symbol(x: float, y: float, label: str, rating: str, *, highlighted: bool = False) -> str:
    stroke = _ACCENT if highlighted else _LINE
    glow = ' filter="url(#glow)"' if highlighted else ""
    parts = [
        _line(x, y - 23, x, y - 10, active=highlighted),
        f'<rect x="{x - 13:.1f}" y="{y - 10:.1f}" width="26" height="20" rx="2" fill="#0a1727" stroke="{stroke}" stroke-width="1.7"{glow}/>',
        f'<line x1="{x - 8:.1f}" y1="{y + 6:.1f}" x2="{x + 8:.1f}" y2="{y - 6:.1f}" stroke="{stroke}" stroke-width="1.9"{glow}/>',
        _line(x, y + 10, x, y + 26, active=highlighted),
        _text(x + 22, y - 1, label, anchor="start", size=11, fill=_TEXT, weight=680),
    ]
    if rating:
        parts.append(_text(x + 22, y + 13, rating, anchor="start", size=9, fill=_TEXT_DIM, weight=560))
    return "".join(parts)


def _draw_busbar(svg: list[str], graph: BoardElectricalGraph, busbar: ElectricalNode, center_x: float, y: float, width_px: float, selected_ids: set[str]) -> None:
    half = max(55.0, width_px / 2 - 22)
    selected = busbar.node_id in selected_ids
    stroke = _ACCENT if selected else _LINE
    glow = ' filter="url(#glow)"' if selected else ""
    svg.append(f'<line x1="{center_x - half:.1f}" y1="{y:.1f}" x2="{center_x + half:.1f}" y2="{y:.1f}" stroke="{stroke}" stroke-width="5" stroke-linecap="round"{glow}/>' )
    svg.append(_text(center_x - half, y - 10, busbar.label, anchor="start", size=11, fill=_TEXT, weight=700))

    devices = _children(graph, busbar, "protective_device")
    if not devices:
        return

    subtree_counts: list[int] = []
    branch_data: list[tuple[ElectricalNode, ElectricalNode | None, ElectricalNode | None, ElectricalNode | None]] = []
    for device in devices:
        cable, endpoint = _branch_endpoint(graph, device)
        child_busbar = _downstream_busbar(graph, endpoint)
        count = _leaf_count(graph, child_busbar) if child_busbar is not None else 1
        subtree_counts.append(count)
        branch_data.append((device, cable, endpoint, child_busbar))

    total = sum(subtree_counts)
    unit = width_px / total
    cursor = center_x - width_px / 2
    for count, (device, cable, endpoint, child_busbar) in zip(subtree_counts, branch_data):
        branch_width = count * unit
        x = cursor + branch_width / 2
        cursor += branch_width
        branch_active = any(
            node is not None and node.node_id in selected_ids
            for node in (device, cable, endpoint, child_busbar)
        )
        svg.append(_line(x, y, x, y + 27, active=branch_active))
        svg.append(_breaker_symbol(x, y + 48, device.label, _rating(device), highlighted=branch_active or device.node_id in selected_ids))
        cable_y1 = y + 74
        endpoint_y = y + 116
        svg.append(_line(x, cable_y1, x, endpoint_y, active=branch_active))
        cable_text = _cable(cable)
        if cable_text:
            svg.append(_text(x + 9, y + 97, cable_text, anchor="start", size=8, fill=_TEXT_DIM, weight=530))

        if endpoint is None:
            svg.append(_text(x, endpoint_y + 18, "Unresolved endpoint", size=9, fill="#f7bf4f"))
            continue

        endpoint_selected = endpoint.node_id in selected_ids
        endpoint_color = _ACCENT if endpoint_selected or branch_active else _GOOD
        endpoint_glow = ' filter="url(#glow)"' if endpoint_selected or branch_active else ""
        if endpoint.kind == "load":
            svg.append(f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="6" fill="#08131f" stroke="{endpoint_color}" stroke-width="2"{endpoint_glow}/>' )
            svg.append(f'<line x1="{x - 4:.1f}" y1="{endpoint_y + 4:.1f}" x2="{x + 4:.1f}" y2="{endpoint_y - 4:.1f}" stroke="{endpoint_color}" stroke-width="1.6"{endpoint_glow}/>' )
            svg.append(_text(x, endpoint_y + 22, endpoint.label, size=11, fill=_TEXT, weight=680))
            detail = endpoint.display_detail or (f"{endpoint.load_kw:g} kW · {'3P' if endpoint.phase == 'three' else '1P'}" if endpoint.load_kw is not None else "")
            if detail:
                svg.append(_text(x, endpoint_y + 36, detail, size=8, fill=_TEXT_DIM, weight=500))
        else:
            svg.append(f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="4.5" fill="{endpoint_color}"{endpoint_glow}/>' )
            svg.append(_text(x + 10, endpoint_y + 4, endpoint.label, anchor="start", size=11, fill=_TEXT, weight=680))
            if child_busbar is not None:
                next_y = endpoint_y + 42
                svg.append(_line(x, endpoint_y + 5, x, next_y, active=branch_active))
                _draw_busbar(svg, graph, child_busbar, x, next_y, max(110.0, branch_width * .86), selected_ids)


def render_hmi_single_line_svg(graph: BoardElectricalGraph, *, selected_node_ids: tuple[str, ...] = ()) -> str:
    """Render a compact conventional single-line view of ``graph`` as SVG."""
    validate_board_graph(graph)
    source = graph.root_nodes[0]
    incomer = _first_child(graph, source, "incomer")
    busbar = _first_child(graph, incomer, "busbar") if incomer is not None else None
    selected_ids = set(selected_node_ids)

    leafs = _leaf_count(graph, busbar) if busbar is not None else 1
    width = max(720, 210 * leafs + 180)
    depth = 1
    if busbar is not None:
        pending = [(busbar, 1)]
        while pending:
            current, level = pending.pop(0)
            depth = max(depth, level)
            for device in _children(graph, current, "protective_device"):
                _, endpoint = _branch_endpoint(graph, device)
                child_busbar = _downstream_busbar(graph, endpoint)
                if child_busbar is not None:
                    pending.append((child_busbar, level + 1))
    height = max(560, 218 + depth * 180)
    cx = width / 2

    source_active = source.node_id in selected_ids
    incomer_active = incomer is not None and incomer.node_id in selected_ids
    busbar_active = busbar is not None and busbar.node_id in selected_ids

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" preserveAspectRatio="xMidYMin meet">',
        '<defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M 28 0 L 0 0 0 28" fill="none" stroke="#18314b" stroke-width="0.6" opacity="0.18"/></pattern></defs>',
        '<rect width="100%" height="100%" fill="#08131f"/><rect width="100%" height="100%" fill="url(#grid)"/>',
    ]

    source_stroke = _ACCENT if source_active else _LINE
    source_glow = ' filter="url(#glow)"' if source_active else ""
    svg.append(f'<circle cx="{cx:.1f}" cy="35" r="17" fill="#0a1727" stroke="{source_stroke}" stroke-width="2"{source_glow}/>' )
    svg.append(_text(cx, 39, "~", size=16, fill=_TEXT, weight=600))
    svg.append(_text(cx + 28, 32, source.label, anchor="start", size=11, fill=_TEXT, weight=700))
    svg.append(_line(cx, 52, cx, 71, active=source_active or incomer_active or busbar_active))

    if incomer is not None:
        svg.append(_breaker_symbol(cx, 92, incomer.label, _rating(incomer), highlighted=incomer_active or busbar_active))
    if busbar is not None:
        svg.append(_line(cx, 118, cx, 139, active=busbar_active))
        _draw_busbar(svg, graph, busbar, cx, 143, width - 120, selected_ids)

    svg.append('</svg>')
    return "".join(svg)
