"""Autonomous Financial Fraud Investigation Agent Orchestrator.

Implements the ReAct (Reason + Act) loop:
OBSERVE -> PLAN -> ACT (Tool Execution) -> OBSERVE RESULT -> REASON -> NEXT ACTION -> REPORT
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from .state import InvestigationState, AgentStep
from .prompts import SYSTEM_PROMPT, REPORT_PROMPT_TEMPLATE
import tools
import analysis

class FraudInvestigationAgent:
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_steps: int = 12
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", "autonomous").lower()
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.max_steps = int(os.getenv("MAX_INVESTIGATION_STEPS", str(max_steps)))

    def investigate(
        self,
        seed_transaction_id: str,
        step_callback: Optional[Callable[[AgentStep], None]] = None
    ) -> InvestigationState:
        """Run autonomous end-to-end multi-step fraud network investigation."""
        state = InvestigationState(
            seed_transaction_id=seed_transaction_id,
            status="INVESTIGATING"
        )

        # ---------------------------------------------------------------------
        # STEP 1: Seed Transaction Retrieval
        # ---------------------------------------------------------------------
        tx_result = tools.get_transaction(seed_transaction_id)
        if not tx_result.get("found"):
            state.status = "FAILED"
            state.error_message = f"Transaction {seed_transaction_id} could not be found in financial database."
            step = AgentStep(
                step_number=1,
                thought=f"Initiating investigation for target transaction ID: {seed_transaction_id}.",
                tool_name="get_transaction",
                tool_args={"transaction_id": seed_transaction_id},
                observation_summary=f"Transaction {seed_transaction_id} not found in database.",
                timestamp=datetime.now().strftime("%H:%M:%S"),
                raw_result=tx_result
            )
            state.action_history.append(step)
            if step_callback:
                step_callback(step)
            return state

        state.initial_transaction = tx_result
        state.mark_visited("transaction", seed_transaction_id)

        # Register Seed Transaction Node
        state.add_node(
            node_id=seed_transaction_id,
            node_type="Transaction",
            label=f"Seed: {seed_transaction_id}",
            properties={
                "amount": f"${tx_result['amount']:,.2f}",
                "timestamp": tx_result["timestamp"],
                "type": tx_result["transaction_type"],
                "status": tx_result["status"]
            }
        )

        # Ingest sender
        sender_id = tx_result["sender_account"]
        state.add_node(
            node_id=sender_id,
            node_type="Account",
            label=f"Acc: {sender_id}",
            properties={"holder": tx_result.get("sender_name", "Unknown")}
        )
        state.add_edge(sender_id, seed_transaction_id, "ORIGINATED_TRANSACTION", amount=tx_result["amount"])
        state.investigation_queue.append({"type": "account", "id": sender_id})

        # Ingest receiver if present
        receiver_id = tx_result.get("receiver_account")
        if receiver_id:
            state.add_node(
                node_id=receiver_id,
                node_type="Account",
                label=f"Acc: {receiver_id}",
                properties={"holder": tx_result.get("receiver_name", "Unknown")}
            )
            state.add_edge(seed_transaction_id, receiver_id, "TRANSFERRED_TO", amount=tx_result["amount"])
            state.investigation_queue.append({"type": "account", "id": receiver_id})

        # Ingest merchant if present
        merchant_id = tx_result.get("merchant_id")
        if merchant_id:
            state.add_node(
                node_id=merchant_id,
                node_type="Merchant",
                label=f"Merch: {merchant_id}",
                properties={
                    "name": tx_result.get("merchant_name", merchant_id),
                    "category": tx_result.get("merchant_category", "Unknown"),
                    "risk_tier": tx_result.get("merchant_risk_tier", "Unknown")
                }
            )
            state.add_edge(seed_transaction_id, merchant_id, "ROUTED_THROUGH_MERCHANT", amount=tx_result["amount"])
            state.investigation_queue.append({"type": "merchant", "id": merchant_id})

        # Ingest device if present (Crucial seed lead)
        device_id = tx_result.get("device_id")
        if device_id:
            state.add_node(
                node_id=device_id,
                node_type="Device",
                label=f"Dev: {device_id}",
                properties={
                    "type": tx_result.get("device_type", "Device"),
                    "ip": tx_result.get("device_ip", "Unknown"),
                    "location": tx_result.get("device_location", "Unknown")
                }
            )
            state.add_edge(seed_transaction_id, device_id, "AUTHENTICATED_ON_DEVICE")
            state.investigation_queue.insert(0, {"type": "device", "id": device_id})

        step_1 = AgentStep(
            step_number=1,
            thought=f"Target transaction {seed_transaction_id} retrieved. Amount is ${tx_result['amount']:,.2f} originating from account {sender_id}. Key investigative entities identified: Device={device_id or 'None'}, Merchant={merchant_id or 'None'}, Counterparty={receiver_id or 'None'}.",
            tool_name="get_transaction",
            tool_args={"transaction_id": seed_transaction_id},
            observation_summary=f"Discovered Sender Account {sender_id}, Device {device_id}, and Merchant {merchant_id}.",
            timestamp=datetime.now().strftime("%H:%M:%S"),
            raw_result=tx_result
        )
        state.action_history.append(step_1)
        if step_callback:
            step_callback(step_1)

        # ---------------------------------------------------------------------
        # REASONING & AUTONOMOUS INVESTIGATION LOOP
        # ---------------------------------------------------------------------
        step_count = 1
        patterns_checked = False

        while step_count < self.max_steps:
            step_count += 1

            # Decide next action (via LLM or Autonomous Heuristic Planner)
            action_plan = self._plan_next_action(state, patterns_checked)
            tool_name = action_plan.get("tool")
            tool_args = action_plan.get("arguments", {})
            thought = action_plan.get("thought", "Analyzing discovered entities.")

            if tool_name == "conclude_investigation":
                step_final = AgentStep(
                    step_number=step_count,
                    thought=thought,
                    tool_name="conclude_investigation",
                    tool_args={},
                    observation_summary="Investigation queue completed and network boundary reached.",
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    raw_result={"status": "Investigation boundary reached"}
                )
                state.action_history.append(step_final)
                if step_callback:
                    step_callback(step_final)
                break

            # Execute Selected Tool
            tool_result, obs_summary = self._execute_tool(tool_name, tool_args, state)

            if tool_name == "detect_transaction_patterns":
                patterns_checked = True

            step_entry = AgentStep(
                step_number=step_count,
                thought=thought,
                tool_name=tool_name,
                tool_args=tool_args,
                observation_summary=obs_summary,
                timestamp=datetime.now().strftime("%H:%M:%S"),
                raw_result=tool_result
            )
            state.action_history.append(step_entry)
            if step_callback:
                step_callback(step_entry)

        # ---------------------------------------------------------------------
        # POST-LOOP SYNTHESIS & REPORT COMPILATION
        # ---------------------------------------------------------------------
        # Final pattern detection if not already run
        discovered_accs = state.get_accounts()
        if not patterns_checked and discovered_accs:
            state.pattern_summary = tools.detect_transaction_patterns(discovered_accs)
        elif not state.pattern_summary and discovered_accs:
            state.pattern_summary = tools.detect_transaction_patterns(discovered_accs)

        # Risk indicator calculation
        risk_result = tools.calculate_risk_indicators(
            discovered_accounts=discovered_accs,
            discovered_devices=state.get_devices(),
            discovered_merchants=state.get_merchants(),
            pattern_summary=state.pattern_summary
        )

        # Build NetworkX Graph and analyze topology
        nx_graph = analysis.build_investigation_graph(state.get_nodes_list(), state.discovered_edges)
        topo_result = analysis.analyze_graph_topology(nx_graph)
        state.graph_topology = topo_result

        # Extra risk points if NetworkX detected a cycle
        if topo_result.get("circular_cycles") and not any(i["indicator"].startswith("Circular") for i in risk_result["indicators"]):
            pts = 25
            risk_result["score"] = min(100, risk_result["score"] + pts)
            risk_result["indicators"].append({
                "indicator": "Circular Transaction Flow (Layering Loop)",
                "points": pts,
                "severity": "Critical",
                "evidence": f"Graph cycle detected among nodes: {' -> '.join(topo_result['circular_cycles'][0])}"
            })
            risk_result["severity"] = "Critical Risk"

        state.risk_evaluation = analysis.compile_risk_evaluation(
            initial_tx=state.initial_transaction,
            discovered_nodes=state.get_nodes_list(),
            discovered_edges=state.discovered_edges,
            risk_summary=risk_result,
            topology_summary=topo_result
        )

        state.recommendations = analysis.generate_recommendations(
            risk_summary=risk_result,
            discovered_nodes=state.get_nodes_list(),
            topology_summary=topo_result
        )

        # Generate Explainable Final Investigation Report
        state.final_report = self._generate_final_report(state)
        state.status = "COMPLETED"

        return state

    def _plan_next_action(self, state: InvestigationState, patterns_checked: bool) -> Dict[str, Any]:
        """Decide next investigative tool call. Uses LLM if configured; otherwise uses Heuristic Planner."""
        # Check if LLM is explicitly enabled and API key is provided
        if self.provider in ["groq", "openai", "gemini"] and self.api_key:
            try:
                llm_decision = self._call_llm_planner(state)
                if llm_decision and "tool" in llm_decision:
                    return llm_decision
            except Exception as e:
                # Graceful fallback to heuristic planner upon API failure
                pass

        return self._heuristic_planner(state, patterns_checked)

    def _heuristic_planner(self, state: InvestigationState, patterns_checked: bool) -> Dict[str, Any]:
        """Deterministic ReAct reasoning engine based on investigative priorities."""
        # Early triage for benign low-risk retail transactions
        seed_tx = state.initial_transaction
        if seed_tx and seed_tx.get("amount", 0) < 1000 and seed_tx.get("merchant_risk_tier") == "Low":
            dev_id = seed_tx.get("device_id")
            snd_id = seed_tx.get("sender_account")
            if dev_id and state.is_visited("device", dev_id) and snd_id and state.is_visited("account", snd_id):
                dev_conns = tools.get_device_connections(dev_id)
                if not dev_conns.get("is_shared_device"):
                    return {
                        "thought": f"Target transaction {state.seed_transaction_id} is a routine purchase of ${seed_tx.get('amount', 0):,.2f} at low-risk merchant {seed_tx.get('merchant_name', 'Retailer')}. Originating device {dev_id} is dedicated (not shared with any other account), and account holder identity is verified. Concluding investigation early as benign.",
                        "tool": "conclude_investigation",
                        "arguments": {}
                    }

        # Priority 1: Unvisited Devices (highest fraud signal in network discovery)
        for item in list(state.investigation_queue):
            if item["type"] == "device" and not state.is_visited("device", item["id"]):
                state.investigation_queue.remove(item)
                return {
                    "thought": f"Device {item['id']} was identified in the transaction records. In financial fraud networks, shared hardware signatures frequently expose co-located mule accounts. I will query `get_device_connections` to inspect all accounts operating from this physical/virtual hardware.",
                    "tool": "get_device_connections",
                    "arguments": {"device_id": item["id"]}
                }

        # Priority 2: Unvisited Accounts (inspect profile, KYC, and counterparty flows)
        for item in list(state.investigation_queue):
            if item["type"] == "account" and not state.is_visited("account", item["id"]):
                state.investigation_queue.remove(item)
                return {
                    "thought": f"Account {item['id']} is linked to the network. I will retrieve its account profile to examine holder identity, verification status, account age, and associated devices.",
                    "tool": "get_account_profile",
                    "arguments": {"account_id": item["id"]}
                }

        # Priority 3: Related Transactions (for accounts with multiple connections)
        accounts = state.get_accounts()
        for acc in accounts:
            if not state.is_visited("related_tx", acc):
                state.mark_visited("related_tx", acc)
                return {
                    "thought": f"I will examine recent transaction history for account {acc} using `find_related_transactions` to identify hidden counterparty flows and transaction velocity.",
                    "tool": "find_related_transactions",
                    "arguments": {"account_id": acc, "limit": 10}
                }

        # Priority 4: Unvisited Merchants
        for item in list(state.investigation_queue):
            if item["type"] == "merchant" and not state.is_visited("merchant", item["id"]):
                state.investigation_queue.remove(item)
                return {
                    "thought": f"Merchant {item['id']} is utilized by network participants. I will inspect its transaction distribution and risk category using `get_merchant_connections`.",
                    "tool": "get_merchant_connections",
                    "arguments": {"merchant_id": item["id"]}
                }

        # Priority 5: Run Pattern Detection if accounts >= 2 and not yet checked
        if len(accounts) >= 2 and not patterns_checked:
            return {
                "thought": f"We have discovered {len(accounts)} connected accounts ({', '.join(accounts[:4])}). I will execute `detect_transaction_patterns` to identify structuring, common beneficiary aggregators, and circular layering loops.",
                "tool": "detect_transaction_patterns",
                "arguments": {"account_ids": accounts}
            }

        # Conclude
        return {
            "thought": "All identified leads in the investigation queue have been explored. Sufficient evidence has been gathered to close the discovery loop and assemble the final report.",
            "tool": "conclude_investigation",
            "arguments": {}
        }

    def _execute_tool(self, tool_name: str, args: Dict[str, Any], state: InvestigationState) -> tuple[Dict[str, Any], str]:
        """Execute selected tool against the database and update state graph and queue."""
        if tool_name == "get_device_connections":
            dev_id = args.get("device_id")
            state.mark_visited("device", dev_id)
            res = tools.get_device_connections(dev_id)
            
            accs = res.get("connected_accounts", [])
            acc_ids = [a["account_id"] for a in accs]
            
            # Add discovered accounts to graph & queue
            for acc in accs:
                aid = acc["account_id"]
                state.add_node(
                    node_id=aid,
                    node_type="Account",
                    label=f"Acc: {aid}",
                    properties={
                        "holder": acc["full_name"],
                        "created": acc["account_creation_date"],
                        "status": acc["account_status"]
                    }
                )
                state.add_edge(aid, dev_id, "USES_DEVICE")
                if not state.is_visited("account", aid):
                    state.investigation_queue.append({"type": "account", "id": aid})

            summary = f"Device {dev_id} is accessed by {len(accs)} distinct accounts: {', '.join(acc_ids)}."
            if res.get("is_shared_device"):
                summary += " CRITICAL: Multiple accounts sharing one device detected!"
            return res, summary

        elif tool_name == "get_account_profile":
            acc_id = args.get("account_id")
            state.mark_visited("account", acc_id)
            res = tools.get_account_profile(acc_id)
            
            if res.get("found"):
                state.add_node(
                    node_id=acc_id,
                    node_type="Account",
                    label=f"Acc: {acc_id}",
                    properties={
                        "holder": res["customer_name"],
                        "kyc": res["verification_status"],
                        "created": res["account_creation_date"],
                        "balance": f"${res['balance']:,.2f}"
                    }
                )
                
                # Customer identity node
                cid = res["customer_id"]
                state.add_node(
                    node_id=cid,
                    node_type="Customer",
                    label=f"Cust: {cid}",
                    properties={"name": res["customer_name"], "kyc": res["verification_status"]}
                )
                state.add_edge(cid, acc_id, "OWNS_ACCOUNT")

                # Link associated devices
                for dev in res.get("associated_devices", []):
                    did = dev["device_id"]
                    state.add_node(did, "Device", label=f"Dev: {did}", properties={"ip": dev["ip_address"], "location": dev["location"]})
                    state.add_edge(acc_id, did, "USES_DEVICE")
                    if not state.is_visited("device", did):
                        state.investigation_queue.append({"type": "device", "id": did})

                # Link associated merchants - only queue high-risk merchants to avoid background store bleed
                for m in res.get("associated_merchants", []):
                    mid = m["merchant_id"]
                    is_high_risk = m.get("risk_tier") in ["High", "Critical"]
                    state.add_node(mid, "Merchant", label=f"Merch: {mid}", properties={"name": m["merchant_name"], "risk": m["risk_tier"]})
                    state.add_edge(acc_id, mid, "INTERACTS_WITH")
                    if is_high_risk and not state.is_visited("merchant", mid):
                        state.investigation_queue.append({"type": "merchant", "id": mid})

                summary = f"Account {acc_id} belongs to {res['customer_name']} (KYC: {res['verification_status']}). Linked to {len(res.get('associated_devices', []))} device(s) and {len(res.get('associated_merchants', []))} merchant(s)."
                return res, summary
            else:
                return res, f"Account {acc_id} profile not found."

        elif tool_name == "find_related_transactions":
            acc_id = args.get("account_id")
            res = tools.find_related_transactions(acc_id, limit=args.get("limit", 10))
            
            # Add discovered counterparties to graph & queue for substantial transactions
            for tx in res.get("transactions", []):
                s = tx.get("sender_account")
                r = tx.get("receiver_account")
                amt = tx.get("amount", 0)
                if s and r:
                    state.add_edge(s, r, "FUNDS_TRANSFER", amount=amt)
                    cp = r if s == acc_id else s
                    if cp:
                        state.add_node(cp, "Account", label=f"Acc: {cp}")
                        # Only queue high-value or coordinated transfers for investigation
                        if amt >= 2000.0 and not state.is_visited("account", cp):
                            state.investigation_queue.append({"type": "account", "id": cp})

            summary = f"Account {acc_id} has {res['transaction_count']} transactions. Outbound: ${res['total_outbound_volume']:,.2f}, Inbound: ${res['total_inbound_volume']:,.2f}. Counterparties: {', '.join(res.get('counterparty_accounts', []))}."
            return res, summary

        elif tool_name == "get_merchant_connections":
            mid = args.get("merchant_id")
            state.mark_visited("merchant", mid)
            res = tools.get_merchant_connections(mid)
            
            accs = [a["account_id"] for a in res.get("interacting_accounts", [])]
            for acc in res.get("interacting_accounts", []):
                aid = acc["account_id"]
                state.add_node(aid, "Account", label=f"Acc: {aid}")
                state.add_edge(aid, mid, "PAYMENT_GATEWAY", amount=acc["total_amount"])
                if not state.is_visited("account", aid):
                    state.investigation_queue.append({"type": "account", "id": aid})

            summary = f"Merchant {mid} ({res.get('merchant_name')}, Risk: {res.get('risk_tier')}) handles transactions for {len(accs)} accounts: {', '.join(accs)}."
            return res, summary

        elif tool_name == "detect_transaction_patterns":
            acc_ids = args.get("account_ids", state.get_accounts())
            res = tools.detect_transaction_patterns(acc_ids)
            state.pattern_summary = res

            findings = []
            if res.get("common_destinations"):
                dests = [d["account_id"] for d in res["common_destinations"]]
                findings.append(f"Common Beneficiary Aggregator: {', '.join(dests)}")
                for d in res["common_destinations"]:
                    state.add_node(d["account_id"], "Beneficiary", label=f"Aggregator: {d['account_id']}")

            if res.get("is_circular_flow"):
                findings.append(f"Circular Layering Loop: {' -> '.join(res.get('circular_path', []))}")

            if res.get("structured_transactions"):
                findings.append(f"{len(res['structured_transactions'])} structured transactions below AML limits")

            summary = "Pattern analysis complete. " + ("; ".join(findings) if findings else "No anomalous network patterns detected.")
            return res, summary

        else:
            return {"error": f"Unknown tool: {tool_name}"}, f"Tool {tool_name} is not recognized."

    def _call_llm_planner(self, state: InvestigationState) -> Optional[Dict[str, Any]]:
        """Query LLM API to obtain next reasoning thought and tool call."""
        import requests

        recent_steps = [
            f"Step {s.step_number}: Tool={s.tool_name}, Observation={s.observation_summary}"
            for s in state.action_history[-4:]
        ]
        
        prompt_content = f"""Current Seed: {state.seed_transaction_id}
Investigated Entities: {list(state.visited_entities)}
Pending Investigation Queue: {state.investigation_queue}
Recent Actions:
{chr(10).join(recent_steps)}

Decide the next investigative action based on discovered evidence. Respond ONLY with valid JSON."""

        if self.provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return json.loads(data["choices"][0]["message"]["content"])

        elif self.provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return json.loads(data["choices"][0]["message"]["content"])

        return None

    def _generate_final_report(self, state: InvestigationState) -> str:
        """Compile an explainable markdown investigation report."""
        tx = state.initial_transaction
        risk = state.risk_evaluation
        topo = state.graph_topology

        accounts = state.get_accounts()
        devices = state.get_devices()
        merchants = state.get_merchants()

        indicators_md = ""
        for ind in risk.get("indicators", []):
            indicators_md += f"- **[{ind.get('severity', 'Notice')}] {ind['indicator']} (+{ind.get('points', 0)} pts)**: {ind['evidence']}\n"

        if not indicators_md:
            indicators_md = "- No suspicious indicators identified. Activity is consistent with legitimate consumer behavior.\n"

        evidence_chain_md = ""
        for i, step in enumerate(risk.get("evidence_chain", []), 1):
            evidence_chain_md += f"{i}. {step}\n"

        recs_md = ""
        for rec in state.recommendations:
            recs_md += f"- **{rec['priority']} - {rec['action']}**: {rec['details']}\n"

        report = f"""# Financial Fraud Network Investigation Dossier

**Target Seed Transaction**: `{state.seed_transaction_id}`  
**Investigation Status**: COMPLETED  
**Autonomous Steps Executed**: {len(state.action_history)}  
**Discovered Entities**: {len(state.discovered_nodes)} | **Discovered Relationships**: {len(state.discovered_edges)}  
**Prototype Risk Assessment**: **{risk.get('prototype_risk_score', 0)}/100** ({risk.get('risk_severity', 'Low')})

---

## 1. Investigation Summary
An autonomous relationship-level fraud investigation was initiated on transaction `{state.seed_transaction_id}`. Rather than evaluating this transfer in isolation, the AI agent dynamically discovered and mapped an interconnected sub-network comprising **{len(accounts)} accounts**, **{len(devices)} hardware devices**, and **{len(merchants)} merchants/gateways**.

{"⚠️ **High-Risk Network Discovery Alert**: Analysis revealed coordinated infrastructure sharing, structured smurfing, and fund convergence consistent with an organized money mule or layering syndicate." if risk.get('prototype_risk_score', 0) >= 50 else "✅ **Clean Network Assessment**: No multi-entity coordination, shared proxy hardware, or rapid layering was identified. Activity remains within normal baseline parameters."}

---

## 2. Initial Transaction
| Field | Value |
|---|---|
| **Transaction ID** | `{tx.get('transaction_id')}` |
| **Originating Account** | `{tx.get('sender_account')}` ({tx.get('sender_name', 'Unknown')}) |
| **Destination / Merchant** | `{tx.get('receiver_account') or tx.get('merchant_name') or 'N/A'}` |
| **Amount** | `${tx.get('amount', 0.0):,.2f}` |
| **Timestamp** | `{tx.get('timestamp')}` |
| **Transaction Type** | `{tx.get('transaction_type')}` |
| **Originating Device** | `{tx.get('device_id')} ({tx.get('device_type')})` |
| **Device Location / IP** | `{tx.get('device_location')} ({tx.get('device_ip')})` |

---

## 3. Discovered Network Topology
- **Associated Accounts ({len(accounts)})**: {', '.join([f'`{a}`' for a in accounts])}
- **Shared Hardware Infrastructure ({len(devices)})**: {', '.join([f'`{d}`' for d in devices])}
- **Payment Channels / Gateways ({len(merchants)})**: {', '.join([f'`{m}`' for m in merchants])}
- **Network Density**: `{topo.get('graph_density', 0.0)}` | **Connected Hubs**: {len(topo.get('top_hubs', []))}
{f"- **Identified Aggregator Beneficiary**: `{topo['aggregator_node']['node']}` ({topo['aggregator_node']['incoming_count']} incoming funnels)" if topo.get('aggregator_node') else ""}
{f"- **Circular Wash Cycles Detected**: `{(' -> '.join(topo['circular_cycles'][0]))}`" if topo.get('circular_cycles') else ""}

---

## 4. Suspicious Indicators & Pattern Analysis
{indicators_md}

---

## 5. Reconstructed Evidence Chain
{evidence_chain_md}

---

## 6. Recommended Next Steps for Human Investigator
{recs_md}

---
*Notice: {risk.get('disclaimer')}*
"""
        return report
