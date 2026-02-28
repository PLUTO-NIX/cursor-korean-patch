#!/usr/bin/env python3
"""
이전 버전의 추출 결과와 비교하여 신규/변경/삭제된 문자열을 감지하는 스크립트.

사용법:
    python3 src/diff.py translations/old_strings.json translations/new_strings.json
    python3 src/diff.py --ko translations/ko.json translations/strings.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_strings(path: str) -> dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    strings = data.get("strings", data)
    if isinstance(strings, list):
        return {s["text"]: s for s in strings}
    return strings


def load_ko_dict(path: str) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    translations = data.get("translations", data)
    if isinstance(translations, list):
        return {t["original"]: t["translated"] for t in translations}
    return translations


def diff_strings(old_strings: dict, new_strings: dict) -> dict:
    old_keys = set(old_strings.keys())
    new_keys = set(new_strings.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    unchanged = sorted(old_keys & new_keys)

    return {
        "added": [{"text": k, **new_strings[k]} for k in added],
        "removed": [{"text": k, **old_strings[k]} for k in removed],
        "unchanged": unchanged,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "unchanged": len(unchanged),
        },
    }


def find_untranslated(strings_path: str, ko_path: str) -> list[dict]:
    with open(strings_path, "r", encoding="utf-8") as f:
        strings_data = json.load(f)
    strings = strings_data.get("strings", [])

    with open(ko_path, "r", encoding="utf-8") as f:
        ko_data = json.load(f)
    translations = ko_data.get("translations", [])
    translated_originals = {t["original"] for t in translations}

    untranslated = []
    for s in strings:
        if s["text"] not in translated_originals:
            untranslated.append(s)

    return untranslated


def main():
    parser = argparse.ArgumentParser(description="Cursor 문자열 버전 비교")
    subparsers = parser.add_subparsers(dest="command")

    diff_parser = subparsers.add_parser("diff", help="두 추출본 비교")
    diff_parser.add_argument("old", help="이전 버전 strings.json")
    diff_parser.add_argument("new", help="새 버전 strings.json")
    diff_parser.add_argument("--output", "-o", help="결과 저장 경로")

    untrans_parser = subparsers.add_parser("untranslated", help="미번역 문자열 찾기")
    untrans_parser.add_argument("--strings", "-s", default="translations/strings.json")
    untrans_parser.add_argument("--ko", "-k", default="translations/ko.json")
    untrans_parser.add_argument("--output", "-o", help="결과 저장 경로")

    args = parser.parse_args()

    if args.command == "diff":
        old = load_strings(args.old)
        new = load_strings(args.new)
        result = diff_strings(old, new)

        print(f"버전 비교 결과:")
        print(f"  추가됨: {result['summary']['added']}개")
        print(f"  삭제됨: {result['summary']['removed']}개")
        print(f"  변경없음: {result['summary']['unchanged']}개")

        if result["added"]:
            print(f"\n--- 추가된 문자열 ---")
            for item in result["added"][:20]:
                print(f"  + {item['text'][:80]}")
            if len(result["added"]) > 20:
                print(f"  ... +{len(result['added'])-20} more")

        if result["removed"]:
            print(f"\n--- 삭제된 문자열 ---")
            for item in result["removed"][:20]:
                print(f"  - {item['text'][:80]}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n결과 저장: {args.output}")

    elif args.command == "untranslated":
        untranslated = find_untranslated(args.strings, args.ko)
        print(f"미번역 문자열: {len(untranslated)}개\n")

        for item in untranslated[:30]:
            print(f"  [{item['category']}] {item['text'][:80]}")
        if len(untranslated) > 30:
            print(f"  ... +{len(untranslated)-30} more")

        if args.output:
            output_data = {
                "total": len(untranslated),
                "strings": untranslated,
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\n결과 저장: {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
