"""法律知识库统一接口 - 初始化索引 + 检索单例"""

import os
from pathlib import Path
from typing import List, Optional

from .indexer import LegalIndexer
from .searcher import LegalSearcher, legal_search_tool
from .loader import LegalDocLoader


class LegalKnowledgeBase:
    """
    法律知识库统一管理类。

    提供索引构建、检索能力，全局单例。
    """

    _instance: Optional["LegalKnowledgeBase"] = None

    def __init__(
        self,
        embedding_model: str | None = None,
        embedding_base_url: str | None = None,
        index_path: str | None = None,
        chunk_mode: str = "by_article",
    ):
        embedding_model = embedding_model or os.getenv("LEGAL_EMBEDDING_MODEL", "nomic-embed-text")
        embedding_base_url = embedding_base_url or os.getenv("LEGAL_EMBEDDING_BASE_URL", "http://localhost:11434")
        index_path = index_path or os.getenv("LEGAL_INDEX_PATH", None)

        self.indexer = LegalIndexer(
            embedding_model=embedding_model,
            embedding_base_url=embedding_base_url,
            index_path=index_path,
        )
        self.searcher = LegalSearcher(indexer=self.indexer)
        self.chunk_mode = chunk_mode
        self._initialized = False

    @classmethod
    def get_instance(cls, **kwargs) -> "LegalKnowledgeBase":
        """获取或创建单例实例"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    def initialize(self, force_rebuild: bool = False) -> None:
        """初始化知识库（构建/加载索引）"""
        if self._initialized and not force_rebuild:
            return
        self.indexer.build_index(force_rebuild=force_rebuild, chunk_mode=self.chunk_mode)
        self._initialized = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
        contract_type: str | None = None,
    ):
        """检索法律条文"""
        if not self._initialized:
            self.initialize()
        return self.searcher.search(
            query=query,
            mode=mode,
            top_k=top_k,
            contract_type=contract_type,
        )

    def search_as_text(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
        contract_type: str | None = None,
    ) -> str:
        """检索并格式化为字符串，直接拼入 prompt"""
        results = self.search(query, top_k=top_k, mode=mode, contract_type=contract_type)
        if not results:
            return "未找到相关法律条文。"

        lines = ["【相关法律条文】"]
        for r in results:
            loc = f"{r.chapter}" if r.chapter else (r.section or r.book)
            lines.append(f"\n{r.article_no}（{loc}）:")
            lines.append(r.content)

        return "\n".join(lines)

    def stats(self) -> dict:
        """返回知识库状态"""
        return self.indexer.index_stats()

    @staticmethod
    def reset_instance() -> None:
        """重置单例（用于测试或重新初始化）"""
        LegalKnowledgeBase._instance = None


def get_legal_kb(**kwargs) -> LegalKnowledgeBase:
    """快捷函数：获取知识库实例"""
    return LegalKnowledgeBase.get_instance(**kwargs)
