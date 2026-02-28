#!/usr/bin/env python3
"""
번역 사전(ko.json)을 기반으로 Cursor의 workbench.desktop.main.js를 패치하는 스크립트.

사용법:
    python3 src/patch.py [--dict translations/ko.json] [--dry-run]
    python3 src/patch.py --revert
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent

CURSOR_APP_PATH_MAC = "/Applications/Cursor.app/Contents/Resources/app"
WORKBENCH_REL = os.path.join("out", "vs", "workbench", "workbench.desktop.main.js")
BACKUP_SUFFIX = ".bak"


def _get_cursor_path_windows() -> Optional[str]:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    path = os.path.join(local_app_data, "Programs", "Cursor", "resources", "app")
    if os.path.exists(path):
        return path
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        path = os.path.join(program_files, "Cursor", "resources", "app")
        if os.path.exists(path):
            return path
    return None


def find_cursor_path() -> str:
    if sys.platform == "darwin":
        if os.path.exists(CURSOR_APP_PATH_MAC):
            return CURSOR_APP_PATH_MAC
    elif sys.platform == "win32":
        path = _get_cursor_path_windows()
        if path:
            return path
    raise FileNotFoundError(
        "Cursor 설치 경로를 찾을 수 없습니다. macOS/Windows만 지원합니다. "
        "--cursor-path 옵션으로 경로를 직접 지정하세요."
    )


def load_translation_dict(dict_path: str) -> dict:
    with open(dict_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("translations", data)


def backup_file(filepath: str) -> str:
    backup_path = filepath + BACKUP_SUFFIX
    if not os.path.exists(backup_path):
        shutil.copy2(filepath, backup_path)
        print(f"백업 생성: {backup_path}")
    else:
        print(f"기존 백업 사용: {backup_path}")
    return backup_path


def revert_file(filepath: str) -> bool:
    backup_path = filepath + BACKUP_SUFFIX
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, filepath)
        print(f"원본 복원 완료: {filepath}")
        return True
    print(f"백업 파일이 없습니다: {backup_path}", file=sys.stderr)
    return False


SETTINGS_START_PATTERN = re.compile(r'[A-Za-z]{2,4}=\{general:"General"')


def apply_patch(
    workbench_path: str,
    translations: dict,
    dry_run: bool = False,
    section_start_marker: bytes = b"WPl={",
    section_end_markers: list[bytes] = None,
) -> dict:
    if section_end_markers is None:
        section_end_markers = [b"Extend Cursor with Skills", b"Skills are specialized capabilities"]

    with open(workbench_path, "rb") as f:
        content = f.read()

    original_size = len(content)
    content_str = content.decode("utf-8", errors="replace")

    match = SETTINGS_START_PATTERN.search(content_str)
    if match:
        section_start = match.start()
    else:
        section_start = content_str.find("WPl={")
    if section_start == -1:
        raise ValueError("설정 섹션을 찾을 수 없습니다.")

    section_end_candidates = [content_str.find(m.decode()) for m in section_end_markers]
    section_end = max(e for e in section_end_candidates if e > 0) + 1000

    before = content_str[:section_start]
    section = content_str[section_start:section_end]
    after = content_str[section_end:]

    stats = {"applied": 0, "skipped": 0, "not_found": 0, "details": []}

    for entry in translations:
        original = entry.get("original", "")
        translated = entry.get("translated", "")
        match_type = entry.get("match_type", "exact")

        if not original or not translated or original == translated:
            stats["skipped"] += 1
            continue

        if match_type == "exact_quoted":
            escaped_original = json.dumps(original, ensure_ascii=False)[1:-1]
            escaped_translated = json.dumps(translated, ensure_ascii=False)[1:-1]

            count = 0

            for quote in ['"', "`"]:
                search = f"{quote}{escaped_original}{quote}"
                replace = f"{quote}{escaped_translated}{quote}"
                occurrences = section.count(search)
                if occurrences > 0:
                    section = section.replace(search, replace)
                    count += occurrences

            if count == 0:
                search = f">{escaped_original}<"
                replace = f">{escaped_translated}<"
                occurrences = section.count(search)
                if occurrences > 0:
                    section = section.replace(search, replace)
                    count += occurrences

            if count == 0:
                for ending in ['"', '`', ")", "<"]:
                    search = f">{escaped_original}{ending}"
                    replace = f">{escaped_translated}{ending}"
                    occurrences = section.count(search)
                    if occurrences > 0:
                        section = section.replace(search, replace)
                        count += occurrences
                        break

            if count == 0:
                for prefix in ["<div>", "<span>", "<button>", "<b>", "<strong>"]:
                    search = f"{prefix}{escaped_original}"
                    replace = f"{prefix}{escaped_translated}"
                    occurrences = section.count(search)
                    if occurrences > 0:
                        section = section.replace(search, replace)
                        count += occurrences
                        break

            if count > 0:
                stats["applied"] += 1
                stats["details"].append({
                    "original": original[:60],
                    "translated": translated[:60],
                    "occurrences": count,
                })
            else:
                stats["not_found"] += 1

        elif match_type == "exact":
            escaped_original = re.escape(original)
            pattern = re.compile(escaped_original)
            matches = pattern.findall(section)
            if matches:
                section = pattern.sub(translated, section)
                stats["applied"] += 1
                stats["details"].append({
                    "original": original[:60],
                    "translated": translated[:60],
                    "occurrences": len(matches),
                })
            else:
                stats["not_found"] += 1

        elif match_type == "regex":
            flags_str = entry.get("flags", "")
            flags = 0
            if "i" in flags_str:
                flags |= re.IGNORECASE
            pattern = re.compile(original, flags)
            matches = pattern.findall(section)
            if matches:
                section = pattern.sub(translated, section)
                stats["applied"] += 1
                stats["details"].append({
                    "original": original[:60],
                    "translated": translated[:60],
                    "occurrences": len(matches),
                })
            else:
                stats["not_found"] += 1

    patched = before + section + after

    runtime_dict_path = Path(__file__).parent.parent / "translations" / "runtime_ko.json"
    inject_js_path = Path(__file__).parent / "runtime_inject.js"
    runtime_injected = 0

    if runtime_dict_path.exists() and inject_js_path.exists():
        with open(runtime_dict_path, "r", encoding="utf-8") as f:
            runtime_data = json.load(f)
        runtime_entries = runtime_data.get("entries", [])

        if runtime_entries:
            with open(inject_js_path, "r", encoding="utf-8") as f:
                inject_template = f.read()

            runtime_json = json.dumps(runtime_entries, ensure_ascii=False)
            inject_code = inject_template.replace("'${RUNTIME_DICT}'", runtime_json)
            patched = inject_code + ";\n" + patched
            runtime_injected = len(runtime_entries)

    if not dry_run:
        backup_file(workbench_path)
        with open(workbench_path, "w", encoding="utf-8") as f:
            f.write(patched)

    patched_size = len(patched.encode("utf-8"))
    stats["original_size"] = original_size
    stats["patched_size"] = patched_size
    stats["size_diff"] = patched_size - original_size
    stats["runtime_injected"] = runtime_injected

    return stats


def main():
    parser = argparse.ArgumentParser(description="Cursor Settings 한글 패치")
    parser.add_argument(
        "--dict", "-d",
        default="translations/ko.json",
        help="번역 사전 경로 (default: translations/ko.json)",
    )
    parser.add_argument(
        "--cursor-path",
        default=None,
        help="Cursor 앱 경로 (default: 자동 탐색)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일을 수정하지 않고 시뮬레이션만 실행",
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="백업에서 원본 복원",
    )
    args = parser.parse_args()

    app_path = args.cursor_path or find_cursor_path()
    workbench_path = os.path.join(app_path, WORKBENCH_REL)

    if not os.path.exists(workbench_path):
        print(f"오류: {workbench_path} 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    if args.revert:
        success = revert_file(workbench_path)
        sys.exit(0 if success else 1)

    if not os.path.exists(args.dict):
        print(f"오류: 번역 사전 {args.dict}을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    translations = load_translation_dict(args.dict)
    mode = "DRY RUN" if args.dry_run else "PATCH"
    print(f"[{mode}] 번역 사전: {args.dict} ({len(translations)}개 항목)")
    print(f"[{mode}] 대상 파일: {workbench_path}")

    stats = apply_patch(workbench_path, translations, dry_run=args.dry_run)

    print(f"\n패치 결과:")
    print(f"  소스 패치 적용: {stats['applied']}개")
    print(f"  런타임 번역 주입: {stats.get('runtime_injected', 0)}개")
    print(f"  건너뜀: {stats['skipped']}개")
    print(f"  미발견: {stats['not_found']}개")
    print(f"  파일 크기: {stats['original_size']:,} → {stats['patched_size']:,} ({stats['size_diff']:+,} bytes)")

    if args.dry_run:
        print(f"\n(DRY RUN 모드 - 실제 파일은 수정되지 않았습니다)")
    else:
        print(f"\n패치 적용 완료! Cursor를 재시작해주세요.")

    if stats["not_found"] > 0:
        print(f"\n미발견 항목 수: {stats['not_found']}개 (Cursor 버전 변경으로 문자열이 변경되었을 수 있음)")


if __name__ == "__main__":
    main()
