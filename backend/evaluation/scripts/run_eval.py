#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_eval.py
================================================================================
标准评测集入口脚本（行业深度研究评测集）。

对每个评测题运行 DeepResearch 并计算规则指标，聚合输出综合得分与按行业统计。

用法:
    python -m evaluation.scripts.run_eval --num_questions 8
    python -m evaluation.scripts.run_eval --domain 智慧交通 --num_questions 2
    python -m evaluation.scripts.run_eval --config eval_config.json
================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import time

# 确保 backend/app 与 backend 可导入
import sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parent.parent.parent          # backend/
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))

from evaluation.core.runner import setup_logging, load_config, initialize_modules, run_research_full
from evaluation.benchmarks.research_bench import IndustryResearchBench
from evaluation.report import EvaluationReport
from evaluation.metrics.rule_based import evaluate_rule_metrics


def run_bench_eval(num_questions: int, domain: str | None, config: dict) -> EvaluationReport:
    logger = logging.getLogger("run_eval")
    bench = IndustryResearchBench()
    questions = bench.get_questions(domain=domain, n=num_questions)
    logger.info(f"评测集加载 {len(questions)} 道题（行业: {domain or '全部'}）")

    modules = initialize_modules(config)
    report = EvaluationReport(name="IndustryBench_Evaluation", num_questions=len(questions))

    for idx, q in enumerate(questions, 1):
        qid = q["id"]
        logger.info(f"[{idx}/{len(questions)}] 题目: {qid} - {q['query'][:40]}...")
        start = time.time()
        try:
            result = run_research_full(q["query"], config, modules)
            elapsed = time.time() - start
            metrics = evaluate_rule_metrics(result, q)
            detail = {
                "question_id": qid,
                "domain": q.get("domain", ""),
                "metrics": {k: v for k, v in metrics.items() if k != "composite_score"},
                "composite_score": metrics["composite_score"],
                "elapsed_seconds": round(elapsed, 2),
            }
            report.add_detail(detail)
            logger.info(f"  → composite={detail['composite_score']:.3f}, time={elapsed:.1f}s")
        except Exception as e:
            logger.warning(f"  → FAILED: {e}")
            report.add_detail({"question_id": qid, "error": str(e), "composite_score": 0.0})

    valid = [d["composite_score"] for d in report.details if "composite_score" in d]
    report.set_summary({
        "average_composite": round(sum(valid) / len(valid), 4) if valid else 0.0,
        "num_success": len([d for d in report.details if "error" not in d]),
        "num_failed": len([d for d in report.details if "error" in d]),
        "by_domain": _domain_avg(report.details),
    })
    return report


def _domain_avg(details: list[dict]) -> dict[str, float]:
    by: dict[str, list[float]] = {}
    for d in details:
        if "composite_score" in d and "error" not in d:
            by.setdefault(d.get("domain", ""), []).append(d["composite_score"])
    return {d: round(sum(v) / len(v), 4) for d, v in by.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="行业信息助手 标准评测")
    parser.add_argument("--num_questions", type=int, default=0, help="题目数（0=全部）")
    parser.add_argument("--domain", type=str, default=None, help="按行业过滤")
    parser.add_argument("--config", type=str, default=None, help="评测配置 JSON/YAML")
    parser.add_argument("--output_dir", type=str, default="outputs/eval")
    parser.add_argument("--log_level", type=str, default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = load_config(args.config)
    report = run_bench_eval(args.num_questions, args.domain, config)

    json_path = report.save(args.output_dir)
    md_path = report.save_markdown(args.output_dir)
    print(f"\n评测摘要:\n{json.dumps(report.summary, ensure_ascii=False, indent=2)}")
    print(f"\nJSON: {json_path}\nMarkdown: {md_path}")


if __name__ == "__main__":
    main()
