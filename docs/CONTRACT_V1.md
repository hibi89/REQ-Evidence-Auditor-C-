# REQEA — 교차 저장소 인터페이스 계약 V1 (FROZEN)
**Authoritative:** A: `docs/CONTRACT_V1.md` · **version string:** `reqea.v1` · **2026-11-18 KST**
A·B·C가 서로의 소스에 접근하지 않아도 동일 JSON 계약만으로 병렬 구현 가능하도록 아래를 **불변 기본값**으로 한다. 변경은 A 통합자가 사용자 승인 범위 확인 후 버전 상승+3곳 동일 전파 전까지 금지.

## 1. 실행 경계·모듈 import
- A: `src/reqea/`; 공개 CLI `python -m reqea.cli audit --repo <local-root> --requirements <local-file> --out <safe-output-dir>`.
- B: `src/reqea_codegraph/`; 함수 `build_code_index(root: str, options: dict) -> dict`; 옵션 `{"source_sha":"40-hex-or-UNVERIFIED","max_files":10000,"max_file_bytes":2000000,"max_total_bytes":50000000,"max_depth":32}`. root는 절대 경로이며 B가 실제 경계 검증.
- C: `src/reqea_evidence/`; 함수 `evaluate(requirement_manifest: dict, code_index: dict, options: dict) -> dict`, `render_html(audit: dict) -> str`; JSON 외부 네트워크 호출 0.
- B/C는 `reqea`나 서로를 import하지 않는다. A만 연결. 세 모듈은 Python 3.11 표준 라이브러리로 실행 가능해야 한다.
- 반환 예외는 `ValueError` 또는 명세된 `warnings/errors`로 정상화. Python code를 `import`해서 분석하지 않는다.

## 2. 공통 필드 정책
- 모든 데이터에 `schema_version: "reqea.v1"`, `source_sha`(hex40 또는 `UNVERIFIED`), `warnings`(string[] 정렬·중복 제거).
- 경로: POSIX 방식 루트 상대 경로(예 `src/app.py`). 절대 경로, `../`, 파일 본문, 환경변수 값 금지.
- 순서: requirements req_id ASC, files path ASC, symbols name+line ASC, edges src+dst+kind ASC, findings req_id ASC. JSON UTF-8, `ensure_ascii=False`, 유효한 반복 실행 결과는 시간값 외 동일. 단 스캔 시각은 audit 메타에 별도 기록.
- `source_sha=UNVERIFIED`는 검증된 커밋으로 오인하지 않는다. `policy_sha`는 기준 해총 정책 SHA, `tool_version`은 REQEA 출시 버전.
- 필수 키 누락/잘못된 타입은 안전하게 예외 또는 `UNASSESSED`로 표기.

## 3. A → C: RequirementManifest JSON
```json
{
  "schema_version": "reqea.v1",
  "source_sha": "UNVERIFIED",
  "policy_sha": "f633dcf1d3c533d2b674648e4a6515d80b85f05c",
  "requirements": [
    {
      "req_id": "REQ-001",
      "title": "로컬 폴더 선택",
      "description": "사용자가 로컬 폴더를 선택",
      "acceptance_criteria": ["선택한 로컬 프로젝트만 읽기"],
      "explicit_refs": ["src/reqea/gui/app.py"],
      "source_document": "docs/FINAL_BLUEPRINT.md"
    }
  ],
  "warnings": []
}
```
- `explicit_refs`는 요구사항 문서에서 명시적으로 기재된 상대 경로만 허용; A가 추측해 생성하지 않는다.
- Markdown은 REQ-ID 출현을 순서대로 파싱하고 중복/모호성 경고. 파싱 불가 항목을 없던 REQ로 처리하지 않는다.
- acceptance_criteria가 비어 있는 경우 해당 REQ는 자동 완료/충족 판단 불가, `UNASSESSED`.

## 4. B → C: CodeIndex JSON
```json
{
  "schema_version": "reqea.v1",
  "source_sha": "UNVERIFIED",
  "files": [
    {
      "path": "src/app.py",
      "language": "python",
      "sha256": "0a0b...lowercase-64-hex",
      "bytes": 512,
      "symbols": [{"name":"run","kind":"function","line":10}],
      "imports": ["json"]
    }
  ],
  "edges": [
    {"src":"src/app.py:run","dst":"json","kind":"import_candidate"}
  ],
  "warnings": [],
  "limits": {"truncated":false,"scanned_files":1,"skipped_files":0}
}
```
- 파일 무결성 SHA256 64hex 실제 값만, 위 `0a0b...`는 설명용 placeholder. `source_sha`는 A에서 제공한 고정 입력 commit/ref 또는 `UNVERIFIED`. B는 GitHub 네트워크로 SHA 조회하지 않는다.
- path/text/language 입력은 untrusted; symlink 처리 금지, root 탈출 금지. JS/TS 파서는 지원되지 않는 구문을 과신하지 않고 `warnings`에 넣는다.
- `limits.truncated=true`이면 C는 빠진 REQ를 확정 GAP으로 분류하지 않는다.

## 5. C → A: Audit JSON
```json
{
  "schema_version": "reqea.v1",
  "source_sha": "UNVERIFIED",
  "status": "UNASSESSED",
  "findings": [
    {
      "req_id":"REQ-001",
      "status":"CODE_CANDIDATE",
      "rationale":"explicit source path reference exists; execution unverified",
      "evidence":[{"path":"src/app.py","symbol":"run","line":10,"kind":"static","source_sha":"UNVERIFIED"}],
      "acceptance_criteria":[{"criterion":"선택한 로컬 프로젝트만 읽기","status":"UNASSESSED"}],
      "warnings":[]
    }
  ],
  "summary":{"code_candidates":1,"gap_candidates":0,"review_required":0,"unassessed":0},
  "warnings":[]
}
```
- `status` enum: `CODE_CANDIDATE|GAP_CANDIDATE|REVIEW_REQUIRED|UNASSESSED`. `status` 최상위는 정보 요약이며 `PASS`/`VERIFIED` 금지.
- **정적 검색 부재를 확정 기능 누락으로 해석 금지**. `GAP_CANDIDATE`에도 확인 필요한 파일/검색 범위를 명시. 모호한 요구나 파싱/스캔 제한은 `UNASSESSED`.
- `evidence`는 path, symbol, line, kind, source_sha만 담는다. 소스 코드 전문/시크릿 값 저장하지 않는다.
- **P2 검증률은 이 데이터에서 계산하지 않는다.** 리포트는 JSON findings만 렌더, 원본 코드 미변경.

## 6. 실패 계약
| 상황 | 행동 |
|---|---|
| 동일 req_id 두 번 | A가 입력 거절 또는 `UNASSESSED` 항목 기록 |
| source_sha 불일치(A vs B vs C) | C가 해당 증거를 `REVIEW_REQUIRED` 또는 `UNASSESSED`; verified 금지 |
| B scan truncated | C가 탐색 못한 REQ를 `UNASSESSED` 처리 |
| TS dynamic import/eval | 코드 실행 금지; 정적 후보·`UNASSESSED` 경고 |
| 파서 오류/파일 접근 실패 | 해당 파일 경고, 다른 안전 경로 계속 |
| 출력 폴더 = 검사 루트 내부 | A 기본 거절 |
| 문서의 HTML/JS 문자열 | HTML escape, 단순 문자열 출력; 활성 스크립트 금지 |
| B/C 모듈 버전 다름 | A 통합 거절·`UNASSESSED` |
| 기본 로그·artifact | 원본 코드/시크릿/절대 파일 경로 제외 |

## 7. 파일 복사 통합 규칙
A가 완료된 B의 **오직** `src/reqea_codegraph/**`, `tests/b/**`를 A 동일 경로로 복사. C는 `src/reqea_evidence/**`, `tests/c/**`만 복사. 통합 후 A가 version/schema/import 계약과 정상/핵심 실패 경로의 최소 smoke 실행. `README`, `AGENTS`, `pyproject`, `src/reqea/**` 등 공통 파일 복사/덮어쓰기 금지. 세 레포의 정확 SHA와 파일별 SHA256을 A의 `docs/INTEGRATION_LOG.md`에 기록한다.
