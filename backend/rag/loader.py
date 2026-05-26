"""文档加载器 - 从 markdown 文件加载法律条文"""

import re
from pathlib import Path
from typing import List, Dict, Any


class LegalDocLoader:
    """加载民法典 markdown 文件，按章节+条款结构化"""

    LEGAL_DIR = Path(__file__).parent.parent.parent / "legal"

    def load(self, filepath: str | Path | None = None) -> List[Dict[str, Any]]:
        """
        加载法律文档，返回结构化条文列表

        Returns:
            List[Dict] - 每条为一个 dict:
            {
                "chapter": "第一章 一般规定",
                "section": "第一分编 通则",
                "book": "第三编 合同",
                "article_no": "第四百六十三条",
                "article_text": "本编调整因合同产生的民事关系。",
                "full_markdown": "**第四百六十三条** 本编调整..."
            }
        """
        path = Path(filepath) if filepath else self.LEGAL_DIR / "中华人民共和国民法典.md"
        content = path.read_text(encoding="utf-8")
        return self._parse_legal_doc(content)

    def _parse_legal_doc(self, content: str) -> List[Dict[str, Any]]:
        """解析法律文档，按章节和条款切分"""
        lines = content.split("\n")

        current_book = ""
        current_section = ""
        current_chapter = ""
        documents = []

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # 追踪当前章节层级
            if line.startswith("# "):
                current_book = line.lstrip("# ").strip()
                current_section = ""
                current_chapter = ""
            elif line.startswith("## "):
                current_section = line.lstrip("## ").strip()
                current_chapter = ""
            elif line.startswith("### "):
                current_chapter = line.lstrip("### ").strip()

            # 匹配条款：`**第XXX条** 文字内容` 或 `**第XXX条**\n内容`（跨行）
            article_match = re.match(r"^\*\*(第[一二三四五六七八九十百零\d]+条)\*\*(.*)$", line)
            if article_match:
                article_no = article_match.group(1)
                first_part = article_match.group(2).strip()

                # 如果条款正文在同一行已完整，直接使用
                if first_part:
                    article_text = first_part
                else:
                    # 否则收集后续行直到下一条款或空行/新章节
                    article_text_parts = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].rstrip()
                        # 遇到新条款、新章节、空行结束
                        if re.match(r"^\*\*(第[一二三四五六七八九十百零\d]+条)\*\*", next_line):
                            break
                        if next_line.startswith("#"):
                            break
                        if next_line.strip() == "" and not article_text_parts:
                            j += 1
                            continue
                        if next_line.strip() == "":
                            break
                        article_text_parts.append(next_line.strip())
                        j += 1
                    article_text = "".join(article_text_parts).strip()

                documents.append({
                    "book": current_book,
                    "section": current_section,
                    "chapter": current_chapter,
                    "article_no": article_no,
                    "article_text": article_text,
                    "full_markdown": f"**{article_no}** {article_text}",
                })

            i += 1

        return documents

    def load_as_text(self, filepath: str | Path | None = None) -> str:
        """简单加载为纯文本（用于调试/备用）"""
        docs = self.load(filepath)
        return "\n\n".join(d["full_markdown"] for d in docs)
