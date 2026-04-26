#!/usr/bin/env python3
"""Auto-tag diary entries based on keyword matching."""

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
RULES_PATH = Path(__file__).with_name("tag_rules.json")


def load_rules() -> list[dict]:
    """Load tagging rules from JSON file."""
    if RULES_PATH.exists():
        data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        return data.get("rules", [])
    return []


RULES = load_rules()


def extract_tags(content: str) -> list[str]:
    """Return matched tags based on content text, with exclude_from handling."""
    text = content.lower()
    matched_rules: list[dict] = []

    for rule in RULES:
        matched = False
        # Keyword matching
        if "keywords" in rule:
            for kw in rule["keywords"]:
                if kw in text:
                    matched = True
                    break
        # Regex matching
        if not matched and "regex" in rule:
            for pattern in rule["regex"]:
                if re.search(pattern, content):
                    matched = True
                    break
        if matched:
            matched_rules.append(rule)

    # Build tag set and check exclusions
    tags: set[str] = set()
    for rule in matched_rules:
        tag = rule["tag"]
        excludes = rule.get("exclude_from", [])
        # If this tag excludes another, check if that other tag is also matched
        if excludes:
            excluded_tags = set(excludes)
            other_matched = {r["tag"] for r in matched_rules if r["tag"] != tag}
            # Only keep this tag if none of its excluded tags are matched
            if not excluded_tags & other_matched:
                tags.add(tag)
        else:
            tags.add(tag)

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

    # Extract auto tags from body
    auto_tags = extract_tags(body)
    if not auto_tags:
        return False

    # Merge tags: keep existing tags, append auto tags
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

    # Update frontmatter
    frontmatter["tags"] = merged_tags
    frontmatter["auto_tagged"] = True
    frontmatter["auto_tagged_at"] = datetime.now(timezone.utc).isoformat()

    # Rebuild file content
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
