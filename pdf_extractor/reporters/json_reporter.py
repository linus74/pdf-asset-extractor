"""
JSON Reporter: exports full extracted PDF data into report.json.
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_json_report(data: Dict[str, Any], output_dir: Path) -> Path:
    """
    Writes formatted JSON report to `output_dir / "report.json"`.
    """
    report_file = output_dir / "report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return report_file
