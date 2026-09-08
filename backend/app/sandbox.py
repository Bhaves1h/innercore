"""
INNERCORE Restricted Local Analysis Sandbox
Provides safe, deterministic computation and anomaly detection on tabular/CSV data
without arbitrary shell execution or network access.
100% on-premise, zero cloud egress.
"""
from __future__ import annotations

import os
import csv
import math
from typing import Dict, Any, List, Optional
from datetime import datetime


def find_csv_file(filename: str = "operations.csv") -> Optional[str]:
    """Locate target CSV dataset safely within project boundaries."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", filename)),
        os.path.abspath(os.path.join(os.getcwd(), filename)),
        os.path.abspath(os.path.join(os.getcwd(), "backend", filename)),
        os.path.abspath(os.path.join(os.getcwd(), "uploaded_docs", filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploaded_docs", filename)),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            return p
    return None


def analyze_csv_dataset(
    filename: str = "operations.csv",
    target_column: str = "temperature",
    threshold: float = 95.0,
    z_threshold: float = 2.5
) -> Dict[str, Any]:
    """
    Perform restricted, isolated statistical analysis and anomaly detection on a CSV file.
    Runs entirely in memory with strictly bounded execution.
    """
    from .network_monitor import record_network_activity

    # Record sandbox local bus activity
    record_network_activity(
        destination="Restricted Local Sandbox",
        protocol="IPC / In-Memory",
        purpose=f"Safe tabular anomaly analysis on {filename}",
        status="LOCAL",
        is_external=False
    )

    filepath = find_csv_file(filename)
    if not filepath:
        return {
            "tool": "csv_analysis",
            "sandbox_mode": "RESTRICTED_LOCAL",
            "network_access": False,
            "status": "FAILED",
            "error": f"CSV dataset '{filename}' not found within sovereign boundary.",
            "rows_analyzed": 0,
            "columns": [],
            "anomalies_detected": 0,
            "anomalous_records": []
        }

    rows: List[Dict[str, str]] = []
    headers: List[str] = []

    with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for r in reader:
            rows.append(r)

    # Determine target numeric column
    actual_col = None
    for h in headers:
        if target_column.lower() in h.lower():
            actual_col = h
            break
    if not actual_col and headers:
        # Fallback to first numeric-like column
        actual_col = headers[1] if len(headers) > 1 else headers[0]

    values: List[float] = []
    parsed_rows: List[tuple[int, Dict[str, str], float]] = []

    for idx, r in enumerate(rows, 1):
        raw_val = r.get(actual_col, "")
        try:
            val_clean = float(str(raw_val).replace("°C", "").replace("C", "").replace("psi", "").strip())
            values.append(val_clean)
            parsed_rows.append((idx, r, val_clean))
        except (ValueError, TypeError):
            continue

    if not values:
        return {
            "tool": "csv_analysis",
            "sandbox_mode": "RESTRICTED_LOCAL",
            "network_access": False,
            "status": "COMPLETED_EMPTY",
            "rows_analyzed": len(rows),
            "columns": headers,
            "anomalies_detected": 0,
            "anomalous_records": [],
            "summary": f"Analyzed {len(rows)} rows. No numeric values found in target column '{actual_col}'."
        }

    # Statistical computation
    val_min = round(min(values), 2)
    val_max = round(max(values), 2)
    val_mean = round(sum(values) / len(values), 2)
    variance = sum((x - val_mean) ** 2 for x in values) / len(values)
    val_std = round(math.sqrt(variance), 2) if variance > 0 else 0.0

    # Anomaly detection: threshold-based or statistical z-score
    anomalies: List[Dict[str, Any]] = []
    for row_num, row_data, val in parsed_rows:
        is_threshold_anomaly = val > threshold
        z_score = round((val - val_mean) / val_std, 2) if val_std > 0 else 0.0
        is_z_anomaly = abs(z_score) > z_threshold

        if is_threshold_anomaly or is_z_anomaly:
            severity = "CRITICAL" if val > (threshold * 1.05) or z_score > 3.0 else "HIGH"
            anomalies.append({
                "row": row_num,
                "timestamp": row_data.get("timestamp", row_data.get("time", f"T-{row_num:03d}")),
                "parameter": actual_col,
                "value": val,
                "threshold": threshold,
                "z_score": z_score,
                "severity": severity,
                "pressure": row_data.get("pressure", "N/A"),
                "flow_rate": row_data.get("flow_rate", "N/A"),
            })

    return {
        "tool": "csv_analysis",
        "sandbox_mode": "RESTRICTED_LOCAL",
        "network_access": False,
        "status": "COMPLETED",
        "dataset": os.path.basename(filepath),
        "rows_analyzed": len(rows),
        "columns": headers,
        "target_column": actual_col,
        "statistics": {
            "count": len(values),
            "min": val_min,
            "max": val_max,
            "mean": val_mean,
            "stddev": val_std,
            "unit": "°C" if "temp" in actual_col.lower() else ""
        },
        "threshold_used": threshold,
        "anomalies_detected": len(anomalies),
        "anomalous_records": anomalies,
        "summary": (
            f"Analyzed {len(rows)} records in {os.path.basename(filepath)}. "
            f"Mean {actual_col}: {val_mean}°C (Min: {val_min}°C, Max: {val_max}°C, Std: ±{val_std}°C). "
            f"Identified {len(anomalies)} anomalous readings exceeding threshold ({threshold}°C)."
        )
    }
