#!/usr/bin/env python3
"""
Cursor Settings 페이지에서 번역 대상 문자열을 추출하는 스크립트.

사용법:
    python3 src/extract.py [--output translations/strings.json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

CURSOR_APP_PATH_MAC = "/Applications/Cursor.app/Contents/Resources/app"
WORKBENCH_REL = os.path.join("out", "vs", "workbench", "workbench.desktop.main.js")
PRODUCT_JSON_REL = "product.json"

# 설정 섹션 마커 (미니파이 시 변수명 변경됨 — 2.5.20: WPl, 2.5.25: bLl)
SETTINGS_START_PATTERN = rb"[A-Za-z]{2,4}=\{general:\"General\""
SETTINGS_START_FALLBACK = b"WPl={"
SETTINGS_END_MARKERS = [b"Extend Cursor with Skills", b"Skills are specialized capabilities"]
END_BUFFER = 2000


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


def get_cursor_version(app_path: str) -> str:
    product_json = os.path.join(app_path, PRODUCT_JSON_REL)
    with open(product_json, "r") as f:
        data = json.load(f)
    return data.get("version", "unknown")


def read_settings_section(workbench_path: str) -> tuple[bytes, int, int]:
    with open(workbench_path, "rb") as f:
        content = f.read()

    match = re.search(SETTINGS_START_PATTERN, content)
    if match:
        start = match.start()
    else:
        start = content.find(SETTINGS_START_FALLBACK)
    if start == -1:
        raise ValueError("설정 섹션 시작 마커를 찾을 수 없습니다.")

    end = max(content.find(m) for m in SETTINGS_END_MARKERS)
    if end == -1:
        raise ValueError("설정 섹션 끝 마커를 찾을 수 없습니다.")
    end += END_BUFFER

    return content[start:end], start, end


def extract_tab_names(section: str) -> list[dict]:
    results = []
    # 탭 객체 패턴 (미니파이 시 변수명 변경: WPl, bLl 등)
    wpl_match = re.search(r"[A-Za-z]{2,4}=\{(.*?)\}", section)
    if not wpl_match:
        return results

    raw = wpl_match.group(1)
    for m in re.finditer(r'(?:"([^"]+)"|(\w+))\s*:\s*"([^"]+)"', raw):
        key = m.group(1) or m.group(2)
        value = m.group(3)
        results.append({
            "text": value,
            "key": f"tab.{key}",
            "category": "tab_name",
            "context": f"WPl tab label for '{key}'",
        })
    return results


def extract_oe_templates(section: str) -> list[dict]:
    results = []
    seen = set()

    for m in re.finditer(r'Oe\([`"](.+?)["`]\)', section, re.DOTALL):
        template = m.group(1)

        texts_in_tags = re.findall(r">([^<>]{2,})<", template)
        for text in texts_in_tags:
            text = text.strip()
            if text and text not in seen and _is_translatable(text):
                seen.add(text)
                results.append({
                    "text": text,
                    "key": f"template.{_make_key(text)}",
                    "category": "oe_template",
                    "context": f"HTML template text: <...>{text}<...>",
                })

        full_text = re.sub(r"<[^>]+>", "", template).strip()
        if full_text and full_text not in seen and _is_translatable(full_text):
            if len(full_text) > 5:
                seen.add(full_text)
                results.append({
                    "text": full_text,
                    "key": f"template_full.{_make_key(full_text)}",
                    "category": "oe_template_full",
                    "context": f"Full template text (tags removed)",
                })

    return results


def extract_property_values(section: str) -> list[dict]:
    results = []
    seen = set()

    prop_patterns = [
        r'(?:title|label|description|placeholder|text|message|caption|heading|tooltip|ariaLabel)\s*:\s*"([^"]{3,300})"',
        r'(?:title|label|description|placeholder|text|message|caption|heading|tooltip|ariaLabel)\s*:\s*`([^`]{3,300})`',
    ]

    for pattern in prop_patterns:
        for m in re.finditer(pattern, section):
            text = m.group(1).strip()
            if text not in seen and _is_translatable(text, allow_single_word=True):
                seen.add(text)
                results.append({
                    "text": text,
                    "key": f"prop.{_make_key(text)}",
                    "category": "property_value",
                    "context": f"Property value in settings code",
                })

    return results


def extract_getter_templates(section: str) -> list[dict]:
    """getter + 템플릿 리터럴: get description(){return`...${var}...`}"""
    results = []
    seen = set()

    pattern = r'(?:get\s+)?(?:description|label|title)\s*\(\)\s*\{return\s*`([^`]{5,500})`'
    for m in re.finditer(pattern, section):
        text = m.group(1).strip()
        if text not in seen and len(text) > 5:
            seen.add(text)
            results.append({
                "text": text,
                "key": f"getter.{_make_key(text)}",
                "category": "getter_template",
                "context": "Getter function returning template literal",
            })

    return results


def extract_return_values(section: str) -> list[dict]:
    """switch/case return 값: return"Ask Every Time" """
    results = []
    seen = set()

    pattern = r'return\s*"([A-Z][^"]{3,80})"'
    for m in re.finditer(pattern, section):
        text = m.group(1).strip()
        if text not in seen and _is_translatable(text) and not text.startswith(("STATUS_", "CURSOR_", "cursor-")):
            seen.add(text)
            results.append({
                "text": text,
                "key": f"return.{_make_key(text)}",
                "category": "return_value",
                "context": "Return value string in settings code",
            })

    return results


def extract_dropdown_items(section: str) -> list[dict]:
    """드롭다운/선택 항목: {id:"...", label:"..."} """
    results = []
    seen = set()

    pattern = r'id:\s*"[^"]+"\s*,\s*(?:label|title):\s*"([^"]{1,80})"'
    for m in re.finditer(pattern, section):
        text = m.group(1).strip()
        if text not in seen and len(text) >= 2 and re.search(r'[a-zA-Z]', text):
            if not text.startswith(("vs/", "http", "cursor-", "\\")) and not re.match(r'^[a-z]+\.[a-z]', text):
                seen.add(text)
                results.append({
                    "text": text,
                    "key": f"dropdown.{_make_key(text)}",
                    "category": "dropdown_item",
                    "context": "Dropdown/select item label",
                })

    return results


def extract_inline_strings(section: str) -> list[dict]:
    """설정 코드 내 인라인 문자열 리터럴 추출 (버튼 텍스트, 상태 메시지 등)."""
    results = []
    seen = set()

    patterns = [
        r'"((?:Enable|Disable|Show|Hide|Add|Remove|Delete|Save|Cancel|Apply|Reset|Configure|Edit|Create|Update|Refresh|Close|Open|Browse|Import|Export|Copy|Paste|Undo|Redo|Search|Filter|Sort|Select|Deselect|Expand|Collapse|Download|Upload|Install|Uninstall|Connect|Disconnect|Verify|Test|Submit|Approve|Reject|Allow|Block|Deny|Accept|Decline)[^"]{0,100})"',
        r'"((?:No |Not |Cannot |Failed |Error |Warning |Info |Success |Loading|Saving|Waiting|Processing|Checking|Connecting)[^"]{0,150})"',
        r'"((?:Are you sure|This will|This cannot|You can|You have|You need|Please |If you |When )[^"]{0,200})"',
        r'"((?:Enabled|Disabled|Active|Inactive|On|Off|Yes|No|Default|Custom|Auto|Manual|Always|Never|Optional|Required) \([^"]{0,100}\))"',
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, section):
            text = m.group(1).strip()
            if text not in seen and _is_translatable(text) and len(text) > 5:
                seen.add(text)
                results.append({
                    "text": text,
                    "key": f"inline.{_make_key(text)}",
                    "category": "inline_string",
                    "context": "Inline string literal in settings code",
                })

    return results


def _is_translatable(text: str, allow_single_word: bool = False) -> bool:
    if not text or len(text) < 2:
        return False
    if text.startswith(("vs/", "http", "vscode", "${", "\\", "cursor-settings-")):
        return False
    if re.match(r"^[\w.-]+$", text) and " " not in text:
        if allow_single_word and re.match(r"^[A-Z]", text) and len(text) >= 3:
            return True
        return False
    if re.match(r"^[^a-zA-Z]*$", text):
        return False
    if text.startswith(("&&", "||")):
        return False
    if re.match(r"^[a-z]+\.[a-z]", text):
        return False
    if len(text) > 300:
        return False
    return True


def _make_key(text: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", text[:50]).strip("_").lower()
    return key or "unknown"


def extract_all(workbench_path: str) -> list[dict]:
    section_bytes, start_offset, end_offset = read_settings_section(workbench_path)
    section = section_bytes.decode("utf-8", errors="replace")

    all_strings = []
    seen_texts = set()

    extractors = [
        extract_tab_names,
        extract_oe_templates,
        extract_property_values,
        extract_getter_templates,
        extract_return_values,
        extract_dropdown_items,
        extract_inline_strings,
    ]

    for extractor in extractors:
        for item in extractor(section):
            if item["text"] not in seen_texts:
                seen_texts.add(item["text"])
                all_strings.append(item)

    all_strings.sort(key=lambda x: (x["category"], x["text"]))

    return all_strings


def main():
    parser = argparse.ArgumentParser(description="Cursor Settings 문자열 추출")
    parser.add_argument(
        "--output", "-o",
        default="translations/strings.json",
        help="추출 결과 저장 경로 (default: translations/strings.json)",
    )
    parser.add_argument(
        "--cursor-path",
        default=None,
        help="Cursor 앱 경로 (default: 자동 탐색)",
    )
    args = parser.parse_args()

    app_path = args.cursor_path or find_cursor_path()
    workbench_path = os.path.join(app_path, WORKBENCH_REL)

    if not os.path.exists(workbench_path):
        print(f"오류: {workbench_path} 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    version = get_cursor_version(app_path)
    print(f"Cursor 버전: {version}")
    print(f"Workbench 파일: {workbench_path}")

    strings = extract_all(workbench_path)

    categories = {}
    for s in strings:
        cat = s["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n추출 결과:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}개")
    print(f"  총합: {len(strings)}개")

    output_data = {
        "version": version,
        "cursor_path": app_path,
        "total_strings": len(strings),
        "categories": categories,
        "strings": strings,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {output_path}")
    return strings


if __name__ == "__main__":
    main()
