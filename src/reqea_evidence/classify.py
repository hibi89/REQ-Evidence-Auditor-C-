"""Conservative, explicitly non-verifying classification."""
from __future__ import annotations


def classify(match: dict, *, incomplete: bool, sha_mismatch: bool,
             ambiguous: bool = False, contradictory: bool = False) -> str:
    if sha_mismatch:
        return "REVIEW_REQUIRED"
    if contradictory:
        return "REVIEW_REQUIRED"
    if incomplete or ambiguous or match["warnings"]:
        return "UNASSESSED" if not match["evidence"] else "REVIEW_REQUIRED"
    if not match["criteria"]:
        return "UNASSESSED"
    if match["missing_refs"] and match["evidence"]:
        return "REVIEW_REQUIRED"
    if match["evidence"]:
        return "CODE_CANDIDATE"
    # No explicit, in-scope reference -> no evidence is *not* proof of missing code.
    if match["missing_refs"] and match["ref_count"] > 0:
        return "GAP_CANDIDATE"
    return "UNASSESSED"


def overall_status(findings: list[dict]) -> str:
    if not findings:
        return "UNASSESSED"
    statuses = {f["status"] for f in findings}
    for status in ("REVIEW_REQUIRED", "UNASSESSED", "GAP_CANDIDATE", "CODE_CANDIDATE"):
        if status in statuses:
            return status
    return "UNASSESSED"
