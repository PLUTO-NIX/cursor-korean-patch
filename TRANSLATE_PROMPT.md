# Cursor Settings 한글 번역 에이전트 지시사항

## 작업 목표

Cursor IDE 설정 페이지의 영어 문자열을 한국어로 번역합니다.
`translations/untranslated.json`의 미번역 문자열을 `ko.json` 또는 `runtime_ko.json`에 추가합니다.

## 권장 워크플로우 (repatch.py)

```bash
cd cursor-korean-patch
python3 src/repatch.py              # 추출 + 미번역 감지 + 패치 적용
# 미번역이 있으면 번역 후:
python3 src/repatch.py --translate-and-patch
```

## ko.json vs runtime_ko.json 분류 기준

| 조건 | 추가 대상 | 이유 |
|------|-----------|------|
| `${변수}` 포함 | **runtime_ko.json** | 소스 패치 불가 (동적 조합) |
| 단어 하나 (Open, Cancel, Default, Apply 등) | **runtime_ko.json** | 파일 전체에 수백 번 등장 → 소스 패치 시 코드 깨짐 |
| 2단어 이상 정적 문자열 | **ko.json** | 소스 패치 가능 |
| 드롭다운 노이즈 (loud, op, quiet, unspecified) | **번역 생략** | 소리 설정 등, 번역 불필요 |

## ko.json 형식 (소스 패치)

```json
{
  "original": "영어 원문 (untranslated.json의 text 필드 그대로)",
  "translated": "한국어 번역",
  "match_type": "exact_quoted"
}
```

- `original`은 **완전히 동일**해야 함 (공백, 마침표, 따옴표 포함)
- `match_type`은 `exact_quoted` 유지

## runtime_ko.json 형식 (런타임 DOM 번역)

```json
{
  "en": "영어 원문 또는 부분 문자열",
  "ko": "한국어 번역",
  "type": "exact"
}
```

- `type`: `exact` (전체 일치), `partial` (부분 포함 시 치환)
- `${변수}` 포함 문자열: 고정 부분만 추출하여 `partial`로 추가 가능

## 번역 규칙

### 반드시 지켜야 할 것

- `original`/`en` 값은 원본과 **완전히 동일** (오타, 공백, 마침표 주의)
- 기술 용어 보존: API, MCP, Git, GitHub, PR, IDE, TypeScript, Python, Composer
- `${...}` 변수 플레이스홀더는 그대로 유지
- 합쇼체(-습니다/-입니다) 사용
- 이미 존재하는 항목 중복 추가 금지

### 절대 하지 말 것

- `original`/`en` 필드 수정
- 기술 용어 번역 (MCP, API, URL 등)
- 변수 플레이스홀더 번역

### 용어집

| 영어 | 한국어 |
|------|--------|
| Agent | 에이전트 |
| Background Agent / Cloud Agent | 클라우드 에이전트 |
| Settings | 설정 |
| Workspace | 워크스페이스 |
| Sandbox | 샌드박스 |
| Allowlist | 허용 목록 |
| Snapshot | 스냅샷 |
| Worktree | 워크트리 |
| Dashboard | 대시보드 |
| Marketplace | 마켓플레이스 |

## 주의사항: 원문 정확성

**소스 패치가 적용되지 않는 경우** (`not_found`):

1. **마침표 유무**: JS에서는 `"Only enable..."` (마침표 없음) + `${변수}` 형태일 수 있음. `ko.json`에 마침표를 붙여 넣으면 매칭 실패.
2. **원본 확인**: `workbench.desktop.main.js.bak`에서 `rg "문자열"` 또는 Python으로 정확한 형태 검색 후 `original`에 그대로 입력.
3. **커스텀 키**: `autoTitle`, `apiDescription` 등 extract.py 패턴에 없는 키는 `untranslated.json`에 없을 수 있음. 스크린샷으로 발견 시 수동 추가.

## 특수한 경우

1. **템플릿 변수 포함**: `${변수}`는 그대로 두고 나머지만 번역 → `runtime_ko.json`에 `partial`로 추가
2. **HTML/태그 포함**: 태그 구조 보존, 텍스트만 번역
3. **단일 단어**: `ko.json`이 아닌 `runtime_ko.json`에 추가 (소스 패치 위험)

## 패치 테스트

```bash
python3 src/patch.py -d translations/ko.json --dry-run
```

`미발견`이 많으면 Cursor 버전 변경으로 문자열이 바뀐 것. `repatch.py`로 재추출 후 `original` 값을 실제 JS와 맞춰 수정.

## 원본 복원

```bash
python3 src/patch.py --revert
```

## 플랫폼 지원

- **macOS**: `/Applications/Cursor.app/Contents/Resources/app` 자동 탐지
- **Windows**: `%LOCALAPPDATA%\Programs\Cursor\resources\app` 또는 `%ProgramFiles%\Cursor\resources\app` 자동 탐지
- 자동 탐지 실패 시: `--cursor-path` 옵션으로 경로 직접 지정. Windows에서 파일 수정 시 관리자 권한이 필요할 수 있음.
