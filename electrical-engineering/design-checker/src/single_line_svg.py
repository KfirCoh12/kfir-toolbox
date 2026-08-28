"""Dependency-free live SVG rendering for the hierarchy-native board graph."""
from html import escape

from .board_graph import BoardElectricalGraph, ElectricalNode, validate_board_graph

_NODE_WIDTH = 188
_X_GAP = 225
_Y_GAP = 132
_MARGIN = 72
_MIN_WIDTH = 820
_VISIBLE_KINDS = {"source", "incomer", "busbar", "load", "field", "sub_board"}
_GROUP_CLASSES = ("group-green", "group-blue", "group-purple", "group-amber", "group-teal", "group-rose")


def _status_class(*nodes: ElectricalNode) -> str:
    if any(node.scope_status == "NOT_VERIFIED" for node in nodes):
        return "bad"
    if any(node.scope_status == "PARTIAL_SCOPE" or node.issue_codes for node in nodes):
        return "warn"
    return "normal"


def _branch_components(graph: BoardElectricalGraph, endpoint: ElectricalNode) -> tuple[ElectricalNode | None, ElectricalNode | None]:
    """Return the hidden cable and protection nodes feeding a visible endpoint."""
    by_id = graph.node_by_id
    cable = by_id.get(endpoint.parent_id) if endpoint.parent_id else None
    if cable is None or cable.kind != "cable":
        return None, None
    device = by_id.get(cable.parent_id) if cable.parent_id else None
    if device is None or device.kind != "protective_device":
        device = None
    return cable, device


def _protection_text(device: ElectricalNode | None) -> str:
    if device is None or device.rating_a is None:
        return "protection pending"
    return f"{device.rating_a:g} A protection"


def _cable_text(cable: ElectricalNode | None) -> str:
    if cable is None or cable.cable_mm2 is None:
        return "cable pending"
    runs = cable.cable_runs or 1
    prefix = f"{runs} × " if runs > 1 else ""
    return f"{prefix}{cable.cable_mm2:g} mm² cable"


def _visible_text(graph: BoardElectricalGraph, node: ElectricalNode) -> tuple[str, str, str]:
    """Return title plus two compact information lines for one visible object."""
    if node.kind == "source":
        return node.label, "incoming supply", ""
    if node.kind == "incomer":
        rating = f"{node.rating_a:g} A" if node.rating_a is not None else "auto · rating pending"
        return node.label, rating, ""
    if node.kind == "busbar":
        return node.label, "busbar", ""

    cable, device = _branch_components(graph, node)
    cid = (node.circuit_id or "").strip()
    branch_info = " · ".join(x for x in (cid, _protection_text(device), _cable_text(cable)) if x)

    if node.kind == "load":
        load_bits = []
        if node.load_kw is not None:
            load_bits.append(f"{node.load_kw:g} kW")
        if node.assigned_phase:
            load_bits.append(node.assigned_phase)
        elif node.phase:
            load_bits.append("3P" if node.phase == "three" else "1P")
        return f"{cid} · {node.label}" if cid else node.label, " · ".join(load_bits), branch_info
    if node.kind == "field":
        return node.label, f"{node.field_ref or 'Field'} · grouped circuits", branch_info
    if node.kind == "sub_board":
        return node.label, f"{node.board_ref or 'Sub-board'} · downstream board", branch_info
    return node.label, node.kind.replace("_", " "), branch_info


def _visible_parent_id(graph: BoardElectricalGraph, node: ElectricalNode) -> str | None:
    by_id = graph.node_by_id
    parent_id = node.parent_id
    while parent_id is not None:
        parent = by_id[parent_id]
        if parent.kind in _VISIBLE_KINDS:
            return parent.node_id
        parent_id = parent.parent_id
    return None


def _group_class_for_node(graph: BoardElectricalGraph, node: ElectricalNode, group_index: dict[str, int]) -> str:
    group_node: ElectricalNode | None = node if node.kind in ("field", "sub_board") else None
    if group_node is None:
        for ancestor in graph.ancestors_of(node.node_id):
            if ancestor.kind in ("field", "sub_board"):
                group_node = ancestor
                break
    if group_node is None:
        return ""
    index = group_index.setdefault(group_node.node_id, len(group_index))
    return _GROUP_CLASSES[index % len(_GROUP_CLASSES)]


def render_board_graph_svg(
    graph: BoardElectricalGraph,
    selected_node_ids: tuple[str, ...] = tuple(),
) -> str:
    """Render a compact, fit-to-view SLD from the electrical hierarchy.

    Protection and cable nodes stay in the engineering graph but are presented as
    information inside their final-load/field/sub-board box. The visual hierarchy
    therefore follows what the user is designing rather than exposing every backend
    component as a separate selectable box.
    """
    validate_board_graph(graph)
    visible_nodes = tuple(node for node in graph.nodes if node.kind in _VISIBLE_KINDS)
    visible_by_id = {node.node_id: node for node in visible_nodes}
    root = graph.root_nodes[0]

    parent_of = {node.node_id: _visible_parent_id(graph, node) for node in visible_nodes}
    children: dict[str, list[ElectricalNode]] = {node.node_id: [] for node in visible_nodes}
    for node in visible_nodes:
        parent_id = parent_of[node.node_id]
        if parent_id is not None:
            children[parent_id].append(node)

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

    leaf_span = max(0, len(leaves) - 1) * _X_GAP
    natural_width = int((_MARGIN * 2) + leaf_span + _NODE_WIDTH)
    width = max(_MIN_WIDTH, natural_width)
    first_leaf_x = (width - leaf_span) / 2
    leaf_x = {node_id: first_leaf_x + index * _X_GAP for index, node_id in enumerate(leaves)}
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
    max_depth = max(depth.values()) if depth else 0
    height = int((_MARGIN * 2) + max_depth * _Y_GAP + 120)

    edges: list[str] = []
    for node in visible_nodes:
        parent_id = parent_of[node.node_id]
        if parent_id is None:
            continue
        px = x[parent_id]
        py = _MARGIN + depth[parent_id] * _Y_GAP + 45
        cx = x[node.node_id]
        cy = _MARGIN + depth[node.node_id] * _Y_GAP - 36
        mid_y = (py + cy) / 2
        edges.append(
            f'<path d="M {px:.1f} {py:.1f} V {mid_y:.1f} H {cx:.1f} V {cy:.1f}" class="edge" />'
        )

    shapes: list[str] = []
    selected = set(selected_node_ids)
    group_index: dict[str, int] = {}
    for node in visible_nodes:
        cx = x[node.node_id]
        cy = _MARGIN + depth[node.node_id] * _Y_GAP
        title, detail1, detail2 = (escape(part) for part in _visible_text(graph, node))
        group_class = _group_class_for_node(graph, node, group_index)

        if node.kind == "busbar":
            child_positions = [x[child.node_id] for child in children[node.node_id]]
            left = min(child_positions) - 66 if child_positions else cx - 105
            right = max(child_positions) + 66 if child_positions else cx + 105
            selected_class = " selected" if node.node_id in selected else ""
            shapes.append(
                f'<line x1="{left:.1f}" y1="{cy:.1f}" x2="{right:.1f}" y2="{cy:.1f}" class="bus{selected_class}" />'
                f'<text x="{cx:.1f}" y="{cy - 15:.1f}" class="label center">{title}</text>'
                f'<text x="{cx:.1f}" y="{cy + 24:.1f}" class="detail center">{detail1}</text>'
            )
            continue

        cable, device = _branch_components(graph, node) if node.kind in ("load", "field", "sub_board") else (None, None)
        status = _status_class(node, *(part for part in (cable, device) if part is not None))
        selected_class = " selected" if node.node_id in selected else ""
        classes = " ".join(part for part in ("node", status, group_class, selected_class.strip()) if part)
        box_height = 78 if detail2 else 62
        rx = cx - _NODE_WIDTH / 2
        top = cy - box_height / 2
        shapes.append(
            f'<rect x="{rx:.1f}" y="{top:.1f}" width="{_NODE_WIDTH}" height="{box_height}" rx="12" class="{classes}" />'
            f'<text x="{cx:.1f}" y="{cy - (15 if detail2 else 9):.1f}" class="label center">{title}</text>'
            f'<text x="{cx:.1f}" y="{cy + (6 if detail2 else 13):.1f}" class="detail center">{detail1}</text>'
            + (f'<text x="{cx:.1f}" y="{cy + 27:.1f}" class="detail small center">{detail2}</text>' if detail2 else "")
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Single line diagram for {escape(graph.board_id)}">
<style>
svg {{ background:#0b1220; border:1px solid #263449; border-radius:16px; font-family:Inter,Segoe UI,Arial,sans-serif; }}
.edge {{ fill:none; stroke:#64748b; stroke-width:2; }}
.bus {{ stroke:#e2e8f0; stroke-width:5; stroke-linecap:round; }}
.bus.selected {{ stroke:#60a5fa; stroke-width:8; }}
.node {{ fill:#111827; stroke:#475569; stroke-width:1.5; }}
.node.warn {{ stroke:#f59e0b; }}
.node.bad {{ stroke:#ef4444; }}
.node.selected {{ stroke:#60a5fa; stroke-width:3; }}
.node.group-green {{ fill:#10231c; stroke:#2f6b52; }}
.node.group-blue {{ fill:#102036; stroke:#355f91; }}
.node.group-purple {{ fill:#20182f; stroke:#69518f; }}
.node.group-amber {{ fill:#2a2111; stroke:#856c32; }}
.node.group-teal {{ fill:#102627; stroke:#367678; }}
.node.group-rose {{ fill:#2b1721; stroke:#875068; }}
.label {{ fill:#f8fafc; font-size:13px; font-weight:650; }}
.detail {{ fill:#a8b4c6; font-size:11px; }}
.detail.small {{ fill:#7f8da3; font-size:9.5px; }}
.center {{ text-anchor:middle; dominant-baseline:middle; }}
</style>
{''.join(edges)}
{''.join(shapes)}
</svg>'''