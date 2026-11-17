# AGENTS — REQEA C

CURRENT_MISSION = REQ Evidence Auditor C independent feature coding and exact-SHA handoff to A. No switching to EAI, MLA, Repository Provisioner or any other product.
Canonical owner A design SHA: e58e14ee4ef84dfc226d657cfe45b1d40cfb9ba9.
Central policy last seen SHA f633dcf1d3c533d2b674648e4a6515d80b85f05c; ALWAYS recheck remote kmong-productization HEAD before coding. Policy: docs/strategy/OWNER_DEV_EXECUTION_CANONICAL_20261116.md §0J and GPT6_HIGH_STANDARD_WORK_UNIT_20261117.md §0E in hibi89/hackathon-command-center-2026.
Precedence: latest user instruction/approved A final design and safety > latest central policy > actual code SHA and schema > HANDOFF/STATUS. Read repo/branch/HEAD -> AGENTS -> HANDOFF -> STATUS -> REQUIREMENTS -> A blueprint -> docs/CONTRACT_V1.md -> own code.
Only edit source under src/reqea_evidence/** or tests/c/**. Never edit other workers' packages; A owns src/reqea/**, common packaging, final docs and integration. Own status/handoff/queue files may be updated when code changes.
Contract (frozen): evaluate(requirement_manifest: dict, code_index: dict, options: dict) -> dict; render_html(audit: dict) -> str, exact reqea.v1 schema. Do not unilaterally extend or rename required fields. Raise CONTRACT_CHANGE_REQUEST to A first.
Use actual P1 BE caller->callee->output+core errors in SWU-CPAA/WE waves 1..6 READY as safe. Initial 2 no-progress attempts -> ISOLATED_REDESIGN_PENDING; redesigned next 2 -> SOLMAX_BATCH_PENDING. P1 local syntax/type/smoke and urgent safety checks remain; P2 full CI/security/E2E/Windows deferred. High implements through verified model transition; no claim of parallel background AI.
Source imports/eval, paid calls, data export, permissions changes, force push, main merge, Production, commercial release, and B/C deletion require owner authorization. Never place customer source/keys in PUBLIC GitHub.
Report each work unit's REQ IDs, exact code paths, commit SHA, local PASS/FAIL/NOT_RUN, blockers, and next READY. Implementation and verification percent UNASSESSED unless grounded. This document setup is NOT product implementation.
