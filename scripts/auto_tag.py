#!/usr/bin/env python3
"""Auto-tag diary entries based on keyword matching from diary-tags.json."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("pyyaml is required. Run: pip install pyyaml")
    raise SystemExit(1)

DIARY_DIR = Path("diary")
TAGS_PATH = Path("diary-tags.json")

DEFAULT_RULES = [
    {"tag": "#工作", "keywords": ["加班","项目","会议","汇报","领导","处室","大队","信控","无人机","方案","推进","落实","调研","值班","执勤","部署"]},
    {"tag": "#阅读", "keywords": ["读完","看了","阅读","书籍"], "regex": [r"《([^》]+)》"]},
    {"tag": "#生活", "keywords": ["雪宝","老婆","家人","吃饭","散步","周末","假期","宅"]},
    {"tag": "#运动", "keywords": ["锻炼","健身","跑步","练腿","深蹲"]},
    {"tag": "#情绪", "keywords": ["焦虑","反思","感悟","复盘","成长","调整"]},
    {"tag": "#技术", "keywords": ["代码","API","GitHub","Docker","模型","AI","部署"]},
    {"tag": "#人际", "keywords": ["沟通","交流","饭局","关系","人脉","人情"]},
]


def load_rules() -> list[dict]:
    """Load tagging rules from diary-tags.json, fallback to defaults."""
    if TAGS_PATH.exists():
        try:
            data = json.loads(TAGS_PATH.read_text(encoding="utf-8"))
            tags = data.get("tags", [])
            rules = []
            for t in tags:
                rule = {"tag": t["name"], "keywords": t.get("keywords", [])}
                if "regex" in t:
                    rule["regex"] = t["regex"]
                rules.append(rule)
            return rules
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[WARN] Failed to load {TAGS_PATH}: {e}, using defaults")
    return DEFAULT_RULES


RULES = load_rules()


def extract_tags(content: str) -> list[str]:
    """Return matched tags based on content text."""
    text = content.lower()
    tags: set[str] = set()

    for rule in RULES:
        matched = False
        if "keywords" in rule:
            for kw in rule["keywords"]:
                if kw in text:
                    matched = True
                    break
        if not matched and "regex" in rule:
            for pattern in rule["regex"]:
                if re.search(pattern, content):
                    matched = True
                    break
        if matched:
            tags.add(rule["tag"])

    return sorted(tags)


def process_file(filepath: Path) -> bool:
    """Process a single diary file. Return True if modified."""
    content = filepath.read_text(encoding="utf-8")

    # Parse frontmatter
    frontmatter: dict = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2]
            except yaml.YAMLError:
                pass

    # Skip if manually edited
    if frontmatter.get("manual_edited"):
        print(f"Skip (manual_edited): {filepath.name}")
        return False

    auto_tags = extract_tags(body)
    if not auto_tags:
        return False

    existing_tags = frontmatter.get("tags", [])
    if isinstance(existing_tags, str):
        existing_tags = [existing_tags]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    # Separate system tags and user-defined tags
    system_tags = {r["tag"] for r in RULES}
    user_tags = [t for t in existing_tags if t not in system_tags]
    sys_tags = [t for t in existing_tags if t in system_tags]

    merged_sys = list(dict.fromkeys(sys_tags + auto_tags))
    merged_tags = list(dict.fromkeys(merged_sys + user_tags))

    if set(merged_tags) == set(existing_tags):
        return False

    frontmatter["tags"] = merged_tags
    frontmatter["auto_tagged"] = True
    frontmatter["auto_tagged_at"] = datetime.now(timezone.utc).isoformat()

    fm_yaml = yaml.dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    body_stripped = body.lstrip("\n")
    new_content = f"---\n{fm_yaml}---\n{body_stripped}"
    filepath.write_text(new_content, encoding="utf-8")
    return True


def main() -> None:
    modified = 0
    for md_file in sorted(DIARY_DIR.glob("*.md")):
        if process_file(md_file):
            modified += 1
            print(f"Tagged: {md_file.name}")
    print(f"Total modified: {modified}")


if __name__ == "__main__":
    main()
