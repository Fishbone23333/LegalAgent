"""向量索引器 - 将法律条文转换为向量并存储到 FAISS"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .loader import LegalDocLoader
from .chunker import LegalChunker


class LegalIndexer:
    """
    法律知识库索引器。

    负责：
    1. 加载民法典 markdown
    2. 切分为 chunks
    3. 向量化后存入 FAISS
    4. 持久化索引到磁盘
    """

    def __init__(
        self,
        embedding_model: str = "nomic-embed-text",
        embedding_base_url: str = "http://localhost:11434",
        index_path: str | None = None,
    ):
        self.loader = LegalDocLoader()
        self.chunker = LegalChunker()
        self.embedding_model = embedding_model
        self.embedding_base_url = embedding_base_url
        self.index_path = Path(index_path) if index_path else self._default_index_path()
        self._embeddings: Optional[OllamaEmbeddings] = None
        self._vectorstore: Optional[FAISS] = None

    def _default_index_path(self) -> Path:
        base = Path(__file__).parent / "data"
        base.mkdir(parents=True, exist_ok=True)
        return base / "legal_faiss"

    def _get_embeddings(self) -> OllamaEmbeddings:
        if self._embeddings is None:
            self._embeddings = OllamaEmbeddings(
                model=self.embedding_model,
                base_url=self.embedding_base_url,
            )
        return self._embeddings

    def build_index(
        self,
        force_rebuild: bool = False,
        chunk_mode: str = "by_article",
        legal_file: str | None = None,
    ) -> FAISS:
        """
        构建或加载索引

        Args:
            force_rebuild: 强制重建索引
            chunk_mode: "by_article" 或 "by_chapter"
            legal_file: 可选，指定法律文件路径
        """
        if not force_rebuild and self._load_index():
            return self._vectorstore

        documents = self.loader.load(legal_file)
        chunks = self.chunker.chunk_documents(documents, chunk_mode=chunk_mode)

        docs = [
            Document(
                page_content=chunk["content"],
                metadata=chunk.get("metadata", {}),
            )
            for chunk in chunks
        ]

        self._vectorstore = FAISS.from_documents(docs, self._get_embeddings())
        self._save_index()
        return self._vectorstore

    def _save_index(self) -> None:
        """持久化索引到磁盘"""
        if self._vectorstore is None:
            return
        self._vectorstore.save_local(str(self.index_path))
        # 保存 chunks 原始数据（不含向量）供调试/分析
        chunks_path = self.index_path.parent / f"{self.index_path.name}_chunks.pkl"
        chunks = self.loader.load()
        with open(chunks_path, "wb") as f:
            pickle.dump(chunks, f)

    def _load_index(self) -> bool:
        """尝试从磁盘加载索引"""
        if not self.index_path.exists():
            return False
        try:
            self._vectorstore = FAISS.load_local(
                str(self.index_path),
                self._get_embeddings(),
                allow_dangerous_deserialization=True,
            )
            return True
        except Exception:
            return False

    def get_vectorstore(self) -> FAISS | None:
        """获取已加载的向量存储"""
        if self._vectorstore is None:
            self._load_index()
        return self._vectorstore

    def index_stats(self) -> Dict[str, Any]:
        """返回索引统计信息"""
        vs = self.get_vectorstore()
        if vs is None:
            return {"status": "not_loaded", "chunks": 0}
        return {
            "status": "loaded",
            "chunks": vs.index.ntotal,
            "embedding_model": self.embedding_model,
            "index_path": str(self.index_path),
        }
