# `agent/fs_ro.py`

## Overview
- Provides a **read‑only, sandboxed filesystem** abstraction rooted at a configurable directory.  
- Guarantees that all accessed paths stay **inside the sandbox root**, raising `SandboxViolation` on any traversal attempt.  
- Offers helpers to **list Python files**, **read text files safely**, and **convert absolute paths to sandbox‑relative paths**.  
- Enforces a **maximum file size** (default 2 MiB) to avoid loading huge files into memory.  
- Uses `Path.resolve(..., strict=False)` for resolution while still preventing escape via `Path.is_relative_to`.  

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `SandboxViolation` | `Exception` | Raised when a path resolves outside the configured sandbox root. |
| `ReadOnlySandboxFS` | `dataclass` (frozen) | Core sandbox class. |
| `ReadOnlySandboxFS.root_dir` | `Path` | Absolute, resolved root directory of the sandbox (set on init). |
| `ReadOnlySandboxFS.list_python_files()` | `list[Path]` | Returns sorted absolute paths of all `*.py` files under the root (recursive). |
| `ReadOnlySandboxFS.read_text(rel_or_abs_path, *, max_bytes=2_000_000)` | `str` | Reads a UTF‑8 text file (or raises on size limit, missing file, or sandbox violation). |
| `ReadOnlySandboxFS.relpath(abs_path)` | `Path` | Converts an absolute path that lies under the sandbox root to a path relative to the root. |

## Key Behaviors and Edge Cases
- **Root Normalisation** – In `__post_init__`, the supplied `root_dir` is expanded (`~`), resolved (symlinks resolved, absolute), and stored as a canonical `Path`.  
- **Path Resolution** – `_resolve_under_root` joins a relative path to the root, or accepts an absolute path *only* if it still resolves under the root. It uses `Path.is_relative_to` (Python 3.11+) for the containment check.  
- **Traversal Protection** – Any attempt to escape the sandbox (e.g., `../..`, symlink tricks) triggers `SandboxViolation`.  
- **File Size Guard** – `read_text` refuses to read files larger than `max_bytes` (default 2 MiB) and raises `ValueError`.  
- **Missing Files** – If the resolved path does not exist or is not a regular file, `FileNotFoundError` is raised.  
- **Encoding** – Files are read as bytes then decoded with UTF‑8, using `errors="replace"` to avoid UnicodeDecodeError on malformed data.  
- **Relative Path Helper** – `relpath` validates that the supplied absolute path is inside the sandbox before computing the relative component.  

## Inputs / Outputs / Side Effects
| Method | Input(s) | Output | Side Effects |
|--------|----------|--------|--------------|
| `list_python_files()` | none | `list[Path]` (absolute, sorted) | Reads the filesystem (directory traversal). |
| `read_text(rel_or_abs_path, *, max_bytes)` | `str` or `Path` (relative or absolute) | `str` (file contents) | Reads file bytes; raises on size limit, missing file, or sandbox violation. |
| `relpath(abs_path)` | `Path` (absolute) | `Path` (relative to sandbox root) | No I/O, only path manipulation and validation. |

## Usage Examples
```python
from pathlib import Path
from agent.fs_ro import ReadOnlySandboxFS, SandboxViolation

# Initialise sandbox rooted at the project's "src" directory
sandbox = ReadOnlySandboxFS(root_dir=Path("~/my_project/src"))

# 1. List all Python modules in the sandbox
for py_path in sandbox.list_python_files():
    print(py_path)

# 2. Safely read a file (relative path)
try:
    content = sandbox.read_text("utils/helpers.py")
    print(content[:200])          # preview first 200 characters
except (FileNotFoundError, ValueError, SandboxViolation) as exc:
    print(f"Cannot read file: {exc}")

# 3. Convert an absolute path to a sandbox‑relative path
abs_path = Path("/home/user/my_project/src/utils/helpers.py")
try:
    rel = sandbox.relpath(abs_path)
    print(f"Relative path: {rel}")
except SandboxViolation as exc:
    print(f"Path outside sandbox: {exc}")
```

## Risks / TODOs
- **No secrets detected** in the source file.  
- Consider adding **unit tests** for edge cases (symlink loops, extremely long paths).  
- Optionally expose a **read‑only iterator** for large directory trees to avoid loading all paths into memory at once.  
- Document the expected **character encoding** policy more explicitly if non‑UTF‑8 files may appear.
