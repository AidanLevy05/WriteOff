"""Keyboard-driven terminal UI for Write Off."""

import shutil
import textwrap

from writeoff.colors import Colors
from writeoff.content import BACKGROUNDS, DIFFICULTIES, TASKS
from writeoff.engine import GameEngine
from writeoff.models import Action, Asset, Contact, Employee, Evidence, EvidenceCategory, GameStatus, Operation, Requirement, Task


def clear_screen() -> None:
    print("\033[H\033[2J", end="")


def hide_cursor() -> None:
    print("\033[?25l", end="")


def show_cursor() -> None:
    print("\033[?25h", end="")


def compact_money(value: int) -> str:
    absolute = abs(value)
    sign = "-" if value < 0 else ""
    if absolute >= 1_000_000_000:
        return f"{sign}${absolute / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{sign}${absolute / 1_000:.0f}K"
    return f"{sign}${absolute}"


def trim(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: max(0, width - 3)] + "..." if width > 3 else text[:width]


def progress_bar(value: int, width: int = 22) -> str:
    value = max(0, min(100, value))
    filled = round(value / 100 * width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {value:3d}%"


def render(engine: GameEngine) -> None:
    clear_screen()
    terminal = shutil.get_terminal_size(fallback=(100, 35))
    width = max(60, min(terminal.columns, 100))
    height = terminal.lines
    colors = Colors(engine.state.settings.color_enabled)
    if engine.state.status is GameStatus.SETUP:
        render_setup(engine, width, colors)
    elif engine.state.view == "help":
        render_help(engine, width, colors)
    elif engine.state.view == "settings":
        render_settings(engine, width, colors)
    elif engine.state.view == "confirm":
        render_confirm(engine, width, colors)
    elif engine.state.view == "asset_confirm":
        render_asset_confirm(engine, width, colors)
    elif engine.state.view == "task":
        render_task_menu(engine, width, colors)
    elif engine.state.view == "evidence_action":
        render_evidence_action(engine, width, colors)
    elif engine.state.view == "load_confirm":
        render_load_confirm(engine, width, colors)
    elif engine.state.pending_request:
        render_legal_request(engine, width, colors)
    elif engine.state.pending_encounter:
        render_encounter(engine, width, colors)
    else:
        render_normal(engine, width, height, colors)
    print("", flush=True)


def render_setup(engine: GameEngine, width: int, colors: Colors) -> None:
    state = engine.state
    print(colors.heading("WRITE OFF"))
    print("-" * width)
    if state.setup_step == "difficulty":
        print("Choose difficulty")
        keys = list(DIFFICULTIES)
        for index, key in enumerate(keys):
            label = DIFFICULTIES[key]["name"]
            print(menu_row(label, index == state.menu.setup_selection, False, width, colors))
    else:
        print("Choose background")
        keys = list(BACKGROUNDS)
        for index, key in enumerate(keys):
            data = BACKGROUNDS[key]
            label = f"{data['name']:<28} {compact_money(data['cash'])}"
            print(menu_row(label, index == state.menu.setup_selection, False, width, colors))
    print()
    print(trim(state.message, width))
    footer(width)


def render_normal(engine: GameEngine, width: int, height: int, colors: Colors) -> None:
    state = engine.state
    print(colors.heading("WRITE OFF"))
    print(trim(f"Cash {compact_money(state.cash)} | Assets {compact_money(state.asset_value)} | Rep {state.reputation} | Upkeep {compact_money(state.upkeep_costs)}/turn", width))
    render_clock(engine, width, colors)
    print(render_tabs(engine, width, colors))
    tab = engine.current_tab()
    list_height = max(8, min(14, height - 19))
    render_tab_list(engine, tab, width, list_height, colors)
    render_description_panel(engine, tab, width, colors)
    render_messages(engine, width, 2, colors)
    footer(width)


def render_clock(engine: GameEngine, width: int, colors: Colors) -> None:
    state = engine.state
    clock = f"FEDERAL CLOCK {progress_bar(state.federal_clock)} {state.pressure_label}"
    if state.federal_clock >= 75:
        clock = colors.danger(clock)
    elif state.federal_clock >= 50:
        clock = colors.warning(clock)
    else:
        clock = colors.reputation(clock)
    print(trim(clock, width))
    sign = "+" if state.last_clock_change > 0 else ""
    last = f"Last change: {sign}{state.last_clock_change} - {state.last_clock_reason}"
    print(trim(last, width))


def render_tabs(engine: GameEngine, width: int, colors: Colors) -> str:
    labels = []
    for index, tab in enumerate(engine.state.menu.tabs):
        label = f"[{tab.upper()}]" if index == engine.state.menu.tab_index else tab.upper()
        labels.append(colors.heading(label) if index == engine.state.menu.tab_index else label)
    return trim("  ".join(labels), width)


def render_tab_list(engine: GameEngine, tab: str, width: int, list_height: int, colors: Colors) -> None:
    items = engine.items_for_tab(tab)
    selected = engine.selected_index(tab) if items else 0
    if not items:
        empty = {
            "Employees": "No employees yet.",
            "Evidence": "No evidence.",
            "Assets": "No assets to write off.",
            "Operations": "No active operations.",
            "Contacts": "No contacts.",
        }.get(tab, "Nothing here.")
        print(menu_row(empty, False, True, width, colors))
        for _ in range(list_height - 1):
            print()
        return
    start = max(0, min(selected - list_height // 2, max(0, len(items) - list_height)))
    for index in range(start, min(start + list_height, len(items))):
        item = items[index]
        locked = tab == "Actions" and engine.action_lock_reason(item) is not None
        print(menu_row(row_text(engine, tab, item), index == selected, locked, width, colors))
    for _ in range(list_height - min(list_height, len(items) - start)):
        print()


def row_text(engine: GameEngine, tab: str, item: object) -> str:
    if tab == "Actions":
        action = item
        assert isinstance(action, Action)
        reason = engine.action_lock_reason(action)
        status = "LOCKED" if reason else compact_money(engine._action_cost(action))
        risk = action.risk_label.upper()
        return f"{action.name:<42} {status:<10} {risk}"
    if tab == "Employees":
        employee = item
        assert isinstance(employee, Employee)
        task = employee.assigned_task.task_name if employee.assigned_task else "idle"
        return f"{employee.name:<24} C{employee.competence} L{employee.loyalty} S{employee.stress}  {task}"
    if tab == "Evidence":
        evidence = item
        assert isinstance(evidence, Evidence)
        return f"{evidence.name:<42} {evidence.label:<12} {evidence.category.value} {evidence.agency}"
    if tab == "Assets":
        asset = item
        assert isinstance(asset, Asset)
        return f"{asset.name:<42} {compact_money(asset.value):<10} upkeep {compact_money(asset.upkeep_cost)}/turn"
    if tab == "Operations":
        operation = item
        assert isinstance(operation, Operation)
        return f"{operation.name:<42} {operation.turns_remaining} turns  +{operation.clock_per_turn}/turn"
    if tab == "Contacts":
        contact = item
        assert isinstance(contact, Contact)
        return f"{contact.name:<28} {contact.status:<11} rel {contact.relationship:>4}"
    if tab == "Settings":
        return "Open settings"
    return str(item)


def menu_row(text: str, selected: bool, locked: bool, width: int, colors: Colors) -> str:
    prefix = "> " if selected else "  "
    line = trim(prefix + text, width)
    if selected:
        return colors.selected(line)
    if locked:
        return colors.muted(line)
    return line


def render_description_panel(engine: GameEngine, tab: str, width: int, colors: Colors) -> None:
    print("-" * width)
    lines = description_lines(engine, tab)
    for line in lines[:6]:
        print(trim(line, width))
    for _ in range(6 - min(6, len(lines))):
        print()


def description_lines(engine: GameEngine, tab: str) -> list[str]:
    items = engine.items_for_tab(tab)
    if not items:
        return ["No selectable item.", "Use Left/Right to change tabs."]
    item = items[engine.selected_index(tab)]
    if tab == "Actions":
        action = item
        assert isinstance(action, Action)
        reason = engine.action_lock_reason(action)
        lines = [
            action.name.upper(),
            f"Cost: {compact_money(engine._action_cost(action))} | Rep +{action.reputation_gain} | Risk: {action.risk_label} ({action.clock_min} to +{action.clock_max})",
            action.description,
            f"Requires: {requirement_text(action.requirement)}",
            f"Outcomes: {', '.join(action.outcomes) or 'Unknown'}",
        ]
        if reason:
            lines.append(f"LOCKED: {reason}")
        elif action.confirmation_required:
            lines.append("Enter opens confirmation.")
        return wrap_lines(lines, 96)
    if tab == "Employees":
        employee = item
        assert isinstance(employee, Employee)
        task = employee.assigned_task.task_name if employee.assigned_task else "Idle"
        return [
            employee.name.upper(),
            f"{employee.role} | Cost {compact_money(employee.upkeep_cost)}/turn",
            f"Competence {employee.competence} | Loyalty {employee.loyalty} | Stress {employee.stress}",
            f"Trait: {', '.join(employee.traits) or 'None'}",
            f"Assignment: {task}",
            "Enter opens task selection when idle.",
        ]
    if tab == "Evidence":
        evidence = item
        assert isinstance(evidence, Evidence)
        return [
            evidence.name.upper(),
            f"Strength {evidence.strength}/10 {evidence.label} | {evidence.category.value} | {evidence.agency}",
            f"Source: {evidence.source}",
            f"Responses: {evidence_actions(evidence.category)}",
            "Enter opens available evidence-management options.",
        ]
    if tab == "Assets":
        asset = item
        assert isinstance(asset, Asset)
        risk = engine.asset_write_off_risk(asset)
        return [
            asset.name.upper(),
            f"Value {compact_money(asset.value)} | Upkeep {compact_money(asset.upkeep_cost)}/turn",
            "Enter writes off this asset permanently. It cannot be recovered.",
            f"Expected Federal Clock change: +{risk}",
            "Use this to dispose of remaining wealth, especially when cash is exhausted.",
        ]
    if tab == "Operations":
        operation = item
        assert isinstance(operation, Operation)
        return [
            operation.name.upper(),
            f"Turns remaining: {operation.turns_remaining} | Upkeep {compact_money(operation.upkeep_cost)}/turn",
            f"Federal Clock pressure: +{operation.clock_per_turn}/turn{' (hidden)' if operation.hidden else ''}",
            f"Completion: {operation.completion_message}",
            "Support options are employee assignments.",
        ]
    if tab == "Settings":
        return [
            "SETTINGS",
            "Enter opens color, animation, and sound toggles.",
            "Changing settings does not advance turns or the Federal Clock.",
        ]
    contact = item
    assert isinstance(contact, Contact)
    return [
        contact.name.upper(),
        contact.role,
        f"Status: {contact.status} | Relationship: {contact.relationship}",
        f"Unlock: {requirement_text(contact.unlock_condition)}",
        "Contacts unlock schemes, discounts, risks, and encounters.",
    ]


def render_messages(engine: GameEngine, width: int, max_lines: int, colors: Colors) -> None:
    lines = engine.state.messages[-max_lines:] or [engine.state.message]
    print("-" * width)
    for line in lines[-max_lines:]:
        if line.startswith("FEDERAL CLOCK") or "LOCKED" in line:
            print(colors.warning(trim(line, width)))
        else:
            print(trim(line, width))


def render_confirm(engine: GameEngine, width: int, colors: Colors) -> None:
    index = engine.state.menu.confirm_action_index
    action = engine.available_actions()[index or 0]
    print(colors.heading(action.name.upper()))
    print("-" * width)
    print(f"Cost: {compact_money(engine._action_cost(action))}")
    print(f"Expected Federal Clock change: +{action.clock_min} to +{action.clock_max}")
    if action.operation_turns:
        print(f"This begins a {action.operation_turns}-turn operation.")
    print()
    print("Proceed?")
    options = ("Yes", "No")
    for i, option in enumerate(options):
        print(menu_row(option, i == engine.state.menu.modal_selection, False, width, colors))
    footer(width, "↑↓ Choose  Enter Select  Esc Cancel")


def render_asset_confirm(engine: GameEngine, width: int, colors: Colors) -> None:
    assets = engine.state.assets
    index = engine.selected_index("Assets")
    if not assets or index >= len(assets):
        print("Asset not found.")
        return
    asset = assets[index]
    risk = engine.asset_write_off_risk(asset)
    print(colors.warning("WRITE OFF ASSET"))
    print("-" * width)
    print(trim(f"{asset.name} | Value {compact_money(asset.value)} | Upkeep {compact_money(asset.upkeep_cost)}/turn", width))
    print(f"This permanently removes the asset. Expected Federal Clock change: +{risk}.")
    print()
    for option_index, option in enumerate(("Yes, write it off", "No")):
        print(menu_row(option, option_index == engine.state.menu.modal_selection, False, width, colors))
    footer(width, "↑↓ Choose  Enter Select  Esc Cancel")


def render_task_menu(engine: GameEngine, width: int, colors: Colors) -> None:
    employee = engine.state.employee(engine.state.menu.employee_task_key)
    if employee is None:
        print("Employee not found.")
        return
    print(colors.heading(f"ASSIGN {employee.name.upper()}"))
    print("-" * width)
    tasks = TASKS[employee.key]
    for index, task in enumerate(tasks):
        chance = engine._task_chance(employee, task)
        line = f"{task.name:<38} {task.turns} turns  {compact_money(task.cost):<8} {chance}%"
        print(menu_row(line, index == engine.state.menu.modal_selection, False, width, colors))
    print("-" * width)
    task = tasks[engine.state.menu.modal_selection]
    print(trim(task.description, width))
    print(trim(f"Clock on success {task.clock_success:+}; failure +{task.clock_failure}", width))
    footer(width, "↑↓ Move  Enter Assign  Esc Back")


def render_evidence_action(engine: GameEngine, width: int, colors: Colors) -> None:
    options = engine.evidence_options()
    index = engine.state.menu.evidence_index or 0
    item = engine.state.evidence[index] if engine.state.evidence else None
    print(colors.heading("EVIDENCE RESPONSE"))
    print("-" * width)
    if item:
        print(trim(f"{item.name} | {item.label} {item.strength}/10 | {item.category.value}", width))
    if not options:
        print("No employee can act on this evidence right now.")
    for option_index, (_, text, cost) in enumerate(options):
        print(menu_row(f"{text:<48} {compact_money(cost)}", option_index == engine.state.menu.modal_selection, False, width, colors))
    footer(width, "↑↓ Move  Enter Select  Esc Back")


def render_legal_request(engine: GameEngine, width: int, colors: Colors) -> None:
    request = engine.state.pending_request
    assert request is not None
    print(colors.danger("IRS REQUEST FOR INFORMATION"))
    print("-" * width)
    print(trim(request.description, width))
    print()
    options = engine.legal_response_options()
    for index, option in enumerate(options):
        print(menu_row(f"{option.text:<48} {compact_money(option.cost)}  Clock {option.clock_change:+}", index == engine.state.menu.modal_selection, False, width, colors))
    if engine.state.settings.sound_enabled:
        print("\a", end="")
    footer(width, "↑↓ Move  Enter Select  Q Quit")


def render_encounter(engine: GameEngine, width: int, colors: Colors) -> None:
    encounter = engine.state.pending_encounter
    assert encounter is not None
    print(colors.warning(encounter.title))
    print("-" * width)
    for line in wrap(encounter.description, width, 2):
        print(line)
    print()
    for index, option in enumerate(encounter.options):
        locked = engine._requirement_reason(option.requirement)
        status = "LOCKED" if locked else compact_money(option.cost)
        line = f"{option.text:<48} {status:<10} Clock {option.clock_change:+}"
        print(menu_row(line, index == engine.state.menu.modal_selection, locked is not None, width, colors))
    selected = encounter.options[engine.state.menu.modal_selection]
    print("-" * width)
    print(trim(selected.description or "Choose how to make this worse in a useful direction.", width))
    if engine.state.settings.sound_enabled:
        print("\a", end="")
    footer(width, "↑↓ Move  Enter Select  Q Quit")


def render_settings(engine: GameEngine, width: int, colors: Colors) -> None:
    settings = engine.state.settings
    print(colors.heading("SETTINGS"))
    print("-" * width)
    rows = (
        ("Color", settings.color_enabled),
        ("Animation", settings.animation_enabled),
        ("Sound", settings.sound_enabled),
    )
    for index, (name, enabled) in enumerate(rows):
        print(menu_row(f"{name:<16} {'on' if enabled else 'off'}", index == engine.state.menu.modal_selection, False, width, colors))
    footer(width, "↑↓ Move  Enter Toggle  Esc Back")


def render_load_confirm(engine: GameEngine, width: int, colors: Colors) -> None:
    print(colors.heading("LOAD GAME"))
    print("-" * width)
    print("Load the saved game if it exists?")
    print()
    for index, option in enumerate(("Yes", "No")):
        print(menu_row(option, index == engine.state.menu.modal_selection, False, width, colors))
    footer(width, "↑↓ Choose  Enter Select  Esc Cancel")


def render_help(engine: GameEngine, width: int, colors: Colors) -> None:
    print(colors.heading("HELP"))
    print("-" * width)
    lines = (
        "Up/Down move the current selection. Left/Right changes tabs.",
        "Enter selects. Escape closes detail screens or menus.",
        "S saves immediately. L opens load confirmation. Q quits.",
        "The Federal Clock is the single loss countdown: 0 quiet, 50 targeted, 90 final warning, 100 game over.",
        "Informational navigation does not advance turns. Spending, assignments, evidence responses, legal responses, and encounters do.",
    )
    for line in lines:
        for wrapped in wrap(line, width, 2):
            print(wrapped)
    footer(width, "Enter/Esc Back")


def footer(width: int, text: str = "↑↓ Move  ←→ Tabs  Enter Select  S Save  L Load  H Help  Q Quit") -> None:
    print("-" * width)
    print(trim(text, width))


def requirement_text(req: Requirement) -> str:
    parts = []
    if req.reputation:
        parts.append(f"reputation {req.reputation}")
    if req.employee:
        parts.append(f"employee {req.employee}")
    if req.flag:
        parts.append(f"completed {req.flag}")
    if req.contact:
        parts.append(f"contact {req.contact}")
    return ", ".join(parts) if parts else "None"


def evidence_actions(category: EvidenceCategory) -> str:
    actions = ["Saul can challenge legally"]
    if category is EvidenceCategory.FINANCIAL:
        actions.append("Gary can fabricate matching records")
    if category is EvidenceCategory.DIGITAL:
        actions.append("NullPointer can attack it")
    if category is EvidenceCategory.PUBLIC:
        actions.append("Saul can handle media response")
    return "; ".join(actions)


def wrap_lines(lines: list[str], width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(wrap(line, width, 2))
    return wrapped


def wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=max(20, width), break_long_words=False, break_on_hyphens=False)
    return lines[:max_lines] if lines else [""]


def render_game_over(engine: GameEngine) -> None:
    clear_screen()
    width = max(60, min(shutil.get_terminal_size(fallback=(100, 35)).columns, 100))
    colors = Colors(engine.state.settings.color_enabled)
    if engine.state.status is GameStatus.WON:
        title = colors.good("WRITE-OFF COMPLETE")
        reason = "Victory condition achieved: total wealth reached $0."
    else:
        title = colors.danger("FEDERAL INTERVENTION")
        reason = "Loss condition reached: the Federal Clock reached 100."
    print("=" * width)
    print(title)
    print("=" * width)
    print(trim(engine.state.ending or "The operation has concluded.", width))
    print()
    print(f"Final cash:        {compact_money(engine.state.cash)}")
    print(f"Final assets:      {compact_money(engine.state.asset_value)}")
    print(f"Final total wealth:{compact_money(engine.state.total_wealth)}")
    print(f"Federal Clock:     {engine.state.federal_clock}/100 {engine.state.pressure_label}")
    print(f"Reputation:        {engine.state.reputation}")
    print(f"Total turns:       {engine.state.turn_count}")
    print(f"Difficulty:        {engine.state.difficulty.upper() or 'UNKNOWN'}")
    print(f"Background:        {engine.state.background.upper() or 'UNKNOWN'}")
    print(trim(f"Ending reason: {reason}", width))
    print(f"Score:             {engine.state.score:,}")
    print(f"High score:        {engine.state.high_score:,}")
    if engine.state.new_high_score:
        print(colors.reputation("NEW HIGH SCORE"))
    print()
    for index, option in enumerate(("Play Again", "Quit")):
        print(menu_row(option, index == engine.state.menu.result_selection, False, width, colors))
    footer(width, "↑↓ Move  Enter Select  Q Quit")
