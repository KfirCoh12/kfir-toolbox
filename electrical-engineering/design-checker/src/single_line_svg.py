"""Dependency-free live SVG rendering for the hierarchy-native board graph."""
from html import escape

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph

_NODE_WIDTH = 150
_X_GAP = 185
_Y_GAP = 115
_MARGIN = 70


def _detail(node: ElectricalNode) -> str:
    if node.kind in ("incomer", "protective_device"):
        return f"{node.rating_a:g} A" if node.rating_a is not None else "rating pending"
    if node.kind == "cable":
        if node.cable_mm2 is None:
            return "cable pending"
        runs = node.cable_runs or 1
        prefix = f"{runs} × " if runs > 1 else ""
        return f"{prefix}{node.cable_mm2:g} mm²"
    if node.kind == "load":
        bits = []
        if node.load_kw is not None:
            bits.append(f"{node.load_kw:g} kW")
        if node.assigned_phase:
            bits.append(node.assigned_phase)
        elif node.phase:
            bits.append("3P" if node.phase == "three" else "1P")
        return " · ".join(bits) if bits else "load pending"
    if node.kind == "busbar":
        return "busbar"
    if node.kind == "source":
        return "incoming supply"
    return node.kind.replace("_", " ")


def _node_status_class(node: ElectricalNode) -> str:
    if node.scope_status == "NOT_VERIFIED":
        return "bad"
    if node.scope_status == "PARTIAL_SCOPE" or node.issue_codes:
        return "warn"
    return "normal"


def render_board_graph_svg(graph: BoardElectricalGraph) -> str:
    """Render the current electrical hierarchy as an SVG string.

    The layout is deterministic and based only on parent/child relationships. It is
    intentionally simple, but supports arbitrary depth so sub-board hierarchy can be
    added without rewriting the renderer.
    """
    validate_board_graph(graph)
    by_id = graph.node_by_id
    children = {node.node_id: list(graph.children_of(node.node_id)) for node in graph.nodes}
    root = graph.root_nodes[0]

    depth: dict[str, int] = {}
    leaves: list[str] = []

    def walk(node_id: str, level: int) -> None:
        depth[node_id] = level
        node_children = children[node_id]
        if not node_children:
            leaves.append(node_id)
            return
        for child in node_children:
            walk(child.node_id, level + 1)

    walk(root.node_id, 0)
    leaf_x = {
        node_id: _MARGIN + index * _X_GAP
        for index, node_id in enumerate(leaves)
    }
    x: dict[str, float] = {}

    def place(node_id: str) -> float:
        if node_id in x:
            return x[node_id]
        node_children = children[node_id]
        if not node_children:
            x[node_id] = leaf_x[node_id]
        else:
            child_positions = [place(child.node_id) for child in node_children]
            x[node_id] = sum(child_positions) / len(child_positions)
        return x[node_id]

    place(root.node_id)
    max_depth = max(depth.values())
    width = max(760, int((_MARGIN * 2) + max(0, len(leaves) - 1) * _X_GAP + _NODE_WIDTH))
    height = int((_MARGIN * 2) + max_depth * _Y_GAP + 110)

    lines: list[str] = []
    for node in graph.nodes:
        if node.parent_id is None:
            continue
        px = x[node.parent_id]
        py = _MARGIN + depth[node.parent_id] * _Y_GAP + 48
        cx = x[node.node_id]
        cy = _MARGIN + depth[node.node_id] * _Y_GAP - 4
        mid_y = (py + cy) / 2
        lines.append(
            f'<path d="M {px:.1f} {py:.1f} V {mid_y:.1f} H {cx:.1f} V {cy:.1f}" '
            'class="edge" />'
        )

    shapes: list[str] = []
    for node in graph.nodes:
        cx = x[node.node_id]
        cy = _MARGIN + depth[node.node_id] * _Y_GAP
        klass = _node_status_class(node)
        label = escape(node.label)
        detail = escape(_detail(node))
        if node.kind == "busbar":
            child_positions = [x[child.node_id] for child in children[node.node_id]]
            left = min(child_positions) - 55 if child_positions else cx - 90
            right = max(child_positions) + 55 if child_positions else cx + 90
            shapes.append(
                f'<line x1="{left:.1f}" y1="{cy:.1f}" x2="{right:.1f}" y2="{cy:.1f}" class="bus" />'
                f'<text x="{cx:.1f}" y="{cy - 13:.1f}" class="label center">{label}</text>'
                f'<text x="{cx:.1f}" y="{cy + 23:.1f}" class="detail center">{detail}</text>'
            )
            continue

        rx = cx - _NODE_WIDTH / 2
        shapes.append(
            f'<rect x="{rx:.1f}" y="{cy - 28:.1f}" width="{_NODE_WIDTH}" height="58" rx="10" class="node {klass}" />'
            f'<text x="{cx:.1f}" y="{cy - 4:.1f}" class="label center">{label}</text>'
            f'<text x="{cx:.1f}" y="{cy + 17:.1f}" class="detail center">{detail}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {width} {height}" role="img" aria-label="Single line diagram for {escape(graph.board_id)}">
<style>
svg {{ background:#0b1220; border:1px solid #263449; border-radius:16px; font-family:Inter,Segoe UI,Arial,sans-serif; }}
.edge {{ fill:none; stroke:#94a3b8; stroke-width:2; }}
.bus {{ stroke:#e2e8f0; stroke-width:5; stroke-linecap:round; }}
.node {{ fill:#111827; stroke:#475569; stroke-width:1.5; }}
.node.warn {{ stroke:#f59e0b; }}
.node.bad {{ stroke:#ef4444; }}
.label {{ fill:#f8fafc; font-size:13px; font-weight:650; }}
.detail {{ fill:#94a3b8; font-size:11px; }}
.center {{ text-anchor:middle; dominant-baseline:middle; }}
</style>
{''.join(lines)}
{''.join(shapes)}
</svg>'''
