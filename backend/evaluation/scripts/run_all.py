#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_all.py
================================================================================
一键批量实验：跑通测评体系全流程。

  1. 标准评测集（规则指标，全行业）
  2. 模块消融实验
  3. 审核轮数消融实验
  4. 可选: Agent vs 单轮 LLM 对比

每个实验独立运行，失败不中断整体流程。最后生成 Markdown 汇总报告。

用法:
    python -m evaluation.scripts.run_all --eval_questions 8 --ablation_questions 4
================================================================================
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND / "app"))
sys.path.insert(0, str(BACKEND))


def run_subprocess(name: str, cmd: list[str], cwd: str = str(BACKEND)) -> dict:
    print(f"\n{'='*70}\n[批量] 启动: {name}\n{'='*70}")
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, timeout=None)
        status = "success" if proc.returncode == 0 else "failed"
        print(f"[批量] {name} | {status} | {time.time()-t0:.1f}s")
        return {"name": name, "status": status, "elapsed_seconds": round(time.time() - t0, 2)}
    except Exception as e:
        return {"name": name, "status": "error", "elapsed_seconds": round(time.time() - t0, 2), "error": str(e)}


def generate_summary(results: list[dict], output_dir: str) -> str:
    lines = [
        "# 行业信息助手 批量实验汇总报告",
        "",
        f"- **实验时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **实验项**: {len(results)}",
        "",
        "## 实验结果一览",
        "",
        "| 实验 | 状态 | 耗时(s) | 备注 |",
        "|------|------|---------|------|",
    ]
    for r in results:
        note = "✓" if r.get("status") == "success" else r.get("error", "✗")[:40]
        lines.append(f"| {r['name']} | {r.get('status')} | {r.get('elapsed_seconds', 0):.1f} | {note} |")
    md = "\n".join(lines)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = os.path.join(output_dir, "SUMMARY.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def main() -> None:
    import os
    parser = argparse.ArgumentParser(description="行业信息助手 批量实验")
    parser.add_argument("--eval_questions", type=int, default=0, help="标准评测题数（0=全部）")
    parser.add_argument("--ablation_questions", type=int, default=4, help="消融题数")
    parser.add_argument("--max_rounds", type=int, default=3)
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--output_dir", type=str, default="outputs/eval/experiments")
    parser.add_argument("--skip_benchmark", action="store_true", help="跳过 Agent vs LLM 对比")
    args = parser.parse_args()

    results = []
    cwd = str(BACKEND)
    config_args = ["--config", args.config] if args.config else []

    results.append(run_subprocess(
        "标准评测集",
        [sys.executable, "-m", "evaluation.scripts.run_eval",
         "--num_questions", str(args.eval_questions),
         "--output_dir", os.path.join(args.output_dir, "eval"),
         *config_args], cwd))

    results.append(run_subprocess(
        "模块消融",
        [sys.executable, "-m", "evaluation.scripts.run_ablation",
         "--mode", "module", "--questions", str(args.ablation_questions),
         "--output_dir", os.path.join(args.output_dir, "ablation"),
         *config_args], cwd))

    results.append(run_subprocess(
        "轮数消融",
        [sys.executable, "-m", "evaluation.scripts.run_ablation",
         "--mode", "rounds", "--questions", str(args.ablation_questions),
         "--max_rounds", str(args.max_rounds),
         "--output_dir", os.path.join(args.output_dir, "ablation_rounds"),
         *config_args], cwd))

    if not args.skip_benchmark:
        results.append(run_subprocess(
            "Agent vs 单轮LLM",
            [sys.executable, "-m", "evaluation.scripts.run_benchmark",
             "--num_questions", str(min(args.ablation_questions, 3)),
             "--output", os.path.join(args.output_dir, "benchmark", "results.json"),
             *config_args], cwd))

    md = generate_summary(results, args.output_dir)
    print(f"\n汇总报告: {md}")


if __name__ == "__main__":
    main()