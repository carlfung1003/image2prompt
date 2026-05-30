#!/usr/bin/env python3
"""Build a static gallery from multiple GPT-Image-2 prompt repos.

Sources (see SOURCES below):
  - EvoLinkAI/awesome-gpt-image-2-prompts  → cases/<category>.md
  - ZeroLu/awesome-gpt-image               → README.md (## sections + ### cases)
  - cases-local/<category>.md               → Carl's local additions

Usage:
  python3 build.py            # clones (or pulls) each upstream into .cache/
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
LOCAL_CASES = HERE / "cases-local"
OUT = HERE / "index.html"

# ────────────────────────────────────────────────────────────────────────────
# EvoLink parser — original behavior, per-category files
# ────────────────────────────────────────────────────────────────────────────
EVOLINK_CATS = ["poster", "portrait", "character", "ad-creative", "ecommerce", "comparison", "ui"]

EVOLINK_CASE_RE = re.compile(r"^###\s+Case\s+(?P<num>\d+):\s+(?P<rest>.+?)$", re.M)
LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)")
AUTHOR_RE = re.compile(r"by\s+\[@?(?P<author>[^\]]+)\]\((?P<url>[^)]+)\)")
IMG_HTML_RE = re.compile(r'<img[^>]+src="(?P<src>[^"]+)"', re.I)
IMG_MD_RE = re.compile(r'!\[[^\]]*\]\((?P<src>[^)\s]+)')
PROMPT_RE = re.compile(r"\*\*Prompt[s]?:\*\*\s*\n+\s*```(?:\w*)?\n(?P<prompt>.*?)\n```", re.S)


def parse_evolink_block(block, category, num):
    head = block.split("\n", 1)[0]
    title_match = LINK_RE.search(head)
    title = title_match.group("title").strip() if title_match else f"Case {num}"
    source_url = title_match.group("url").strip() if title_match else ""

    author_match = AUTHOR_RE.search(head)
    author = author_match.group("author").strip().lstrip("@") if author_match else ""
    author_url = author_match.group("url").strip() if author_match else ""

    img_match = IMG_HTML_RE.search(block)
    if not img_match:
        return None
    img_src = img_match.group("src")

    prompts = [m.group("prompt").strip() for m in PROMPT_RE.finditer(block)]
    if not prompts:
        return None

    return {
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


def parse_evolink(src: Path):
    cases = []
    for cat in EVOLINK_CATS:
        rel = f"cases/{cat}.md"
        path = src / rel
        if not path.exists():
            print(f"  WARN: {path} missing")
            continue
        text = path.read_text(encoding="utf-8")
        added = collect_added_dates(src, rel)
        matches = list(EVOLINK_CASE_RE.finditer(text))
        n_before = len(cases)
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end]
            c = parse_evolink_block(block, cat, m.group("num"))
            if c:
                c["id"] = f"evolinkai-{cat}-{m.group('num')}"
                c["source"] = "evolinkai"
                heading = block.split("\n", 1)[0]
                c["added_at"] = added.get(heading)
                cases.append(c)
        print(f"  evolinkai {cat:14s}  {len(cases) - n_before:3d}")
    return cases


# ────────────────────────────────────────────────────────────────────────────
# ZeroLu parser — single README.md, ## sections + ### cases
# Categories: 8 sections. Map "Typography & Poster" → poster, "Character" → character,
# "UI/UX & Social" → ui (shared with EvoLink). Add new ones: photography, game, video,
# infographics, image-editing.
# ────────────────────────────────────────────────────────────────────────────
ZEROLU_SECTIONS = [
    ("📷 Photography & Photorealism", "photography"),
    ("🎮 Game & Entertainment", "game"),
    ("📱 UI/UX & Social Media", "ui"),
    ("🎬 Video, Animation & Collage", "video"),
    ("📰 Typography & Poster Design", "poster"),
    ("📚 Infographics, Education & Documents", "infographics"),
    ("🎭 Character & Consistency", "character"),
    ("🖼️ Image Editing & Style Transfer", "image-editing"),
]

ZEROLU_RAW_BASE = "https://raw.githubusercontent.com/ZeroLu/awesome-gpt-image/main/"
ZEROLU_H2_RE = re.compile(r"^##\s+(?P<title>.+?)$", re.M)
ZEROLU_H3_RE = re.compile(r"^###\s+(?P<title>.+?)$", re.M)
ZEROLU_PROMPT_RE = re.compile(r"\*\*Prompt:\*\*\s*\n+\s*```(?:\w*)?\n(?P<prompt>.*?)\n```", re.S)
ZEROLU_SOURCE_RE = re.compile(r"\*?\*?Source:?\*?\*?:?\s*\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)")


def _resolve_zerolu_img(url: str) -> str:
    if url.startswith(("http://", "https://", "//")):
        return url
    return ZEROLU_RAW_BASE + url.lstrip("./")


def parse_zerolu(src: Path):
    """Parse ZeroLu's main README into cases keyed by mapped category."""
    path = src / "README.md"
    if not path.exists():
        print(f"  WARN: {path} missing")
        return []
    text = path.read_text(encoding="utf-8")
    added = collect_added_dates(src, "README.md")

    # Split into ## sections, keep only the ones in ZEROLU_SECTIONS
    h2s = [(m.start(), m.group("title").strip()) for m in ZEROLU_H2_RE.finditer(text)]
    h2s.append((len(text), ""))  # sentinel
    title_to_cat = {t: c for (t, c) in ZEROLU_SECTIONS}

    cases = []
    per_cat_counter = {}

    for i in range(len(h2s) - 1):
        start, h2_title = h2s[i]
        end = h2s[i + 1][0]
        if h2_title not in title_to_cat:
            continue
        cat = title_to_cat[h2_title]
        section = text[start:end]

        # Find ### case headings within this section
        h3s = [(m.start(), m.group("title").strip()) for m in ZEROLU_H3_RE.finditer(section)]
        h3s.append((len(section), ""))
        n_before = len([c for c in cases if c["category"] == cat or c.get("_z_cat") == cat])

        for j in range(len(h3s) - 1):
            block = section[h3s[j][0]:h3s[j + 1][0]]
            title = h3s[j][1]

            # First image — HTML <img> or markdown ![](...) — wins
            img_html = IMG_HTML_RE.search(block)
            img_md = IMG_MD_RE.search(block)
            if img_html and (not img_md or img_html.start() <= img_md.start()):
                img_src = img_html.group("src")
            elif img_md:
                img_src = img_md.group("src")
            else:
                continue
            img_src = _resolve_zerolu_img(img_src)

            # First fenced prompt
            pm = ZEROLU_PROMPT_RE.search(block)
            if not pm:
                continue
            prompt = pm.group("prompt").strip()

            # Source/author (optional)
            sm = ZEROLU_SOURCE_RE.search(block)
            if sm:
                author_text = sm.group("text").strip().lstrip("@")
                source_url = sm.group("url").strip()
                # X/Twitter handle → use as author; otherwise keep as plain text
                author = author_text
                author_url = source_url
            else:
                author = ""
                author_url = ""
                source_url = ""

            per_cat_counter[cat] = per_cat_counter.get(cat, 0) + 1
            num = per_cat_counter[cat]

            cases.append({
                "id": f"zerolu-{cat}-{num}",
                "source": "zerolu",
                "category": cat,
                "num": num,
                "title": title,
                "source_url": source_url,
                "author": author,
                "author_url": author_url,
                "image": img_src,
                "prompt": prompt,
                "extra_prompts": [],
                "added_at": added.get(f"### {title}"),
            })

        added_count = per_cat_counter.get(cat, 0) - n_before
        print(f"  zerolu    {cat:14s}  {added_count:3d}")

    return cases


# ────────────────────────────────────────────────────────────────────────────
# Local cases — same format as EvoLink upstream
# ────────────────────────────────────────────────────────────────────────────
def parse_local():
    if not LOCAL_CASES.exists():
        return []
    cases = []
    # Use the project repo's git history (cases-local lives here) for added_at;
    # fall back to file mtime for uncommitted local cases.
    proj_repo = HERE if (HERE / ".git").exists() else None
    for cat_dir in EVOLINK_CATS:
        rel = f"cases-local/{cat_dir}.md"
        path = LOCAL_CASES / f"{cat_dir}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        added = collect_added_dates(proj_repo, rel) if proj_repo else {}
        from datetime import datetime, timezone
        mtime_iso = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        matches = list(EVOLINK_CASE_RE.finditer(text))
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end]
            c = parse_evolink_block(block, cat_dir, m.group("num"))
            if c:
                c["id"] = f"local-{cat_dir}-{m.group('num')}"
                c["source"] = "local"
                c["local"] = True
                heading = block.split("\n", 1)[0]
                c["added_at"] = added.get(heading) or mtime_iso
                cases.append(c)
        if cases:
            print(f"  local     {cat_dir:14s}  {sum(1 for x in cases if x['category'] == cat_dir):3d}")
    return cases


# ────────────────────────────────────────────────────────────────────────────
# Source registry
# ────────────────────────────────────────────────────────────────────────────
SOURCES = [
    {
        "id": "evolinkai",
        "name": "EvoLinkAI",
        "repo_url": "https://github.com/EvoLinkAI/awesome-gpt-image-2-prompts.git",
        "dir": "awesome-gpt-image-2-prompts",
        "parser": parse_evolink,
    },
    {
        "id": "zerolu",
        "name": "ZeroLu",
        "repo_url": "https://github.com/ZeroLu/awesome-gpt-image.git",
        "dir": "awesome-gpt-image",
        "parser": parse_zerolu,
    },
]


def ensure_clone(repo_url: str, dest: Path):
    if (dest / ".git").exists():
        print(f"  pulling {dest.name}")
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False, capture_output=True)
    else:
        print(f"  cloning {repo_url}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Full history needed for added-date attribution per case
        subprocess.run(["git", "clone", repo_url, str(dest)], check=True)
        return
    # If a previous run cloned with --depth 1, deepen so git log shows real dates
    is_shallow = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "--is-shallow-repository"],
        capture_output=True, text=True,
    ).stdout.strip() == "true"
    if is_shallow:
        print(f"  unshallowing {dest.name}")
        subprocess.run(["git", "-C", str(dest), "fetch", "--unshallow"], check=False, capture_output=True)


def collect_added_dates(repo_path: Path, file_rel: str) -> dict:
    """Walk file's full diff history; return {added_line_text: earliest_iso_date}.

    Used to attribute each `### Case N:` (EvoLink) or `### Title` (ZeroLu) heading
    to the commit that first introduced it. setdefault preserves the earliest hit.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--reverse", "--format=COMMIT %cI", "-p", "--", file_rel],
        capture_output=True, text=True,
    )
    dates = {}
    cur_date = None
    for line in proc.stdout.splitlines():
        if line.startswith("COMMIT "):
            cur_date = line[7:]
        elif cur_date and line.startswith("+") and not line.startswith("+++"):
            content = line[1:]
            if content.startswith("### "):
                dates.setdefault(content, cur_date)
    return dates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="Comma-separated source ids to build (e.g. 'evolinkai,zerolu')")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None

    all_cases = []
    for s in SOURCES:
        if only and s["id"] not in only:
            continue
        dest = CACHE / s["dir"]
        ensure_clone(s["repo_url"], dest)
        cs = s["parser"](dest)
        all_cases.extend(cs)
        print(f"  {s['id']:10s} TOTAL          {len(cs):3d}")

    local = parse_local()
    all_cases.extend(local)

    by_source = {}
    for c in all_cases:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    print(f"\n  GRAND TOTAL: {len(all_cases)} cases  ({', '.join(f'{k}={v}' for k, v in by_source.items())})")

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
