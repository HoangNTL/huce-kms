import uuid
from pathlib import Path


def atomic_write_text(target: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically by staging to a temporary file in the target directory and replacing."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp.{uuid.uuid4().hex[:8]}")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(target)
