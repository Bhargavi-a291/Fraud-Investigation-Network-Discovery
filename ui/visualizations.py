"""Interactive Graph Network Visualizer and Risk Gauge Components."""

import json
import tempfile
import os
import plotly.graph_objects as go
import networkx as nx
from typing import List, Dict, Any

COLOR_PALETTE = {
    "Transaction": "#F59E0B", # Amber
    "Account": "#3B82F6",     # Blue
    "Customer": "#10B981",    # Emerald
    "Device": "#EF4444",      # Red
    "Merchant": "#8B5CF6",    # Purple
    "Beneficiary": "#EC4899", # Pink
    "Entity": "#94A3B8"       # Slate
}

def render_network_graph(
    discovered_nodes: List[Dict[str, Any]],
    discovered_edges: List[Dict[str, Any]],
    height: str = "540px"
) -> str:
    """Generate an interactive HTML string for the discovered network graph using PyVis."""
    try:
        from pyvis.network import Network
        
        net = Network(
            height=height,
            width="100%",
            bgcolor="#0E1726",
            font_color="#F8FAFC",
            directed=True
        )

        # Configure physics for clear, readable cluster spacing
        net.set_options("""
        {
          "physics": {
            "forceAtlas2Based": {
              "gravitationalConstant": -50,
              "centralGravity": 0.01,
              "springLength": 100,
              "springConstant": 0.08
            },
            "maxVelocity": 50,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"iterations": 150}
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 200,
            "navigationButtons": true,
            "keyboard": true
          },
          "edges": {
            "smooth": {"type": "continuous"},
            "color": {"color": "#64748B", "highlight": "#38BDF8"}
          }
        }
        """)

        for node in discovered_nodes:
            n_id = str(node["id"])
            n_type = node.get("type", "Entity")
            color = COLOR_PALETTE.get(n_type, "#94A3B8")
            
            # Tooltip
            props = node.get("properties", {})
            tooltip = f"<b>{n_id}</b> [{n_type}]<br>" + "<br>".join([f"{k}: {v}" for k, v in props.items()])

            shape = "diamond" if n_type == "Transaction" else ("triangle" if n_type == "Device" else "dot")
            size = 28 if n_type in ["Device", "Beneficiary", "Transaction"] else 20

            net.add_node(
                n_id,
                label=f"{n_id}\n({n_type})",
                title=tooltip,
                color=color,
                shape=shape,
                size=size
            )

        for edge in discovered_edges:
            src = str(edge["source"])
            tgt = str(edge["target"])
            rel = edge.get("relationship", "")
            amt = edge.get("amount")
            edge_label = f"${amt:,.0f}" if amt else rel
            
            net.add_edge(
                src,
                tgt,
                title=f"{rel}" + (f": ${amt:,.2f}" if amt else ""),
                label=edge_label,
                arrows="to",
                width=2
            )

        # Generate HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            temp_path = f.name
            net.write_html(temp_path)

        with open(temp_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        try:
            os.remove(temp_path)
        except Exception:
            pass

        return html_content

    except Exception as e:
        # Fallback to pure Plotly graph if PyVis encounters an issue
        return _render_plotly_graph_html(discovered_nodes, discovered_edges)

def _render_plotly_graph_html(
    discovered_nodes: List[Dict[str, Any]],
    discovered_edges: List[Dict[str, Any]]
) -> str:
    """Plotly-based 2D network graph fallback."""
    import networkx as nx
    
    G = nx.Graph()
    for n in discovered_nodes:
        G.add_node(n["id"], type=n.get("type", "Entity"))
    for e in discovered_edges:
        G.add_edge(e["source"], e["target"])

    pos = nx.spring_layout(G, seed=42)

    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color='#64748B'),
        hoverinfo='none',
        mode='lines'
    )

    node_x, node_y, node_color, node_text = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        ntype = G.nodes[node].get("type", "Entity")
        node_color.append(COLOR_PALETTE.get(ntype, "#94A3B8"))
        node_text.append(f"{node} ({ntype})")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[n for n in G.nodes()],
        textposition="top center",
        marker=dict(
            size=22,
            color=node_color,
            line_width=2,
            line_color='#FFFFFF'
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    paper_bgcolor='#0E1726',
                    plot_bgcolor='#0E1726',
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=10, l=10, r=10, t=10),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                 ))
    return fig.to_html(include_plotlyjs='cdn', full_html=False)

def render_risk_gauge(score: int, severity: str) -> go.Figure:
    """Create a clean dark-mode Plotly gauge indicator."""
    if score >= 75:
        bar_color = "#EF4444" # Critical Red
    elif score >= 50:
        bar_color = "#F97316" # Orange
    elif score >= 25:
        bar_color = "#FBBF24" # Yellow
    else:
        bar_color = "#10B981" # Green

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'size': 32, 'color': '#F8FAFC'}},
        title={'text': f"Risk: {severity}", 'font': {'size': 18, 'color': bar_color}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#475569"},
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': "#1E293B",
            'borderwidth': 1,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, 25], 'color': "rgba(16, 185, 129, 0.15)"},
                {'range': [25, 50], 'color': "rgba(251, 191, 36, 0.15)"},
                {'range': [50, 75], 'color': "rgba(249, 115, 22, 0.15)"},
                {'range': [75, 100], 'color': "rgba(239, 68, 68, 0.15)"}
            ],
            'threshold': {
                'line': {'color': "#EF4444", 'width': 3},
                'thickness': 0.8,
                'value': 75
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'color': "#F8FAFC", 'family': "Inter, sans-serif"},
        height=220,
        margin=dict(l=25, r=25, t=30, b=10)
    )
    return fig
