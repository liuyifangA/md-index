import tempfile
import unittest
from pathlib import Path

from md_index import Note, collect_notes, parse_note, render, split_frontmatter, strip_markup


class StripMarkupTest(unittest.TestCase):
    def test_removes_inline_markup(self):
        self.assertEqual(strip_markup("**粗体** 和 `代码`"), "粗体 和 代码")

    def test_keeps_link_text_drops_target(self):
        self.assertEqual(strip_markup("看 [文档](https://example.com) 吧"), "看 文档 吧")

    def test_collapses_whitespace(self):
        self.assertEqual(strip_markup("  a   b  "), "a b")


class FrontmatterTest(unittest.TestCase):
    def test_drops_leading_block(self):
        lines = ["---", "tags: [a]", "---", "# 标题"]
        self.assertEqual(split_frontmatter(lines), ["# 标题"])

    def test_leaves_plain_text_alone(self):
        lines = ["# 标题", "正文"]
        self.assertEqual(split_frontmatter(lines), lines)

    def test_unclosed_block_is_not_treated_as_frontmatter(self):
        lines = ["---", "tags: [a]", "# 标题"]
        self.assertEqual(split_frontmatter(lines), lines)


class ParseNoteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_title_and_excerpt(self):
        path = self._write("a.md", "# 你好\n\n这是**摘要**。\n")
        note = parse_note(path, self.root)
        self.assertEqual(note.title, "你好")
        self.assertEqual(note.excerpt, "这是摘要。")

    def test_falls_back_to_filename(self):
        path = self._write("无标题.md", "只有正文，没有一级标题。\n")
        note = parse_note(path, self.root)
        self.assertEqual(note.title, "无标题")
        self.assertEqual(note.excerpt, "只有正文，没有一级标题。")

    def test_skips_code_fence_when_looking_for_excerpt(self):
        path = self._write("b.md", "# T\n\n```\ncode here\n```\n\n真正的正文\n")
        note = parse_note(path, self.root)
        self.assertEqual(note.excerpt, "真正的正文")

    def test_skips_list_quote_and_table_lines(self):
        path = self._write("c.md", "# T\n\n- 列表项\n> 引用\n| 表格 |\n\n正文\n")
        note = parse_note(path, self.root)
        self.assertEqual(note.excerpt, "正文")

    def test_relative_path_is_posix(self):
        path = self._write("sub/dir/d.md", "# D\n")
        note = parse_note(path, self.root)
        self.assertEqual(note.rel, "sub/dir/d.md")


class CollectNotesTest(unittest.TestCase):
    def test_skips_hidden_and_vendor_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.md").write_text("# K\n", encoding="utf-8")
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "skip.md").write_text("# S\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "x.md").write_text("# X\n", encoding="utf-8")

            rels = [note.rel for note in collect_notes(root)]
            self.assertEqual(rels, ["keep.md"])

    def test_sorted_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("b.md", "a.md", "C.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            rels = [note.rel for note in collect_notes(root)]
            self.assertEqual(rels, ["a.md", "b.md", "C.md"])


class RenderTest(unittest.TestCase):
    def test_escapes_html_and_quotes_attribute(self):
        page = render([Note(rel="a.md", title='<script>"x"', excerpt="1 < 2")], "T")
        self.assertNotIn("<script>", page.split("<body>")[0])
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("1 &lt; 2", page)

    def test_output_is_valid_shell_with_empty_list(self):
        page = render([], "空")
        self.assertIn("没有 .md 文件", page)
        self.assertIn("<title>空</title>", page)

    def test_links_are_url_encoded(self):
        page = render([Note(rel="目录/文件.md", title="t", excerpt="")], "T")
        self.assertIn('href="%E7%9B%AE%E5%BD%95/%E6%96%87%E4%BB%B6.md"', page)


if __name__ == "__main__":
    unittest.main()
