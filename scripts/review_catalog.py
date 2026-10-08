"""Show catalog records that require manual source review."""
import json
from datetime import date, timedelta
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "data"
today = date.today()
for kind in ("jobs", "courses"):
    records = json.loads((root / f"{kind}.json").read_text(encoding="utf-8"))
    print(f"{kind}: {len(records)} registros")
    for item in records:
        if item["status"] != "published":
            continue
        due = date.fromisoformat(item["review_by"])
        if item.get("expires_on"):
            due = min(due, date.fromisoformat(item["expires_on"]))
        if due <= today + timedelta(days=7):
            label = "VENCIDO" if due < today else "REVISAR"
            print(f"  {label} {due.isoformat()} | {item['title']} | {item['original_url']}")
