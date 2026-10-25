#!/usr/bin/env python3
"""md-index — 把一堆 Markdown 笔记变成一个单文件、可搜索的 HTML 索引。

用法：
    python3 md_index.py ~/notes -o index.html --title "我的笔记"

零依赖，只用标准库。
"""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Sequence
from urllib.parse import quote

SKIP_DIRS = {".git", ".obsidian", ".trash", "node_modules", "__pycache__", ".venv"}
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
MARKUP_RE = re.compile(r"[*_`>#]+")


@dataclass(frozen=True)
class Note:
    rel: str
    title: str
    excerpt: str


def strip_markup(text: str) -> str:
    """去掉行内 Markdown 标记，留下可读文本。"""
    text = LINK_RE.sub(r"\1", text)
    text = MARKUP_RE.sub("", text)
    return " ".join(text.split())


def split_frontmatter(lines: Sequence[str]) -> list[str]:
    """丢弃以 --- 包裹的 YAML frontmatter。"""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return list(lines[i + 1 :])
    return list(lines)


def parse_note(path: Path, root: Path) -> Note:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = split_frontmatter(text.splitlines())

    title = ""
    excerpt = ""
    in_fence = False

    for raw in lines:
        line = raw.rstrip()
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        stripped = line.strip()
        if not title:
            if not stripped:
                continue
            match = HEADING_RE.match(line)
            if match:
                title = strip_markup(match.group(1))
                continue
            if stripped.startswith("#"):
                continue
            excerpt = strip_markup(stripped)
            break

        if not stripped or stripped[0] in "#->|":
            continue
        excerpt = strip_markup(stripped)
        break

    return Note(
        rel=path.relative_to(root).as_posix(),
        title=title or path.stem,
        excerpt=excerpt,
    )


def collect_notes(root: Path) -> list[Note]:
    """递归收集 root 下的 .md 文件，跳过隐藏/依赖目录。"""
    notes: list[Note] = []
    for path in sorted(root.rglob("*.md")):
        parents = path.relative_to(root).parts[:-1]
        if any(part in SKIP_DIRS for part in parents):
            continue
        notes.append(parse_note(path, root))
    notes.sort(key=lambda note: note.rel.lower())
    return notes


TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 32px 16px 64px;
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", sans-serif;
    background: #fbfbfa; color: #1f2328;
  }
  main { max-width: 820px; margin: 0 auto; }
  header {
    position: sticky; top: 0; z-index: 1;
    padding: 12px 0 14px; background: #fbfbfa;
    border-bottom: 1px solid #e6e6e3;
  }
  h1 { font-size: 20px; margin: 0 0 10px; }
  #q {
    width: 100%; padding: 9px 12px; font-size: 15px;
    border: 1px solid #d0d7de; border-radius: 8px; background: #fff; color: inherit;
  }
  #q:focus { outline: 2px solid #0969da33; border-color: #0969da; }
  #count { display: block; margin-top: 8px; font-size: 12.5px; color: #6e7781; }
  .note { padding: 18px 0 16px; border-bottom: 1px solid #ececea; }
  .note h2 { font-size: 16.5px; margin: 0 0 4px; font-weight: 600; }
  .note a { color: #0969da; text-decoration: none; }
  .note a:hover { text-decoration: underline; }
  .path { margin: 0 0 6px; font-size: 12.5px; color: #8c959f; font-family: ui-monospace, Menlo, monospace; }
  .excerpt { margin: 0; font-size: 14.5px; color: #57606a; }
  .empty { padding: 40px 0; text-align: center; color: #8c959f; }
</style>
</head>
<body>
<main>
  <header>
    <h1>$title</h1>
    <input id="q" type="search" placeholder="搜索标题、路径或摘要…" autocomplete="off">
    <span id="count"></span>
  </header>
$items
</main>
<script>
  var box = document.getElementById("q");
  var items = Array.prototype.slice.call(document.querySelectorAll(".note"));
  var count = document.getElementById("count");
  function apply() {
    var q = box.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function (el) {
      var hit = !q || el.dataset.k.indexOf(q) !== -1;
      el.hidden = !hit;
      if (hit) shown++;
    });
    count.textContent = shown + " / " + items.length + " 篇";
  }
  box.addEventListener("input", apply);
  apply();
</script>
</body>
</html>
"""
)

ITEM_TEMPLATE = Template(
    """  <article class="note" data-k="$key">
    <h2><a href="$href">$title</a></h2>
    <p class="path">$rel</p>
    <p class="excerpt">$excerpt</p>
  </article>
"""
)


def render(notes: Sequence[Note], title: str) -> str:
    """把笔记列表渲染成一个完整的 HTML 页面。"""
    items = "\n".join(
        ITEM_TEMPLATE.substitute(
            key=html.escape(f"{note.title} {note.rel} {note.excerpt}".lower(), quote=True),
            href=quote(note.rel),
            title=html.escape(note.title),
            rel=html.escape(note.rel),
            excerpt=html.escape(note.excerpt),
        )
        for note in notes
    )
    if not items:
        items = '  <p class="empty">这个目录里没有 .md 文件。</p>'
    return TEMPLATE.substitute(title=html.escape(title), items=items)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="md-index",
        description="把 Markdown 笔记目录生成单文件、可搜索的 HTML 索引。",
    )
    parser.add_argument("root", nargs="?", default=".", help="笔记目录（默认当前目录）")
    parser.add_argument("-o", "--output", default="index.html", help="输出文件（默认 index.html）")
    parser.add_argument("-t", "--title", default="Notes", help="页面标题（默认 Notes）")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"不是目录：{root}")

    notes = collect_notes(root)
    output = Path(args.output)
    output.write_text(render(notes, args.title), encoding="utf-8")
    print(f"{len(notes)} 篇笔记 → {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
