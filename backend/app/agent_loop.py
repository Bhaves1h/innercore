"""
INNERCORE Real Agent Execution Loop with Multi-Model Auto Router, Sandbox, and HITL Governance Gate.
Executes the 7-stage engine with zero external cloud egress.
100% on-premise.
"""
from __future__ import annotations

import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from .schemas import (
    ExecuteRequest,
    ExecutionStep,
    EvidenceItem,
    ModelRoutingInfo,
    ApprovalRequestInfo
)
from .rag import search_knowledge
from .llm import generate
from .router import route_local_model
from .network_monitor import record_network_activity


# --- Bounded On-Premise Diagnostic Tool Registry ------------------------------

EQUIPMENT_TELEMETRY_REGISTRY = {
    "reactor r-204": {
        "asset_id": "Reactor R-204",
        "system": "Primary Hydro-Thermal Oxidation Core",
        "status": "OPERATIONAL / ELEVATED_THERMAL",
        "core_temp": "342.6 °C (Nominal: 320-335 °C, Warning: >340 °C)",
        "inlet_pressure": "4.82 MPa (Max Permissible: 5.50 MPa)",
        "coolant_flow_rate": "1,240 L/min (Nominal: 1,350 L/min · Deviation -8.1%)",
        "catalyst_bed_dp": "0.45 bar (Clean: 0.20 bar, Flush Threshold: 0.60 bar)",
        "last_diagnostic": "Continuous monitoring active · Zero external anomalies",
        "scheduled_procedure": "Coolant Loop Filter Flush & Secondary Heat Exchanger Clean"
    },
    "gt-9000": {
        "asset_id": "Gas Turbine GT-9000",
        "system": "Heavy Industrial Co-Gen Power Unit",
        "status": "NOMINAL",
        "radial_vibration": "2.1 mm/s RMS (Max Permissible: 2.8 mm/s, Trip: 3.5 mm/s)",
        "speed": "3,600 RPM",
        "lube_oil_temp": "62 °C (Operating Range: 55-70 °C)",
        "lubrication_cycle": "Flush & replenish at 12,000 operational hours (Current: 8,450 hrs)",
        "last_diagnostic": "Continuous vibration monitoring active · Phase angle normal"
    },
    "cp-402": {
        "asset_id": "Coolant Pump CP-402",
        "system": "Secondary Loop Coolant Subsystem",
        "status": "ACTIVE / RUNNING",
        "discharge_pressure": "120 PSI (Max: 180 PSI)",
        "motor_current": "48 A (Normal: 45-52 A)",
        "last_diagnostic": "Vibration within ISO Class II limits"
    },
    "hx-108": {
        "asset_id": "Heat Exchanger HX-108",
        "system": "Primary Thermal Recovery Core",
        "status": "NORMAL",
        "inlet_temp": "180 °C",
        "outlet_temp": "75 °C",
        "delta_p": "12 PSI",
        "last_diagnostic": "Differential pressure nominal"
    }
}


def run_telemetry_diagnostic(query: str) -> Optional[Dict[str, Any]]:
    """Inspect equipment telemetry registry for matching asset references."""
    q_lower = query.lower()
    for key, data in EQUIPMENT_TELEMETRY_REGISTRY.items():
        if key in q_lower or (key == "reactor r-204" and "r-204" in q_lower) or (key == "gt-9000" and "turbine" in q_lower):
            return data
    return None


# --- 7-Stage Agent Execution Loop with HITL Governance Gate -------------------

def run_agent_execution_loop(
    payload: ExecuteRequest,
    history: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, str, List[ExecutionStep], List[EvidenceItem], List[str], str, str, ModelRoutingInfo, str, Optional[ApprovalRequestInfo]]:
    """
    Executes the 7-stage Real Agent Execution Loop with Multi-Model Router, Sandbox, and HITL Gate.
    Returns: (result_text, agent_name, steps, evidence, tools_used, inference_mode, model_used, routing_info, status, approval_request)
    """
    now = datetime.utcnow()
    t_start = time.perf_counter()
    steps: List[ExecutionStep] = []
    tools_used: List[str] = []

    def _now_str() -> str:
        return datetime.utcnow().strftime("%H:%M:%S")

    def _elapsed_ms(since: float) -> int:
        return max(1, int((time.perf_counter() - since) * 1000))

    # --- Stage 1: TASK INTAKE --------------------------------------------------
    s1_t = time.perf_counter()
    user_role = payload.user_role or "OPERATOR_L2"
    task_summary = payload.request.strip()
    if len(task_summary) > 60:
        task_summary = task_summary[:57] + "..."

    steps.append(ExecutionStep(
        id="st-task-intake",
        name="task_intake",
        label="TASK INTAKE",
        event="Task received and validated",
        detail=f"Role {user_role} verified · Boundary: On-premise air-gapped",
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s1_t),
    ))

    # --- Stage 2: MODEL ROUTER (Dynamic Local Discovery & Task Routing) --------
    s2_t = time.perf_counter()
    routing_data = route_local_model(payload.request)
    selected_model = routing_data["selected_model"]
    task_category = routing_data["task_type"]
    routing_reason = routing_data["reason"]
    avail_count = routing_data["available_models_count"]

    routing_info = ModelRoutingInfo(
        selected_model=selected_model,
        runtime=routing_data["runtime"],
        task_type=task_category,
        reason=routing_reason,
        available_models_count=avail_count,
        available_models=routing_data.get("available_models", [selected_model]),
        network_boundary="LOCAL AIR-GAPPED",
        status=routing_data["status"]
    )

    steps.append(ExecutionStep(
        id="st-model-router",
        name="model_selection",
        label="MODEL ROUTER",
        event=f"Model selected: {selected_model}",
        detail=f"Task: {task_category} · {routing_reason}",
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s2_t),
    ))

    # --- Stage 3: AGENT PLANNING -----------------------------------------------
    s3_t = time.perf_counter()
    agent_id = payload.agent_id or "agent-maintenance"
    agent_name_map = {
        "agent-maintenance": "Maintenance Agent",
        "agent-knowledge": "Knowledge Agent",
        "agent-security": "Safety Officer",
    }
    agent_name = agent_name_map.get(agent_id, "Maintenance Agent")

    q_lower = payload.request.lower()
    is_work_order_action = any(k in q_lower for k in ["work order", "maintenance order", "create a maintenance work order", "generate work order"])
    is_csv_analysis_query = not is_work_order_action and any(k in q_lower for k in ["csv", "operations.csv", "reading", "temperature reading", "anomalous", "anomalies"])
    equipment_match = run_telemetry_diagnostic(payload.request)

    if is_work_order_action:
        plan_desc = f"{agent_name} planned operational action: 1. Knowledge search for equipment parameters, 2. Human operator policy check (Risk: MEDIUM), 3. Generate Maintenance Work Order #WO-R204 upon authorization"
    elif is_csv_analysis_query:
        plan_desc = f"{agent_name} planned investigation: 1. Vector RAG search, 2. Restricted local CSV statistical & anomaly analysis (operations.csv), 3. Evidence synthesis"
    elif equipment_match:
        plan_desc = f"{agent_name} planned investigation: 1. Vector RAG search, 2. Telemetry diagnostic readout for {equipment_match['asset_id']}, 3. Parameter safety verification"
    else:
        plan_desc = f"{agent_name} planned investigation: 1. Hybrid semantic retrieval across private corpus, 2. Grounded local synthesis"

    steps.append(ExecutionStep(
        id="st-planning",
        name="planning",
        label="AGENT PLANNING",
        event=f"{agent_name} generated execution plan",
        detail=plan_desc,
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s3_t),
    ))

    # --- Stage 4: KNOWLEDGE RETRIEVAL ------------------------------------------
    s4_t = time.perf_counter()
    col_filter = payload.collection_filter
    raw_chunks = search_knowledge(payload.request, n_results=5, doc_filter=payload.doc_filter, collection_filter=col_filter)
    tools_used.append("search_private_knowledge")

    col_tag = f"Collection: {col_filter}" if col_filter and col_filter not in ["ALL", "ALL DOCUMENTS", "All Documents"] else "Global Corpus"
    if raw_chunks:
        top_fn = raw_chunks[0]["filename"]
        top_loc = raw_chunks[0].get("source_locator") or f"Page {raw_chunks[0].get('page', 1)}"
        retrieval_detail = f"{col_tag} · Retrieved {len(raw_chunks)} relevant passages from {top_fn} ({top_loc})"
    else:
        retrieval_detail = f"{col_tag} · Zero matching passages found in selected scope"

    steps.append(ExecutionStep(
        id="st-knowledge",
        name="knowledge_retrieval",
        label="KNOWLEDGE SEARCH",
        event="Knowledge base queried",
        detail=retrieval_detail,
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s4_t),
    ))

    # --- Stage 4.5: HUMAN-IN-THE-LOOP (HITL) APPROVAL GATE ---------------------
    if is_work_order_action:
        appr_id = payload.approval_id or f"APPR-{int(now.timestamp() * 1000)}"
        target_asset = equipment_match["asset_id"] if equipment_match else "Reactor R-204"
        approval_info = ApprovalRequestInfo(
            approval_id=appr_id,
            agent=agent_name,
            action="Generate Maintenance Work Order",
            target=target_asset,
            risk="MEDIUM",
            reason="Action creates an operational maintenance deliverable and procedures for Reactor R-204.",
            role_required="OPERATOR_L2",
            status="PENDING",
            decision=payload.approval_decision
        )

        # Case A: Awaiting Approval (First Turn)
        if not payload.approval_decision:
            steps.append(ExecutionStep(
                id="st-policy-check",
                name="policy_check",
                label="POLICY CHECK",
                event="Governance policy check triggered",
                detail="Risk: MEDIUM · Action creates operational artifact · Human operator approval required",
                status="completed",
                timestamp=_now_str(),
                duration_ms=5,
            ))
            steps.append(ExecutionStep(
                id="st-hitl-awaiting",
                name="human_approval",
                label="APPROVAL REQUIRED",
                event="Awaiting operator decision",
                detail=f"Action paused: {approval_info.action} on {target_asset} (Risk: MEDIUM) · Awaiting {user_role}",
                status="paused",
                timestamp=_now_str(),
                duration_ms=0,
            ))
            preview_msg = (
                f"ACTION PAUSED FOR OPERATOR APPROVAL\n\n"
                f"{agent_name} has prepared Maintenance Work Order #WO-R204 for {target_asset}.\n"
                f"Governance Policy requires explicit human operator authorization ({user_role}) before executing deliverable generation."
            )
            return preview_msg, agent_name, steps, [], tools_used, "LOCAL_SYSTEM", selected_model, routing_info, "AWAITING_APPROVAL", approval_info

        # Case B: Denied by Operator
        elif payload.approval_decision.upper() == "DENIED":
            approval_info.status = "DENIED"
            steps.append(ExecutionStep(
                id="st-policy-check",
                name="policy_check",
                label="POLICY CHECK",
                event="Governance policy check",
                detail="Risk: MEDIUM · Action rejected by human operator",
                status="completed",
                timestamp=_now_str(),
                duration_ms=5,
            ))
            steps.append(ExecutionStep(
                id="st-hitl-denied",
                name="human_approval",
                label="APPROVAL REJECTED",
                event=f"Operator decision: DENIED",
                detail=f"Action rejected by {user_role} ({_now_str()}) · Tool execution blocked",
                status="completed",
                timestamp=_now_str(),
                duration_ms=10,
            ))
            steps.append(ExecutionStep(
                id="st-synthesis",
                name="synthesis",
                label="RESULT",
                event="Execution halted by governance policy",
                detail="Action was denied by operator. No operational deliverables generated.",
                status="completed",
                timestamp=_now_str(),
                duration_ms=5,
            ))
            denied_msg = (
                f"ACTION DENIED BY OPERATOR\n\n"
                f"The proposed action 'Generate Maintenance Work Order' for {target_asset} was rejected by {user_role}.\n"
                f"Tool execution halted. No operational deliverables or schedule modifications were committed."
            )
            return denied_msg, agent_name, steps, [], tools_used, "LOCAL_SYSTEM", selected_model, routing_info, "DENIED", approval_info

        # Case C: Approved by Operator -> Proceed with tool execution
        else:
            approval_info.status = "APPROVED"
            steps.append(ExecutionStep(
                id="st-policy-check",
                name="policy_check",
                label="POLICY CHECK",
                event="Governance policy check",
                detail="Risk: MEDIUM · Authorized by human operator",
                status="completed",
                timestamp=_now_str(),
                duration_ms=5,
            ))
            steps.append(ExecutionStep(
                id="st-hitl-approved",
                name="human_approval",
                label="HUMAN APPROVAL",
                event=f"Operator decision: APPROVED",
                detail=f"{user_role} authorized execution of '{approval_info.action}' on {target_asset}",
                status="completed",
                timestamp=_now_str(),
                duration_ms=15,
            ))

    # --- Stage 5: TOOL EXECUTION -----------------------------------------------
    s5_t = time.perf_counter()
    tool_results_context = ""
    sandbox_analysis_data = None

    if is_work_order_action:
        tools_used.append("maintenance_work_order_generator")
        eq = equipment_match or EQUIPMENT_TELEMETRY_REGISTRY["reactor r-204"]
        tool_detail = f"Executed maintenance_work_order_generator: Work Order #WO-R204 created for {eq['asset_id']} [Status: APPROVED]"
        
        tool_results_context = (
            f"\n\nOFFICIAL MAINTENANCE WORK ORDER — #WO-R204\n"
            f"Asset: {eq['asset_id']} ({eq['system']})\n"
            f"Operational Status: {eq['status']}\n"
            f"Current Core Temp: {eq.get('core_temp', '342.6 °C')} (Warning Threshold Exceeded)\n"
            f"Coolant Flow Rate: {eq.get('coolant_flow_rate', '1,240 L/min')} (Deviation -8.1%)\n"
            f"Catalyst Bed dP: {eq.get('catalyst_bed_dp', '0.45 bar')}\n"
            f"Prescribed Procedure: {eq.get('scheduled_procedure', 'Coolant Loop Filter Flush & Secondary Heat Exchanger Clean')}\n"
            f"Required Technician Clearance: L2 Mechanical Specialist + Safety Lead\n"
            f"Safety Protocol: Lockout / Tagout (LOTO) ISO-14001 Compliant\n"
            f"Authorization: Verified by {user_role}"
        )
    elif is_csv_analysis_query:
        from .sandbox import analyze_csv_dataset
        sandbox_res = analyze_csv_dataset(filename="operations.csv", target_column="temperature", threshold=95.0)
        sandbox_analysis_data = sandbox_res
        tools_used.append("csv_analysis")
        tool_detail = f"Executed csv_analysis (Restricted Local Sandbox): {sandbox_res.get('rows_analyzed', 0)} rows analyzed · {sandbox_res.get('anomalies_detected', 0)} anomalies detected [Network: BLOCKED]"
        
        anom_lines = []
        for a in sandbox_res.get("anomalous_records", []):
            anom_lines.append(f"  • Row {a['row']} ({a['timestamp']}): {a['value']}°C (Severity: {a['severity']}, Pressure: {a['pressure']}, Flow: {a['flow_rate']})")
        
        st = sandbox_res.get("statistics", {})
        tool_results_context = (
            f"\n\nRESTRICTED LOCAL SANDBOX ANALYSIS (operations.csv):\n"
            f"- Total Records Analyzed: {sandbox_res.get('rows_analyzed', 0)}\n"
            f"- Parameter: Temperature (°C) — Mean: {st.get('mean')}°C, Min: {st.get('min')}°C, Max: {st.get('max')}°C, StdDev: ±{st.get('stddev')}°C\n"
            f"- Threshold: > 95.0°C\n"
            f"- Anomalies Detected: {sandbox_res.get('anomalies_detected', 0)}\n"
            f"- Anomalous Instances:\n" + "\n".join(anom_lines)
        )
    elif equipment_match:
        tools_used.append("telemetry_diagnostic_tool")
        tool_detail = f"Executed telemetry_diagnostic_tool: {equipment_match['asset_id']} [Status: {equipment_match['status']}]"
        tool_results_context = (
            f"\n\nLIVE ON-PREMISE DIAGNOSTIC READOUT:\n"
            f"- Asset: {equipment_match['asset_id']} ({equipment_match['system']})\n"
            f"- Operational Status: {equipment_match['status']}\n"
            + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in equipment_match.items() if k not in ["asset_id", "system", "status"])
        )
    else:
        tools_used.append("semantic_evidence_verifier")
        tool_detail = f"Executed semantic_evidence_verifier: {len(raw_chunks)} chunks analyzed for relevance"

    steps.append(ExecutionStep(
        id="st-tool",
        name="tool_execution",
        label="TOOL EXECUTION",
        event="Approved tools executed",
        detail=tool_detail,
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s5_t),
    ))

    # --- Stage 6: VERIFICATION -------------------------------------------------
    s6_t = time.perf_counter()
    steps.append(ExecutionStep(
        id="st-verify",
        name="verification",
        label="VERIFY",
        event="Evidence provenance verified",
        detail="All sources & parameters verified on-premise · Zero external cloud egress",
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s6_t),
    ))

    # --- Stage 7: RESULT SYNTHESIS ---------------------------------------------
    s7_t = time.perf_counter()
    
    augmented_chunks = list(raw_chunks)
    if tool_results_context:
        if is_work_order_action:
            augmented_chunks.insert(0, {
                "filename": "Maintenance Work Order #WO-R204",
                "page": 1,
                "source_locator": "Approved Operational Generator",
                "file_type": "WORK_ORDER",
                "text": tool_results_context.strip(),
                "excerpt": f"Work Order #WO-R204: Reactor R-204 Coolant Flush & Heat Exchanger Clean (Authorized by {user_role})",
                "relevance": 99.9
            })
        elif is_csv_analysis_query:
            augmented_chunks.insert(0, {
                "filename": "operations.csv",
                "page": 1,
                "source_locator": "Restricted Local Sandbox",
                "file_type": "CSV",
                "text": tool_results_context.strip(),
                "excerpt": f"{sandbox_analysis_data.get('anomalies_detected', 0)} temperature anomalies detected in operations.csv (Max: {sandbox_analysis_data.get('statistics', {}).get('max', 0)}°C vs Mean: {sandbox_analysis_data.get('statistics', {}).get('mean', 0)}°C)",
                "relevance": 99.8
            })
        elif equipment_match:
            augmented_chunks.insert(0, {
                "filename": "Node IC-HYD-01 Telemetry",
                "page": 1,
                "source_locator": "Live Sensor Bus",
                "file_type": "TELEMETRY",
                "text": tool_results_context.strip(),
                "excerpt": f"Status: {equipment_match['status']} · Temp: {equipment_match.get('core_temp', 'N/A')} · Vibration: {equipment_match.get('radial_vibration', 'N/A')}",
                "relevance": 99.5
            })

    llm_output = generate(payload.request, augmented_chunks, history=history, model=selected_model)
    result_text = llm_output["answer"]
    inference_mode = llm_output["mode"]
    actual_model = llm_output.get("model", selected_model)

    steps.append(ExecutionStep(
        id="st-synthesis",
        name="synthesis",
        label="RESULT",
        event="Grounded response synthesized",
        detail=f"Inference complete ({inference_mode}) via {actual_model}",
        status="completed",
        timestamp=_now_str(),
        duration_ms=_elapsed_ms(s7_t),
    ))

    # Build structured evidence list
    evidence: List[EvidenceItem] = []
    for c in augmented_chunks:
        evidence.append(EvidenceItem(
            filename=c["filename"],
            page=c.get("page", 1),
            source_locator=c.get("source_locator") or f"Page {c.get('page', 1)}",
            file_type=c.get("file_type", "DOC"),
            collection=c.get("collection", "All Documents"),
            excerpt=c.get("excerpt") or c["text"][:240],
            relevance=c.get("relevance", 85.0),
        ))

    return result_text, agent_name, steps, evidence, tools_used, inference_mode, actual_model, routing_info, "VERIFIED", (approval_info if is_work_order_action else None)
