"""
dep_license_check.py

Checks licenses for dependencies listed in requirements.txt (direct deps).
Uses installed package metadata (importlib.metadata).
No web calls. Deterministic.

Limitations:
- If dependencies are not installed in the environment running the agent, licenses will be NOT_INSTALLED.
- Requirements parsing is intentionally conservative; complex pip options are ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import metadata
from typing import Iterable


# ---- Data models ----


@dataclass(frozen=True)
class DepLicenseInfo:
    requirement: str  # original requirement line (cleaned)
    distribution: str  # normalized dist name (best-effort)
    version: str | None
    license: str  # normalized license id or UNKNOWN/NOT_INSTALLED
    source: str  # license_field | classifier | unknown | not_installed


@dataclass(frozen=True)
class DepLicenseCheckResult:
    ok: bool
    deps: list[DepLicenseInfo]
    failures: list[DepLicenseInfo]
    warnings: list[DepLicenseInfo]
    message: str


# ---- Requirements parsing (direct deps only) ----

_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")  # dist name at start
_IGNORE_PREFIXES = (
    "-r",
    "--requirement",
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "--trusted-host",
)


def parse_requirements_txt(text: str) -> list[str]:
    """
    Returns cleaned requirement lines (direct deps).
    Ignores comments, empty lines, and pip options.
    Keeps markers/extras/version pins as part of the requirement string, but extracts dist name separately later.
    """
    reqs: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(_IGNORE_PREFIXES):
            # conservative: ignore includes and index directives
            continue
        # drop inline comments: "pkg==1.2  # comment"
        if " #" in line:
            line = line.split(" #", 1)[0].rstrip()
        reqs.append(line)
    return reqs


def extract_dist_name(requirement: str) -> str | None:
    """
    Best-effort extraction of distribution name from a requirement line.
    Handles:
      - requests==2.32.3
      - pydantic>=2
      - fastapi[standard]>=0.100
      - package ; python_version < "3.12"
    """
    # Strip environment marker
    base = requirement.split(";", 1)[0].strip()
    # Strip extras
    base = base.split("[", 1)[0].strip()
    m = _REQ_NAME_RE.match(base)
    if not m:
        return None
    return m.group(1)


# ---- License extraction from installed metadata ----


def _normalize_license_string(s: str) -> str:
    """
    Normalize common license strings to SPDX-ish ids.
    Keep it conservative; expand mapping as you need.
    """
    v = (s or "").strip()
    if not v:
        return "UNKNOWN"

    u = v.upper().strip()
    if u in {"UNKNOWN", "NONE", "N/A"}:
        return "UNKNOWN"

    # Common normalizations
    mapping = {
        "APACHE 2.0": "Apache-2.0",
        "APACHE-2.0": "Apache-2.0",
        "APACHE SOFTWARE LICENSE": "Apache-2.0",
        "MIT": "MIT",
        "MIT LICENSE": "MIT",
        "BSD": "BSD",  # ambiguous; you may choose to treat as warn
        "ISC": "ISC",
        "MPL 2.0": "MPL-2.0",
        "MPL-2.0": "MPL-2.0",
        "MOZILLA PUBLIC LICENSE 2.0": "MPL-2.0",
    }

    # direct hit
    if u in mapping:
        return mapping[u]

    # a few substring matches
    if "APACHE" in u and "2" in u:
        return "Apache-2.0"
    if "MIT" in u:
        return "MIT"
    if "BSD" in u and "3" in u:
        return "BSD-3-Clause"
    if "BSD" in u and "2" in u:
        return "BSD-2-Clause"
    if "MPL" in u and "2" in u:
        return "MPL-2.0"
    if "ISC" in u:
        return "ISC"

    # Keep original (but trimmed) if it looks like an SPDX-ish token
    if re.fullmatch(r"[A-Za-z0-9.\-+]+", v):
        return v

    return v  # last resort


def _license_from_classifiers(classifiers: Iterable[str]) -> str | None:
    """
    Map Trove classifiers to normalized license ids.
    """
    # Minimal mapping; extend as needed
    trove_map = {
        "License :: OSI Approved :: MIT License": "MIT",
        "License :: OSI Approved :: Apache Software License": "Apache-2.0",
        "License :: OSI Approved :: BSD License": "BSD",
        "License :: OSI Approved :: ISC License (ISCL)": "ISC",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
        'License :: OSI Approved :: BSD 3-Clause "New" or "Revised" License': "BSD-3-Clause",
        'License :: OSI Approved :: BSD 2-Clause "Simplified" License': "BSD-2-Clause",
    }
    for c in classifiers:
        c = c.strip()
        if c in trove_map:
            return trove_map[c]
    # fallback: any license classifier contains keywords
    for c in classifiers:
        u = c.upper()
        if "LICENSE ::" not in u:
            continue
        if "MIT" in u:
            return "MIT"
        if "APACHE" in u:
            return "Apache-2.0"
        if "BSD 3-CLAUSE" in u or ("BSD" in u and "3" in u):
            return "BSD-3-Clause"
        if "BSD 2-CLAUSE" in u or ("BSD" in u and "2" in u):
            return "BSD-2-Clause"
        if "MPL" in u and "2" in u:
            return "MPL-2.0"
        if "ISC" in u:
            return "ISC"
    return None


def get_installed_dist_license(dist_name: str) -> DepLicenseInfo:
    """
    dist_name is a distribution name (best-effort).
    """
    try:
        md = metadata.metadata(dist_name)
        ver = metadata.version(dist_name)
    except metadata.PackageNotFoundError:
        return DepLicenseInfo(
            requirement=dist_name,
            distribution=dist_name,
            version=None,
            license="NOT_INSTALLED",
            source="not_installed",
        )

    lic_raw = (md.get("License") or "").strip()
    lic = _normalize_license_string(lic_raw)
    if lic not in {"UNKNOWN"} and lic_raw:
        return DepLicenseInfo(
            requirement=dist_name,
            distribution=dist_name,
            version=ver,
            license=lic,
            source="license_field",
        )

    classifiers = md.get_all("Classifier") or []
    lic2 = _license_from_classifiers(classifiers)
    if lic2:
        return DepLicenseInfo(
            requirement=dist_name,
            distribution=dist_name,
            version=ver,
            license=lic2,
            source="classifier",
        )

    return DepLicenseInfo(
        requirement=dist_name,
        distribution=dist_name,
        version=ver,
        license="UNKNOWN",
        source="unknown",
    )


def check_dependency_licenses(
    *,
    requirements_text: str,
    accepted_licenses: set[str],
    fail_on_unknown: bool,
    fail_on_not_installed: bool,
) -> DepLicenseCheckResult:
    req_lines = parse_requirements_txt(requirements_text)

    infos: list[DepLicenseInfo] = []
    failures: list[DepLicenseInfo] = []
    warnings: list[DepLicenseInfo] = []

    for req in req_lines:
        dist = extract_dist_name(req)
        if not dist:
            # weird line; warn
            warnings.append(
                DepLicenseInfo(
                    requirement=req,
                    distribution="(unparsed)",
                    version=None,
                    license="UNKNOWN",
                    source="unknown",
                )
            )
            continue

        info = get_installed_dist_license(dist)
        # Keep original requirement for traceability
        info = DepLicenseInfo(
            requirement=req,
            distribution=info.distribution,
            version=info.version,
            license=info.license,
            source=info.source,
        )
        infos.append(info)

        # Evaluate
        if info.license == "NOT_INSTALLED":
            if fail_on_not_installed:
                failures.append(info)
            else:
                warnings.append(info)
            continue

        if info.license == "UNKNOWN" or info.license == "BSD":
            # BSD is ambiguous; treat as warning unless you explicitly allow "BSD"
            if info.license in accepted_licenses:
                continue
            if fail_on_unknown:
                failures.append(info)
            else:
                warnings.append(info)
            continue

        if info.license not in accepted_licenses:
            failures.append(info)

    ok = len(failures) == 0
    msg = (
        f"Checked {len(infos)} direct dependencies from requirements.txt. "
        f"Failures: {len(failures)}. Warnings: {len(warnings)}."
    )
    return DepLicenseCheckResult(
        ok=ok, deps=infos, failures=failures, warnings=warnings, message=msg
    )
