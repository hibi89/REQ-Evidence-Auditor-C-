"""Read-only provenance and coverage diagnostics. Untrusted strings are never echoed."""
from __future__ import annotations

import re

COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SAFE_WARNING = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


def valid_sha(value: object) -> bool:
    return value == "UNVERIFIED" or (isinstance(value, str) and bool(COMMIT_SHA.fullmatch(value)))


def provenance(manifest: dict, index: dict, options: dict) -> tuple[bool, list[str]]:
    a, b = manifest.get("source_sha"), index.get("source_sha")
    if not valid_sha(a) or not valid_sha(b):
        raise ValueError("source_sha must be 40-lowercase-hex or UNVERIFIED")
    warnings: set[str] = set()
    mismatch = a != b
    if mismatch:
        warnings.add("SOURCE_SHA_MISMATCH")
    if a == "UNVERIFIED" or b == "UNVERIFIED":
        warnings.add("SOURCE_SHA_UNVERIFIED")
    o = options.get("source_sha")
    if o is not None:
        if not valid_sha(o):
            raise ValueError("options.source_sha invalid")
        if o != a or o != b:
            mismatch = True
            warnings.add("SOURCE_SHA_MISMATCH")
    return mismatch, sorted(warnings)


def limited_scan(index: dict) -> tuple[bool, list[str]]:
    limits = index.get("limits")
    if not isinstance(limits, dict) or type(limits.get("truncated")) is not bool or \
       type(limits.get("scanned_files")) is not int or \
       type(limits.get("skipped_files")) is not int or \
       limits["scanned_files"] < 0 or limits["skipped_files"] < 0:
        raise ValueError("code_index.limits must have valid counters")
    warnings = []
    # A contradictory file count cannot support a complete or trustworthy scan.
    files = index.get("files")
    if isinstance(files, list) and limits["scanned_files"] < len(files):
        warnings.append("INDEX_SCAN_COUNT_MISMATCH")
    if limits["truncated"]:
        warnings.append("SCAN_TRUNCATED")
    if limits["skipped_files"]:
        warnings.append("SCAN_SKIPPED_FILES")
    # A parser warning means coverage cannot be assumed complete.
    if index.get("warnings"):
        warnings.append("INDEX_WARNINGS_PRESENT")
    return bool(warnings), warnings


def public_warnings(values: object) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("warnings must be a list")
    codes = set()
    for item in values:
        if isinstance(item, str) and SAFE_WARNING.fullmatch(item):
            codes.add(item)
        else:
            codes.add("UPSTREAM_WARNING_REDACTED")
    return sorted(codes)
