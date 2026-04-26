#!/usr/bin/env python3
"""Auto-tag diary entries based on keyword matching."""

import re
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("pyyaml is required. Run: pip install pyyaml")
    raise SystemExit(1)

DIARY_DIR = Path("diary")

RULES = [
    {
        "tag": "#工作",
        "keywords": [
            "加班", "项目", "会议", "汇报", "领导", "处室", "大队",
            "信控", "无人机", "智能体", "方案", "推进", "落实", "调研",
            "验收", "招标", "采购", "预算", "经费", "批示", "请示",
            "报告", "值班", "执勤", "部署", "排查", "整治", "专项行动",
        ],
    },
    {
        "tag": "#阅读",
        "keywords": ["读完", "看了", "阅读", "书籍", "书名", "作者", "小说", "散文", "论文", "报告文学"],
        "regex": [r"《([^》]+)》"],
    },
    {
        "tag": "#生活",
        "keywords": [
            "雪宝", "老婆", "家人", "爸妈", "吃饭", "散步", "逛街",
            "电影", "周末", "假期", "旅行", "宅", "做饭", "买菜", "家务",
        ],
    },
    {
        "tag": "#运动",
        "keywords": [
            "锻炼", "健身", "跑步", "练腿", "深蹲", "俯卧撑",
            "游泳", "打球", "操场", "体能", "训练",
        ],
    },
    {
        "tag": "#情绪",
        "keywords": [
            "焦虑", "情绪", "疲惫", "调整", "冥想", "反思", "感悟",
            "心得", "体会", "思考", "复盘", "总结", "成长", "阵痛",
        ],
    },
    {
        "tag": "#技术",
        "keywords": [
            "代码", "编程", "API", "GitHub", "Docker", "WSL", "模型",
            "大模型", "AI", "算法", "部署", "服务器", "数据库", "前端", "后端",
        ],
    },
    {
        "tag": "#人际",
        "keywords": [
            "沟通", "交流", "聊天", "吐槽", "饭局", "聚餐", "请客",
            "送礼", "关系", "人脉", "人情", "面子", "尊重", "分寸",
        ],
    },
]


def extract_tags(content: str) -> list[str]:
    """Return matched tags based on content text."""
    tags: set[str] = set()
    text = content.lower()

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

    # Extract tags from body
    auto_tags = extract_tags(body)
    if not auto_tags:
        return False

    # Merge with existing tags
    existing_tags = frontmatter.get("tags", [])
    if isinstance(existing_tags, str):
        existing_tags = [existing_tags]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    merged_tags = list(dict.fromkeys(existing_tags + auto_tags))

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
