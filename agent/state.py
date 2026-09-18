"""Investigation state model and data structures."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set, Optional

@dataclass
class AgentStep:
    step_number: int
    thought: str
    tool_name: str
    tool_args: Dict[str, Any]
    observation_summary: str
    timestamp: str
    raw_result: Optional[Dict[str, Any]] = None

@dataclass
class InvestigationState:
    seed_transaction_id: str
    status: str = "INITIALIZING" # INITIALIZING, INVESTIGATING, COMPLETED, FAILED
    error_message: Optional[str] = None
    
    # Discovery Queue & Visited Tracking
    investigation_queue: List[Dict[str, str]] = field(default_factory=list) # [{"type": "device", "id": "D77"}, ...]
    visited_entities: Set[str] = field(default_factory=set) # {"account:A102", "device:D77"}
    
    # Graph Representation
    discovered_nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict) # id -> node_dict
    discovered_edges: List[Dict[str, Any]] = field(default_factory=list)
    
    # Agent Action History
    action_history: List[AgentStep] = field(default_factory=list)
    
    # Initial Transaction Snapshot
    initial_transaction: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis & Scoring Results
    pattern_summary: Dict[str, Any] = field(default_factory=dict)
    risk_evaluation: Dict[str, Any] = field(default_factory=dict)
    graph_topology: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[Dict[str, str]] = field(default_factory=list)
    final_report: str = ""

    def is_visited(self, entity_type: str, entity_id: str) -> bool:
        return f"{entity_type.lower()}:{entity_id.upper()}" in self.visited_entities

    def mark_visited(self, entity_type: str, entity_id: str):
        self.visited_entities.add(f"{entity_type.lower()}:{entity_id.upper()}")

    def add_node(self, node_id: str, node_type: str, label: Optional[str] = None, properties: Optional[Dict[str, Any]] = None):
        nid = str(node_id).strip()
        if nid not in self.discovered_nodes:
            self.discovered_nodes[nid] = {
                "id": nid,
                "type": node_type,
                "label": label or nid,
                "properties": properties or {}
            }
        else:
            if properties:
                self.discovered_nodes[nid]["properties"].update(properties)

    def add_edge(self, source: str, target: str, relationship: str, amount: Optional[float] = None, label: Optional[str] = None):
        src = str(source).strip()
        tgt = str(target).strip()
        # Avoid duplicate identical edges
        for edge in self.discovered_edges:
            if edge["source"] == src and edge["target"] == tgt and edge["relationship"] == relationship:
                return
        self.discovered_edges.append({
            "source": src,
            "target": tgt,
            "relationship": relationship,
            "amount": amount,
            "label": label or relationship
        })

    def get_nodes_list(self) -> List[Dict[str, Any]]:
        return list(self.discovered_nodes.values())

    def get_accounts(self) -> List[str]:
        return [n["id"] for n in self.discovered_nodes.values() if n["type"] == "Account"]

    def get_devices(self) -> List[str]:
        return [n["id"] for n in self.discovered_nodes.values() if n["type"] == "Device"]

    def get_merchants(self) -> List[str]:
        return [n["id"] for n in self.discovered_nodes.values() if n["type"] == "Merchant"]
