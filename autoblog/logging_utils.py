from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def append_jsonl_log(log_path: Path, payload: dict[str, object]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    enriched = {
        "logged_at": datetime.now().isoformat(),
        **payload,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")
