#!/usr/bin/env python3
"""Build a static gallery from EvoLinkAI/awesome-gpt-image-2-prompts cases.

Usage:
  python3 build.py            # uses ./.cache/awesome-gpt-image-2-prompts (clones if missing, pulls if present)
  python3 build.py --src PATH # use an existing local clone

The output is index.html in the same directory as this script.
The HTML template lives in template.html (extracted so the script stays small).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

UPSTREAM = "https://github.com/EvoLinkAI/awesome-gpt-image-2-prompts.git"
HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE / ".cache" / "awesome-gpt-image-2-prompts"
OUT = HERE / "index.html"

CATEGORIES = ["poster", "portrait", "character", "ad-creative", "ecommerce", "comparison", "ui"]

CASE_RE = re.compile(r"^###\s+Case\s+(?P<num>\d+):\s+(?P<rest>.+?)$", re.M)
LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)")
AUTHOR_RE = re.compile(r"by\s+\[@?(?P<author>[^\]]+)\]\((?P<url>[^)]+)\)")
IMG_RE = re.compile(r'<img[^>]+src="(?P<src>[^"]+)"', re.I)
PROMPT_RE = re.compile(r"\*\*Prompt[s]?:\*\*\s*\n+\s*```(?:\w*)?\n(?P<prompt>.*?)\n```", re.S)


def ensure_clone(src: Path) -> Path:
    if (src / ".git").exists():
        print(f"  pulling {src}")
        subprocess.run(["git", "-C", str(src), "pull", "--ff-only"], check=False, capture_output=True)
    else:
        print(f"  cloning {UPSTREAM} -> {src}")
        src.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", UPSTREAM, str(src)], check=True)
    return src


def parse_case_block(block, category, num):
    head = block.split("\n", 1)[0]
    title_match = LINK_RE.search(head)
    title = title_match.group("title").strip() if title_match else f"Case {num}"
    source_url = title_match.group("url").strip() if title_match else ""

    author_match = AUTHOR_RE.search(head)
    author = author_match.group("author").strip().lstrip("@") if author_match else ""
    author_url = author_match.group("url").strip() if author_match else ""

    img_match = IMG_RE.search(block)
    if not img_match:
        return None
    img_src = img_match.group("src")

    prompts = [m.group("prompt").strip() for m in PROMPT_RE.finditer(block)]
    if not prompts:
        return None

    return {
        "id": f"{category}-{num}",
        "category": category,
        "num": int(num),
        "title": title,
        "source_url": source_url,
        "author": author,
        "author_url": author_url,
        "image": img_src,
        "prompt": prompts[0],
        "extra_prompts": prompts[1:],
    }


def parse_category_file(path, category):
    text = path.read_text(encoding="utf-8")
    matches = list(CASE_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        c = parse_case_block(text[start:end], category, m.group("num"))
        if c:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC,
                    help="Path to a local clone (auto-cloned/pulled if not given)")
    args = ap.parse_args()
    src = ensure_clone(args.src)

    all_cases = []
    for cat in CATEGORIES:
        path = src / "cases" / f"{cat}.md"
        if not path.exists():
            print(f"  WARN: {path} missing")
            continue
        cs = parse_category_file(path, cat)
        all_cases.extend(cs)
        print(f"  {cat:14s}  {len(cs):3d} cases")
    print(f"  {'TOTAL':14s}  {len(all_cases):3d} cases")

    cases_json = json.dumps(all_cases, ensure_ascii=False)

    template_path = HERE / "template.html"
    if not template_path.exists():
        print(f"ERROR: missing {template_path}", file=sys.stderr)
        sys.exit(1)
    html = template_path.read_text(encoding="utf-8").replace("__CASES_JSON__", cases_json)
    OUT.write_text(html, encoding="utf-8")
    print(f"  -> {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
