#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_ablation.py
================================================================================
消融实验入口脚本。

支持:
  --mode module : 模块消融 (full / no_review / no_web_search / no_local_search)
  --mode rounds : 审核轮数消融 (0/1/2/3 轮, 对应 max_iterations)

每个模式均输出 full vs 消融的 bootstrap 95% CI + Cohen's d。

用法:
    python -m evaluation.scripts.run_ablation --mode module --questions 8
    python -m evaluation.scripts.run_ablation --mode rounds --max_rounds 3 --questions 8
================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))

from evaluation.core.runner import setup_logging, load_config
from evaluation.core.ablation import AblationStudy
from evaluation.benchmarks.research_bench import IndustryResearchBench
from evaluation.metrics.rule_based import evaluate_rule_metrics


def make_scorer():
    """返回一个把 research_sync 结果转成综合分的评分函数。"""
    def scorer(result: dict, q: dict) -> float:
        metrics = evaluate_rule_metrics(result, q)
        return metrics["composite_score"]
    return scorer


def main() -> None:
    parser = argparse.ArgumentParser(description="行业信息助手 消融实验")
    parser.add_argument("--mode", type=str, choices=["module", "rounds"], default="module")
    parser.add_argument("--questions", type=int, default=8, help="题目数（0=全部）")
    parser.add_argument("--domain", type=str, default=None)
    parser.add_argument("--max_rounds", type=int, default=3)
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--output_dir", type=str, default="outputs/eval/ablation")
    parser.add_argument("--log_level", type=str, default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = load_config(args.config)

    bench = IndustryResearchBench()
    questions = bench.get_questions(domain=args.domain, n=args.questions)
    print(f"加载 {len(questions)} 道评测题")

    scorer = make_scorer()

    if args.mode == "module":
        report = AblationStudy.run_module_ablation(config, questions, scorer)
        prefix = "module_ablation"
    else:
        report = AblationStudy.run_rounds_ablation(config, questions, scorer, max_rounds=args.max_rounds)
        prefix = "rounds_ablation"

    path = AblationStudy.save_results(report, args.output_dir, prefix)
    print(f"\n消融摘要: {json.dumps(report['summary'], ensure_ascii=False, indent=2)}")
    print(f"\n统计检验:")
    for name, st in report.get("statistical_tests", {}).items():
        sig = "✓显著" if st.get("significant") else "✗不显著"
        print(f"  {name:20s}: Δ={st['mean_diff']:+.4f} "
              f"CI=[{st['ci_lower']:+.4f},{st['ci_upper']:+.4f}] p={st['p_value']:.4f} d={st['cohens_d']:.3f} {sig}")
    print(f"\n结果已保存: {path}")


if __name__ == "__main__":
    main()
