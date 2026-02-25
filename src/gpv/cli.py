"""GPV CLI entry point."""

import sys
from pathlib import Path

import click

from .commands import commit, extract, info, init, prompt, uncommit
from .config import ConfigError
from .db import DBError


def main() -> None:
    """Entry point for gpv command."""
    cli()


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """GPV: prompt versioning where the prompt is assembled from jinja2 sub-prompt template files."""
    ctx.ensure_object(dict)


@cli.command("init")
def init_cmd() -> None:
    """Verify gpv tables to the target database (creating the database if necessary)."""
    try:
        init.run_init()
    except (ConfigError, DBError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("commit")
@click.option("-no-j2-validate", "no_validate", is_flag=True, help="Skip jinja2 validation")
@click.option("-m", "message", required=True, help="Commit message")
@click.option("-branch", "branch_specs", nargs=2, type=(int, click.Path(path_type=Path)), multiple=True)
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path, exists=True))
def commit_cmd(no_validate: bool, message: str, branch_specs: tuple, paths: tuple) -> None:
    """Commit sub-prompts and create new master prompt."""
    try:
        if branch_specs:
            run_commit_branch(message, list(branch_specs), no_validate)
        elif paths:
            run_commit_paths(message, list(paths), no_validate)
        else:
            run_commit(message=message, no_validate=no_validate)
    except (ConfigError, commit.CommitError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def run_commit(message: str, no_validate: bool = False) -> None:
    commit.run_commit(message=message, no_validate=no_validate)


def run_commit_paths(message: str, paths: list[Path], no_validate: bool = False) -> None:
    commit.run_commit_paths(message=message, paths=paths, no_validate=no_validate)


def run_commit_branch(
    message: str, branch_specs: list[tuple[int, Path]], no_validate: bool = False
) -> None:
    commit.run_commit_branch(message=message, branch_specs=branch_specs, no_validate=no_validate)


@cli.command("uncommit")
def uncommit_cmd() -> None:
    """Undo the previous commit."""
    try:
        uncommit.run_uncommit()
    except (ConfigError, uncommit.UncommitError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("info")
def info_cmd() -> None:
    """Print details of current master prompt."""
    try:
        info.run_info()
    except (ConfigError, info.InfoError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("prompt")
@click.option("-key", "master_pk", type=int, default=None, help="Master prompt id")
def prompt_cmd(master_pk: int | None) -> None:
    """Print concatenated sub-prompts in order, each preceded by its type."""
    try:
        prompt.run_prompt(master_pk=master_pk)
    except (ConfigError, prompt.PromptError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("extract")
@click.option("-key", "master_pk", type=int, default=None, help="Master prompt id")
def extract_cmd(master_pk: int | None) -> None:
    """Create .j2 files from current master sub-prompts."""
    try:
        extract.run_extract(master_pk=master_pk)
    except (ConfigError, extract.ExtractError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


