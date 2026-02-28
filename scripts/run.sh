#!/bin/bash
#
# Cursor Settings 한글 패치 원클릭 스크립트
#
# 사용법:
#   ./scripts/run.sh          # 추출 + 패치 적용
#   ./scripts/run.sh --revert # 원본 복원
#   ./scripts/run.sh --dry-run # 시뮬레이션만 실행
#   ./scripts/run.sh --extract-only # 문자열 추출만
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TRANSLATIONS_DIR="$PROJECT_DIR/translations"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "python3이 설치되어 있지 않습니다."
        exit 1
    fi
}

check_cursor() {
    if [ ! -d "/Applications/Cursor.app" ]; then
        log_error "Cursor.app을 찾을 수 없습니다."
        exit 1
    fi
    log_info "Cursor 발견: /Applications/Cursor.app"
}

extract_strings() {
    log_info "문자열 추출 중..."
    python3 "$PROJECT_DIR/src/extract.py" -o "$TRANSLATIONS_DIR/strings.json"
    log_success "추출 완료: $TRANSLATIONS_DIR/strings.json"
}

check_untranslated() {
    if [ -f "$TRANSLATIONS_DIR/ko.json" ]; then
        log_info "미번역 문자열 확인 중..."
        python3 "$PROJECT_DIR/src/diff.py" untranslated \
            -s "$TRANSLATIONS_DIR/strings.json" \
            -k "$TRANSLATIONS_DIR/ko.json" \
            -o "$TRANSLATIONS_DIR/untranslated.json" 2>/dev/null || true
    fi
}

apply_patch() {
    local extra_args="$1"
    log_info "패치 적용 중..."
    python3 "$PROJECT_DIR/src/patch.py" \
        -d "$TRANSLATIONS_DIR/ko.json" \
        $extra_args
}

revert_patch() {
    log_info "원본 복원 중..."
    python3 "$PROJECT_DIR/src/patch.py" --revert
}

restart_cursor() {
    log_info "Cursor를 재시작합니다..."
    if pgrep -x "Cursor" > /dev/null 2>&1; then
        osascript -e 'quit app "Cursor"' 2>/dev/null || true
        sleep 2
    fi
    open -a "Cursor"
    log_success "Cursor 재시작 완료!"
}

main() {
    echo ""
    echo "================================================"
    echo "  Cursor Settings 한글 패치 도구"
    echo "================================================"
    echo ""

    check_python
    check_cursor

    case "${1:-}" in
        --revert)
            revert_patch
            log_success "원본 복원 완료! Cursor를 재시작해주세요."
            read -p "Cursor를 재시작하시겠습니까? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                restart_cursor
            fi
            ;;
        --dry-run)
            extract_strings
            check_untranslated
            apply_patch "--dry-run"
            ;;
        --extract-only)
            extract_strings
            check_untranslated
            log_success "추출 완료. translations/ 디렉토리를 확인하세요."
            ;;
        *)
            extract_strings
            check_untranslated
            apply_patch ""
            log_success "패치 적용 완료!"
            echo ""
            read -p "Cursor를 재시작하시겠습니까? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                restart_cursor
            fi
            ;;
    esac
}

main "$@"
