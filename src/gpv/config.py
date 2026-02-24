"""Configuration: .gpv dotfile parsing and validation."""

from pathlib import Path


class GPVError(Exception):
    """Base exception for GPV."""


class ConfigError(GPVError):
    """Configuration error (missing or invalid .gpv)."""


def get_db_path(cwd: Path | None = None) -> Path:
    """
    Read and validate the database path from .gpv in CWD.
    Raises ConfigError if .gpv is missing, empty, or path is invalid.
    """
    if cwd is None:
        cwd = Path.cwd()
    gpv_file = cwd / ".gpv"
    if not gpv_file.exists():
        raise ConfigError(".gpv file not found in current directory")
    path_str = gpv_file.read_text().strip()
    if not path_str:
        raise ConfigError(".gpv file is empty")
    db_path = Path(path_str)
    if not db_path.is_absolute():
        db_path = (cwd / path_str).resolve()
    parent = db_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not db_path.is_file():
        raise ConfigError(f"Database path exists but is not a file: {db_path}")
    try:
        parent.stat()
    except OSError as e:
        raise ConfigError(f"Cannot access database directory {parent}: {e}") from e
    return db_path
