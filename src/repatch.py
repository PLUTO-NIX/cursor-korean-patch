#!/usr/bin/env python3
"""
Cursor Settings 한글 재패치 통합 스크립트.

AI 에이전트가 이 스크립트 하나로 전체 파이프라인을 실행합니다:
1. 현재 패치 복원 (필요 시)
2. 새 버전 문자열 추출
3. 미번역 문자열 감지 → untranslated.json 출력
4. 기존 번역으로 패치 적용

사용법:
    python3 src/repatch.py                    # 전체 파이프라인
    python3 src/repatch.py --check            # 미번역 문자열만 확인
    python3 src/repatch.py --translate-and-patch  # 번역 후 패치 (ko.json 업데이트된 후)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TRANSLATIONS_DIR = PROJECT_DIR / "translations"

sys.path.insert(0, str(SCRIPT_DIR))
from extract import find_cursor_path, get_cursor_version, extract_all, WORKBENCH_REL
from patch import apply_patch, revert_file, backup_file, load_translation_dict
from diff import find_untranslated


def run_full_pipeline(apply: bool = True, cursor_path: Optional[str] = None):
    app_path = cursor_path or find_cursor_path()
    workbench_path = os.path.join(app_path, WORKBENCH_REL)
    version = get_cursor_version(app_path)

    print(f"{'='*50}")
    print(f"  Cursor Settings 한글 재패치")
    print(f"  Cursor 버전: {version}")
    print(f"{'='*50}\n")

    backup_path = workbench_path + ".bak"
    if os.path.exists(backup_path):
        print("[1/5] 이전 패치 복원 중...")
        revert_file(workbench_path)
    else:
        print("[1/5] 백업 없음 - 원본 상태로 진행")

    print("\n[2/5] 문자열 추출 중...")
    strings = extract_all(workbench_path)
    strings_path = TRANSLATIONS_DIR / "strings.json"
    strings_data = {
        "version": version,
        "total_strings": len(strings),
        "strings": strings,
    }
    with open(strings_path, "w", encoding="utf-8") as f:
        json.dump(strings_data, f, ensure_ascii=False, indent=2)
    print(f"   추출 완료: {len(strings)}개 문자열")

    ko_path = TRANSLATIONS_DIR / "ko.json"
    if not ko_path.exists():
        print("\n[3/5] ko.json이 없습니다. 새로 생성해주세요.")
        return

    print("\n[3/5] 미번역 문자열 확인 중...")
    untranslated = find_untranslated(str(strings_path), str(ko_path))
    untranslated_path = TRANSLATIONS_DIR / "untranslated.json"

    if untranslated:
        untranslated_data = {
            "version": version,
            "total": len(untranslated),
            "strings": untranslated,
        }
        with open(untranslated_path, "w", encoding="utf-8") as f:
            json.dump(untranslated_data, f, ensure_ascii=False, indent=2)
        print(f"   미번역: {len(untranslated)}개")
        print(f"   저장: {untranslated_path}")

        cats = {}
        for s in untranslated:
            cat = s["category"]
            cats[cat] = cats.get(cat, 0) + 1
        for cat, count in sorted(cats.items()):
            print(f"     {cat}: {count}개")
    else:
        print("   모든 문자열이 번역되어 있습니다!")
        if untranslated_path.exists():
            untranslated_path.unlink()

    if not apply:
        print("\n[체크 모드] 패치를 적용하지 않습니다.")
        if untranslated:
            print(f"\n다음 단계: {len(untranslated)}개 문자열을 번역하여 ko.json에 추가하세요.")
            print("그 후 'python3 src/repatch.py --translate-and-patch' 실행")
        return

    print("\n[4/5] 하이브리드 패치 적용 중...")
    translations = load_translation_dict(str(ko_path))
    stats = apply_patch(workbench_path, translations, dry_run=False)
    print(f"   소스 패치 적용: {stats['applied']}개")
    print(f"   런타임 번역 주입: {stats.get('runtime_injected', 0)}개")
    print(f"   건너뜀: {stats['skipped']}개")
    print(f"   미발견: {stats['not_found']}개")

    print(f"\n[5/5] 완료!")
    print(f"   Cursor를 재시작해주세요.")

    if untranslated:
        print(f"\n   참고: {len(untranslated)}개 미번역 문자열이 있습니다.")
        print(f"   translations/untranslated.json을 확인하세요.")


def main():
    parser = argparse.ArgumentParser(description="Cursor Settings 한글 재패치 통합 스크립트")
    parser.add_argument("--check", action="store_true", help="미번역 문자열만 확인 (패치 적용 안함)")
    parser.add_argument("--translate-and-patch", action="store_true", help="ko.json 업데이트 후 패치만 적용")
    parser.add_argument("--cursor-path", default=None, help="Cursor 앱 경로 (자동 탐지 실패 시 지정)")
    args = parser.parse_args()

    if args.translate_and_patch:
        app_path = args.cursor_path or find_cursor_path()
        workbench_path = os.path.join(app_path, WORKBENCH_REL)
        ko_path = TRANSLATIONS_DIR / "ko.json"
        translations = load_translation_dict(str(ko_path))
        print(f"하이브리드 패치 적용 중... ({len(translations)}개 소스 번역)")
        stats = apply_patch(workbench_path, translations, dry_run=False)
        print(f"소스 패치: {stats['applied']}개, 런타임 주입: {stats.get('runtime_injected', 0)}개, 미발견: {stats['not_found']}개")
        print("Cursor를 재시작해주세요.")
    else:
        run_full_pipeline(apply=not args.check, cursor_path=args.cursor_path)


if __name__ == "__main__":
    main()
