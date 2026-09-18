"""NetworkX-based graph construction and topological analysis."""

import networkx as nx
from typing import Dict, Any, List, Tuple

# Color palette adhering to sleek, high-contrast dark fintech UI
COLOR_MAP = {
    "Transaction": "#F59E0B", # Amber
    "Account": "#3B82F6",     # Vibrant Blue
    "Customer": "#10B981",    # Emerald Green
    "Device": "#EF4444",      # Crimson / High Alert Red
    "Merchant": "#8B5CF6",    # Violet Purple
    "Beneficiary": "#EC4899"  # Hot Pink
}

SHAPE_MAP = {
    "Transaction": "diamond",
    "Account": "ellipse",
    "Customer": "box",
    "Device": "triangle",
    "Merchant": "hexagon",
    "Beneficiary": "star"
}

def build_investigation_graph(
    discovered_nodes: List[Dict[str, Any]],
    discovered_edges: List[Dict[str, Any]]
) -> nx.DiGraph:
    """Build a NetworkX DiGraph from discovered entities and relationships."""
    G = nx.DiGraph()

    for node in discovered_nodes:
        n_id = str(node["id"])
        n_type = node.get("type", "Account")
        color = COLOR_MAP.get(n_type, "#94A3B8")
        shape = SHAPE_MAP.get(n_type, "ellipse")
        
        # Build hover tooltip
        tooltip_lines = [f"<b>{n_id}</b> ({n_type})"]
        for k, v in node.get("properties", {}).items():
            if k not in ["id", "type"]:
                tooltip_lines.append(f"{k}: {v}")
        title = "<br>".join(tooltip_lines)

        size = 28 if n_type in ["Device", "Beneficiary"] else 22

        G.add_node(
            n_id,
            label=node.get("label", n_id),
            node_type=n_type,
            color=color,
            shape=shape,
            size=size,
            title=title,
            properties=node.get("properties", {})
        )

    for edge in discovered_edges:
        src = str(edge["source"])
        tgt = str(edge["target"])
        rel = edge.get("relationship", "CONNECTED_TO")
        amt = edge.get("amount")
        edge_title = f"{rel}" + (f": ${amt:,.2f}" if amt else "")
        
        # Ensure endpoints exist
        if not G.has_node(src):
            G.add_node(src, label=src, node_type="Entity", color="#94A3B8", shape="ellipse", size=20, title=src)
        if not G.has_node(tgt):
            G.add_node(tgt, label=tgt, node_type="Entity", color="#94A3B8", shape="ellipse", size=20, title=tgt)

        G.add_edge(
            src,
            tgt,
            relationship=rel,
            label=edge.get("label", rel),
            title=edge_title,
            weight=edge.get("weight", 1.0),
            amount=amt
        )

    return G

def analyze_graph_topology(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze network topology to detect graph-level fraud signatures."""
    if len(G.nodes) == 0:
        return {
            "total_nodes": 0,
            "total_edges": 0,
            "hubs": [],
            "cycles": [],
            "max_in_degree": None,
            "is_densely_connected": False
        }

    # 1. Degree Analysis
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    total_degrees = {n: in_degrees[n] + out_degrees[n] for n in G.nodes}

    # Sort hubs by degree
    sorted_hubs = sorted(total_degrees.items(), key=lambda x: x[1], reverse=True)
    top_hubs = [{"node": n, "degree": d, "type": G.nodes[n].get("node_type", "Unknown")} for n, d in sorted_hubs if d >= 3]

    # Find maximum in-degree node (candidate aggregator / cashout point)
    sorted_in = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)
    max_in = sorted_in[0] if sorted_in and sorted_in[0][1] >= 2 else None

    # 2. Cycle Detection (Circular money laundering)
    cycles = []
    try:
        simple_cyc = list(nx.simple_cycles(G))
        # Keep small distinct cycles
        for c in simple_cyc[:3]:
            if len(c) >= 3:
                cycles.append(c + [c[0]])
    except Exception:
        pass

    # 3. Density / Connected Components
    undirected = G.to_undirected()
    components = list(nx.connected_components(undirected))
    density = nx.density(G)

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "top_hubs": top_hubs[:5],
        "aggregator_node": {"node": max_in[0], "incoming_count": max_in[1]} if max_in else None,
        "circular_cycles": cycles,
        "connected_components_count": len(components),
        "graph_density": round(density, 4)
    }
