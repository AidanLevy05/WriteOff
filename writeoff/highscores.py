"""Small, fault-tolerant local high-score store."""

import json
from datetime import date
from pathlib import Path


HIGH_SCORE_PATH = Path(__file__).resolve().parents[1] / "highscores.json"
DIFFICULTIES = ("easy", "normal", "hard")


def record_score(difficulty: str, score: int, background: str) -> tuple[int, bool]:
    scores = _load_scores()
    key = difficulty if difficulty in DIFFICULTIES else "normal"
    current = int(scores[key].get("score", 0))
    if score <= current:
        return current, False

    scores[key] = {"score": score, "background": background, "date": date.today().isoformat()}
    try:
        HIGH_SCORE_PATH.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    except OSError:
        pass
    return score, True


def _load_scores() -> dict[str, dict[str, object]]:
    empty = {difficulty: {"score": 0} for difficulty in DIFFICULTIES}
    try:
        data = json.loads(HIGH_SCORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return empty
    if not isinstance(data, dict):
        return empty
    for difficulty in DIFFICULTIES:
        entry = data.get(difficulty)
        if not isinstance(entry, dict) or not isinstance(entry.get("score"), int):
            continue
        empty[difficulty] = entry
    return empty
