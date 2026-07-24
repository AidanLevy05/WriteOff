from writeoff.engine import GameEngine
from writeoff.models import GameStatus
from writeoff.terminal_input import TerminalInput
from writeoff.ui import hide_cursor, render, render_game_over, show_cursor


def main() -> None:
    engine = GameEngine()

    try:
        hide_cursor()
        with TerminalInput() as terminal:
            while engine.state.status is not GameStatus.QUIT:
                if engine.state.status in {GameStatus.WON, GameStatus.LOST}:
                    render_game_over(engine)
                    engine.process_result_key(terminal.read_key())
                else:
                    render(engine)
                    engine.process_key(terminal.read_key())
    except KeyboardInterrupt:
        engine.state.status = GameStatus.QUIT
        engine.state.add_message("Interrupted. Terminal restored.")
    finally:
        show_cursor()

    if engine.state.status is GameStatus.QUIT and engine.state.ending:
        render_game_over(engine)


if __name__ == "__main__":
    main()
