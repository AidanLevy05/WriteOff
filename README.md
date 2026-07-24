# Write Off

`Write Off` is a keyboard-driven terminal game about disposing of a ridiculous fortune before the Federal Clock reaches 100.

Spend badly, hire unreliable specialists, build implausible schemes, manage evidence, and write off any assets left behind. You win when your total wealth reaches zero. You lose when investigators reach the end of the Federal Clock.

## Requirements

- Python 3
- A terminal with ANSI escape-sequence support

The game uses only the Python standard library. No package installation is required.

## Run

From the project directory:

```bash
python main.py
```

The included container definition can also be used:

```bash
docker build -t writeoff .
docker run -it --rm writeoff
```

Run the container interactively so it can receive raw keyboard input.

## Controls

| Key | Action |
| --- | --- |
| Up / Down | Move the highlighted selection |
| Left / Right / Tab | Change the active tab |
| Enter | Select the highlighted item |
| Escape | Close a menu or cancel a confirmation |
| S | Save the current running game |
| L | Open the load confirmation |
| H or `?` | Open help |
| Q | Quit immediately |

Menus use inverse video for the current selection. Dangerous actions and asset write-offs open with `No` selected by default.

## Starting a Run

Choose a difficulty, then a background.

### Difficulties

| Difficulty | Starting Federal Clock | Notes |
| --- | ---: | --- |
| Easy | 4 | Lower ongoing pressure and more favorable odds |
| Normal | 8 | Baseline rules |
| Hard | 14 | Higher pressure, more incidents, less favorable odds |

### Backgrounds

| Background | Starting cash | Notable effect |
| --- | ---: | --- |
| Crypto Millionaire | $12M | Higher public attention and crypto advantages |
| Corrupt Executive | $9M | Starts with Gary Ledger |
| Lottery Winner | $18M | A lower starting Federal Clock |
| Government Contractor | $11M | Legal-action and consultant discounts, but FBI attention |

## Objective and Core Systems

### Win and loss conditions

- **Win:** `cash + asset value` reaches `$0`.
- **Loss:** the **Federal Clock** reaches `100`.

The top status line always shows cash, assets, reputation, and per-turn upkeep. The Federal Clock is the only loss countdown; it is quiet below 25, watched from 25, targeted from 50, imminent from 75, and at its final warning from 90.

### Turns and pressure

Navigation is free. A turn advances when you take a meaningful action, assign an employee, respond to evidence, resolve a legal request, resolve an encounter, or write off an asset.

At the end of a turn, the game can charge upkeep, advance operations and assignments, add Federal Clock pressure from evidence or public attention, trigger employee incidents, and generate encounters or random events. Actions and active operations may also add their own Federal Clock pressure.

### Actions

The **Actions** tab contains spending schemes. Each entry shows its cost, lock status, and risk rating. The detail panel explains requirements, outcomes, and expected Federal Clock range.

Many actions increase reputation, which unlocks more expensive and more destructive options. Some schemes create multi-turn operations; these create ongoing upkeep and Federal Clock pressure while they are active.

### Employees

Employees provide assignments that can slow the Federal Clock, manage evidence, reduce attention, or support operations. They also have upkeep, competence, loyalty, stress, and traits. High stress or poor loyalty can create incidents.

- **Gary Ledger:** financial records and fake-business work.
- **Saul Fineprint:** legal delay, evidence challenges, and media handling.
- **NullPointer:** digital disruption and operation concealment, with substantial failure risk.

### Evidence, operations, and contacts

- **Evidence** raises ongoing pressure. Select it to see available employee responses.
- **Operations** show active long-running schemes, their upkeep, and their clock pressure.
- **Contacts** unlock selected schemes and encounter options as relationships and reputation develop.

### Assets and write-offs

Some schemes turn cash into assets, such as art, sports stakes, or a yacht. Assets count toward total wealth and may also have upkeep.

The **Assets** tab prevents an asset-only dead end. Select an asset and choose **Write off** to permanently dispose of it. This removes its value and upkeep, advances one turn, and adds a Federal Clock increase based on its value. Use this to finish a run after cash has been exhausted, but consider the clock risk before doing it early.

## End Screen, Score, and High Scores

Wins and losses open a full-screen result menu. It reports final cash, assets, total wealth, Federal Clock, reputation, turns, difficulty, background, ending reason, score, and high score.

The score calculation lives in `GameEngine.calculate_score()`. It combines:

- A large victory bonus for winning.
- Wealth successfully disposed of from the starting amount.
- A lower Federal Clock on victory.
- Fewer turns used.
- Reputation.
- A multiplier for Normal and Hard difficulty.

Losses receive a much smaller score using the same broad factors. High scores are kept separately for Easy, Normal, and Hard in the project-relative `highscores.json` file. Missing or malformed high-score data is treated as an empty score table.

At the bottom of the end screen:

```text
> Play Again
  Quit
```

Use Up/Down and Enter to choose. **Play Again** creates a fresh run and returns to difficulty selection while preserving settings and high scores. `Q` exits immediately.

## Save Data

- `S` writes the running game to `savegame.json` in the project directory.
- `L` opens a confirmation before loading that file.
- Save data includes the game state and random-number state, so a loaded run continues consistently.
- Save files from incompatible older game schemas are rejected with a concise error instead of crashing.

`savegame.json` and `highscores.json` are local runtime data. They are not required to launch a new game.

## Project Layout

| Path | Purpose |
| --- | --- |
| `main.py` | Application loop, terminal lifecycle, and result-menu routing |
| `writeoff/engine.py` | Game rules, turn resolution, scoring, and game restart |
| `writeoff/content.py` | Difficulties, backgrounds, actions, tasks, contacts, and encounters |
| `writeoff/models.py` | Game-state data models |
| `writeoff/ui.py` | Terminal rendering and menus |
| `writeoff/terminal_input.py` | Cross-platform semantic key input |
| `writeoff/save.py` | Save/load serialization |
| `writeoff/highscores.py` | Local per-difficulty high-score persistence |
| `writeoff/colors.py` | ANSI color and selection helpers |
| `Dockerfile` | Minimal Python container launch configuration |

## Development Check

Run the built-in syntax compilation check after changes:

```bash
python -m compileall -q .
```
