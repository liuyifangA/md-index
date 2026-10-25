# md-index

把一堆 Markdown 笔记变成一个**单文件、可搜索、可离线打开**的 HTML 索引。

零依赖，只要有 Python 3.9+。生成的页面不需要服务器，双击就能看，也能直接丢到任何静态托管上。

![截图](assets/screenshot.png)

## 为什么做这个

笔记软件导出的 Markdown 动辄几百个文件，想整理一份目录给人看（或者给自己回顾），一般有两条路：换一个更重的工具，或者手动写一份索引。这个脚本只做一件事——扫一遍目录，把每篇的标题和第一段摘出来，生成一个能搜索的 HTML 页面。

## 用法

```bash
python3 md_index.py ~/notes -o index.html --title "我的笔记"
```

参数：

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `root` | 笔记目录 | 当前目录 |
| `-o, --output` | 输出文件 | `index.html` |
| `-t, --title` | 页面标题 | `Notes` |

想先看看效果，用自带的示例：

```bash
python3 md_index.py examples -o index.html --title "示例笔记"
```

## 提取规则

- **标题**：第一个 `# ` 一级标题；没有就用文件名。
- **摘要**：标题之后的第一段正文。跳过列表、引用、表格、代码块。
- **跳过**：YAML frontmatter、`.git`、`.obsidian`、`node_modules` 等目录。
- **转义**：标题和摘要里的 HTML 会被转义，笔记里写 `<script>` 也不会破坏页面。

这几条是刻意做窄的：按你的笔记习惯改几行就行，逻辑都在 `parse_note()` 里。

## 开发

```bash
python3 -m unittest -v
```

16 个用例，覆盖标题/摘要提取、frontmatter、目录过滤、HTML 转义和链接编码。

## 已知限制

- 只扫描 `.md`，不解析 wikilink（`[[双链]]`）和反向链接。
- 摘要只取一段，不做全文索引；搜索走的是浏览器端字符串匹配。
- 没有增量构建，每次都全量重扫（几千个文件仍然是秒级）。

## License

[MIT](LICENSE)
