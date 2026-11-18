"""Self-contained HTML report; never renders code bodies or arbitrary audit fields."""
from __future__ import annotations

from html import escape
import re

VALID_STATUSES = {"CODE_CANDIDATE", "GAP_CANDIDATE", "REVIEW_REQUIRED", "UNASSESSED"}
SAFE_RATIONALES = {
    "static reference candidate found; behavior and acceptance unverified",
    "explicit reference not indexed within reported scan scope; confirm manually",
    "conflicting/partial source evidence or SHA provenance; human review required",
    "insufficient, unsupported or incomplete static evidence; no completion inference",
}
SAFE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9_./@+\-\u0080-\uffff]{1,1024}$")


def _h(value: object, limit: int = 240) -> str:
    return escape(str(value)[:limit], quote=True)


def _safe_warning(w: object) -> str:
    return str(w) if isinstance(w, str) and SAFE_CODE.fullmatch(w) else "WARNING_REDACTED"


def _safe_path(path: object) -> str:
    from .matcher import safe_path
    if not safe_path(path) or any(ch in path for ch in "<>\"'{}" + chr(96)):
        return "[path redacted]"
    return str(path)


def render_html(audit: dict) -> str:
    """Render only known contract fields with escaped text, no JS/external assets."""
    if not isinstance(audit, dict) or audit.get("schema_version") != "reqea.v1":
        raise ValueError("expected reqea.v1 audit")
    findings = audit.get("findings")
    if not isinstance(findings, list) or len(findings) > 100_000:
        raise ValueError("audit.findings must be a bounded list")
    chunks = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
              "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
              "<title>REQ Evidence Audit (static candidates only)</title>",
              "<style>body{font-family:system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#17233a}",
              "table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border:1px solid #cbd5e1;padding:.5rem;text-align:left;vertical-align:top}",
              "small{color:#475569}code{overflow-wrap:anywhere}section{margin-bottom:2rem}</style></head><body>",
              "<h1>REQ Evidence Audit</h1><p><strong>Static candidates only — not VERIFIED, PASS, or security certification.</strong></p>",
              "<p>P1 implementation: UNASSESSED · P2 verification: NOT_RUN</p>",
              "<p>Contract: reqea.v1 · Source SHA: <code>", _h(audit.get("source_sha", "UNVERIFIED"), 40), "</code></p>",
              "<p>Overall classification: <strong>",
              _h(audit.get("status") if audit.get("status") in VALID_STATUSES else "UNASSESSED"), "</strong></p>"]
    summary = audit.get("summary", {})
    if isinstance(summary, dict):
        chunks.append("<p>Counts (static classifications): ")
        for k in ("code_candidates", "gap_candidates", "review_required", "unassessed"):
            n = summary.get(k)
            chunks.extend([_h(k), "=", str(n) if type(n) is int and 0 <= n <= 100_000 else "?", " "])
        chunks.append("</p>")
    warnings = audit.get("warnings", [])
    if isinstance(warnings, list) and warnings:
        chunks.append("<section><h2>Warnings</h2><ul>")
        for w in sorted(set(_safe_warning(v) for v in warnings))[:1000]:
            chunks.extend(["<li>", _h(w), "</li>"])
        chunks.append("</ul></section>")
    for f in sorted(findings, key=lambda f: str(f.get("req_id", "")) if isinstance(f, dict) else ""):
        if not isinstance(f, dict):
            continue
        status = f.get("status", "UNASSESSED")
        if status not in VALID_STATUSES:
            status = "UNASSESSED"
        req_id = f.get("req_id", "UNKNOWN")
        if not isinstance(req_id, str) or not re.fullmatch(r"REQ-[0-9]{3,}", req_id):
            req_id = "INVALID_REQ_ID"
        chunks.extend(["<section><h2>", _h(req_id), " — ", _h(status), "</h2>",
                       "<p>", _h(f.get("rationale") if f.get("rationale") in SAFE_RATIONALES
                                  else "manual review required; rationale redacted"), "</p>",
                       "<table><thead><tr><th>Source path</th><th>Symbol</th><th>Line</th><th>Reason</th></tr></thead><tbody>"])
        evs = f.get("evidence", [])
        if isinstance(evs, list):
            for e in evs[:10000]:
                if not isinstance(e, dict):
                    continue
                path = _safe_path(e.get("path"))
                sym = e.get("symbol", "")
                if not isinstance(sym, str) or not re.fullmatch(r"[A-Za-z0-9_.]{0,256}", sym):
                    sym = "[redacted]"
                line = e.get("line", 0)
                if type(line) is not int or not 0 <= line <= 10_000_000:
                    line = 0
                chunks.extend(["<tr><td><code>", _h(path, 1024), "</code></td><td>",
                               _h(sym, 256), "</td><td>", str(line),
                               "</td><td>static index reference (execution unverified)</td></tr>"])
        chunks.append("</tbody></table><h3>Acceptance criteria (not verified)</h3><ul>")
        criteria = f.get("acceptance_criteria", [])
        if isinstance(criteria, list):
            for i, c in enumerate(criteria[:10000], start=1):
                if not isinstance(c, dict):
                    continue
                st = c.get("status")
                st = st if st in VALID_STATUSES else "UNASSESSED"
                # Criterion text may embed secrets or code snippets; publish index/status, not body.
                chunks.extend(["<li>Criterion ", str(i), ": ", _h(st), " (human review required)</li>"])
        chunks.append("</ul><small>Next: inspect exact file/symbol and run separately authorized acceptance tests.</small>")
        ws = f.get("warnings", [])
        if isinstance(ws, list) and ws:
            chunks.append("<p>Warnings: ")
            chunks.append(", ".join(_h(w) for w in sorted(set(_safe_warning(v) for v in ws))[:1000]))
            chunks.append("</p>")
        chunks.append("</section>")
    chunks.append("</body></html>")
    return "".join(chunks)
