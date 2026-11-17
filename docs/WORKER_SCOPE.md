# REQEA worker C — locked work unit boundaries

Mission: REQ 근거 매칭, 보수적 상태 분류, HTML·JSON 보고 엔진. Frozen API: evaluate(requirement_manifest: dict, code_index: dict, options: dict) -> dict; render_html(audit: dict) -> str.
A canonical final blueprint: https://github.com/hibi89/REQ-Evidence-Auditor-A-/blob/e58e14ee4ef84dfc226d657cfe45b1d40cfb9ba9/docs/FINAL_BLUEPRINT.md
Shared schema: docs/CONTRACT_V1.md (byte-for-byte copied from A).
Owned source and test paths: src/reqea_evidence/**, tests/c/**.
Forbidden integration changes: src/reqea/**, other worker module, A pyproject, A CLI/GUI, shared contract, final product scope.

## Assigned SWUs and acceptance
- C-01 (REQ-019, REQ-021): REQ-ID·explicit_ref·criteria 정적 후보 상호 연결; depends none; path src/reqea_evidence/matcher.py; acceptance 동일 경로/심볼 근거 후보 및 criteria 별 불명확성
- C-02 (REQ-020, REQ-023): 상태 결정기: candidate/review/gap/unassessed; depends C-01; path src/reqea_evidence/classify.py; acceptance 미지원/제한 scan 시 false PASS/false GAP 금지
- C-03 (REQ-022, REQ-027): SHA 불일치·모순 근거 경고; depends C-02; path src/reqea_evidence/provenance.py; acceptance 다른 SHA 근거 합치지 않고 warnings로 처리
- C-04 (REQ-024, REQ-029): evaluate() + deterministic audit JSON 집계; depends C-01, C-02, C-03; path src/reqea_evidence/__init__.py; acceptance 정렬된 findings, status/summary 일관
- C-05 (REQ-025, REQ-026, REQ-028): XSS-safe HTML 오프라인 report renderer; depends C-04; path src/reqea_evidence/report.py; acceptance untrusted title/path escape, secret/code full text 제외

## Development and handoff
Implement actual functions and their core error paths, not stubs or test-only records. Static analysis must not execute the inspected target.
CLI and module return values MUST conform to reqea.v1. No network or file writes to input. Unsupported scope is UNASSESSED, not fabricated PASS/GAP.
At module completion hand off exact repo/branch/SHA, SHA256 manifest for whitelisted files, warnings, min tests PASS/FAIL/NOT_RUN. A manually copies only allowed module and tests to its integration branch.
Do not delete this repo or update main; preserve history until user separately approves deletion following verified archive.
Next READY: C-01
