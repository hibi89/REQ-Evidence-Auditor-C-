"""C worker entrypoint for reqea.v1 static evidence audits (not verification)."""
from __future__ import annotations

import re

from .classify import classify, overall_status
from .matcher import MAX_ITEMS, REQ_ID, match_requirement, normalize_index_files
from .provenance import limited_scan, provenance, public_warnings

SCHEMA_VERSION = "reqea.v1"


def evaluate(requirement_manifest: dict, code_index: dict, options: dict) -> dict:
    """Evaluate contract data without I/O, importing target code, or claiming PASS."""
    if not all(isinstance(x, dict) for x in (requirement_manifest, code_index, options)):
        raise ValueError("manifest, code_index, options must be dictionaries")
    if requirement_manifest.get("schema_version") != SCHEMA_VERSION or \
       code_index.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("reqea.v1 schema version required")
    reqs = requirement_manifest.get("requirements")
    if not isinstance(reqs, list) or len(reqs) > MAX_ITEMS:
        raise ValueError("requirements must be a bounded list")
    policy = requirement_manifest.get("policy_sha")
    if policy is not None and not (isinstance(policy, str) and re.fullmatch(r"[0-9a-f]{40}", policy)):
        raise ValueError("policy_sha must be a lowercase 40-hex SHA")
    mismatch, sha_warnings = provenance(requirement_manifest, code_index, options)
    incomplete, limit_warnings = limited_scan(code_index)
    files, index_warnings = normalize_index_files(code_index)
    incomplete = incomplete or bool(index_warnings)
    global_warnings = set(sha_warnings + limit_warnings + index_warnings)
    global_warnings.update(public_warnings(requirement_manifest.get("warnings", [])))
    global_warnings.update(public_warnings(code_index.get("warnings", [])))
    # Upstream parse warnings make a negative evidence search inconclusive.
    incomplete = incomplete or bool(requirement_manifest.get("warnings"))
    findings = []
    seen = set()
    for req in sorted(reqs, key=lambda r: r.get("req_id", "") if isinstance(r, dict) else ""):
        if not isinstance(req, dict) or not isinstance(req.get("req_id"), str) or \
           not REQ_ID.fullmatch(req["req_id"]):
            raise ValueError("every requirement needs a valid REQ-ID")
        req_id = req["req_id"]
        if req_id in seen:
            raise ValueError("duplicate requirement id")
        seen.add(req_id)
        if not all(isinstance(req.get(k), str) for k in ("title", "description", "source_document")):
            raise ValueError("requirement title/description/source_document must be strings")
        match = match_requirement(req, files, code_index["source_sha"])
        contradictory = "CONFLICTING_FILE_HASH" in index_warnings
        unsupported = any(r.lower().split(":", 1)[0].endswith((".js", ".jsx", ".ts", ".tsx"))
                          for r in match["missing_refs"])
        status = classify(match, incomplete=incomplete or unsupported, sha_mismatch=mismatch,
                          contradictory=contradictory)
        warnings = set(match["warnings"])
        if mismatch:
            warnings.add("SOURCE_SHA_MISMATCH")
        if incomplete:
            warnings.add("INCOMPLETE_SCAN")
        if unsupported:
            warnings.add("UNSUPPORTED_STATIC_SCOPE")
        if match["missing_refs"]:
            warnings.add("EXPLICIT_REFERENCE_NOT_INDEXED")
        if contradictory:
            warnings.add("CONFLICTING_FILE_HASH")
        # Do not attach evidence collected under a different source revision.
        evidence = [] if mismatch else match["evidence"]
        criteria = match["criteria"]
        if mismatch or incomplete or unsupported or contradictory:
            criteria = [{"criterion": c["criterion"], "status": "UNASSESSED"} for c in criteria]
        rationale = {
            "CODE_CANDIDATE": "static reference candidate found; behavior and acceptance unverified",
            "GAP_CANDIDATE": "explicit reference not indexed within reported scan scope; confirm manually",
            "REVIEW_REQUIRED": "conflicting/partial source evidence or SHA provenance; human review required",
            "UNASSESSED": "insufficient, unsupported or incomplete static evidence; no completion inference",
        }[status]
        findings.append({"req_id": req_id, "status": status, "rationale": rationale,
                         "evidence": evidence, "acceptance_criteria": criteria,
                         "warnings": sorted(warnings)})
        global_warnings.update(warnings)
    counts = {"code_candidates": 0, "gap_candidates": 0, "review_required": 0, "unassessed": 0}
    for f in findings:
        counts[{"CODE_CANDIDATE": "code_candidates", "GAP_CANDIDATE": "gap_candidates",
                "REVIEW_REQUIRED": "review_required", "UNASSESSED": "unassessed"}[f["status"]]] += 1
    audit = {"schema_version": SCHEMA_VERSION, "source_sha": requirement_manifest["source_sha"],
             "status": overall_status(findings), "findings": findings,
             "summary": counts, "warnings": sorted(global_warnings)}
    if policy is not None:
        audit["policy_sha"] = policy
    tool_version = options.get("tool_version")
    if tool_version is not None:
        if not isinstance(tool_version, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", tool_version):
            raise ValueError("invalid tool_version")
        audit["tool_version"] = tool_version
    return audit


from .report import render_html  # noqa: E402 - public entrypoint
