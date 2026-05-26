"""
RAG 索引构建脚本

用法:
    python build_index.py              # 使用默认配置构建索引
    python build_index.py --rebuild    # 强制重建
    python build_index.py --stats       # 仅查看索引状态

依赖:
    - ollama (本地运行): ollama pull nomic-embed-text
    - 或设置环境变量 LEGAL_EMBEDDING_MODEL / LEGAL_EMBEDDING_BASE_URL
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.legal_kb import LegalKnowledgeBase
from rag.loader import LegalDocLoader
from rag.chunker import LegalChunker


def main():
    parser = argparse.ArgumentParser(description="构建法律知识库 RAG 索引")
    parser.add_argument("--rebuild", action="store_true", help="强制重建索引")
    parser.add_argument("--stats", action="store_true", help="仅显示索引统计信息")
    parser.add_argument("--chunk-mode", choices=["by_article", "by_chapter"], default="by_article")
    parser.add_argument("--test-search", metavar="QUERY", help="构建后执行一次检索测试")
    args = parser.parse_args()

    kb = LegalKnowledgeBase(chunk_mode=args.chunk_mode)

    if args.stats:
        stats = kb.stats()
        print("=== 索引状态 ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        return

    print("=== 构建法律知识库索引 ===")
    print(f"  chunk_mode: {args.chunk_mode}")
    print(f"  embedding: {kb.indexer.embedding_model} @ {kb.indexer.embedding_base_url}")
    print()

    # 先检查文档加载
    loader = LegalDocLoader()
    docs = loader.load()
    print(f"文档加载完成: {len(docs)} 条法律条文")

    chunker = LegalChunker()
    chunks = chunker.chunk_documents(docs, chunk_mode=args.chunk_mode)
    print(f"文本切分完成: {len(chunks)} 个 chunks")
    print()

    # 展示切分样例
    print("=== 切分样例 ===")
    for c in chunks[:3]:
        print(f"  [{c['article_no']}] {c['content'][:80]}...")
    print()

    # 构建索引
    print("开始构建向量索引（需要 Ollama 服务运行中）...")
    kb.initialize(force_rebuild=args.rebuild)

    stats = kb.stats()
    print(f"\n索引构建完成: {stats}")
    print(f"索引路径: {stats.get('index_path')}")

    # 测试检索
    if args.test_search:
        print(f"\n=== 检索测试: {args.test_search} ===")
        results = kb.searcher.search(args.test_search, top_k=3)
        for r in results:
            print(f"\n{r.article_no}（{r.chapter}）")
            print(f"  {r.content[:200]}")
            print(f"  [score: {r.score:.4f}]")


if __name__ == "__main__":
    main()
