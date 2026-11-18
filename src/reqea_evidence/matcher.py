"""Read-only candidate correlation over the frozen reqea.v1 JSON contract."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

REQ_ID = re.compile(r"^REQ-[0-9]{3,}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_ITEMS = 100_000


def safe_path(value: object) -> bool:
    """Reject absolute, traversal, control and potentially secret path references."""
    if not isinstance(value, str) or not value or len(value) > 1024:
        return False
    if "\\" in value or ":" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    if value.startswith("/") or value.startswith("~") or "//" in value:
        return False
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    if any(p.lower() in (".git", ".ssh", ".aws", "node_modules", "secrets") or
           p.lower().startswith((".env", "id_rsa", "id_ed25519")) for p in parts):
        return False
    return PurePosixPath(value).as_posix() == value


def safe_ref(value: object) -> tuple[str, str] | None:
    if not isinstance(value, str) or len(value) > 1200:
        return None
    path, sep, symbol = value.partition(":")
    if not safe_path(path) or (sep and (not symbol or len(symbol) > 256 or
          not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", symbol))):
        return None
    return path, symbol if sep else ""


def normalize_index_files(code_index: dict) -> tuple[dict, list[str]]:
    """Returns safe path-index and diagnostic codes; never reads target files."""
    raw = code_index.get("files")
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise ValueError("code_index.files must be a bounded list")
    files: dict[str, dict] = {}
    warnings: list[str] = []
    conflicted: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or not safe_path(item.get("path")):
            warnings.append("INVALID_FILE_PATH")
            continue
        path = item["path"]
        digest = item.get("sha256")
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            warnings.append("INVALID_FILE_HASH")
            continue
        symbols = item.get("symbols", [])
        if not isinstance(symbols, list) or len(symbols) > MAX_ITEMS:
            warnings.append("INVALID_SYMBOL_INDEX")
            continue
        clean_symbols = []
        for sym in symbols:
            if not isinstance(sym, dict) or not isinstance(sym.get("name"), str):
                warnings.append("INVALID_SYMBOL_INDEX")
                continue
            name, line = sym["name"], sym.get("line")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", name) or len(name) > 256 or \
               type(line) is not int or not 1 <= line <= 10_000_000:
                warnings.append("INVALID_SYMBOL_INDEX")
                continue
            clean_symbols.append({"name": name, "line": line})
        if path in conflicted:
            continue
        if path in files:
            if files[path]["sha256"] != digest:
                warnings.append("CONFLICTING_FILE_HASH")
                files.pop(path, None)
                conflicted.add(path)
            else:
                warnings.append("DUPLICATE_FILE_ENTRY")
            continue
        files[path] = {"sha256": digest, "language": item.get("language"),
                       "symbols": sorted(clean_symbols, key=lambda s: (s["name"], s["line"]))}
    return files, sorted(set(warnings))


def match_requirement(requirement: dict, files: dict, source_sha: str) -> dict:
    """Match only exact declared paths/symbols or REQ-ID in indexed identifiers."""
    refs = requirement.get("explicit_refs", [])
    if not isinstance(refs, list) or len(refs) > MAX_ITEMS:
        raise ValueError("explicit_refs must be a bounded list")
    warnings: set[str] = set()
    evidence: dict[tuple, dict] = {}
    missing: list[str] = []
    indexed_refs: set[str] = set()
    for ref in refs:
        parsed = safe_ref(ref)
        if parsed is None:
            warnings.add("INVALID_EXPLICIT_REF")
            continue
        path, symbol = parsed
        if path not in files:
            missing.append(path)
            continue
        found = files[path]
        if symbol:
            symbols = [s for s in found["symbols"] if s["name"] == symbol]
            if not symbols:
                missing.append(f"{path}:{symbol}")
                continue
            for s in symbols:
                ev = {"path": path, "symbol": symbol, "line": s["line"],
                      "kind": "static", "source_sha": source_sha}
                evidence[(path, symbol, s["line"])] = ev
        else:
            ev = {"path": path, "symbol": "", "line": 0,
                  "kind": "static", "source_sha": source_sha}
            evidence[(path, "", 0)] = ev
        indexed_refs.add(ref)
    # Indexed symbol/path naming may nominate a weak candidate, but never certify functionality.
    req_id = requirement["req_id"]
    token = req_id.lower().replace("-", "_")
    for path, found in files.items():
        basename = path.rsplit("/", 1)[-1].lower().replace("-", "_")
        if token in basename:
            evidence.setdefault((path, "", 0), {"path": path, "symbol": "", "line": 0,
               "kind": "static", "source_sha": source_sha})
        for s in found["symbols"]:
            if token in s["name"].lower():
                evidence.setdefault((path, s["name"], s["line"]),
                    {"path": path, "symbol": s["name"], "line": s["line"],
                     "kind": "static", "source_sha": source_sha})
    criteria = requirement.get("acceptance_criteria", [])
    if not isinstance(criteria, list) or len(criteria) > MAX_ITEMS:
        raise ValueError("acceptance_criteria must be a bounded list")
    per_criterion = []
    for criterion in criteria:
        if not isinstance(criterion, str) or not criterion.strip() or len(criterion) > 4000:
            warnings.add("INVALID_CRITERION")
            per_criterion.append({"criterion": "[invalid criterion]", "status": "UNASSESSED"})
            continue
        # A static reference can nominate an implementation site, never prove behavioral acceptance.
        related = [r for r in indexed_refs if r in criterion]
        absent = [r for r in missing if r in criterion]
        state = "CODE_CANDIDATE" if related else "GAP_CANDIDATE" if absent else "UNASSESSED"
        per_criterion.append({"criterion": criterion, "status": state})
    return {"evidence": sorted(evidence.values(), key=lambda e: (e["path"], e["symbol"], e["line"])),
            "missing_refs": sorted(set(missing)), "criteria": per_criterion,
            "warnings": sorted(warnings), "ref_count": len(refs)}
