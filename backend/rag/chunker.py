"""文本切分器 - 将法律条文切分为适合检索的 chunks"""

import re
from typing import List, Dict, Any, Optional


class LegalChunker:
    """
    法律文档专用切分器。

    策略：优先按「章节+条款」切分，每条单独做一个 chunk；
    如果条款文本过长（> 800 字），则在句号/分号处进一步切分。
    """

    MAX_CHUNK_SIZE = 800  # 字符数上限

    def chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_mode: str = "by_article",
    ) -> List[Dict[str, Any]]:
        """
        将结构化条文列表切分为 chunks

        Args:
            documents: loader 返回的条文列表
            chunk_mode: "by_article" | "by_chapter"
        """
        if chunk_mode == "by_chapter":
            return self._chunk_by_chapter(documents)
        return self._chunk_by_article(documents)

    def _chunk_by_article(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """每条法律条文作为一个 chunk"""
        chunks = []
        for doc in documents:
            text = doc["full_markdown"]
            if len(text) <= self.MAX_CHUNK_SIZE:
                chunks.append({
                    "content": text,
                    "article_no": doc["article_no"],
                    "chapter": doc["chapter"],
                    "section": doc["section"],
                    "book": doc["book"],
                    "metadata": {
                        "article_no": doc["article_no"],
                        "chapter": doc["chapter"],
                        "section": doc["section"],
                        "book": doc["book"],
                        "article_text": doc["article_text"],
                    },
                })
            else:
                # 条款过长时在句号/分号处切分，保留元信息
                sub_chunks = self._split_long_text(text)
                for idx, sub_text in enumerate(sub_chunks):
                    chunks.append({
                        "content": sub_text,
                        "article_no": f"{doc['article_no']}({idx + 1})",
                        "chapter": doc["chapter"],
                        "section": doc["section"],
                        "book": doc["book"],
                        "metadata": {
                            "article_no": doc["article_no"],
                            "chapter": doc["chapter"],
                            "section": doc["section"],
                            "book": doc["book"],
                            "article_text": doc["article_text"],
                            "sub_index": idx + 1,
                        },
                    })
        return chunks

    def _chunk_by_chapter(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将同一章节的条款合并为一个 chunk（保留最多上下文）"""
        chapters: Dict[str, List[Dict[str, Any]]] = {}
        for doc in documents:
            key = f"{doc['book']} / {doc['section']} / {doc['chapter']}"
            chapters.setdefault(key, []).append(doc)

        chunks = []
        for chapter_key, docs in chapters.items():
            # 拆分过于庞大的章节（如合同订立通则）
            combined_text = "\n\n".join(d["full_markdown"] for d in docs)
            if len(combined_text) <= self.MAX_CHUNK_SIZE * 3:
                parts = [combined_text]
            else:
                parts = self._split_long_text(combined_text)

            for idx, part in enumerate(parts):
                book = docs[0]["book"]
                section = docs[0]["section"]
                chapter = docs[0]["chapter"]
                chunks.append({
                    "content": part,
                    "article_no": f"{docs[0]['article_no']}..." if len(parts) > 1 else docs[0]["article_no"],
                    "chapter": chapter,
                    "section": section,
                    "book": book,
                    "metadata": {
                        "article_nos": [d["article_no"] for d in docs],
                        "chapter": chapter,
                        "section": section,
                        "book": book,
                        "part_index": idx + 1,
                        "total_parts": len(parts),
                    },
                })
        return chunks

    def _split_long_text(self, text: str, max_size: int | None = None) -> List[str]:
        """在句号、分号处将长文本切分，保留至少一半 max_size"""
        max_size = max_size or self.MAX_CHUNK_SIZE
        sentences = re.split(r"(?<=[；。；])", text)
        chunks = []
        current = []

        for s in sentences:
            if sum(len(x) for x in current) + len(s) <= max_size:
                current.append(s)
            else:
                if current:
                    chunks.append("".join(current))
                # 如果单个句子就超过限制，直接保留
                if len(s) > max_size:
                    chunks.append(s)
                    current = []
                else:
                    current = [s]

        if current:
            chunks.append("".join(current))

        return [c for c in chunks if c.strip()]
