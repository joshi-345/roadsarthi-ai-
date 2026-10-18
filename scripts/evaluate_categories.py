"""Report category accuracy on synthetic complaints; model calls need opt-in."""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from roadsaarthi.complaint_assistance import suggest_from_rules
from roadsaarthi.model_provider import call_model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-model", action="store_true",
                        help="Opt in to send synthetic rows to local Ollama.")
    parser.add_argument(
        "--csv",
        default=str(Path(__file__).resolve().parents[1] / "tests/data/sample_complaints.csv"),
    )
    args = parser.parse_args()
    rows = list(csv.DictReader(Path(args.csv).open(encoding="utf-8-sig", newline="")))
    stats = defaultdict(lambda: {"n": 0, "rules_correct": 0, "rules_covered": 0,
                                 "combined_correct": 0, "combined_covered": 0})
    for row in rows:
        language, text, expected = row["language"], row["complaint"], row["expected_category"]
        rule = suggest_from_rules(text, language)
        combined = rule
        s = stats[language]
        s["n"] += 1
        s["rules_covered"] += rule is not None
        s["rules_correct"] += rule == expected
        if args.with_model and rule is None and language not in ("Gurmukhi Punjabi", "Roman Punjabi"):
            try:
                combined = call_model(text=text, language=language, task="category")
                combined = combined.get("category") if isinstance(combined, dict) else None
                if combined not in {
                    "Pothole", "Broken Guardrail", "Missing / Damaged Sign",
                    "Waterlogging / Flooding", "Road Debris", "Unmarked Speed Bump",
                    "Damaged Road Surface", "Other",
                }:
                    combined = None
            except Exception:
                combined = None
        s["combined_covered"] += combined is not None
        s["combined_correct"] += combined == expected
    total = {key: sum(values[key] for values in stats.values()) for key in next(iter(stats.values()))}
    print("language,n,rules_accuracy,rules_coverage,rules_plus_model_accuracy,rules_plus_model_coverage")
    for language, s in sorted(stats.items()):
        print(f"{language},{s['n']},{s['rules_correct']/s['n']:.3f},"
              f"{s['rules_covered']/s['n']:.3f},{s['combined_correct']/s['n']:.3f},"
              f"{s['combined_covered']/s['n']:.3f}")
    print(f"OVERALL,{total['n']},{total['rules_correct']/total['n']:.3f},"
          f"{total['rules_covered']/total['n']:.3f},"
          f"{total['combined_correct']/total['n']:.3f},"
          f"{total['combined_covered']/total['n']:.3f}")


if __name__ == "__main__":
    main()
