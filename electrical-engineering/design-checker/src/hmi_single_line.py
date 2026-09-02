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


def _breaker_symbol(x: float, y: float, label: str, rating: str, *, highlighted: bool = False) -> str:
    stroke = _ACCENT if highlighted else _LINE
    parts = [
        f'<line x1="{x:.1f}" y1="{y - 23:.1f}" x2="{x:.1f}" y2="{y - 10:.1f}" stroke="{stroke}" stroke-width="2"/>',
        f'<rect x="{x - 13:.1f}" y="{y - 10:.1f}" width="26" height="20" rx="2" fill="#0a1727" stroke="{stroke}" stroke-width="1.5"/>',
        f'<line x1="{x - 8:.1f}" y1="{y + 6:.1f}" x2="{x + 8:.1f}" y2="{y - 6:.1f}" stroke="{stroke}" stroke-width="1.8"/>',
        f'<line x1="{x:.1f}" y1="{y + 10:.1f}" x2="{x:.1f}" y2="{y + 26:.1f}" stroke="{stroke}" stroke-width="2"/>',
        _text(x + 22, y - 1, label, anchor="start", size=10, fill=_TEXT, weight=650),
    ]
    if rating:
        parts.append(_text(x + 22, y + 12, rating, anchor="start", size=9, fill=_TEXT_DIM, weight=550))
    return "".join(parts)


def _draw_busbar(svg: list[str], graph: BoardElectricalGraph, busbar: ElectricalNode, center_x: float, y: float, width_px: float, selected_ids: set[str]) -> None:
    half = max(55.0, width_px / 2 - 22)
    selected = busbar.node_id in selected_ids
    stroke = _ACCENT if selected else _LINE
    svg.append(f'<line x1="{center_x - half:.1f}" y1="{y:.1f}" x2="{center_x + half:.1f}" y2="{y:.1f}" stroke="{stroke}" stroke-width="5" stroke-linecap="round"/>')
    svg.append(_text(center_x - half, y - 10, busbar.label, anchor="start", size=10, fill=_TEXT, weight=680))

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
        svg.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y + 30:.1f}" stroke="{_LINE_DIM}" stroke-width="2"/>')
        svg.append(_breaker_symbol(x, y + 52, device.label, _rating(device), highlighted=device.node_id in selected_ids))
        cable_y1 = y + 78
        endpoint_y = y + 126
        svg.append(f'<line x1="{x:.1f}" y1="{cable_y1:.1f}" x2="{x:.1f}" y2="{endpoint_y:.1f}" stroke="{_LINE_DIM}" stroke-width="2"/>')
        cable_text = _cable(cable)
        if cable_text:
            svg.append(_text(x + 9, y + 102, cable_text, anchor="start", size=8, fill=_TEXT_DIM, weight=520))

        if endpoint is None:
            svg.append(_text(x, endpoint_y + 18, "Unresolved endpoint", size=9, fill="#f7bf4f"))
            continue

        endpoint_selected = endpoint.node_id in selected_ids
        endpoint_color = _ACCENT if endpoint_selected else _GOOD
        if endpoint.kind == "load":
            svg.append(f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="6" fill="#08131f" stroke="{endpoint_color}" stroke-width="2"/>')
            svg.append(f'<line x1="{x - 4:.1f}" y1="{endpoint_y + 4:.1f}" x2="{x + 4:.1f}" y2="{endpoint_y - 4:.1f}" stroke="{endpoint_color}" stroke-width="1.5"/>')
            svg.append(_text(x, endpoint_y + 21, endpoint.label, size=10, fill=_TEXT, weight=650))
            detail = endpoint.display_detail or (f"{endpoint.load_kw:g} kW · {'3P' if endpoint.phase == 'three' else '1P'}" if endpoint.load_kw is not None else "")
            if detail:
                svg.append(_text(x, endpoint_y + 34, detail, size=8, fill=_TEXT_DIM, weight=500))
        else:
            svg.append(f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="4" fill="{endpoint_color}"/>')
            svg.append(_text(x + 10, endpoint_y + 4, endpoint.label, anchor="start", size=10, fill=_TEXT, weight=650))
            if child_busbar is not None:
                next_y = endpoint_y + 46
                svg.append(f'<line x1="{x:.1f}" y1="{endpoint_y + 5:.1f}" x2="{x:.1f}" y2="{next_y:.1f}" stroke="{_LINE_DIM}" stroke-width="2"/>')
                _draw_busbar(svg, graph, child_busbar, x, next_y, max(110.0, branch_width * .86), selected_ids)


def render_hmi_single_line_svg(graph: BoardElectricalGraph, *, selected_node_ids: tuple[str, ...] = ()) -> str:
    """Render a compact conventional single-line view of ``graph`` as SVG."""
    validate_board_graph(graph)
    by_id = graph.node_by_id
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
    height = max(560, 235 + depth * 190)
    cx = width / 2

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" preserveAspectRatio="xMidYMin meet">',
        '<defs><filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
        '<rect width="100%" height="100%" fill="#08131f"/>',
    ]

    # Source / supply symbol.
    svg.append(f'<circle cx="{cx:.1f}" cy="38" r="17" fill="#0a1727" stroke="{_LINE}" stroke-width="2"/>')
    svg.append(_text(cx, 42, "~", size=16, fill=_TEXT, weight=600))
    svg.append(_text(cx + 28, 35, source.label, anchor="start", size=11, fill=_TEXT, weight=680))
    svg.append(f'<line x1="{cx:.1f}" y1="55" x2="{cx:.1f}" y2="75" stroke="{_LINE_DIM}" stroke-width="2"/>')

    if incomer is not None:
        svg.append(_breaker_symbol(cx, 98, incomer.label, _rating(incomer), highlighted=incomer.node_id in selected_ids))
    if busbar is not None:
        svg.append(f'<line x1="{cx:.1f}" y1="124" x2="{cx:.1f}" y2="148" stroke="{_LINE_DIM}" stroke-width="2"/>')
        _draw_busbar(svg, graph, busbar, cx, 152, width - 120, selected_ids)

    svg.append('</svg>')
    return "".join(svg)
