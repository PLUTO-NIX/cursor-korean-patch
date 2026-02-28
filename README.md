# Cursor Settings 한글 패치

Cursor IDE의 설정 페이지(Cursor Settings)를 한국어로 번역하는 도구입니다.

**하이브리드 방식**: 소스 패치(정적 문자열) + 런타임 DOM 번역(동적 문자열)을 조합합니다.

## 요구 사항

- **macOS** 또는 **Windows**
- Python 3.10+
- Cursor IDE

### 지원 경로

| OS | 기본 탐지 경로 |
|----|----------------|
| macOS | `/Applications/Cursor.app/Contents/Resources/app` |
| Windows | `%LOCALAPPDATA%\Programs\Cursor\resources\app` 또는 `%ProgramFiles%\Cursor\resources\app` |

다른 경로에 설치된 경우 `--cursor-path` 옵션으로 직접 지정할 수 있습니다. Windows에서 파일 수정 시 관리자 권한이 필요할 수 있습니다.

## 사용법

### 패치 적용 (권장: 통합 스크립트)

```bash
cd cursor-korean-patch
python3 src/repatch.py
```

**Windows** (PowerShell 또는 CMD):
```cmd
cd cursor-korean-patch
python src\repatch.py
```

이 명령이 다음을 한 번에 수행합니다:
- 이전 패치 복원
- 문자열 추출 → `translations/strings.json`
- 미번역 감지 → `translations/untranslated.json`
- 소스 패치 + 런타임 번역 적용

### 수동 실행 (단계별)

```bash
python3 src/extract.py                         # 문자열 추출
python3 src/patch.py -d translations/ko.json  # 패치 적용 (runtime_ko.json 자동 포함)
```

### 경로 직접 지정 (자동 탐지 실패 시)

```bash
python3 src/repatch.py --cursor-path /path/to/Cursor/resources/app
# Windows 예시:
python src\repatch.py --cursor-path "C:\Users\사용자\AppData\Local\Programs\Cursor\resources\app"
```

### 원본 복원

```bash
python3 src/patch.py --revert
# Windows: python src\patch.py --revert
```

### 원클릭 스크립트 (선택)

- **macOS**: `./scripts/run.sh` (bash)
- **Windows**: `scripts\run.bat` (CMD)

### Dry Run (시뮬레이션)

```bash
python3 src/patch.py -d translations/ko.json --dry-run
```

## Cursor 업데이트 후

Cursor 업데이트 시 `workbench.desktop.main.js`가 덮어씌워집니다.

1. `python3 src/repatch.py` 실행
2. `translations/untranslated.json`에 신규 문자열이 있으면 번역
3. 번역 결과를 `ko.json` 또는 `runtime_ko.json`에 추가 (아래 분류 기준 참고)
4. `python3 src/repatch.py --translate-and-patch` 실행
5. Cursor 재시작

**에이전트에게 요청 예시**: "cursor-korean-patch 재패치해줘"

## 아키텍처

| 방식 | 파일 | 대상 | 특징 |
|------|------|------|------|
| **소스 패치** | `ko.json` | 정적 문자열 (따옴표, 속성값) | 깜박임 없음, 즉시 적용 |
| **런타임 번역** | `runtime_ko.json` | `${변수}` 포함, 단어 하나짜리(Open, Cancel 등) | MutationObserver로 DOM 실시간 번역 |

- 단어 하나짜리(Open, Cancel, Default 등)는 파일 전체에서 수백 번 등장하므로 **소스 패치 불가** → 런타임만 사용
- `${변수}` 포함 문자열은 **런타임 전용**

## Cursor 버전 호환성

미니파이 시 변수명이 버전마다 바뀝니다 (예: 2.5.20 `WPl`, 2.5.25 `bLl`).
설정 섹션은 `general:"General"` 패턴으로 탐지하므로 새 버전에서도 동작합니다.

## 프로젝트 구조

```
cursor-korean-patch/
├── src/
│   ├── extract.py        # 문자열 추출 (getter, return, dropdown 등)
│   ├── patch.py          # 소스 패치 + 런타임 주입
│   ├── repatch.py        # 통합 파이프라인 (권장)
│   ├── diff.py           # 미번역 감지
│   └── runtime_inject.js # 런타임 번역 스크립트
├── scripts/
│   ├── run.sh            # macOS 원클릭 스크립트
│   └── run.bat            # Windows 원클릭 스크립트
├── translations/
│   ├── strings.json      # 추출된 영어 문자열
│   ├── ko.json           # 소스 패치 번역 사전
│   ├── runtime_ko.json   # 런타임 번역 사전
│   └── untranslated.json # 미번역 문자열 (repatch 시 생성)
├── .cursor/rules/
│   └── korean-patch.mdc  # 에이전트 재패치 지침
├── TRANSLATE_PROMPT.md    # AI 번역 에이전트 상세 지시사항
└── README.md
```
