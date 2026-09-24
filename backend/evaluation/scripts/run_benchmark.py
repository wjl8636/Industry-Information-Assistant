#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_benchmark.py
================================================================================
Agent vs 单轮 LLM 定量对比评测。

对每个 query 分别运行:
  - baseline: 单轮 LLM 直接回答
  - agent   : DeepResearch 完整流程
并调用 LLM-as-Judge 做 head-to-head 对比，最后输出统计显著性
（配对 bootstrap 95% CI）。

用法:
    python -m evaluation.scripts.run_benchmark --queries "..."
    python -m evaluation.scripts.run_benchmark --queries_file q.txt --output out.json
================================================================================
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))


def run_baseline(query: str, policy) -> dict:
    """单轮 LLM 直接回答。"""
    messages = [
        {"role": "system", "content": (
            "你是行业研究助手。请用 Markdown 撰写一份结构化、有数据、带引用的研究报告，"
            "回答用户的问题。尽量给出具体数字与来源。" )},
        {"role": "user", "content": query},
    ]
    resp = policy(messages)
    content = resp.get("content", "")
    return {
        "query": query,
        "content": content,
        "length": len(content),
        "source_count": content.count("http"),
    }


def run_agent(query: str, config: dict, modules: dict) -> dict:
    from evaluation.core.runner import run_research_full
    result = run_research_full(query, config, modules)
    report = result.get("final_report", "")
    return {
        "query": query,
        "content": report,
        "length": len(report),
        "source_count": report.count("http"),
        "quality_score": result.get("quality_score", 0.0),
        "session_id": result.get("session_id", ""),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Agent vs 单轮 LLM Benchmark")
    parser.add_argument("--queries", type=str, nargs="+", default=None)
    parser.add_argument("--queries_file", type=str, default=None)
    parser.add_argument("--output", type=str, default="outputs/eval/benchmark_results.json")
    parser.add_argument("--num_questions", type=int, default=3, help="从评测集自动抽取题数")
    parser.add_argument("--skip_baseline", action="store_true")
    parser.add_argument("--skip_agent", action="store_true")
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--log_level", type=str, default="INFO")
    args = parser.parse_args()

    from evaluation.core.runner import setup_logging, load_config, initialize_modules
    from evaluation.core.llm import get_baseline_policy
    from evaluation.core.judge import LLMJudge
    from evaluation.metrics.stats import bootstrap_ci_paired
    from evaluation.benchmarks.research_bench import IndustryResearchBench
    import asyncio

    setup_logging(args.log_level)

    # 解析 queries
    if args.queries:
        queries = args.queries
    elif args.queries_file:
        with open(args.queries_file, "r", encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
    else:
        bench = IndustryResearchBench()
        queries = [q["query"] for q in bench.get_questions(n=args.num_questions)]

    config = load_config(args.config)
    modules = initialize_modules(config)
    baseline_policy = get_baseline_policy()
    judge = LLMJudge()

    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}\n[Benchmark] {i}/{len(queries)}: {query[:50]}...\n{'='*60}")
        record = {"query": query, "baseline": None, "agent": None, "scores": None}

        if not args.skip_baseline:
            t0 = time.time()
            b = run_baseline(query, baseline_policy)
            b["elapsed"] = round(time.time() - t0, 2)
            record["baseline"] = b
            print(f"  [Baseline] 字数={b['length']}, 来源={b['source_count']}")

        if not args.skip_agent:
            t0 = time.time()
            a = run_agent(query, config, modules)
            a["elapsed"] = round(time.time() - t0, 2)
            record["agent"] = a
            print(f"  [Agent] 字数={a['length']}, 来源={a['source_count']}, quality={a['quality_score']:.2f}")

        if record["baseline"] and record["agent"]:
            scores = judge.compare_two(record["baseline"]["content"], record["agent"]["content"], query)
            record["scores"] = scores
            print(f"  [Judge] {json.dumps(scores, ensure_ascii=False)}")

        results.append(record)

    # 统计显著性
    final_output = {"results": results, "num_questions": len(queries),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if not args.skip_baseline and not args.skip_agent:
        dims = ["comprehensiveness", "accuracy", "structure", "sources"]
        dim_scores = {d: {"agent": [], "baseline": []} for d in dims}
        for r in results:
            sc = r.get("scores", {})
            for d in dims:
                dd = sc.get(d, {})
                if isinstance(dd, dict) and "A" in dd and "B" in dd:
                    dim_scores[d]["baseline"].append(float(dd["A"]))
                    dim_scores[d]["agent"].append(float(dd["B"]))

        stats = {}
        print(f"\n统计显著性 (Agent vs Baseline, 配对 bootstrap 95% CI):")
        for d in dims:
            a = dim_scores[d]["agent"]
            b = dim_scores[d]["baseline"]
            if len(a) < 2:
                continue
            diffs = [x - y for x, y in zip(a, b)]
            s = bootstrap_ci_paired(diffs)
            stats[d] = s
            print(f"  {d:18s}: Agent={sum(a)/len(a):.2f} Baseline={sum(b)/len(b):.2f} "
                  f"Δ={s['mean_diff']:+.2f} CI=[{s['ci_lower']:+.2f},{s['ci_upper']:+.2f}] {s['significant']}")
        final_output["statistical_tests"] = stats

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {args.output}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())