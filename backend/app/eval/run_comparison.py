# -*- coding: utf-8 -*-
"""
配对评测流水线：Direct(qwen3.7-plus) vs Multi-Agent(qwen3.7-plus)

流程：
1. 逐题跑 Direct（项目生成模型，直出报告）
2. 逐题跑 Multi-Agent（同一项目生成模型）
3. 对两份报告分别判分（独立 Judge，默认 deepseek-v4-pro，temperature=0，双判取均值）
4. 保存 comparison 结果 → results/comparison.json

用法：
    python app/eval/run_comparison.py
    python app/eval/run_comparison.py --n 2        # 只跑前 2 题
    python app/eval/run_comparison.py --skip-multi  # 只跑 Direct（供快速冒烟）
"""

import os
import sys
import asyncio
import argparse

# 确保 backend 根目录在 path 上，以便导入 app.eval.*
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_APP = os.path.join(BACKEND_ROOT, "app")
for p in [BACKEND_ROOT, BACKEND_APP]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.eval.config import (
    load_dataset, save_result, eval_llm_available, get_multi_agent_config,
    get_eval_llm_config, ensure_ssl
)
from app.eval.runners.direct_llm import run_direct
from app.eval.runners.multi_agent import run_multi_agent
from app.eval.judge import judge_report, overall_from_dimensions

# 清理无效 SSL_CERT_FILE（conda env 遗留）
ensure_ssl()


async def judge_report_robust(query: str, report: str, model: str = None, tries: int = 2):
    """双判取均值；失败一次则降级为单判"""
    scores = []
    for i in range(tries):
        try:
            scores.append(await judge_report(query, report, model))
        except Exception as e:
            print(f"  [Judge] 第 {i + 1} 次失败: {e}")
    if not scores:
        return None
    # 取最后一次（若两次都在则取平均）
    if len(scores) == 1:
        return scores[0]
    return {
        "dimensions": {
            k: (scores[0]["dimensions"][k] + scores[1]["dimensions"][k]) / 2
            for k in scores[0]["dimensions"]
        },
        "fact": scores[0]["fact"],
        "overall_score": (scores[0].get("overall_score", 0) + scores[1].get("overall_score", 0)) / 2,
        "comment": scores[0].get("comment", ""),
        "judge_tries": len(scores),
    }


async def run_one(item: dict, generation_model: str, judge_model: str, do_multi: bool) -> dict:
    """跑一题并判分"""
    result = {"id": item["id"], "prompt": item["prompt"]}

    # Direct
    print(f"[{item['id']}] Direct 开始...")
    if eval_llm_available():
        try:
            direct = await run_direct(item["prompt"], generation_model)
            result["direct"] = {"report": direct["report"], "usage": direct["usage"]}
            result["direct_judge"] = await judge_report_robust(item["prompt"], direct["report"], judge_model)
            print(f"[{item['id']}] Direct 完成, overall={result['direct_judge']['overall_score'] if result['direct_judge'] else 'N/A'}")
        except Exception as e:
            print(f"[{item['id']}] Direct 失败: {e}")
            result["direct_error"] = str(e)
    else:
        print(f"[{item['id']}] 跳过 Direct（未配置 EVAL_LLM_*）")

    # Multi-Agent
    if do_multi:
        print(f"[{item['id']}] MultiAgent 开始...")
        try:
            multi = await run_multi_agent(item["prompt"])
            if "error" in multi:
                result["multi_error"] = multi["error"]
            else:
                result["multi"] = {
                    "report": multi["report"],
                    "quality_score": multi["quality_score"],
                    "facts_count": multi["facts_count"],
                    "charts_count": multi["charts_count"],
                    "references_count": multi["references_count"],
                    "grounding_gate": multi.get("grounding_gate"),
                }
                result["multi_judge"] = await judge_report_robust(item["prompt"], multi["report"], judge_model)
                print(f"[{item['id']}] MultiAgent 完成, overall={result['multi_judge']['overall_score'] if result['multi_judge'] else 'N/A'}")
        except Exception as e:
            print(f"[{item['id']}] MultiAgent 失败: {e}")
            result["multi_error"] = str(e)
    else:
        print(f"[{item['id']}] 跳过 MultiAgent")

    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=None, help="只跑前 N 题")
    parser.add_argument("--skip-multi", action="store_true", help="跳过 Multi-Agent")
    args = parser.parse_args()

    dataset = load_dataset()
    if args.n:
        dataset = dataset[:args.n]

    generation_cfg = get_multi_agent_config()
    judge_cfg = get_eval_llm_config()
    generation_model = generation_cfg["model"]
    judge_model = judge_cfg["model"]
    results = {
        "generation_model": generation_model,
        "direct_generation_model": generation_model,
        "multi_agent_generation_model": generation_model,
        "judge_model": judge_model,
        "n": len(dataset),
        "samples": [],
    }

    for item in dataset:
        r = await run_one(
            item, generation_model, judge_model, do_multi=not args.skip_multi
        )
        results["samples"].append(r)

    path = save_result("comparison", results)
    print(f"\n保存对比结果: {path}")


if __name__ == "__main__":
    asyncio.run(main())