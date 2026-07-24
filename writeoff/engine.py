import random
import time

from writeoff.colors import should_enable_color
from writeoff.content import ACTIONS, BACKGROUNDS, CONTACT_TEMPLATES, DIFFICULTIES, ENCOUNTERS, TASKS
from writeoff.highscores import record_score
from writeoff.models import (
    Action,
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
    Operation,
    Requirement,
    Task,
)
from writeoff.save import SAVE_PATH, load_game, save_game
from writeoff.terminal_input import DOWN, ENTER, ESCAPE, HELP, LEFT, LOAD, QUIT, RIGHT, SAVE, TAB, UP, Key


EMPLOYEE_NAMES = {
    "gary": ("Gary Ledger", "Questionable Accountant", 35_000),
    "saul": ("Saul Fineprint", "Tax Attorney", 90_000),
    "nullpointer": ("NullPointer", "Cyber Consultant", 75_000),
}

TRAITS = {
    "gary": ("Meticulous", "Nervous", "Creative", "Greedy"),
    "saul": ("Aggressive", "Patient", "Media-savvy", "Expensive"),
    "nullpointer": ("Reckless", "Paranoid", "Brilliant", "Unreliable"),
}


class GameEngine:
    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self.state = GameState()
        self.state.settings.color_enabled = should_enable_color()
        self.state.contacts = [Contact(**vars(contact)) for contact in CONTACT_TEMPLATES]

    def available_actions(self) -> tuple[Action, ...]:
        return ACTIONS

    def process_key(self, key: Key) -> None:
        if key.name == QUIT:
            self.state.status = GameStatus.QUIT
            self.state.add_message("You abandoned the operation.")
            return
        if key.name == SAVE and self.state.status is GameStatus.RUNNING:
            self.save()
            return
        if key.name == LOAD and self.state.status is GameStatus.RUNNING:
            self.open_load_confirmation()
            return
        if key.name == HELP:
            self.state.view = "help"
            return

        if self.state.status is GameStatus.SETUP:
            self._process_setup_key(key)
        elif self.state.view == "help":
            self._close_on_escape_or_enter(key)
        elif self.state.view == "settings":
            self._process_settings_key(key)
        elif self.state.view == "confirm":
            self._process_confirm_key(key)
        elif self.state.view == "asset_confirm":
            self._process_asset_confirm_key(key)
        elif self.state.view == "task":
            self._process_task_key(key)
        elif self.state.view == "evidence_action":
            self._process_evidence_action_key(key)
        elif self.state.view == "load_confirm":
            self._process_load_confirm_key(key)
        elif self.state.pending_request is not None:
            self._process_legal_key(key)
        elif self.state.pending_encounter is not None:
            self._process_encounter_key(key)
        else:
            self._process_normal_key(key)

    def _process_setup_key(self, key: Key) -> None:
        options = list(DIFFICULTIES) if self.state.setup_step == "difficulty" else list(BACKGROUNDS)
        if key.name == UP:
            self.state.menu.setup_selection = (self.state.menu.setup_selection - 1) % len(options)
        elif key.name == DOWN:
            self.state.menu.setup_selection = (self.state.menu.setup_selection + 1) % len(options)
        elif key.name == ENTER:
            selected = options[self.state.menu.setup_selection]
            if self.state.setup_step == "difficulty":
                self._apply_difficulty(selected)
                self.state.setup_step = "background"
                self.state.menu.setup_selection = 0
                self.state.add_message("Choose a background.")
            else:
                self._apply_background(selected)
                self.state.status = GameStatus.RUNNING
                self._check_unlocks([])
                self._check_achievements()

    def _apply_difficulty(self, key: str) -> None:
        data = DIFFICULTIES[key]
        self.state.difficulty = key
        self.state.federal_clock = data["clock_start"]

    def _apply_background(self, key: str) -> None:
        data = BACKGROUNDS[key]
        self.state.background = key
        self.state.cash = data["cash"]
        self.state.starting_wealth = data["cash"]
        self.state.public_attention += data.get("attention", 0)
        self.state.fbi_progress += data.get("fbi", 0)
        self.state.flags.update(data.get("flags", set()))
        self._change_federal_clock(data.get("clock", 0), "Starting background profile")
        if data.get("employee"):
            self._hire_employee(data["employee"], announce=False)
        self.state.messages = []
        self.state.add_message(f"{data['name']}: {data['message']}")
        self.state.clamp()

    def _process_normal_key(self, key: Key) -> None:
        if key.name in {LEFT, RIGHT, TAB}:
            direction = 1 if key.name in {RIGHT, TAB} else -1
            self.state.menu.tab_index = (self.state.menu.tab_index + direction) % len(self.state.menu.tabs)
            return
        tab = self.current_tab()
        count = len(self.items_for_tab(tab))
        if count == 0:
            if key.name == ENTER and tab == "Settings":
                self.state.view = "settings"
            return
        if key.name == UP:
            self._move_selection(tab, -1, count)
        elif key.name == DOWN:
            self._move_selection(tab, 1, count)
        elif key.name == ENTER:
            self._activate_current_selection()

    def _move_selection(self, tab: str, amount: int, count: int) -> None:
        self.state.menu.selections[tab] = (self.state.menu.selections.get(tab, 0) + amount) % count

    def _activate_current_selection(self) -> None:
        tab = self.current_tab()
        index = self.selected_index(tab)
        if tab == "Actions":
            self.activate_action(index)
        elif tab == "Employees":
            if self.state.employees:
                employee = self.state.employees[index]
                if employee.busy:
                    task = employee.assigned_task
                    assert task is not None
                    self.state.add_message(f"{employee.name} is busy: {task.task_name} ({task.turns_remaining} turns).")
                else:
                    self.state.view = "task"
                    self.state.menu.employee_task_key = employee.key
                    self.state.menu.modal_selection = 0
        elif tab == "Evidence":
            if self.state.evidence:
                self.state.view = "evidence_action"
                self.state.menu.evidence_index = index
                self.state.menu.modal_selection = 0
        elif tab == "Assets":
            if self.state.assets:
                self.state.view = "asset_confirm"
                self.state.menu.modal_selection = 1
        elif tab == "Operations":
            if self.state.operations:
                self.state.add_message("Operation support is handled through employee assignments.")
        elif tab == "Contacts":
            self.state.add_message("Contacts change through schemes and encounters.")
        elif tab == "Settings":
            self.state.view = "settings"

    def current_tab(self) -> str:
        return self.state.menu.tabs[self.state.menu.tab_index]

    def selected_index(self, tab: str) -> int:
        count = max(1, len(self.items_for_tab(tab)))
        value = self.state.menu.selections.get(tab, 0)
        value = max(0, min(count - 1, value))
        self.state.menu.selections[tab] = value
        return value

    def items_for_tab(self, tab: str) -> list[object]:
        if tab == "Actions":
            return list(ACTIONS)
        if tab == "Employees":
            return list(self.state.employees)
        if tab == "Evidence":
            return list(self.state.evidence)
        if tab == "Assets":
            return list(self.state.assets)
        if tab == "Operations":
            return list(self.state.operations)
        if tab == "Contacts":
            return list(self.state.contacts)
        if tab == "Settings":
            return [self.state.settings]
        return []

    def activate_action(self, index: int) -> None:
        action = ACTIONS[index]
        reason = self.action_lock_reason(action)
        if reason:
            self.state.add_message(f"LOCKED: {reason}.")
            return
        if action.confirmation_required:
            self.state.view = "confirm"
            self.state.menu.confirm_action_index = index
            self.state.menu.modal_selection = 1
            return
        self.perform_action(index)

    def _process_confirm_key(self, key: Key) -> None:
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name in {UP, DOWN, LEFT, RIGHT}:
            self.state.menu.modal_selection = 1 - self.state.menu.modal_selection
        elif key.name == ENTER:
            if self.state.menu.modal_selection == 0 and self.state.menu.confirm_action_index is not None:
                index = self.state.menu.confirm_action_index
                self._close_modal()
                self.perform_action(index)
            else:
                self._close_modal()

    def _process_asset_confirm_key(self, key: Key) -> None:
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name in {UP, DOWN, LEFT, RIGHT}:
            self.state.menu.modal_selection = 1 - self.state.menu.modal_selection
        elif key.name == ENTER:
            if self.state.menu.modal_selection == 0:
                asset_index = self.selected_index("Assets")
                self._close_modal()
                self.write_off_asset(asset_index)
            else:
                self._close_modal()

    def asset_write_off_risk(self, asset) -> int:
        return min(8, max(1, 1 + asset.value // 500_000))

    def write_off_asset(self, index: int) -> None:
        if not 0 <= index < len(self.state.assets):
            self.state.add_message("That asset is no longer available.")
            return
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {employee.key for employee in self.state.employees if employee.busy}
        asset = self.state.assets.pop(index)
        risk = self.asset_write_off_risk(asset)
        self.state.public_attention += max(0, risk - 2)
        self._change_federal_clock(risk, f"Writing off {asset.name}")
        self.state.add_message(
            f"ASSET WRITTEN OFF: {asset.name} ({asset.value:,}) disappears into a very final expense report."
        )
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def perform_action(self, index: int) -> None:
        action = ACTIONS[index]
        reason = self.action_lock_reason(action)
        if reason:
            self.state.add_message(f"LOCKED: {reason}.")
            return
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {employee.key for employee in self.state.employees if employee.busy}
        self.state.cash -= self._action_cost(action)
        self.state.reputation += action.reputation_gain
        handlers = {
            "dinner": self._act_dinner,
            "casino": self._act_casino,
            "accountant": lambda item: self._hire_employee("gary"),
            "startup": self._act_startup,
            "attorney": lambda item: self._hire_employee("saul"),
            "fake_business": self._act_fake_business,
            "art": self._act_art,
            "movie": self._act_movie,
            "charity": self._act_charity,
            "sports": self._act_sports,
            "campaign": self._act_campaign,
            "crypto_token": self._act_crypto,
            "consultant": self._act_consultant,
            "celebrity_party": self._act_party,
            "hacker": lambda item: self._hire_employee("nullpointer"),
            "offshore_trust": self._act_offshore_trust,
            "shell_company": self._act_shell_company,
            "real_estate": self._act_real_estate,
            "yacht": self._act_yacht,
            "island": self._act_island,
        }
        handlers[action.key](action)
        clock_change = self.random.randint(action.clock_min, action.clock_max)
        self._change_federal_clock(clock_change, f"{action.name} risk")
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def action_lock_reason(self, action: Action) -> str | None:
        req = action.requirement
        if self.state.reputation < req.reputation:
            return f"Requires reputation {req.reputation}"
        if req.employee and not self.state.has_employee(req.employee):
            return f"Requires employee: {req.employee}"
        if req.flag and req.flag not in self.state.flags:
            return f"Requires completed operation: {req.flag}"
        if req.contact:
            contact = self.state.contact(req.contact)
            if contact is None or contact.status not in {"available", "trusted"}:
                return f"Requires contact: {req.contact}"
        if self._action_cost(action) > self.state.cash:
            return "Not enough cash"
        employee_key = {"accountant": "gary", "attorney": "saul", "hacker": "nullpointer"}.get(action.key)
        if employee_key and self.state.has_employee(employee_key):
            return "Already hired"
        if action.operation_turns and (action.key in self.state.flags or any(operation.key == action.key for operation in self.state.operations)):
            return "Operation already active or completed"
        return None

    def _action_cost(self, action: Action) -> int:
        cost = action.cost
        if self.state.background == "contractor" and action.path == "legal":
            cost = int(cost * 0.85)
        if "consultant_discount" in self.state.flags and action.key == "consultant":
            cost = int(cost * 0.75)
        return cost

    def _process_task_key(self, key: Key) -> None:
        employee = self.state.employee(self.state.menu.employee_task_key)
        if employee is None:
            self._close_modal()
            return
        tasks = TASKS[employee.key]
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name == UP:
            self.state.menu.modal_selection = (self.state.menu.modal_selection - 1) % len(tasks)
        elif key.name == DOWN:
            self.state.menu.modal_selection = (self.state.menu.modal_selection + 1) % len(tasks)
        elif key.name == ENTER:
            self.assign_task(employee, tasks[self.state.menu.modal_selection])

    def assign_task(self, employee: Employee, task: Task) -> None:
        if employee.busy:
            self.state.add_message(f"{employee.name} is already busy.")
            self._close_modal()
            return
        if task.cost > self.state.cash:
            self.state.add_message("You cannot afford that assignment.")
            self._close_modal()
            return
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {staff.key for staff in self.state.employees if staff.busy}
        target = None
        if task.target_category is not None and self.state.evidence:
            target_item = self._target_evidence(None, task.target_category)
            if target_item:
                target = self.state.evidence.index(target_item)
        employee.assigned_task = Assignment(task.key, task.name, task.turns, target)
        self.state.add_message(f"{employee.name} starts: {task.name} ({task.turns} turns).")
        self._close_modal()
        self._change_federal_clock(1, "Assignment coordination")
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def _process_evidence_action_key(self, key: Key) -> None:
        options = self.evidence_options()
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name == UP and options:
            self.state.menu.modal_selection = (self.state.menu.modal_selection - 1) % len(options)
        elif key.name == DOWN and options:
            self.state.menu.modal_selection = (self.state.menu.modal_selection + 1) % len(options)
        elif key.name == ENTER and options:
            self.perform_evidence_option(options[self.state.menu.modal_selection][0])

    def evidence_options(self) -> list[tuple[str, str, int]]:
        index = self.state.menu.evidence_index
        if index is None or not 0 <= index < len(self.state.evidence):
            return []
        item = self.state.evidence[index]
        options = []
        if self.state.has_employee("saul"):
            options.append(("saul", "Have Saul challenge it", 80_000))
        if item.category is EvidenceCategory.FINANCIAL and self.state.has_employee("gary"):
            options.append(("gary", "Have Gary fabricate matching records", 45_000))
        if item.category is EvidenceCategory.DIGITAL and self.state.has_employee("nullpointer"):
            options.append(("nullpointer", "Have NullPointer attack it", 90_000))
        return options

    def perform_evidence_option(self, key: str) -> None:
        options = dict((item[0], item[2]) for item in self.evidence_options())
        cost = options.get(key)
        if cost is None:
            self.state.add_message("No available response for that evidence.")
            self._close_modal()
            return
        if cost > self.state.cash:
            self.state.add_message("You cannot afford that evidence response.")
            self._close_modal()
            return
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {employee.key for employee in self.state.employees if employee.busy}
        self.state.cash -= cost
        amount = {"saul": 3, "gary": 4, "nullpointer": 5}[key]
        item = self.state.evidence[self.state.menu.evidence_index or 0]
        self._weaken_evidence(item.name, amount)
        self._change_federal_clock(-amount, "Evidence weakened")
        self.state.add_message(f"Evidence response weakens {item.name}.")
        self._close_modal()
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def legal_response_options(self) -> list[EncounterOption]:
        options = []
        if self.state.has_employee("saul"):
            options.append(EncounterOption("attorney", "Transfer to Saul Fineprint", 45_000, clock_change=-6))
        options.append(EncounterOption("documents", "Send 4,000 irrelevant pages", 20_000, clock_change=-2))
        if self.state.has_employee("gary"):
            options.append(EncounterOption("accountant", "Have Gary create matching paperwork", 35_000, clock_change=-4))
        options.append(EncounterOption("ignore", "Ignore the request", 0, clock_change=10))
        return options

    def _process_legal_key(self, key: Key) -> None:
        options = self.legal_response_options()
        if key.name == UP:
            self.state.menu.modal_selection = (self.state.menu.modal_selection - 1) % len(options)
        elif key.name == DOWN:
            self.state.menu.modal_selection = (self.state.menu.modal_selection + 1) % len(options)
        elif key.name == ENTER:
            self.resolve_legal_response(options[self.state.menu.modal_selection])

    def resolve_legal_response(self, option: EncounterOption) -> None:
        request = self.state.pending_request
        if request is None:
            return
        if option.cost > self.state.cash:
            self.state.add_message("You cannot afford that response.")
            return
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {employee.key for employee in self.state.employees if employee.busy}
        self.state.cash -= option.cost
        if option.key == "ignore":
            self.state.ignored_requests += 1
            self._change_federal_clock(10 + request.severity, "Ignored federal request")
            result = "Ignoring the request goes badly."
        else:
            self._weaken_evidence(request.evidence_name, 2 if option.key != "accountant" else 3)
            self._change_federal_clock(option.clock_change + DIFFICULTIES[self.state.difficulty]["legal"], option.text)
            result = f"{option.text} buys time."
        self.state.pending_request = None
        self.state.menu.modal_selection = 0
        self.state.add_message(result)
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def _process_encounter_key(self, key: Key) -> None:
        encounter = self.state.pending_encounter
        if encounter is None:
            return
        options = encounter.options
        if key.name == UP:
            self.state.menu.modal_selection = (self.state.menu.modal_selection - 1) % len(options)
        elif key.name == DOWN:
            self.state.menu.modal_selection = (self.state.menu.modal_selection + 1) % len(options)
        elif key.name == ENTER:
            option = options[self.state.menu.modal_selection]
            if self._requirement_reason(option.requirement):
                self.state.add_message("That option is unavailable.")
                return
            if option.cost > self.state.cash:
                self.state.add_message("You cannot afford that option.")
                return
            self.resolve_encounter_option(encounter, option)

    def resolve_encounter_option(self, encounter: Encounter, option: EncounterOption) -> None:
        active_operations = {operation.key for operation in self.state.operations}
        active_assignments = {employee.key for employee in self.state.employees if employee.busy}
        self.state.cash -= option.cost
        result = self._resolve_encounter(encounter, option)
        self._change_federal_clock(option.clock_change, f"{encounter.title}: {option.text}")
        self.state.pending_encounter = None
        self.state.menu.modal_selection = 0
        self.state.add_message(result)
        self._resolve_meaningful_turn(active_operations, active_assignments)

    def _process_settings_key(self, key: Key) -> None:
        fields = ("color_enabled", "animation_enabled", "sound_enabled")
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name == UP:
            self.state.menu.modal_selection = (self.state.menu.modal_selection - 1) % len(fields)
        elif key.name == DOWN:
            self.state.menu.modal_selection = (self.state.menu.modal_selection + 1) % len(fields)
        elif key.name == ENTER:
            field = fields[self.state.menu.modal_selection]
            value = not getattr(self.state.settings, field)
            setattr(self.state.settings, field, value)
            self.state.add_message(f"{field.replace('_enabled', '').title()} {'on' if value else 'off'}.")

    def open_load_confirmation(self) -> None:
        self.state.view = "load_confirm"
        self.state.menu.modal_selection = 1

    def _process_load_confirm_key(self, key: Key) -> None:
        if key.name == ESCAPE:
            self._close_modal()
        elif key.name in {UP, DOWN, LEFT, RIGHT}:
            self.state.menu.modal_selection = 1 - self.state.menu.modal_selection
        elif key.name == ENTER:
            if self.state.menu.modal_selection == 0:
                self.load()
            else:
                self._close_modal()

    def save(self) -> None:
        try:
            save_game(self.state, self.random)
        except OSError as exc:
            self.state.add_message(f"Save failed: {exc}.")
        else:
            self.state.add_message(f"Saved to {SAVE_PATH}.")

    def load(self) -> None:
        try:
            self.state = load_game(self.random)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.state.add_message(f"Load failed: {exc}.")
        else:
            self.state.add_message("Save loaded.")

    def _close_on_escape_or_enter(self, key: Key) -> None:
        if key.name in {ESCAPE, ENTER}:
            self._close_modal()

    def _close_modal(self) -> None:
        self.state.view = "normal"
        self.state.menu.modal_selection = 0
        self.state.menu.confirm_action_index = None
        self.state.menu.employee_task_key = ""
        self.state.menu.evidence_index = None

    def _resolve_meaningful_turn(self, active_operations: set[str], active_assignments: set[str]) -> None:
        if self.state.status is not GameStatus.RUNNING:
            return
        self.state.turn_count += 1
        log: list[str] = []
        self._pay_upkeep(log)
        self._advance_operations(log, active_operations)
        self._advance_assignments(log, active_assignments)
        self._resolve_turn_pressure(log)
        self._employee_incidents(log)
        self._maybe_legal_request(log)
        self._maybe_encounter(log)
        self._random_event(log)
        self._check_unlocks(log)
        if log:
            self.state.add_message(self.state.message + "\n" + "\n".join(log))
        self._after_change()

    def _pay_upkeep(self, log: list[str]) -> None:
        expenses = min(self.state.upkeep_costs, self.state.cash)
        if expenses:
            self.state.cash -= expenses
            log.append(f"Upkeep consumed ${expenses:,}.")

    def _advance_operations(self, log: list[str], active_keys: set[str]) -> None:
        completed = []
        for operation in self.state.operations:
            if operation.key not in active_keys:
                continue
            operation.turns_remaining -= 1
            pressure = max(0, round(operation.clock_per_turn * (0.5 if operation.hidden else 1)))
            if pressure:
                self._change_federal_clock(pressure, f"{operation.name} active pressure")
            self.state.public_attention += operation.attention_per_turn
            if operation.turns_remaining <= 0:
                completed.append(operation)
                if operation.completion_flag:
                    self.state.flags.add(operation.completion_flag)
                self.state.cash += operation.completion_cash_change
                self.state.reputation += operation.completion_reputation
                log.append(f"OPERATION COMPLETE: {operation.completion_message}")
            else:
                log.append(f"{operation.name}: {operation.turns_remaining} turns remaining.")
        for operation in completed:
            self.state.operations.remove(operation)

    def _advance_assignments(self, log: list[str], active_keys: set[str]) -> None:
        for employee in self.state.employees:
            if employee.assigned_task is None:
                employee.stress = max(0, employee.stress - 1)
                continue
            if employee.key not in active_keys:
                continue
            assignment = employee.assigned_task
            assignment.turns_remaining -= 1
            employee.turns_on_task += 1
            if assignment.turns_remaining > 0:
                continue
            task = self._task_for(employee.key, assignment.task_key)
            assert task is not None
            self._finish_task(employee, task, assignment, log)
            employee.assigned_task = None
            employee.turns_on_task = 0

    def _resolve_turn_pressure(self, log: list[str]) -> None:
        evidence_pressure = sum(item.strength for item in self.state.evidence if not item.inadmissible) // 8
        attention_pressure = self.state.public_attention // 35
        diff = DIFFICULTIES[self.state.difficulty]["pressure"]
        pressure = max(0, evidence_pressure + attention_pressure + diff + self.state.federal_momentum)
        if "monitoring" in self.state.flags:
            pressure = max(0, pressure - 2)
            self.state.flags.remove("monitoring")
        if pressure:
            self._change_federal_clock(pressure, "Evidence and public attention pressure")
            log.append(f"Federal pressure adds +{pressure}.")

    def _change_federal_clock(self, amount: int, reason: str) -> None:
        if amount == 0:
            self.state.last_clock_change = 0
            self.state.last_clock_reason = reason
            return
        before = self.state.federal_clock
        self.state.federal_clock = max(0, min(100, self.state.federal_clock + amount))
        self.state.last_clock_change = self.state.federal_clock - before
        self.state.last_clock_reason = reason

    def _federal_clock_label(self) -> str:
        return self.state.pressure_label

    def _check_clock_end_condition(self) -> None:
        if self.state.federal_clock >= 100:
            if "gary_leaked" in self.state.flags:
                self.state.achievements.add("GARY DID IT")
                ending = "Gary's leak became the Federal Clock roadmap."
            elif any(operation.key == "island" for operation in self.state.operations):
                self.state.achievements.add("INTERNATIONAL INCIDENT")
                ending = "The island deal became an international incident."
            else:
                ending = "The Federal Clock reached its irreversible end state."
            self._finalize_result(GameStatus.LOST, ending)
            self.state.add_message(self.state.message + "\nFEDERAL CLOCK 100: the government reaches your wealth first.")

    def _act_dinner(self, action: Action) -> None:
        self.state.public_attention += 1
        self.state.add_message(f"You wasted ${self._action_cost(action):,} on a dinner nobody enjoyed.")

    def _act_casino(self, action: Action) -> None:
        roll = self.random.random()
        if roll < 0.62 + self._odds_bonus():
            self.state.add_message(f"You lost ${self._action_cost(action):,}. Exactly as planned.")
        elif roll < 0.91:
            self.state.cash += 150_000
            self.state.add_message("You won $150,000. The casino has betrayed you.")
        else:
            self.state.cash += 800_000
            self.state.public_attention += 8
            self._add_evidence("Televised casino jackpot", 4, "Public broadcast", "IRS", EvidenceCategory.PUBLIC)
            self._relationship("victor", 8)
            self.state.add_message("You won $800,000 on live television. Disaster.")

    def _act_startup(self, action: Action) -> None:
        roll = self.random.random()
        if roll < 0.65 + self._odds_bonus():
            self.state.add_message("The AI toaster startup fails immediately. Excellent.")
        elif roll < 0.92:
            self.state.cash += 300_000
            self.state.add_message("The founders return $300,000. Mildly inconvenient.")
        else:
            self.state.cash += 2_000_000
            self.state.public_attention += 10
            self.state.terrible_successes += 1
            self.state.add_message("The startup succeeds and pays $2,000,000. Catastrophic.")

    def _act_fake_business(self, action: Action) -> None:
        self._start_operation("fake_business", "Create Fake Consulting Firm", 3, 40_000, 3, 0, "fake_business", "The fake consulting firm is operational.", 0, 5)
        self._add_evidence("Incoherent consulting invoices", 3, "Gary's printer", "IRS", EvidenceCategory.FINANCIAL)
        self.state.add_message("Gary begins creating a consulting company with no clients.")

    def _act_art(self, action: Action) -> None:
        roll = self.random.random()
        if roll < 0.35 + self._odds_bonus():
            value, result = 25_000, "The artwork is exposed as a forgery. Excellent."
        elif roll < 0.85:
            value, result = 400_000, "The artwork retains most of its value. Annoying."
        else:
            value, result = 950_000, "Critics call it revolutionary. Its value nearly doubles."
        self.state.assets.append(Asset("Suspicious Modern Artwork", value, 5_000))
        self._add_evidence("Undocumented artwork purchase", 3, "Gallery records", "IRS", EvidenceCategory.PROPERTY)
        self.state.add_message(result)

    def _act_movie(self, action: Action) -> None:
        if self.random.random() < 0.78 + self._odds_bonus():
            self.state.add_message("The movie opens in two theaters and one apologizes.")
        else:
            self.state.cash += 1_600_000
            self.state.public_attention += 12
            self.state.terrible_successes += 1
            self.state.add_message("The terrible movie becomes a cult hit. Catastrophic success.")
        self._add_evidence("Questionable film financing", 3, "Entertainment press", "IRS", EvidenceCategory.PUBLIC)

    def _act_charity(self, action: Action) -> None:
        self.state.public_attention += 5
        self._unlock_contact("mira", "NEW CONTACT\nMira Vale has questions.")
        self._add_evidence("Vanity charity gala invoices", 4, "Catering dispute", "IRS", EvidenceCategory.PUBLIC)
        self.state.add_message("The charity spends most of its budget on logo strategy.")

    def _act_sports(self, action: Action) -> None:
        if self.random.random() < 0.70 + self._odds_bonus():
            self.state.assets.append(Asset("Failing sports-team stake", 350_000, 80_000))
            self.state.add_message("The team loses, the fans chant your name incorrectly, and cash burns.")
        else:
            self.state.assets.append(Asset("Suddenly valuable sports stake", 2_200_000, 60_000))
            self.state.terrible_successes += 1
            self.state.add_message("The team makes the playoffs. Financially horrifying.")
        self.state.public_attention += 8

    def _act_campaign(self, action: Action) -> None:
        self._start_operation("campaign", "Doomed Political Campaign", 3, 180_000, 4, 5, None, "The campaign ends behind the decorative plant.", -300_000, 5)
        self._add_evidence("Campaign vendor testimony", 4, "Former staffer", "FBI", EvidenceCategory.WITNESS)
        self.state.add_message("Consultants begin buying ads in districts you are not running in.")

    def _act_crypto(self, action: Action) -> None:
        fail_chance = 0.72 + self._odds_bonus() + (0.10 if "crypto_bonus" in self.state.flags else 0)
        if self.random.random() < fail_chance:
            self.state.add_message("The token collapses after the mascot account loses its password.")
        else:
            self.state.cash += 1_400_000
            self.state.public_attention += 15
            self.state.terrible_successes += 1
            self.state.add_message("The token moons because nobody read the whitepaper.")
        self._add_evidence("Suspicious token deployer wallet", 5, "Blockchain analytics", "FBI", EvidenceCategory.DIGITAL)

    def _act_consultant(self, action: Action) -> None:
        self._unlock_contact("broker", "NEW CONTACT\nThe Broker heard you enjoy bad deals.")
        self.state.add_message("The consultant invoices $350K for a deck titled 'Spend Architecture'.")

    def _act_party(self, action: Action) -> None:
        self.state.public_attention += 14
        self._add_evidence("Celebrity disaster party footage", 5, "Livestream", "IRS", EvidenceCategory.PUBLIC)
        self._unlock_contact("victor", "NEW CONTACT\nVictor Glass offers quieter rooms.")
        self.state.add_message("The party loses money, dignity, and three ice sculptures.")

    def _act_offshore_trust(self, action: Action) -> None:
        self._start_operation("offshore_trust", "Create Offshore Trust", 3, 120_000, 4, 0, "offshore_trust", "The offshore trust is ready.", 0, 6)
        self._add_evidence("Offshore trust paperwork", 5, "Bank compliance desk", "IRS", EvidenceCategory.FINANCIAL)
        self.state.add_message("An offshore trust begins forming under a beach umbrella.")

    def _act_shell_company(self, action: Action) -> None:
        self._start_operation("shell_company", "Create Offshore Shell Company", 4, 100_000, 4, 0, "shell_company", "The offshore shell company is active.", 0, 8)
        self._add_evidence("Shell-company beneficial ownership trail", 5, "Registrar leak", "IRS", EvidenceCategory.FINANCIAL)
        self.state.add_message("The offshore shell-company operation begins.")

    def _act_real_estate(self, action: Action) -> None:
        self._start_operation("real_estate", "Doomed Real-Estate Project", 4, 220_000, 4, 1, None, "The wetlands win in court.", -500_000, 8)
        self._add_evidence("Wetlands project records", 5, "County permits", "IRS", EvidenceCategory.PROPERTY)
        self.state.add_message("Architects start drawing condos that float only in theory.")

    def _act_yacht(self, action: Action) -> None:
        self.state.assets.append(Asset("Structurally Questionable Yacht", 1_250_000, 160_000))
        self.state.public_attention += 8
        self._add_evidence("Luxury yacht purchase", 5, "Maritime registry", "IRS", EvidenceCategory.PROPERTY)
        self.state.add_message("The yacht immediately starts leaking seawater and money.")

    def _act_island(self, action: Action) -> None:
        self._start_operation("island", "Purchase Private Island", 5, 250_000, 7, 3, "island", "The island purchase completes.", -1_500_000, 15)
        self._add_evidence("International island transaction", 8, "Bank transfer", "FBI", EvidenceCategory.FINANCIAL)
        self.state.add_message("The private island purchase enters escrow.")

    def _hire_employee(self, key: str, announce: bool = True) -> None:
        if self.state.has_employee(key):
            return
        name, role, upkeep_cost = EMPLOYEE_NAMES[key]
        trait = self.random.choice(TRAITS[key])
        competence = self.random.randint(48, 78)
        loyalty = self.random.randint(42, 78)
        stress = self.random.randint(8, 28)
        if trait in {"Meticulous", "Patient", "Brilliant"}:
            competence += 10
        if trait in {"Greedy", "Expensive"}:
            upkeep_cost = int(upkeep_cost * 1.25)
            loyalty -= 8
        if trait in {"Nervous", "Unreliable", "Reckless"}:
            stress += 8
        self.state.employees.append(Employee(key, name, role, upkeep_cost, competence, loyalty, stress, [trait]))
        self._unlock_contact(key, "")
        if key == "nullpointer":
            self.fbi_progress_add(5)
            self._add_evidence("Contact with intrusion broker", 4, "FBI surveillance", "FBI", EvidenceCategory.DIGITAL)
        if announce:
            self.state.add_message(f"{name} joins the payroll. Trait: {trait}.")

    def fbi_progress_add(self, amount: int) -> None:
        self.state.fbi_progress += amount

    def _start_operation(self, key: str, name: str, turns: int, upkeep: int, clock: int, attention: int, flag: str | None, message: str, cash: int, rep: int) -> None:
        self.state.operations.append(Operation(key, name, turns, upkeep, clock, attention, flag, message, cash, rep))

    def _finish_task(self, employee: Employee, task: Task, assignment: Assignment, log: list[str]) -> None:
        employee.stress += task.stress_change
        if task.cost:
            self.state.cash -= min(task.cost, self.state.cash)
        chance = self._task_chance(employee, task)
        success = self.random.randint(1, 100) <= chance
        if not success:
            self._task_failure(employee, task, log)
            self._change_federal_clock(task.clock_failure, f"{employee.name} assignment failed")
            return
        self._change_federal_clock(task.clock_success, f"{employee.name}: {task.name}")
        if task.key in {"clean_books", "delay_feds"}:
            log.append(f"{employee.name} slows the Federal Clock.")
        elif task.key in {"records", "challenge", "digital_attack"}:
            self._task_hit_evidence(employee, task, assignment, log)
        elif task.key == "business_docs":
            self.state.flags.add("business_docs")
            log.append("Gary's fake business documents look almost intentional.")
        elif task.key == "refunds":
            refund = self.random.randint(80_000, 260_000)
            self.state.cash += refund
            log.append(f"Gary finds a ${refund:,} refund. Bad news.")
        elif task.key == "legal_structure":
            for operation in self.state.operations:
                operation.clock_per_turn = max(0, operation.clock_per_turn - 1)
            log.append("Saul makes active operations slightly less obvious.")
        elif task.key == "media":
            self.state.public_attention -= 12
            log.append("Saul turns a headline into a correction nobody reads.")
        elif task.key == "disrupt_feds":
            log.append("NullPointer disrupts a federal queue.")
        elif task.key == "hide_operation":
            if self.state.operations:
                self.random.choice(self.state.operations).hidden = True
                log.append("NullPointer hides one active operation.")
        elif task.key == "monitor":
            self.state.flags.add("monitoring")
            log.append("NullPointer monitors investigators for the next turn.")
        else:
            log.append(f"{employee.name} takes a turn off.")

    def _task_failure(self, employee: Employee, task: Task, log: list[str]) -> None:
        employee.loyalty -= 3
        employee.stress += 8
        if employee.key == "nullpointer":
            self.state.nullpointer_net_harm += task.clock_failure
            self._add_evidence("Botched cyber cleanup", 4, "Server logs", "FBI", EvidenceCategory.DIGITAL)
        else:
            self._add_evidence(f"{employee.name} task mistake", 3, "Staff error", "IRS", EvidenceCategory.WITNESS)
        log.append(f"{employee.name}'s assignment fails and creates new risk.")

    def _task_hit_evidence(self, employee: Employee, task: Task, assignment: Assignment, log: list[str]) -> None:
        item = self._target_evidence(assignment.target_evidence, task.target_category)
        if item is None:
            log.append(f"{employee.name} finds no useful evidence target.")
            return
        amount = 3
        if employee.key == "gary" and item.category is EvidenceCategory.FINANCIAL:
            amount += 2
        if employee.key == "nullpointer" and item.category is EvidenceCategory.DIGITAL:
            amount += 3
        if employee.key == "saul" and self.random.random() < 0.25:
            item.inadmissible = True
            log.append(f"Saul makes {item.name} inadmissible.")
            return
        item.strength -= amount
        if item.strength <= 0:
            self.state.evidence.remove(item)
            log.append(f"{employee.name} eliminates {item.name}.")
        else:
            log.append(f"{employee.name} weakens {item.name}.")

    def _employee_incidents(self, log: list[str]) -> None:
        for employee in list(self.state.employees):
            chance = max(0, (employee.stress - 55) / 160 + (45 - employee.loyalty) / 180)
            chance += DIFFICULTIES[self.state.difficulty]["incident"]
            if self.random.random() >= chance:
                continue
            if self.state.pending_encounter is None and self.random.random() < 0.60:
                self.state.pending_encounter = next(item for item in ENCOUNTERS if item.key == "employee_dispute")
                log.append(f"INCIDENT: {employee.name} demands attention before doing more work.")
                return
            if employee.loyalty < 25 and self.random.random() < 0.20:
                self._add_evidence(f"{employee.name} cooperation memo", 8, "Employee leak", "FBI", EvidenceCategory.WITNESS)
                self._change_federal_clock(12, f"{employee.name} leaks to investigators")
                if employee.key == "gary":
                    self.state.flags.add("gary_leaked")
                log.append(f"INCIDENT: {employee.name} leaks information to investigators.")
            elif employee.stress > 70:
                employee.stress -= 18
                employee.loyalty -= 5
                self._add_evidence(f"{employee.name} stress mistake", 4, "Office incident", "IRS", EvidenceCategory.WITNESS)
                self._change_federal_clock(6, f"{employee.name} stress mistake")
                log.append(f"INCIDENT: {employee.name} makes a stress mistake.")
            else:
                employee.upkeep_cost += 20_000
                employee.loyalty += 8
                log.append(f"INCIDENT: {employee.name} demands a raise and gets it.")

    def _maybe_legal_request(self, log: list[str]) -> None:
        if self.state.pending_request is not None or self.state.pending_encounter is not None:
            return
        chance = 0.06 + self.state.federal_clock / 500
        if self.random.random() > chance:
            return
        item = self.random.choice(self.state.evidence) if self.state.evidence else None
        name = item.name if item else "Unexplained financial activity"
        severity = item.strength if item else 3
        self.state.pending_request = LegalRequest(name, severity, f"The IRS demands records about {name.lower()}.")
        self.state.menu.modal_selection = 0
        log.append("URGENT: The IRS issued a request for information.")

    def _maybe_encounter(self, log: list[str]) -> None:
        if self.state.pending_encounter is not None or self.state.pending_request is not None:
            return
        chance = 0.16 + self.state.public_attention / 400
        if self.random.random() > chance:
            return
        candidates = list(ENCOUNTERS)
        if not any(asset.name.startswith("Structurally") for asset in self.state.assets):
            candidates = [item for item in candidates if item.key != "yacht_emergency"]
        self.state.pending_encounter = self.random.choice(candidates)
        self.state.menu.modal_selection = 0
        log.append(f"ENCOUNTER: {self.state.pending_encounter.title}.")

    def _resolve_encounter(self, encounter: Encounter, option: EncounterOption) -> str:
        key = (encounter.key, option.key)
        if key == ("employee_dispute", "bonus"):
            for employee in self.state.employees:
                employee.loyalty += 12
                employee.stress -= 8
            return "The bonus buys temporary loyalty."
        if key == ("employee_dispute", "turns_off"):
            for employee in self.state.employees:
                employee.stress -= 22
            return "Time off lowers stress but nothing gets cleaner."
        if option.key == "threaten":
            for employee in self.state.employees:
                employee.loyalty -= 18
                employee.stress += 12
            return "Threats work briefly and age poorly."
        if encounter.key == "bank_review":
            self._add_evidence("Bank compliance notes", 4, "Bank review", "IRS", EvidenceCategory.FINANCIAL)
        if encounter.key == "reporter":
            self.state.public_attention += 10 if option.key == "brag" else -6
            self._relationship("mira", -8 if option.key == "no_comment" else 4)
        if encounter.key == "pitch" and option.key == "invest" and self.random.random() > 0.75:
            self.state.cash += 900_000
            self.state.terrible_successes += 1
            return "The pitch succeeds. You hate innovation."
        if encounter.key == "casino_vip":
            self._relationship("victor", 12)
            self.state.public_attention += 4
        if encounter.key == "tipster" and option.key == "trace":
            self._weaken_random_evidence(2)
        if encounter.key == "rival":
            self._relationship("broker", 10 if option.key == "broker" else -6)
        if encounter.key == "yacht_emergency" and option.key == "sink":
            self.state.assets = [asset for asset in self.state.assets if not asset.name.startswith("Structurally")]
            self.state.public_attention += 12
            return "The yacht becomes a reef and a headline."
        if encounter.key == "founder_panic" and option.key == "refuse":
            self.state.cash += 200_000
        return "The encounter resolves with suspicious paperwork."

    def _random_event(self, log: list[str]) -> None:
        if self.random.random() > 0.18:
            return
        event = self.random.choice(("refund", "market_crash", "tip", "viral", "quiet"))
        if event == "refund":
            self.state.cash += 250_000
            log.append("EVENT: You receive a $250,000 refund. Terrible.")
        elif event == "market_crash":
            for asset in self.state.assets:
                asset.value = int(asset.value * 0.70)
            log.append("EVENT: Asset values collapse by 30%.")
        elif event == "tip":
            self._change_federal_clock(5, "Anonymous source contacts investigators")
            self._add_evidence("Anonymous financial tip", 3, "Confidential source", "IRS", EvidenceCategory.WITNESS)
            log.append("EVENT: An anonymous source contacts investigators.")
        elif event == "viral":
            self.state.public_attention += 10
            log.append("EVENT: A video of your spending goes viral.")
        else:
            log.append("EVENT: Nothing happens. Everyone is suspicious.")

    def _add_evidence(self, name: str, strength: int, source: str, agency: str, category: EvidenceCategory) -> None:
        for evidence in self.state.evidence:
            if evidence.name == name:
                evidence.strength += strength
                evidence.inadmissible = False
                return
        self.state.evidence.append(Evidence(name, strength, source, agency, category))

    def _weaken_evidence(self, name: str, amount: int) -> None:
        for evidence in list(self.state.evidence):
            if evidence.name == name:
                evidence.strength -= amount
                if evidence.strength <= 0:
                    self.state.evidence.remove(evidence)
                return

    def _weaken_random_evidence(self, amount: int) -> None:
        if self.state.evidence:
            self._weaken_evidence(self.random.choice(self.state.evidence).name, amount)

    def _target_evidence(self, index: int | None, category: EvidenceCategory | None) -> Evidence | None:
        if index is not None and 0 <= index < len(self.state.evidence):
            return self.state.evidence[index]
        candidates = [item for item in self.state.evidence if category is None or item.category is category]
        return max(candidates, key=lambda item: item.strength, default=None)

    def _task_chance(self, employee: Employee, task: Task) -> int:
        chance = task.success_chance + (employee.competence - 50) // 3 - employee.stress // 10
        trait = employee.traits[0] if employee.traits else ""
        if trait in {"Meticulous", "Patient", "Brilliant", "Media-savvy"}:
            chance += 8
        if trait in {"Nervous", "Unreliable"}:
            chance -= 8
        if trait == "Reckless" and task.key in {"disrupt_feds", "digital_attack"}:
            chance += 6
        if trait == "Paranoid" and task.key == "monitor":
            chance += 10
        return max(10, min(95, chance))

    def _task_for(self, employee_key: str, task_key: str) -> Task | None:
        return next((task for task in TASKS[employee_key] if task.key == task_key), None)

    def _requirement_reason(self, req: Requirement) -> str | None:
        fake = Action("", "", "", 0, requirement=req)
        return self.action_lock_reason(fake)

    def _unlock_contact(self, key: str, message: str) -> None:
        contact = self.state.contact(key)
        if contact is None:
            return
        if contact.status == "unknown":
            contact.status = "available"
        if message and f"contact:{key}" not in self.state.announced_unlocks:
            self.state.announced_unlocks.add(f"contact:{key}")
            self.state.add_message(message)

    def _relationship(self, key: str, amount: int) -> None:
        contact = self.state.contact(key)
        if contact is None:
            return
        contact.relationship += amount
        if contact.relationship >= 50:
            contact.status = "trusted"
        elif contact.relationship <= -50:
            contact.status = "hostile"

    def _check_unlocks(self, log: list[str]) -> None:
        for contact in self.state.contacts:
            if contact.status != "unknown":
                continue
            if self._requirement_reason(contact.unlock_condition) is None:
                contact.status = "available"
                key = f"contact:{contact.key}"
                if key not in self.state.announced_unlocks:
                    self.state.announced_unlocks.add(key)
                    log.append(f"NEW CONTACT: {contact.name} is available.")
        for index, action in enumerate(ACTIONS, start=1):
            key = f"action:{action.key}"
            if key in self.state.announced_unlocks:
                continue
            if self.action_lock_reason(action) is None:
                self.state.announced_unlocks.add(key)
                if self.state.turn_count > 0 or action.requirement != Requirement():
                    log.append(f"NEW SCHEME: [{index}] {action.name} is now available.")

    def _check_achievements(self) -> None:
        if self.state.total_wealth == 0:
            self.state.achievements.add("PERFECT WRITE-OFF")
        if self.state.total_wealth >= 25_000_000:
            self.state.achievements.add("TOO BIG TO FAIL")
        if self.state.terrible_successes >= 3:
            self.state.achievements.add("CATASTROPHIC SUCCESS")
        if self.state.ignored_requests >= 5:
            self.state.achievements.add("NO COMMENT")
        if self.state.nullpointer_net_harm > 0:
            self.state.achievements.add("TECHNICAL DIFFICULTIES")

    def _after_change(self) -> None:
        if self.state.settings.animation_enabled:
            time.sleep(0.03)
        self.state.clamp()
        self._check_achievements()
        self._check_end_conditions()

    def _check_end_conditions(self) -> None:
        self.state.clamp()
        if self.state.total_wealth <= 0:
            self._finalize_result(GameStatus.WON, "You personally disposed of every dollar.")
            self.state.add_message(self.state.message + "\nYou successfully lost everything.")
            return
        self._check_clock_end_condition()

    def calculate_score(self) -> int:
        """Calculate one compact score value so balance changes have one home."""
        starting_wealth = self.state.starting_wealth or BACKGROUNDS.get(self.state.background, {}).get("cash", 0)
        disposed = max(0, starting_wealth - self.state.total_wealth)
        difficulty_multiplier = {"easy": 1.0, "normal": 1.25, "hard": 1.5}.get(self.state.difficulty, 1.0)
        reputation_points = self.state.reputation * 100
        turn_bonus = max(0, 180 - self.state.turn_count) * 25
        if self.state.status is GameStatus.WON:
            base = 5_000 + disposed // 1_000 + (100 - self.state.federal_clock) * 30 + turn_bonus + reputation_points
        else:
            base = 500 + disposed // 5_000 + max(0, 100 - self.state.federal_clock) * 5 + turn_bonus // 6 + reputation_points // 6
        return round(base * difficulty_multiplier)

    def _finalize_result(self, status: GameStatus, ending: str) -> None:
        if self.state.status in {GameStatus.WON, GameStatus.LOST}:
            return
        self.state.status = status
        self.state.ending = ending
        self.state.score = self.calculate_score()
        self.state.high_score, self.state.new_high_score = record_score(
            self.state.difficulty, self.state.score, self.state.background
        )

    def process_result_key(self, key: Key) -> None:
        if key.name == QUIT:
            self.state.status = GameStatus.QUIT
        elif key.name in {UP, DOWN}:
            self.state.menu.result_selection = 1 - self.state.menu.result_selection
        elif key.name == ENTER:
            if self.state.menu.result_selection == 0:
                self.restart()
            else:
                self.state.status = GameStatus.QUIT

    def restart(self) -> None:
        settings = self.state.settings
        self.state = GameState(settings=settings)
        self.state.contacts = [Contact(**vars(contact)) for contact in CONTACT_TEMPLATES]

    def _odds_bonus(self) -> float:
        return DIFFICULTIES[self.state.difficulty]["odds"] / 100
