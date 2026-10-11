"""CreditMera Watermark Robustness Lab — Result Serialization.

Handles structured export and parsing of experiment outputs to:
- JSON: Complete hierarchical metadata, system configuration, per-attack statistics.
- CSV: Flat tabular trial logs suitable for data analysis and visualization.
"""
import csv
import json
from pathlib import Path
from typing import Dict, Any, List


def save_results_json(data: Dict[str, Any], filepath: Path) -> Path:
    """Save structured experiment results to a formatted JSON file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def save_results_csv(trials: List[Dict[str, Any]], filepath: Path) -> Path:
    """Save flat list of experiment trials to a CSV file."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not trials:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            pass
        return filepath

    # Collect all field names across trials
    fieldnames = []
    for t in trials:
        for k in t.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in trials:
            # Flatten any nested dictionaries for CSV compatibility
            row = {}
            for k, v in t.items():
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v)
                else:
                    row[k] = v
            writer.writerow(row)

    return filepath


def load_results_json(filepath: Path) -> Dict[str, Any]:
    """Parse JSON experiment results file."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"JSON results file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_results_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Parse CSV experiment results file into list of row dictionaries."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV results file not found: {filepath}")
    trials = []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trials.append(dict(row))
    return trials
