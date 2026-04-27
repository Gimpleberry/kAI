"""
CLI for ops tasks — bypass the API for things you'd rather script.

Commands (planned):
    kai init                   Set up DB and config
    kai validate-taxonomy      Sanity-check taxonomy.yaml
    kai estimate <session_id>  Re-run estimation on existing session
    kai export <session_id>    Export profile in chosen format
    kai diff <id1> <id2>       Compare two profiles
    kai diagnose <session_id>  Run all diagnostics, print report
"""

from __future__ import annotations

import typer

app = typer.Typer(help="kAI CLI")


@app.command()
def init() -> None:
    """Initialize database and verify config."""
    raise NotImplementedError


@app.command()
def validate_taxonomy(path: str = "config/taxonomy.yaml") -> None:
    """Validate taxonomy YAML against schema."""
    from kai.taxonomy import load_taxonomy

    taxonomy = load_taxonomy(path)
    typer.echo(f"[OK] Taxonomy v{taxonomy.version} valid")
    typer.echo(f"  Attributes: {len(taxonomy.attributes)}")
    typer.echo(f"  Tenets: {len(taxonomy.tenets)}")
    typer.echo(f"  Estimable parameters: {taxonomy.n_estimable_params}")


if __name__ == "__main__":
    app()
