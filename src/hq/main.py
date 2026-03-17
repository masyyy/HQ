import typer

from hq.cli.board import board_app
from hq.cli.crm import crm_app
from hq.db.queries import search_all, get_status_summary
from hq.config import get_stages

app = typer.Typer(
    help="HQ -- CLI-first company OS. Manage your Board and CRM from the terminal.",
    no_args_is_help=True,
)

app.add_typer(board_app, name="board")
app.add_typer(crm_app, name="crm")


@app.command()
def status() -> None:
    """Overview of all modules."""
    summary = get_status_summary()

    if not summary:
        print("No data yet. Start with:")
        print('  hq board add "My first task"')
        print('  hq crm add "First lead"')
        return

    for module in ["crm", "board"]:
        if module not in summary:
            continue
        stages = get_stages(module)
        stage_counts = summary[module]
        counts = [f"{stage}: {stage_counts[stage]}" for stage in stages if stage_counts.get(stage, 0) > 0]
        print(f"{module.upper()}  {', '.join(counts)}")


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Full-text search across all modules."""
    results = search_all(query)
    if not results:
        print(f"No results for '{query}'")
        return

    for e in results:
        print(f"  #{e['id']} [{e['module']}] {e['title']} ({e['stage']})")


@app.command()
def tui() -> None:
    """Launch the TUI interface."""
    from hq.tui.app import HQApp
    tui_app = HQApp()
    tui_app.run()
