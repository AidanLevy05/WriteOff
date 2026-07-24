from dataclasses import dataclass, field
from enum import Enum, auto


class GameStatus(Enum):
    SETUP = auto()
    RUNNING = auto()
    WON = auto()
    LOST = auto()
    QUIT = auto()


class EvidenceCategory(Enum):
    FINANCIAL = "financial"
    DIGITAL = "digital"
    PUBLIC = "public"
    WITNESS = "witness"
    PROPERTY = "property"


@dataclass(frozen=True)
class Requirement:
    reputation: int = 0
    employee: str | None = None
    flag: str | None = None
    contact: str | None = None


@dataclass(frozen=True)
class Action:
    key: str
    name: str
    description: str
    cost: int
    reputation_gain: int = 0
    requirement: Requirement = Requirement()
    risks: tuple[str, ...] = ()
    outcomes: tuple[str, ...] = ()
    path: str = "general"
    category: str = "legal"
    clock_min: int = 1
    clock_max: int = 3
    risk_label: str = "Low"
    confirmation_required: bool = False
    operation_turns: int = 0


@dataclass(frozen=True)
class Task:
    key: str
    name: str
    turns: int
    cost: int
    success_chance: int
    stress_change: int
    description: str
    target_category: EvidenceCategory | None = None
    clock_success: int = 0
    clock_failure: int = 4


@dataclass
class Assignment:
    task_key: str
    task_name: str
    turns_remaining: int
    target_evidence: int | None = None


@dataclass
class Employee:
    key: str
    name: str
    role: str
    upkeep_cost: int
    competence: int
    loyalty: int
    stress: int
    traits: list[str] = field(default_factory=list)
    assigned_task: Assignment | None = None
    turns_on_task: int = 0

    @property
    def busy(self) -> bool:
        return self.assigned_task is not None


@dataclass
class Asset:
    name: str
    value: int
    upkeep_cost: int = 0


@dataclass
class Evidence:
    name: str
    strength: int
    source: str
    agency: str = "IRS"
    category: EvidenceCategory = EvidenceCategory.FINANCIAL
    inadmissible: bool = False

    @property
    def label(self) -> str:
        if self.inadmissible:
            return "INADMISSIBLE"
        if self.strength >= 8:
            return "STRONG"
        if self.strength >= 4:
            return "MEDIUM"
        return "WEAK"


@dataclass
class Operation:
    key: str
    name: str
    turns_remaining: int
    upkeep_cost: int
    clock_per_turn: int = 0
    attention_per_turn: int = 0
    completion_flag: str | None = None
    completion_message: str = ""
    completion_cash_change: int = 0
    completion_reputation: int = 0
    hidden: bool = False


@dataclass
class LegalRequest:
    evidence_name: str
    severity: int
    description: str


@dataclass
class Contact:
    key: str
    name: str
    role: str
    relationship: int
    status: str
    unlock_condition: Requirement = Requirement()


@dataclass
class Settings:
    color_enabled: bool = True
    animation_enabled: bool = True
    sound_enabled: bool = False


@dataclass
class EncounterOption:
    key: str
    text: str
    cost: int = 0
    requirement: Requirement = Requirement()
    clock_change: int = 1
    description: str = ""


@dataclass
class Encounter:
    key: str
    title: str
    description: str
    options: list[EncounterOption]


@dataclass
class MenuState:
    tabs: tuple[str, ...] = ("Actions", "Employees", "Evidence", "Assets", "Operations", "Contacts", "Settings")
    tab_index: int = 0
    selections: dict[str, int] = field(
        default_factory=lambda: {
            "Actions": 0,
            "Employees": 0,
            "Evidence": 0,
            "Assets": 0,
            "Operations": 0,
            "Contacts": 0,
            "Settings": 0,
        }
    )
    setup_selection: int = 0
    modal_selection: int = 0
    confirm_action_index: int | None = None
    employee_task_key: str = ""
    evidence_index: int | None = None
    result_selection: int = 0


@dataclass
class GameState:
    status: GameStatus = GameStatus.SETUP
    setup_step: str = "difficulty"
    difficulty: str = ""
    background: str = ""
    view: str = "normal"

    turn_count: int = 0
    federal_clock: int = 8
    federal_momentum: int = 0
    last_clock_change: int = 0
    last_clock_reason: str = "New file opened by the wrong department."
    cash: int = 10_000_000
    reputation: int = 0
    irs_progress: int = 0
    fbi_progress: int = 0
    public_attention: int = 0

    employees: list[Employee] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    operations: list[Operation] = field(default_factory=list)
    contacts: list[Contact] = field(default_factory=list)

    flags: set[str] = field(default_factory=set)
    announced_unlocks: set[str] = field(default_factory=set)
    achievements: set[str] = field(default_factory=set)
    ignored_requests: int = 0
    terrible_successes: int = 0
    nullpointer_net_harm: int = 0
    ending: str = ""
    starting_wealth: int = 0
    score: int = 0
    high_score: int = 0
    new_high_score: bool = False

    settings: Settings = field(default_factory=Settings)
    menu: MenuState = field(default_factory=MenuState)
    pending_request: LegalRequest | None = None
    pending_encounter: Encounter | None = None

    message: str = "Choose a difficulty to begin."
    messages: list[str] = field(default_factory=list)

    @property
    def asset_value(self) -> int:
        return sum(asset.value for asset in self.assets)

    @property
    def total_wealth(self) -> int:
        return self.cash + self.asset_value

    @property
    def upkeep_costs(self) -> int:
        employee_cost = sum(employee.upkeep_cost for employee in self.employees)
        asset_cost = sum(asset.upkeep_cost for asset in self.assets)
        operation_cost = sum(operation.upkeep_cost for operation in self.operations)
        return employee_cost + asset_cost + operation_cost

    @property
    def pressure_label(self) -> str:
        if self.federal_clock >= 90:
            return "FINAL WARNING"
        if self.federal_clock >= 75:
            return "IMMINENT"
        if self.federal_clock >= 50:
            return "TARGETED"
        if self.federal_clock >= 25:
            return "WATCHED"
        return "QUIET"

    def has_employee(self, key: str) -> bool:
        return any(employee.key == key for employee in self.employees)

    def employee(self, key: str) -> Employee | None:
        return next((item for item in self.employees if item.key == key), None)

    def contact(self, key: str) -> Contact | None:
        return next((item for item in self.contacts if item.key == key), None)

    def add_message(self, text: str) -> None:
        self.message = text
        self.messages.extend(line for line in text.splitlines() if line.strip())
        self.messages = self.messages[-12:]

    def clamp(self) -> None:
        self.cash = max(0, self.cash)
        self.reputation = max(0, self.reputation)
        self.federal_clock = max(0, min(100, self.federal_clock))
        self.federal_momentum = max(-10, min(10, self.federal_momentum))
        self.irs_progress = max(0, min(100, self.irs_progress))
        self.fbi_progress = max(0, min(100, self.fbi_progress))
        self.public_attention = max(0, min(100, self.public_attention))
        for employee in self.employees:
            employee.competence = max(0, min(100, employee.competence))
            employee.loyalty = max(0, min(100, employee.loyalty))
            employee.stress = max(0, min(100, employee.stress))
        for contact in self.contacts:
            contact.relationship = max(-100, min(100, contact.relationship))
        for item in self.evidence:
            item.strength = max(0, min(10, item.strength))
