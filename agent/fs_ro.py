"""
File name: fs_ro.py
Author: Luigi Saetta
Date last modified: 2025-12-14
Python Version: 3.11

Description:
    Read-only, sandboxed filesystem access to a root folder and its subfolders.
    Prevents path traversal and forbids access outside the configured root.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class SandboxViolation(Exception):
    """Raised when attempting to access paths outside the configured sandbox root."""


@dataclass(frozen=True)
class ReadOnlySandboxFS:
    root_dir: Path

    def __post_init__(self) -> None:
        root = self.root_dir.expanduser().resolve(strict=True)
        object.__setattr__(self, "root_dir", root)

    def _resolve_under_root(self, path: Path) -> Path:
        # Join relative paths to root; allow absolute paths only if still under root.
        candidate = (self.root_dir / path) if not path.is_absolute() else path
        resolved = candidate.expanduser().resolve(strict=False)

        # Python 3.11: Path.is_relative_to exists
        if not resolved.is_relative_to(self.root_dir):
            raise SandboxViolation(f"Access outside sandbox is forbidden: {resolved}")
        return resolved

    def list_python_files(self) -> list[Path]:
        """Return absolute Paths for all .py files under root (recursive)."""
        return sorted(self.root_dir.rglob("*.py"))

    def read_text(
        self, rel_or_abs_path: str | Path, *, max_bytes: int = 2_000_000
    ) -> str:
        """Read a file as UTF-8 text (best-effort)."""
        p = self._resolve_under_root(Path(rel_or_abs_path))
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(str(p))

        # Guardrail for huge files
        size = p.stat().st_size
        if size > max_bytes:
            raise ValueError(f"File too large ({size} bytes). Refusing to read: {p}")

        data = p.read_bytes()
        return data.decode("utf-8", errors="replace")

    def relpath(self, abs_path: Path) -> Path:
        """Convert an absolute path under root to a relative path."""
        abs_resolved = abs_path.expanduser().resolve(strict=False)
        if not abs_resolved.is_relative_to(self.root_dir):
            raise SandboxViolation(f"Not under sandbox root: {abs_resolved}")
        return abs_resolved.relative_to(self.root_dir)
