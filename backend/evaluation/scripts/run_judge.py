#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_judge.py
================================================================================
LLM-as-Judge 深度评分入口。

对单篇（或多篇）研究报告进行 5 维度专家评分，输出结构化 JSON。

用法:
    python -m evaluation.scripts.run_judge --query "问题" --report_file report.md
    python -m evaluation.scripts.run_judge --query "问题" --report_text "..."
    # 使用项目已有的结构化结果（research_sync dict 文件）:
    python -m evaluation.scripts.run_judge --query "问题" --result_file result.json
================================================================================
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))

from evaluation.core.judge import LLMJudge


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-as-Judge 深度评分")
    parser.add_argument("--report_file", type=str, default=None, help="报告 Markdown 文件")
    parser.add_argument("--report_text", type=str, default=None, help="报告文本")
    parser.add_argument("--result_file", type=str, default=None, help="research_sync 结构化结果 JSON（取 final_report）")
    parser.add_argument("--query", type=str, required=True, help="原始研究问题")
    parser.add_argument("--ground_truth_file", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--backend", type=str, default="judge")
    parser.add_argument("--model", type=str, default=None, help="Judge 模型，默认用 DASHSCOPE/配置")
    args = parser.parse_args()

    report_text = None
    if args.report_file:
        with open(args.report_file, "r", encoding="utf-8") as f:
            report_text = f.read()
    elif args.report_text:
        report_text = args.report_text
    elif args.result_file:
        with open(args.result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        report_text = data.get("final_report", "")

    if not report_text:
        print("错误: 必须指定 --report_file / --report_text / --result_file 之一")
        sys.exit(1)

    ground_truth = None
    if args.ground_truth_file:
        with open(args.ground_truth_file, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)

    llm_kwargs = {"model": args.model} if args.model else {}
    judge = LLMJudge(backend=args.backend, **llm_kwargs)
    result = judge.score_single(report_text, args.query, ground_truth)

    if "error" in result:
        print(f"评分失败: {result['error']}")
        sys.exit(1)

    print("\n===== Judge 评分结果 =====")
    print(f"整体质量: {result['overall']['score']:.1f}/10 — {result['overall']['reason']}")
    print(f"平均分: {result['average']:.2f}")
    for dim, data in result.get("dimensions", {}).items():
        print(f"  {dim:25s}: {data['score']:5.1f} — {data['reason']}")
    print("=" * 40)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"评分结果已保存: {args.output}")


if __name__ == "__main__":
    main()
