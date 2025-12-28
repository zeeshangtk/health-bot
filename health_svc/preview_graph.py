#!/usr/bin/env python3
"""
UX Preview Script for Health Graph Visualization

This script generates a standalone HTML file for visual inspection of the
GraphService output. It is NOT a test — no assertions, no pass/fail.

Purpose:
- Validate layout, colors, legends, spacing, and mobile friendliness
- Review abnormal value highlighting (diamond markers, red fill)
- Check dual Y-axis behavior (primary vs micro metrics)
- Inspect blood pressure range chart
- Verify summary panel and trend indicators

Usage:
    python preview_graph.py

    # Or via pytest (will not fail, just generates file):
    pytest preview_graph.py -s

Output:
    health_graph_preview.html (in project root)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure the package is importable when running from health_svc directory
sys.path.insert(0, str(Path(__file__).parent))

from schemas import HealthRecordResponse
from services.graph import GraphService


def create_sample_records() -> list[HealthRecordResponse]:
    """
    Create realistic sample health records for UX preview.
    
    Covers:
    - Multiple metric types across different Y-axes
    - Normal, borderline, and abnormal values
    - Blood pressure (systolic + diastolic pair)
    - 6-month date range
    """
    records = []
    
    # Base date: 6 months ago
    base_date = datetime.now() - timedelta(days=180)
    
    def iso(days_offset: int) -> str:
        """Generate ISO-8601 timestamp."""
        return (base_date + timedelta(days=days_offset)).isoformat()
    
    # =========================================================================
    # Blood Sugar (Random) - y1 axis, normal range 70-140 mg/dl
    # Mix of normal and abnormal values
    # =========================================================================
    blood_sugar_data = [
        (0, "95"),      # Normal
        (30, "112"),    # Normal
        (60, "145"),    # Abnormal (high)
        (90, "88"),     # Normal
        (120, "156"),   # Abnormal (high)
        (150, "102"),   # Normal
        (180, "135"),   # Borderline
    ]
    for days, value in blood_sugar_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Random Blood Sugar",
            value=value,
            unit="mg/dl",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # Creatinine - y2 axis (small values), normal range 0.6-1.2 mg/dl
    # Shows trend from normal to concerning
    # =========================================================================
    creatinine_data = [
        (0, "0.9"),     # Normal
        (30, "1.0"),    # Normal
        (60, "1.1"),    # Borderline
        (90, "1.3"),    # Abnormal (high)
        (120, "1.4"),   # Abnormal (high)
        (150, "1.2"),   # Borderline
        (180, "1.1"),   # Borderline (improving)
    ]
    for days, value in creatinine_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Creatinine",
            value=value,
            unit="mg/dl",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # Haemoglobin - y1 axis, normal range 12.0-17.5 g/dl
    # Stable with one low reading
    # =========================================================================
    hemoglobin_data = [
        (0, "14.2"),    # Normal
        (45, "13.8"),   # Normal
        (90, "11.5"),   # Abnormal (low)
        (135, "12.8"),  # Normal
        (180, "14.0"),  # Normal
    ]
    for days, value in hemoglobin_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Haemoglobin",
            value=value,
            unit="g/dl",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # Sodium - y1 axis, normal range 136-145 mMol/L
    # =========================================================================
    sodium_data = [
        (15, "140"),    # Normal
        (75, "138"),    # Normal
        (135, "146"),   # Abnormal (high)
        (180, "142"),   # Normal
    ]
    for days, value in sodium_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Sodium",
            value=value,
            unit="mMol/L",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # Potassium - y2 axis (small values), normal range 3.5-5.0 mMol/L
    # =========================================================================
    potassium_data = [
        (15, "4.2"),    # Normal
        (75, "3.3"),    # Abnormal (low)
        (135, "4.8"),   # Normal
        (180, "5.2"),   # Abnormal (high)
    ]
    for days, value in potassium_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Potassium",
            value=value,
            unit="mMol/L",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # Blood Pressure - Systolic + Diastolic (paired for range chart)
    # Normal: <120/<80, Elevated: 120-129/<80, High: 130+/80+
    # =========================================================================
    bp_data = [
        (10, "118", "76"),   # Normal
        (40, "125", "82"),   # Elevated
        (70, "135", "88"),   # High Stage 1
        (100, "142", "92"),  # High Stage 2
        (130, "128", "84"),  # Elevated
        (160, "122", "78"),  # Normal
        (180, "119", "75"),  # Normal
    ]
    for days, systolic, diastolic in bp_data:
        ts = iso(days)
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Systolic",
            value=systolic,
            unit="mmHg",
            timestamp=ts,
        ))
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Diastolic",
            value=diastolic,
            unit="mmHg",
            timestamp=ts,
        ))
    
    # =========================================================================
    # Blood Urea - y1 axis, normal range 15-45 mg/dl
    # Few data points to test sparse data handling
    # =========================================================================
    urea_data = [
        (20, "28"),     # Normal
        (100, "48"),    # Abnormal (high)
        (180, "35"),    # Normal
    ]
    for days, value in urea_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="Blood Urea",
            value=value,
            unit="mg/dl",
            timestamp=iso(days),
        ))
    
    # =========================================================================
    # HbA1c - y2 axis, normal range 4.0-5.6%
    # Quarterly readings (typical clinical pattern)
    # =========================================================================
    hba1c_data = [
        (0, "5.4"),     # Normal
        (90, "5.8"),    # Pre-diabetic (abnormal)
        (180, "5.5"),   # Normal
    ]
    for days, value in hba1c_data:
        records.append(HealthRecordResponse(
            id=len(records) + 1,
            patient="John Doe",
            record_type="HbA1c",
            value=value,
            unit="%",
            timestamp=iso(days),
        ))
    
    return records


def generate_preview():
    """Generate the HTML preview file."""
    print("=" * 60)
    print("Health Graph UX Preview Generator")
    print("=" * 60)
    
    # Create sample data
    records = create_sample_records()
    print(f"\n✓ Created {len(records)} sample health records")
    print(f"  - Date range: ~6 months")
    print(f"  - Metrics: Blood Sugar, Creatinine, Haemoglobin, Sodium,")
    print(f"             Potassium, Blood Pressure, Blood Urea, HbA1c")
    
    # Generate graph
    service = GraphService()
    html_content = service.generate_html_graph(records, patient_name="John Doe")
    print(f"\n✓ Generated HTML graph ({len(html_content):,} bytes)")
    
    # Write to file
    output_path = Path(__file__).parent.parent / "health_graph_preview.html"
    output_path.write_text(html_content, encoding="utf-8")
    print(f"\n✓ Saved to: {output_path.resolve()}")
    
    print("\n" + "=" * 60)
    print("Open the HTML file in a browser to review:")
    print(f"  file://{output_path.resolve()}")
    print("=" * 60)
    
    return str(output_path)


# Allow running directly or via pytest -s
def test_generate_preview():
    """Pytest-compatible entry point (no assertions)."""
    generate_preview()


if __name__ == "__main__":
    generate_preview()

