"""Adaptive single-line SVG renderer for the HMI Board Planner preview.

The renderer is presentation-only. Large boards keep an intrinsic engineering-drawing
width so dense circuits remain readable inside the scrollable workspace. Selected
fields or circuits still narrow the visible branch set, while every visible electrical
path is drawn continuously from its upstream busbar to the downstream busbar/load.
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


def _first_child(graph: BoardElectricalGraph, node: ElectricalNode | None, kind: str) -> ElectricalNode | None:
    if node is None:
        return None
    return next((child for child in graph.children_of(node.node_id) if child.kind == kind), None)


def _branch_endpoint(graph: BoardElectricalGraph, protective: ElectricalNode) -> tuple[ElectricalNode | None, ElectricalNode | None]:
    cable = _first_child(graph, protective, "cable")
    if cable is None:
        return None, None
    endpoint = next((child for child in graph.children_of(cable.node_id) if child.kind in ("load", "field", "sub_board")), None)
    return cable, endpoint


def _downstream_busbar(graph: BoardElectricalGraph, endpoint: ElectricalNode | None) -> ElectricalNode | None:
    if endpoint is None:
        return None
    if endpoint.kind == "field":
        return _first_child(graph, endpoint, "busbar")
    if endpoint.kind == "sub_board":
        return _first_child(graph, _first_child(graph, endpoint, "incomer"), "busbar")
    return None


def _rating(node: ElectricalNode | None) -> str:
    return "" if node is None or node.rating_a is None else f"{node.rating_a:g} A"


def _cable(node: ElectricalNode | None) -> str:
    if node is None or node.cable_mm2 is None:
        return ""
    runs = node.cable_runs or 1
    return f"{runs}×{node.cable_mm2:g} mm²" if runs > 1 else f"{node.cable_mm2:g} mm²"


def _text(
    x: float,
    y: float,
    value: str,
    *,
    anchor: str = "middle",
    size: int = 11,
    fill: str = _TEXT,
    weight: int = 600,
    rotate: int | None = None,
) -> str:
    transform = "" if rotate is None else f' transform="rotate({rotate} {x:.1f} {y:.1f})"'
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{transform} '
        f'font-family="Inter,Segoe UI,sans-serif" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}">{escape(value)}</text>'
    )


def _line(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    active: bool = False,
    width: float = 2.0,
    structural: bool = False,
) -> str:
    stroke = _ACCENT if active else (_LINE if structural else _LINE_DIM)
    glow = ' filter="url(#glow)"' if active else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width:g}"{glow}/>'


def _breaker_symbol(
    x: float,
    y: float,
    label: str,
    rating: str,
    *,
    highlighted: bool = False,
    compact_vertical: bool = False,
    structural: bool = False,
) -> str:
    stroke = _ACCENT if highlighted else _LINE
    glow = ' filter="url(#glow)"' if highlighted else ""
    parts = [
        _line(x, y - 23, x, y - 10, active=highlighted, structural=structural),
        f'<rect x="{x - 13:.1f}" y="{y - 10:.1f}" width="26" height="20" rx="2" fill="#0a1727" stroke="{stroke}" stroke-width="1.7"{glow}/>',
        f'<line x1="{x - 8:.1f}" y1="{y + 6:.1f}" x2="{x + 8:.1f}" y2="{y - 6:.1f}" stroke="{stroke}" stroke-width="1.9"{glow}/>',
        _line(x, y + 10, x, y + 26, active=highlighted, structural=structural),
    ]
    if compact_vertical:
        parts.append(_text(x - 18, y + 12, label, anchor="start", size=9, fill=_TEXT, weight=680, rotate=-90))
        if rating:
            parts.append(_text(x + 18, y + 12, rating, anchor="start", size=8, fill=_TEXT_DIM, weight=560, rotate=-90))
    else:
        parts.append(_text(x + 22, y - 1, label, anchor="start", size=11, fill=_TEXT, weight=680))
        if rating:
            parts.append(_text(x + 22, y + 13, rating, anchor="start", size=9, fill=_TEXT_DIM, weight=560))
    return "".join(parts)


def _subtree_node_ids(graph: BoardElectricalGraph, node: ElectricalNode) -> set[str]:
    result = {node.node_id}
    pending = [node]
    while pending:
        current = pending.pop()
        for child in graph.children_of(current.node_id):
            if child.node_id not in result:
                result.add(child.node_id)
                pending.append(child)
    return result


def _branch_has_selection(graph: BoardElectricalGraph, device: ElectricalNode, selected_ids: set[str]) -> bool:
    """Treat equipment selection as focus, but not passive busbar/incomer context."""
    for node_id in _subtree_node_ids(graph, device) & selected_ids:
        node = graph.node_by_id.get(node_id)
        if node is not None and node.kind not in ("busbar", "incomer"):
            return True
    return False


def _visible_branch_data(graph: BoardElectricalGraph, busbar: ElectricalNode, selected_ids: set[str]):
    data = []
    for device in _children(graph, busbar, "protective_device"):
        cable, endpoint = _branch_endpoint(graph, device)
        child_busbar = _downstream_busbar(graph, endpoint)
        data.append((device, cable, endpoint, child_busbar))
    active = [item for item in data if _branch_has_selection(graph, item[0], selected_ids)]
    return active or data, bool(active)


def _visible_leaf_count(graph: BoardElectricalGraph, busbar: ElectricalNode, selected_ids: set[str]) -> int:
    data, _ = _visible_branch_data(graph, busbar, selected_ids)
    if not data:
        return 1
    total = 0
    for _, _, _, child_busbar in data:
        total += _visible_leaf_count(graph, child_busbar, selected_ids) if child_busbar is not None else 1
    return max(1, total)


def _draw_busbar(
    svg: list[str],
    graph: BoardElectricalGraph,
    busbar: ElectricalNode,
    center_x: float,
    y: float,
    width_px: float,
    selected_ids: set[str],
) -> None:
    half = max(55.0, width_px / 2 - 22)
    selected = busbar.node_id in selected_ids
    stroke = _ACCENT if selected else _LINE
    glow = ' filter="url(#glow)"' if selected else ""
    svg.append(
        f'<line x1="{center_x - half:.1f}" y1="{y:.1f}" x2="{center_x + half:.1f}" y2="{y:.1f}" '
        f'stroke="{stroke}" stroke-width="5" stroke-linecap="round"{glow}/>'
    )
    svg.append(_text(center_x - half, y - 10, busbar.label, anchor="start", size=11, fill=_TEXT, weight=700))

    branch_data, _ = _visible_branch_data(graph, busbar, selected_ids)
    if not branch_data:
        return

    counts = [
        _visible_leaf_count(graph, child_busbar, selected_ids) if child_busbar is not None else 1
        for _, _, _, child_busbar in branch_data
    ]
    total = sum(counts)
    unit = width_px / total
    cursor = center_x - width_px / 2

    for count, (device, cable, endpoint, child_busbar) in zip(counts, branch_data):
        branch_width = count * unit
        x = cursor + branch_width / 2
        cursor += branch_width
        branch_active = _branch_has_selection(graph, device, selected_ids)
        leaf_branch = child_busbar is None
        structural_branch = not leaf_branch

        # Structural field/sub-board feeders are deliberately brighter/heavier than final ways.
        path_width = 3.2 if structural_branch else 2.1
        svg.append(_line(x, y, x, y + 32, active=branch_active, width=path_width, structural=structural_branch))
        svg.append(
            _breaker_symbol(
                x,
                y + 55,
                device.label,
                _rating(device),
                highlighted=branch_active,
                compact_vertical=leaf_branch,
                structural=structural_branch,
            )
        )
        endpoint_y = y + 156
        svg.append(_line(x, y + 81, x, endpoint_y, active=branch_active, width=path_width, structural=structural_branch))

        cable_text = _cable(cable)
        if cable_text:
            if leaf_branch:
                svg.append(_text(x + 10, y + 134, cable_text, anchor="start", size=8, fill=_TEXT_DIM, weight=530, rotate=-90))
            else:
                svg.append(_text(x + 12, y + 116, cable_text, anchor="start", size=9, fill=_TEXT_DIM, weight=580))

        if endpoint is None:
            svg.append(_text(x, endpoint_y + 18, "Unresolved endpoint", size=9, fill="#f7bf4f"))
            continue

        endpoint_color = _ACCENT if branch_active else _GOOD
        endpoint_glow = ' filter="url(#glow)"' if branch_active else ""
        if endpoint.kind == "load":
            svg.append(
                f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="6" fill="#08131f" stroke="{endpoint_color}" '
                f'stroke-width="2"{endpoint_glow}/>'
            )
            svg.append(
                f'<line x1="{x - 4:.1f}" y1="{endpoint_y + 4:.1f}" x2="{x + 4:.1f}" y2="{endpoint_y - 4:.1f}" '
                f'stroke="{endpoint_color}" stroke-width="1.6"{endpoint_glow}/>'
            )
            svg.append(_text(x + 18, endpoint_y - 8, endpoint.label, anchor="start", size=9, fill=_TEXT, weight=650, rotate=-90))
            detail = endpoint.display_detail or (
                f"{endpoint.load_kw:g} kW · {'3P' if endpoint.phase == 'three' else '1P'}"
                if endpoint.load_kw is not None
                else ""
            )
            if detail:
                svg.append(_text(x, endpoint_y + 28, detail, size=8, fill=_TEXT_DIM, weight=500))
        else:
            # Field/sub-board endpoint is a visible junction in the structural feeder spine.
            svg.append(f'<circle cx="{x:.1f}" cy="{endpoint_y:.1f}" r="5.5" fill="{endpoint_color}"{endpoint_glow}/>')
            svg.append(_text(x + 12, endpoint_y + 4, endpoint.label, anchor="start", size=11, fill=_TEXT, weight=700))
            if child_busbar is not None:
                next_y = endpoint_y + 74
                svg.append(_line(x, endpoint_y + 5, x, next_y, active=branch_active, width=3.2, structural=True))
                # Small tee marker makes the physical connection into the downstream busbar explicit.
                svg.append(_line(x - 9, next_y, x + 9, next_y, active=branch_active, width=3.2, structural=True))
                _draw_busbar(
                    svg,
                    graph,
                    child_busbar,
                    x,
                    next_y,
                    max(150.0, branch_width * .94),
                    selected_ids,
                )


def render_hmi_single_line_svg(graph: BoardElectricalGraph, *, selected_node_ids: tuple[str, ...] = ()) -> str:
    """Render a scrollable, readable single-line diagram for large distribution boards."""
    validate_board_graph(graph)
    source = graph.root_nodes[0]
    incomer = _first_child(graph, source, "incomer")
    busbar = _first_child(graph, incomer, "busbar")
    selected_ids = set(selected_node_ids)

    visible_leafs = _visible_leaf_count(graph, busbar, selected_ids) if busbar is not None else 1
    width = max(900, min(6200, 104 * visible_leafs + 320))

    depth = 1
    if busbar is not None:
        pending = [(busbar, 1)]
        seen: set[str] = set()
        while pending:
            current, level = pending.pop(0)
            if current.node_id in seen:
                continue
            seen.add(current.node_id)
            depth = max(depth, level)
            data, _ = _visible_branch_data(graph, current, selected_ids)
            for _, _, _, child_busbar in data:
                if child_busbar is not None:
                    pending.append((child_busbar, level + 1))
    height = max(680, 220 + depth * 265)
    cx = width / 2

    source_active = source.node_id in selected_ids
    incomer_active = incomer is not None and incomer.node_id in selected_ids
    busbar_active = busbar is not None and busbar.node_id in selected_ids
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" preserveAspectRatio="xMidYMin meet">',
        '<defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M 28 0 L 0 0 0 28" fill="none" stroke="#18314b" stroke-width="0.6" opacity="0.18"/></pattern></defs>',
        '<rect width="100%" height="100%" fill="#08131f"/><rect width="100%" height="100%" fill="url(#grid)"/>',
    ]
    source_stroke = _ACCENT if source_active else _LINE
    source_glow = ' filter="url(#glow)"' if source_active else ""
    svg.append(f'<circle cx="{cx:.1f}" cy="35" r="17" fill="#0a1727" stroke="{source_stroke}" stroke-width="2"{source_glow}/>')
    svg.append(_text(cx, 39, "~", size=16, fill=_TEXT, weight=600))
    svg.append(_text(cx + 28, 32, source.label, anchor="start", size=11, fill=_TEXT, weight=700))
    svg.append(_line(cx, 52, cx, 71, active=source_active or incomer_active or busbar_active, width=3.2, structural=True))
    if incomer is not None:
        svg.append(_breaker_symbol(cx, 92, incomer.label, _rating(incomer), highlighted=incomer_active or busbar_active, structural=True))
    if busbar is not None:
        svg.append(_line(cx, 118, cx, 139, active=busbar_active, width=3.2, structural=True))
        _draw_busbar(svg, graph, busbar, cx, 143, width - 140, selected_ids)
    svg.append("</svg>")
    return "".join(svg)
