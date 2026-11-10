"""
RAG evaluation benchmark script.
Evaluates retrieval accuracy, Recall@K, MRR, and latency against benchmark questions.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT
from src.rag.retriever import RAGRetriever


def evaluate_retrieval(
    benchmark_path: Path = PROJECT_ROOT / "tests" / "fixtures" / "rag_retrieval_questions.json",
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Evaluates the RAG retriever across standard benchmark questions.
    """
    with open(benchmark_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    retriever = RAGRetriever()
    if not retriever.is_ready():
        retriever.build_or_refresh_index()

    results = []
    total_reciprocal_rank = 0.0
    recall_hits = 0
    keyword_hits = 0
    latencies = []

    for item in questions:
        q_id = item["question_id"]
        query = item["question"]
        expected_docs = item["expected_document_ids"]
        expected_keywords = item.get("expected_keywords", [])

        res = retriever.retrieve(query=query, top_k=top_k)
        latencies.append(res.metadata.execution_time_ms)

        retrieved_doc_ids = [c.document_id for c in res.chunks]
        combined_text = res.get_combined_text().lower()

        # Check document recall
        hit_rank = None
        for rank, c in enumerate(res.chunks, start=1):
            if c.document_id in expected_docs:
                hit_rank = rank
                break

        if hit_rank is not None:
            recall_hits += 1
            total_reciprocal_rank += 1.0 / hit_rank
        else:
            total_reciprocal_rank += 0.0

        # Check keywords
        kw_found = [kw for kw in expected_keywords if kw.lower() in combined_text]
        kw_ratio = len(kw_found) / len(expected_keywords) if expected_keywords else 1.0
        if kw_ratio >= 0.5:
            keyword_hits += 1

        results.append({
            "question_id": q_id,
            "query": query,
            "expected_docs": expected_docs,
            "retrieved_docs": retrieved_doc_ids,
            "hit_rank": hit_rank,
            "keywords_found": kw_found,
            "keyword_ratio": round(kw_ratio, 2),
            "latency_ms": res.metadata.execution_time_ms,
            "top_score": res.chunks[0].score if res.chunks else 0.0,
            "top_title": res.chunks[0].section_title if res.chunks else None,
        })

    n = len(questions)
    recall_at_k = recall_hits / n if n > 0 else 0.0
    mrr = total_reciprocal_rank / n if n > 0 else 0.0
    avg_latency = sum(latencies) / n if n > 0 else 0.0

    summary = {
        "total_questions": n,
        "top_k": top_k,
        "recall_at_k": round(recall_at_k, 4),
        "mrr": round(mrr, 4),
        "keyword_pass_rate": round(keyword_hits / n, 4) if n > 0 else 0.0,
        "average_latency_ms": round(avg_latency, 2),
        "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
        "results": results,
    }

    return summary


if __name__ == "__main__":
    summary = evaluate_retrieval()
    print("=" * 60)
    print("RAG RETRIEVAL BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total Questions Evaluated: {summary['total_questions']}")
    print(f"Recall@{summary['top_k']}: {summary['recall_at_k'] * 100:.1f}%")
    print(f"MRR (Mean Reciprocal Rank): {summary['mrr']:.4f}")
    print(f"Keyword Pass Rate: {summary['keyword_pass_rate'] * 100:.1f}%")
    print(f"Average Latency: {summary['average_latency_ms']} ms")
    print("-" * 60)
    for r in summary["results"]:
        status = "PASS" if r["hit_rank"] is not None else "FAIL"
        print(f"[{status}] {r['question_id']}: Hit Rank={r['hit_rank']} | Score={r['top_score']:.3f} | Latency={r['latency_ms']:.1f}ms")
        print(f"       Top: {r['top_title']}")
