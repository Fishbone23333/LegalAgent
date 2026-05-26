"""检索器 - 语义检索 + 关键词混合检索，支持 rerank"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from langchain_core.documents import Document

from .indexer import LegalIndexer


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    article_no: str
    chapter: str
    section: str
    book: str
    score: float
    metadata: Dict[str, Any]


class LegalSearcher:
    """
    法律知识库检索器。

    支持三种检索模式：
    - semantic: 纯语义向量检索
    - keyword: BM25 关键词检索
    - hybrid: 语义 + 关键词加权混合
    """

    def __init__(
        self,
        indexer: LegalIndexer | None = None,
        top_k: int = 5,
        rerank: bool = True,
        alpha: float = 0.7,  # 语义权重，keyword 权重 = 1-alpha
    ):
        self.indexer = indexer or LegalIndexer()
        self.top_k = top_k
        self.rerank = rerank
        self.alpha = alpha

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int | None = None,
        contract_type: str | None = None,
    ) -> List[SearchResult]:
        """
        检索相关法律条文

        Args:
            query: 用户查询
            mode: "semantic" | "keyword" | "hybrid"
            top_k: 返回数量（rerank 后会截断到原始数量）
            contract_type: "employment" | "housing" | None，按合同类型过滤
        """
        k = top_k or self.top_k
        vs = self.indexer.get_vectorstore()

        if vs is None:
            return []

        if mode == "semantic":
            docs = self._semantic_search(query, k * 3, vs)
        elif mode == "keyword":
            docs = self._keyword_search(query, k * 3)
        else:
            docs = self._hybrid_search(query, k * 3, vs)

        # 按合同类型过滤
        if contract_type:
            docs = self._filter_by_contract_type(docs, contract_type)

        # Rerank
        if self.rerank and docs:
            docs = self._rerank(query, docs[:k * 2])
            docs = docs[:k]

        return [self._doc_to_result(d) for d in docs]

    def _semantic_search(
        self,
        query: str,
        k: int,
        vs: Any,
    ) -> List[Tuple[Document, float]]:
        results = vs.similarity_search_with_score(query, k=k)
        return results

    def _keyword_search(
        self,
        query: str,
        k: int,
    ) -> List[Tuple[Document, float]]:
        """简单的关键词检索（基于文本相似度）"""
        vs = self.indexer.get_vectorstore()
        if vs is None:
            return []
        docs = vs.docstore._dict.values()
        keywords = self._extract_keywords(query)
        scored = []
        for doc in docs:
            text = doc.page_content
            score = sum(1 for kw in keywords if kw in text) / max(len(keywords), 1)
            if score > 0:
                scored.append((doc, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def _hybrid_search(
        self,
        query: str,
        k: int,
        vs: Any,
    ) -> List[Tuple[Document, float]]:
        """混合检索：语义 + 关键词"""
        semantic_results = self._semantic_search(query, k, vs)
        keyword_results = {
            doc.page_content: score
            for doc, score in self._keyword_search(query, k)
        }

        # 合并分数
        all_docs: Dict[str, Tuple[Document, float]] = {}
        for doc, s_score in semantic_results:
            key = doc.page_content
            k_score = keyword_results.get(key, 0.0)
            combined = self.alpha * self._normalize_score(s_score) + (1 - self.alpha) * k_score
            if key not in all_docs or combined > all_docs[key][1]:
                all_docs[key] = (doc, combined)

        results = list(all_docs.values())
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _rerank(
        self,
        query: str,
        docs: List[Tuple[Document, float]],
    ) -> List[Tuple[Document, float]]:
        """基于关键词重叠的简单 rerank"""
        query_keywords = self._extract_keywords(query)
        reranked = []
        for doc, base_score in docs:
            content = doc.page_content
            # 计算覆盖率
            coverage = sum(1 for kw in query_keywords if kw in content) / max(len(query_keywords), 1)
            # 计算密度（关键词在内容中出现的密度）
            density = sum(content.count(kw) for kw in query_keywords) / max(len(content), 1)
            final_score = base_score * 0.6 + coverage * 0.25 + density * 1e5 * 0.15
            reranked.append((doc, final_score))
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked

    def _filter_by_contract_type(
        self,
        docs: List[Tuple[Document, float]],
        contract_type: str,
    ) -> List[Tuple[Document, float]]:
        """按合同类型过滤"""
        employment_keywords = [
            "劳动", "用人单位", "劳动者", "劳动合同", "试用期", "工资",
            "社会保险", "公积金", "竞业限制", "违约金", "解除合同",
            "经济补偿", "年休假", "加班",
        ]
        housing_keywords = [
            "租赁", "出租人", "承租人", "租金", "押金", "维修",
            "房屋", "物业", "转租", "优先购买", "腾退",
        ]

        target_kws = employment_keywords if contract_type == "employment" else housing_keywords

        filtered = []
        others = []
        for doc, score in docs:
            text = doc.page_content
            relevance = sum(1 for kw in target_kws if kw in text)
            if relevance > 0:
                filtered.append((doc, score, relevance))
            else:
                others.append((doc, score, 0))

        filtered.sort(key=lambda x: x[2], reverse=True)
        others.sort(key=lambda x: x[1], reverse=True)
        return [(d, s) for d, s, _ in filtered + others]

    def _doc_to_result(self, doc_score: Tuple[Document, float]) -> SearchResult:
        doc, score = doc_score
        meta = doc.metadata
        return SearchResult(
            content=doc.page_content,
            article_no=meta.get("article_no", ""),
            chapter=meta.get("chapter", ""),
            section=meta.get("section", ""),
            book=meta.get("book", ""),
            score=score,
            metadata=meta,
        )

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """从查询中提取中文关键词（≥2字的词）"""
        # 移除标点和英文，提取中文词
        text = re.sub(r"[^\u4e00-\u9fff]", " ", query)
        words = [w for w in text.split() if len(w) >= 2]
        return words

    @staticmethod
    def _normalize_score(raw_score: float) -> float:
        """将距离分数归一化到 0-1（距离越小分数越高）"""
        return 1.0 / (1.0 + raw_score)


def legal_search_tool(query: str, top_k: int = 5, contract_type: str = "auto") -> str:
    """
    供 Agent 调用的 RAG 检索工具（同步函数形式）。

    在 Agent 的 prompt 中可以通过 {tool} 机制调用此函数，
    或在 risk_checker / debate 节点的代码中直接调用。

    Args:
        query: 自然语言检索查询
        top_k: 返回的条文数量
        contract_type: "employment" | "housing" | "auto"

    Returns:
        格式化的法律条文检索结果字符串
    """
    searcher = LegalSearcher(top_k=top_k)

    # auto 模式：尝试从 query 推断合同类型
    if contract_type == "auto":
        q_lower = query
        emp_kws = ["劳动", "试用", "工资", "社保", "公积金", "加班", "竞业", "解除"]
        hou_kws = ["租赁", "租金", "押金", "房东", "租客", "房屋", "维修", "转租"]
        emp_score = sum(1 for kw in emp_kws if kw in q_lower)
        hou_score = sum(1 for kw in hou_kws if kw in q_lower)
        contract_type = "employment" if emp_score > hou_score else "housing" if hou_score > emp_score else None

    results = searcher.search(query, mode="hybrid", top_k=top_k, contract_type=contract_type)

    if not results:
        return "未找到相关法律条文。"

    lines = ["【法律条文检索结果】"]
    for r in results:
        lines.append(f"\n📜 {r.article_no}（{r.chapter}）")
        lines.append(r.content)
        if r.score:
            lines.append(f"[相关度: {r.score:.3f}]")

    return "\n".join(lines)
