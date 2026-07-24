import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Any

from writeoff.models import (
    Assignment,
    Asset,
    Contact,
    Employee,
    Encounter,
    EncounterOption,
    Evidence,
    EvidenceCategory,
    GameState,
    GameStatus,
    LegalRequest,
    MenuState,
    Operation,
    Requirement,
    Settings,
)


SAVE_PATH = Path(__file__).resolve().parents[1] / "savegame.json"


def _enum_to_value(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _enum_to_value(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_enum_to_value(value) for value in data]
    if isinstance(data, set):
        return sorted(data)
    if isinstance(data, tuple):
        return [_enum_to_value(value) for value in data]
    if isinstance(data, GameStatus | EvidenceCategory):
        return data.value if isinstance(data, EvidenceCategory) else data.name
    return data


def save_game(state: GameState, rng: random.Random) -> None:
    data = _enum_to_value(asdict(state))
    data["random_state"] = _enum_to_value(rng.getstate())
    data["save_version"] = 2
    SAVE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_game(rng: random.Random) -> GameState:
    raw = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    if raw.get("save_version") != 2:
        raise ValueError("save file is from an older incompatible version")
    random_state = raw.pop("random_state", None)
    raw.pop("save_version", None)
    state = state_from_dict(raw)
    if random_state is not None:
        rng.setstate(_to_tuple(random_state))
    return state


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(item) for item in value)
    return value


def requirement_from_dict(data: dict[str, Any] | None) -> Requirement:
    if not data:
        return Requirement()
    return Requirement(**data)


def assignment_from_dict(data: dict[str, Any] | None) -> Assignment | None:
    if data is None:
        return None
    return Assignment(**data)


def employee_from_dict(data: dict[str, Any]) -> Employee:
    data = dict(data)
    data["assigned_task"] = assignment_from_dict(data.get("assigned_task"))
    return Employee(**data)


def evidence_from_dict(data: dict[str, Any]) -> Evidence:
    data = dict(data)
    data["category"] = EvidenceCategory(data.get("category", "financial"))
    return Evidence(**data)


def contact_from_dict(data: dict[str, Any]) -> Contact:
    data = dict(data)
    data["unlock_condition"] = requirement_from_dict(data.get("unlock_condition"))
    return Contact(**data)


def option_from_dict(data: dict[str, Any]) -> EncounterOption:
    data = dict(data)
    data["requirement"] = requirement_from_dict(data.get("requirement"))
    return EncounterOption(**data)


def encounter_from_dict(data: dict[str, Any] | None) -> Encounter | None:
    if data is None:
        return None
    return Encounter(
        data["key"],
        data["title"],
        data["description"],
        [option_from_dict(item) for item in data["options"]],
    )


def state_from_dict(data: dict[str, Any]) -> GameState:
    data = dict(data)
    data["status"] = GameStatus[data.get("status", "RUNNING")]
    data["employees"] = [employee_from_dict(item) for item in data.get("employees", [])]
    data["assets"] = [Asset(**item) for item in data.get("assets", [])]
    data["evidence"] = [evidence_from_dict(item) for item in data.get("evidence", [])]
    data["operations"] = [Operation(**item) for item in data.get("operations", [])]
    data["contacts"] = [contact_from_dict(item) for item in data.get("contacts", [])]
    data["flags"] = set(data.get("flags", []))
    data["announced_unlocks"] = set(data.get("announced_unlocks", []))
    data["achievements"] = set(data.get("achievements", []))
    data["settings"] = Settings(**data.get("settings", {}))
    menu = MenuState(**data.get("menu", {}))
    saved_tabs = menu.tabs
    saved_current_tab = saved_tabs[min(menu.tab_index, len(saved_tabs) - 1)] if saved_tabs else "Actions"
    menu.tabs = MenuState().tabs
    menu.tab_index = menu.tabs.index(saved_current_tab) if saved_current_tab in menu.tabs else 0
    for tab in menu.tabs:
        menu.selections.setdefault(tab, 0)
    data["menu"] = menu
    request = data.get("pending_request")
    data["pending_request"] = LegalRequest(**request) if request else None
    data["pending_encounter"] = encounter_from_dict(data.get("pending_encounter"))
    return GameState(**data)
