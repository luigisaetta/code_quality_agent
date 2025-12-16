# `agent/fs_ro.py`

## Overview
- Provides a **read‑only, sandboxed filesystem** abstraction rooted at a configurable directory.  
- Guarantees that all file operations stay **inside the sandbox**; attempts to escape raise `SandboxViolation`.  
- Offers helpers to **list Python files**, **read text files safely**, and **convert absolute paths to sandbox‑relative paths**.  
- Enforces a **size guard** (`max_bytes`) when reading files to avoid loading huge data into memory.  
- Uses `Path.is_relative_to` (Python 3.11+) for reliable containment checks.

## Public API
| Symbol | Type | Description |
|--------|------|-------------|
| `SandboxViolation` | `Exception` | Raised when a path resolves outside the configured sandbox root. |
| `ReadOnlySandboxFS` | `dataclass` | Core sandbox class. |
| `ReadOnlySandboxFS.root_dir` | `Path` | Absolute, resolved root of the sandbox (read‑only). |
| `ReadOnlySandboxFS.list_python_files()` | `list[Path]` | Returns sorted absolute paths of all `*.py` files under the root (recursive). |
| `ReadOnlySandboxFS.read_text(rel_or_abs_path, *, max_bytes=2_000_000)` | `str` | Reads a UTF‑8 text file (relative or absolute) inside the sandbox, with a size limit. |
| `ReadOnlySandboxFS.relpath(abs_path)` | `Path` | Converts an absolute sandbox path to a path relative to the sandbox root. |

## Key Behaviors and Edge Cases
| Method | Important Behaviour | Edge Cases |
|--------|--------------------|------------|
| `__post_init__` | Resolves `root_dir` to an absolute, existing path (`strict=True`). | Raises `FileNotFoundError` if the supplied root does not exist. |
| `_resolve_under_root` | Joins a relative path to `root_dir`; accepts absolute paths **only if** they are still under the root. Uses `Path.is_relative_to` for containment. | If the resolved path is outside the sandbox, raises `SandboxViolation`. |
| `list_python_files` | Uses `Path.rglob("*.py")` for recursive discovery. | Returns an empty list when no Python files exist. |
| `read_text` | Checks existence & file‑type, enforces `max_bytes` guard, reads bytes then decodes with `errors="replace"` to avoid UnicodeDecodeError. | - Raises `FileNotFoundError` for missing files.<br>- Raises `ValueError` if file size exceeds `max_bytes`.<br>- Returns a best‑effort string even for malformed UTF‑8. |
| `relpath` | Validates that the supplied absolute path is inside the sandbox before calling `relative_to`. | Raises `SandboxViolation` if the path is outside the sandbox. |

## Inputs / Outputs / Side Effects
| Method | Input(s) | Output | Side Effects |
|--------|----------|--------|--------------|
| `ReadOnlySandboxFS(root_dir)` | `Path` (or string convertible) pointing to an existing directory. | Instance with immutable `root_dir`. | Resolves and validates the root path. |
| `list_python_files()` | *none* | `list[Path]` (absolute, sorted). | Reads the filesystem (no mutation). |
| `read_text(rel_or_abs_path, max_bytes=…)` | `str` or `Path` (relative to or absolute under root), optional `max_bytes`. | `str` containing file contents (UTF‑8, replacement for errors). | Reads file bytes; raises on size limit or missing file. |
| `relpath(abs_path)` | `Path` (absolute). | `Path` relative to sandbox root. | No I/O; only path manipulation. |

## Usage Examples
```python
from pathlib import Path
from agent.fs_ro import ReadOnlySandboxFS, SandboxViolation

# Initialise sandbox (must exist)
sandbox = ReadOnlySandboxFS(root_dir=Path("~/my_project"))

# 1. List all Python source files
for py_path in sandbox.list_python_files():
    print(py_path)

# 2. Safely read a small text file
try:
    content = sandbox.read_text("docs/README.md")
    print(content[:200])          # preview
except (FileNotFoundError, ValueError) as exc:
    print(f"Cannot read file: {exc}")

# 3. Convert an absolute path to a sandbox‑relative path
abs_path = Path("/home/user/my_project/src/module.py")
try:
    rel = sandbox.relpath(abs_path)
    print(f"Relative path: {rel}")
except SandboxViolation:
    print("Path is outside the sandbox!")

# 4. Attempting to escape the sandbox raises an exception
try:
    sandbox.read_text("../outside.txt")
except SandboxViolation as sv:
    print(f"Security violation caught: {sv}")
```

## Risks / TODOs
- **No secret leakage**: the module does not embed credentials or API keys.  
- **Potential race condition**: The sandbox checks are performed *before* file access; a malicious actor with write access to the filesystem could replace a legitimate file with a symlink pointing outside the sandbox between the check and the read. Mitigation would require opening the file via `os.open(..., O_NOFOLLOW)` or using `Path.read_bytes()` on a file descriptor obtained after verification.  
- **Hard‑coded size limit** (`2 000 000` bytes) may be insufficient for some legitimate use‑cases; consider making it configurable.  
- **Unicode handling**: Decoding with `errors="replace"` hides encoding problems; callers needing strict validation should post‑process the result.  

*No immediate security concerns were found in the source code.*
