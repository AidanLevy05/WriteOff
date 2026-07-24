from writeoff.models import (
    Action,
    Contact,
    Encounter,
    EncounterOption,
    EvidenceCategory,
    Requirement,
    Task,
)


DIFFICULTIES = {
    "easy": {
        "name": "EASY",
        "clock_start": 4,
        "pressure": -1,
        "incident": -0.04,
        "odds": 8,
        "legal": 3,
    },
    "normal": {
        "name": "NORMAL",
        "clock_start": 8,
        "pressure": 0,
        "incident": 0.0,
        "odds": 0,
        "legal": 0,
    },
    "hard": {
        "name": "HARD",
        "clock_start": 14,
        "pressure": 2,
        "incident": 0.08,
        "odds": -8,
        "legal": -3,
    },
}


BACKGROUNDS = {
    "crypto": {
        "name": "CRYPTO MILLIONAIRE",
        "cash": 12_000_000,
        "clock": 4,
        "attention": 10,
        "flags": {"crypto_bonus"},
        "message": "You minted money from a token named after a typo.",
    },
    "executive": {
        "name": "CORRUPT EXECUTIVE",
        "cash": 9_000_000,
        "clock": 6,
        "flags": {"business_bonus"},
        "employee": "gary",
        "message": "Gary already knows where the copier paper is buried.",
    },
    "lottery": {
        "name": "LOTTERY WINNER",
        "cash": 18_000_000,
        "clock": -3,
        "message": "You won too much money and learned nothing useful.",
    },
    "contractor": {
        "name": "GOVERNMENT CONTRACTOR",
        "cash": 11_000_000,
        "clock": 5,
        "fbi": 8,
        "flags": {"consultant_discount"},
        "message": "Your invoices have line items named 'miscellaneous patriotism.'",
    },
}


ACTIONS = (
    Action("dinner", "Suspiciously Expensive Dinner", "Burn a small amount of money and gain reputation.", 25_000, 1, risks=("Minor public attention.",), outcomes=("Lose cash cleanly.", "A lifestyle columnist notices."), path="legal", category="legal", clock_min=0, clock_max=1, risk_label="Minimal"),
    Action("casino", "Casino Trip", "Usually loses money. Sometimes you accidentally win.", 100_000, 2, risks=("Unwanted jackpot.", "Public casino footage."), outcomes=("Lose the stake.", "Win money and create evidence."), path="legal", category="public", clock_min=1, clock_max=5, risk_label="Low"),
    Action("accountant", "Hire Gary Ledger", "Unlocks accounting assignments and fake businesses.", 80_000, 2, Requirement(reputation=2), risks=("Gary becomes stressed by reality.",), outcomes=("Gary joins as staff.",), path="financial", category="financial", clock_min=1, clock_max=2, risk_label="Low"),
    Action("startup", "Fund a Terrible Startup", "May fail successfully or become catastrophically profitable.", 400_000, 4, Requirement(reputation=4), risks=("It might work.",), outcomes=("Immediate failure.", "Partial refund.", "Terrible success."), path="legal", category="legal", clock_min=1, clock_max=3, risk_label="Low"),
    Action("attorney", "Retain Saul Fineprint", "Unlocks legal assignments and stronger IRS responses.", 200_000, 3, Requirement(reputation=6), risks=("Very expensive payroll.",), outcomes=("Saul joins as staff.",), path="legal", category="legal", clock_min=0, clock_max=1, risk_label="Minimal"),
    Action("fake_business", "Create Fake Consulting Firm", "Starts a 3-turn operation required for larger schemes.", 300_000, 5, Requirement(reputation=8, employee="gary"), risks=("Financial evidence.", "Federal pressure while active."), outcomes=("Unlocks offshore and cyber schemes.",), path="financial", category="financial", clock_min=3, clock_max=6, risk_label="Moderate", confirmation_required=True, operation_turns=3),
    Action("art", "Buy Suspicious Modern Art", "Converts cash into an unpredictable asset.", 500_000, 4, Requirement(reputation=10), risks=("Property records.", "Artwork might appreciate."), outcomes=("Forgery.", "Mostly retains value.", "Appreciates."), path="public", category="property", clock_min=2, clock_max=5, risk_label="Moderate"),
    Action("movie", "Fund a Terrible Movie", "A director promises a four-hour musical about spreadsheets.", 850_000, 6, Requirement(reputation=12), risks=("Public reviews.", "Cult classic upside."), outcomes=("Box-office collapse.", "Streaming sale.", "Hit premiere."), path="public", category="public", clock_min=3, clock_max=6, risk_label="Moderate"),
    Action("charity", "Launch Vanity Charity", "Pay consultants to name a foundation after yourself.", 650_000, 5, Requirement(reputation=10), risks=("Public evidence.", "Reporter attention."), outcomes=("Money vanishes into galas.", "Mira Vale asks questions."), path="legal", category="public", clock_min=3, clock_max=6, risk_label="Moderate"),
    Action("sports", "Buy Failing Sports Team Stake", "Acquire a minority stake in a last-place franchise.", 1_400_000, 8, Requirement(reputation=18, contact="victor"), risks=("Public scrutiny.", "Unexpected playoff run."), outcomes=("Franchise keeps losing.", "Team value rises."), path="public", category="public", clock_min=5, clock_max=9, risk_label="High", confirmation_required=True),
    Action("campaign", "Start Doomed Political Campaign", "Spend heavily to poll behind a decorative plant.", 1_100_000, 9, Requirement(reputation=20, contact="senator"), risks=("Public scandals.", "Witness evidence."), outcomes=("Consultants consume the budget.", "A scandal erupts."), path="public", category="public", clock_min=6, clock_max=10, risk_label="High", confirmation_required=True, operation_turns=3),
    Action("crypto_token", "Launch Suspicious Crypto Token", "Pay influencers to misunderstand a whitepaper.", 700_000, 7, Requirement(reputation=14), risks=("Digital evidence.", "Token might moon."), outcomes=("Token collapses.", "Exchange listing creates attention."), path="cyber", category="cyber", clock_min=4, clock_max=9, risk_label="High", confirmation_required=True),
    Action("consultant", "Hire Absurd Consultant", "Pay for a deck explaining how to pay for decks.", 350_000, 3, Requirement(reputation=7), risks=("Low risk, high waste.",), outcomes=("Pure fee burn.", "Introduces The Broker."), path="legal", category="legal", clock_min=1, clock_max=2, risk_label="Low"),
    Action("celebrity_party", "Host Celebrity Disaster Party", "Spend on an event remembered mainly by paramedics.", 900_000, 8, Requirement(reputation=16), risks=("Public attention.", "Reporter encounters."), outcomes=("Money lost.", "Viral disaster."), path="public", category="public", clock_min=5, clock_max=10, risk_label="High", confirmation_required=True),
    Action("hacker", "Hire NullPointer", "Unlocks cyber assignments while attracting FBI interest.", 350_000, 6, Requirement(reputation=14, flag="fake_business"), risks=("Digital evidence.", "FBI progress."), outcomes=("NullPointer joins as staff.",), path="cyber", category="cyber", clock_min=4, clock_max=8, risk_label="High", confirmation_required=True),
    Action("offshore_trust", "Create Offshore Trust", "Starts a 3-turn trust operation with a beach address.", 900_000, 8, Requirement(reputation=18, employee="gary"), risks=("Financial evidence.", "FBI interest."), outcomes=("Unlocks island-scale schemes.",), path="financial", category="financial", clock_min=5, clock_max=9, risk_label="High", confirmation_required=True, operation_turns=3),
    Action("shell_company", "Create Offshore Shell Company", "Starts a 4-turn international shell operation.", 700_000, 8, Requirement(reputation=18, employee="gary", flag="fake_business"), risks=("Financial evidence.", "FBI interest."), outcomes=("Unlocks yacht and island purchases.",), path="financial", category="financial", clock_min=5, clock_max=9, risk_label="High", confirmation_required=True, operation_turns=4),
    Action("real_estate", "Finance Doomed Real-Estate Project", "Build luxury condos where maps say 'wetlands'.", 1_700_000, 10, Requirement(reputation=24, contact="broker"), risks=("Property evidence.", "Accidental rezoning success."), outcomes=("Permits fail.", "The project sells units somehow."), path="financial", category="property", clock_min=6, clock_max=10, risk_label="High", confirmation_required=True, operation_turns=4),
    Action("yacht", "Buy a Maintenance Nightmare", "Spend millions on a rapidly depreciating yacht.", 2_000_000, 8, Requirement(reputation=22, flag="shell_company"), risks=("Public attention.", "Property records."), outcomes=("Upkeep burns cash.",), path="public", category="property", clock_min=6, clock_max=10, risk_label="High", confirmation_required=True),
    Action("island", "Purchase a Private Island", "Starts a 5-turn operation that destroys enormous wealth.", 4_000_000, 15, Requirement(reputation=35, flag="shell_company"), risks=("Severe international evidence.", "Loss if scandal explodes."), outcomes=("Major wealth destruction.", "International incident."), path="financial", category="financial", clock_min=10, clock_max=15, risk_label="Extreme", confirmation_required=True, operation_turns=5),
)


TASKS = {
    "gary": (
        Task("clean_books", "Prepare clean books", 2, 30_000, 70, 8, "Reduce Federal Clock pressure from financial mess.", clock_success=-6, clock_failure=4),
        Task("records", "Fabricate matching records", 2, 45_000, 60, 14, "Weaken financial evidence.", EvidenceCategory.FINANCIAL, clock_success=-4, clock_failure=6),
        Task("business_docs", "Build fake business documents", 3, 60_000, 58, 16, "Improve fake-business credibility.", clock_success=-3, clock_failure=6),
        Task("refunds", "Search for tax refunds", 1, 20_000, 50, 10, "May recover unwanted cash.", clock_success=1, clock_failure=3),
        Task("gary_rest", "Take a turn off", 1, 0, 100, -24, "Reduce Gary's stress.", clock_success=0, clock_failure=0),
    ),
    "saul": (
        Task("delay_feds", "Delay Federal Clock", 2, 65_000, 72, 10, "Reduce the Federal Clock with procedural fog.", clock_success=-8, clock_failure=3),
        Task("challenge", "Challenge one evidence item", 2, 80_000, 64, 12, "May weaken or remove evidence.", clock_success=-5, clock_failure=4),
        Task("legal_structure", "Prepare legal structure", 3, 120_000, 68, 15, "Reduce operation pressure.", clock_success=-4, clock_failure=4),
        Task("media", "Handle media response", 1, 55_000, 75, 8, "Reduce public attention.", EvidenceCategory.PUBLIC, clock_success=-4, clock_failure=3),
        Task("saul_rest", "Take a turn off", 1, 0, 100, -20, "Reduce Saul's stress.", clock_success=0, clock_failure=0),
    ),
    "nullpointer": (
        Task("disrupt_feds", "Disrupt federal systems", 2, 70_000, 62, 18, "May reduce Federal Clock, but failures are loud.", clock_success=-7, clock_failure=8),
        Task("digital_attack", "Attack one digital evidence item", 2, 90_000, 60, 20, "May erase digital evidence.", EvidenceCategory.DIGITAL, clock_success=-5, clock_failure=9),
        Task("hide_operation", "Hide an operation", 2, 75_000, 65, 16, "Reduce operation clock pressure.", clock_success=-3, clock_failure=6),
        Task("monitor", "Monitor investigators", 1, 45_000, 76, 10, "Reduce next-turn pressure.", clock_success=-2, clock_failure=4),
        Task("null_rest", "Take a turn off", 1, 0, 100, -22, "Reduce NullPointer's stress.", clock_success=0, clock_failure=0),
    ),
}


CONTACT_TEMPLATES = (
    Contact("gary", "Gary Ledger", "Questionable Accountant", 10, "available"),
    Contact("saul", "Saul Fineprint", "Tax Attorney", 0, "unknown", Requirement(reputation=5)),
    Contact("nullpointer", "NullPointer", "Cyber Consultant", -5, "unknown", Requirement(flag="fake_business")),
    Contact("broker", "The Broker", "Deals that come with fog", 0, "unknown", Requirement(reputation=15)),
    Contact("senator", "Senator Holloway", "Retired influence merchant", -10, "unknown", Requirement(reputation=20)),
    Contact("mira", "Mira Vale", "Investigative Reporter", -15, "unknown", Requirement(reputation=12)),
    Contact("victor", "Victor Glass", "Casino Host", 5, "unknown", Requirement(reputation=9)),
)


ENCOUNTERS = (
    Encounter("irs_call", "IRS PHONE CALL", "An auditor asks why your charity owns a fog machine.", [
        EncounterOption("stall", "Promise records soon", 10_000, clock_change=2, description="Small delay, some suspicion."),
        EncounterOption("saul", "Let Saul answer", 45_000, Requirement(employee="saul"), clock_change=-4, description="Saul can lower the clock."),
        EncounterOption("panic", "Hang up immediately", clock_change=6, description="Cheap and bad."),
    ]),
    Encounter("bank_review", "BANK COMPLIANCE REVIEW", "Your bank wants an explanation for a wire memo reading 'oops'.", [
        EncounterOption("explain", "Send vague paperwork", 25_000, clock_change=3),
        EncounterOption("gary", "Have Gary reconcile it", 40_000, Requirement(employee="gary"), clock_change=-3),
        EncounterOption("move", "Move money somewhere worse", 75_000, clock_change=5),
    ]),
    Encounter("reporter", "NEWS REPORTER QUESTION", "Mira Vale asks whether your yacht is also a school.", [
        EncounterOption("no_comment", "Say no comment", clock_change=2),
        EncounterOption("media", "Stage a polished response", 60_000, Requirement(employee="saul"), clock_change=-3),
        EncounterOption("brag", "Invite cameras aboard", clock_change=7),
    ]),
    Encounter("employee_dispute", "EMPLOYEE DISPUTE", "A staff member has discovered the payroll vibes.", [
        EncounterOption("bonus", "Pay a $100K bonus", 100_000, clock_change=1),
        EncounterOption("turns_off", "Give three turns off", clock_change=1),
        EncounterOption("refuse", "Refuse", clock_change=4),
        EncounterOption("threaten", "Threaten them", clock_change=7),
    ]),
    Encounter("pitch", "INVESTMENT PITCH", "A founder offers a guaranteed failure with a confusing cap table.", [
        EncounterOption("invest", "Invest $300K", 300_000, clock_change=2),
        EncounterOption("broker", "Ask The Broker", 40_000, Requirement(contact="broker"), clock_change=0),
        EncounterOption("pass", "Decline", clock_change=1),
    ]),
    Encounter("casino_vip", "CASINO VIP OFFER", "Victor Glass offers a private table and suspiciously fresh dice.", [
        EncounterOption("play", "Lose like a VIP", 250_000, clock_change=3),
        EncounterOption("relationship", "Ask Victor for discretion", 50_000, Requirement(contact="victor"), clock_change=-1),
        EncounterOption("decline", "Decline", clock_change=1),
    ]),
    Encounter("tipster", "ANONYMOUS TIPSTER", "Someone offers to identify an informant for cash.", [
        EncounterOption("pay", "Pay the tipster", 80_000, clock_change=-2),
        EncounterOption("ignore", "Ignore the message", clock_change=4),
        EncounterOption("trace", "Let NullPointer trace it", 55_000, Requirement(employee="nullpointer"), clock_change=-4),
    ]),
    Encounter("rival", "RIVAL CRIMINAL CONTACT", "A rival proposes a joint scheme with too many boats.", [
        EncounterOption("deal", "Join the deal", 200_000, clock_change=6),
        EncounterOption("snub", "Publicly snub them", clock_change=2),
        EncounterOption("broker", "Have The Broker negotiate", 70_000, Requirement(contact="broker"), clock_change=0),
    ]),
    Encounter("yacht_emergency", "YACHT EMERGENCY", "The yacht crew reports smoke where water should be.", [
        EncounterOption("repair", "Overpay for repairs", 300_000, clock_change=1),
        EncounterOption("sink", "Let it become an artificial reef", clock_change=7),
        EncounterOption("insure", "Call the insurer", clock_change=4),
    ]),
    Encounter("founder_panic", "STARTUP FOUNDER PANIC", "A founder wants to return your investment out of guilt.", [
        EncounterOption("refuse", "Refuse the refund", clock_change=1),
        EncounterOption("double", "Double down", 250_000, clock_change=3),
        EncounterOption("lawyer", "Have Saul draft a scarier memo", 50_000, Requirement(employee="saul"), clock_change=-2),
    ]),
)
