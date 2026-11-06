# CLAUDE.md

이 저장소에서 작업할 때(사람과 AI 도구 모두) 지키는 규칙이다. 설계의 근거는 `docs/PRD.md`, `docs/SDD.md`이다.

## 1. 프로젝트 개요
- 이름: grant-finder-rag
- 목적: 정부·지자체 지원사업 공고를 수집·정제하여 RAG로 구축하고, 조건이 포함된 질문에 출처가 붙은 답변을 제공한다.
- 기간: 2026-11-09 ~ 2026-11-19 (1인 개발, 평일 14:00~17:00 9회차 총 27시간, 주말 작업 없음)
- 핵심 조건: **비용 없이** 동작해야 한다 (로컬 Ollama, 무료 티어만 사용). 공개 배포는 GitHub Pages 정적 재생 데모뿐이며 백엔드는 로컬에서만 실행한다

## 2. 작업 전에 읽을 문서
1. `docs/PRD.md`: 범위, 스토리, 수락 기준
2. `docs/SDD.md`: 계층 규칙, 데이터 모델, API, 평가 설계
3. 작업 대상 폴더의 `__init__.py`와 기존 코드

PRD·SDD에 없는 기능, 테이블 구조, API를 임의로 추가하지 않는다. 필요하면 먼저 문서를 수정하고 변경 이력에 기록한다.

## 3. 구조와 의존성 규칙
```
api ─▶ retrieval, generation ─▶ contracts ◀─ storage, embedding
ingestion ─▶ contracts, storage, embedding
evaluation ─▶ retrieval, generation, contracts
```
- `api`는 `ingestion`을 import하지 않는다.
- `retrieval`은 Qdrant를, `generation`은 Ollama를 직접 import하지 않는다. `contracts/ports.py`의 Port만 사용한다.
- `contracts`는 다른 내부 패키지를 import하지 않는다.
- 새 외부 서비스 연동은 Port 뒤에 둔다.

## 4. 하지 않는 것
- 서버 시작 시 파싱·색인을 자동 실행하지 않는다 (적재는 CLI에서만 실행).
- `data/raw`의 원본 파일을 수정하지 않는다.
- API 키, `.env`, 원본 데이터, 개인정보를 커밋하지 않는다.
- 로그에 키, 개인정보, 공고 본문을 남기지 않는다.
- 값을 추측하여 메타데이터를 채우지 않는다 (추출 실패는 None으로 두고 결측으로 집계).
- 마감된 공고를 기본 검색 결과에 포함하지 않는다 ("마감 포함" 옵션일 때만). 지역 필터는 선택 지역 + "전국"이다.
- 현재 날짜를 코드에서 직접 호출해 평가·데모에 쓰지 않는다. 기준일은 `as_of_date`(`AS_OF_DATE`)를 사용한다.
- LLM 호출은 FallbackLLM만 사용한다. 429/5xx/시간 초과일 때만 다음 공급자로 전환하고, 같은 공급자 반복 재시도나 키 교체를 하지 않는다.
- Docling, parent-child, Contextual Retrieval, SSE는 v1.0 범위가 아니다.
- 로그인·회원 기능은 v1.1 범위이며 v1.0에서 구현하지 않는다.
- 유료 서비스와 유료 API를 사용하지 않는다.
- 설치·테스트·평가가 실제로 성공하기 전에는 성공했다고 문서(README 포함)에 쓰지 않는다.
- 평가하지 않은 구성의 수치를 기록하지 않는다.

## 5. 코딩 규칙
| 대상 | 규칙 |
|---|---|
| Python | PEP 8 `snake_case`. 클래스·Protocol·예외는 `PascalCase`. 모듈 파일명에 하이픈 금지 |
| API JSON 필드 | `camelCase`. 경로는 `/api/`로 시작 |
| 오류 응답 | `{ "code": "...", "message": "..." }` |
| 타입 | 공개 함수와 Port에 타입 힌트를 쓴다 |
| 포맷·린트 | Ruff (`ruff check`, `ruff format`) |
| 주석·문서 | 한국어. 식별자(변수, 함수, 파일명)는 영어 |
| 프론트엔드 | React + TypeScript + Tailwind, Biome. 파일명 kebab-case, 컴포넌트 PascalCase, `features/`·`shared/` 구조. 실행은 `npm --prefix frontend run dev`, 테스트는 Vitest |

## 6. 의존성 추가 규칙
- 새 라이브러리는 `uv add`로 추가하고, 이유를 `docs/SDD.md` 12절(기술 선택 기록)에 한 줄 남긴다.
- `uv.lock`은 항상 함께 커밋한다.
- Python 버전은 `.python-version`(3.11)을 따른다.

## 7. 명령어
```bash
uv sync                      # 환경 설치
uv run ruff check .          # 린트
uv run pytest                # 테스트
uv run grant-rag --help      # CLI (구현 후)
npm --prefix frontend run dev   # 프론트엔드 (구현 후)
ollama serve                 # 별도 터미널에서 Ollama 실행
```
필요한 로컬 모델: `ollama pull bge-m3`, `ollama pull qwen3:8b`

## 8. 테스트 규칙
- 파이프라인과 API는 Fake Port로 테스트한다 (Ollama, Qdrant, 외부 API 없이 실행 가능해야 한다).
- cleaner, normalizer, compose, 필터 의미(지역 + 전국, 마감, 결측), FallbackLLM 전환은 입력·출력 단위 테스트를 둔다.
- 외부 서비스를 연결한 실행 결과는 `docs/EVALUATION.md`에 실행 일시와 함께 기록한다.

## 9. Git 규칙
- 브랜치: `main`에서 작업하되 큰 기능은 `feat/<이름>` 브랜치를 사용한다.
- 커밋 메시지: `<종류>: <내용>` (종류: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`)
- 한 커밋에는 하나의 목적만 담는다.
- 커밋 전에 `git status`로 `.env`, `data/raw`, `.venv`가 포함되지 않았는지 확인한다.

## 10. 작업 완료 보고에 포함할 것
- 변경한 파일 목록
- 근거가 된 PRD 스토리 ID (예: 2-2)
- 실행한 테스트와 결과
- 확인하지 못한 항목
