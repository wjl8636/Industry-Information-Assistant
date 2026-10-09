# -*- coding: utf-8 -*-
"""
Multi-Agent Runner - 本项目多智能体跑报告（基线 B）

复用 DeepResearchV2Service.research（SSE 流式），收集 final_report 与
过程评测字段（quality_score, review_dimensions, grounding, grounding_coverage,
citation_validation, budget, grounding_gate）。

用法：
    python app/eval/runners/multi_agent.py
"""

import os
import sys
import json
import asyncio

# 确保 backend 根目录在 path 上，以便导入 app.eval.*
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_APP = os.path.join(BACKEND_ROOT, "app")
for p in [BACKEND_ROOT, BACKEND_APP]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.eval.config import load_dataset, get_multi_agent_config, save_result, ensure_ssl

# 清理无效 SSL_CERT_FILE（conda env 遗留）
ensure_ssl()


async def run_multi_agent(query: str, session_id: str = None) -> dict:
    """跑一题多智能体，收集最终报告与评测字段"""
    from service.deep_research_v2.service import DeepResearchV2Service

    cfg = get_multi_agent_config()
    service = DeepResearchV2Service(
        llm_api_key=cfg["llm_api_key"],
        llm_base_url=cfg["llm_base_url"],
        search_api_key=cfg["search_api_key"],
        model=cfg["model"],
        max_iterations=2,  # 复用测试脚本：2 轮，让质检闭环实际跑起来
    )

    final_event = None
    eval_fields = {}
    session_id = session_id or f"eval_{os.urandom(4).hex()}"

    # 捕获 budget / grounding / citation / gate 相关事件
    captured = {"budget": None, "grounding_gate": None}

    try:
        async for sse in service.research(query, session_id=session_id, search_web=True, search_local=False):
            if sse.startswith("data: "):
                payload = sse[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    ev = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                t = ev.get("type")
                if t == "research_complete":
                    final_event = ev
                elif t == "grounding_gate":
                    captured["grounding_gate"] = ev.get("content", {})
                elif t == "budget":
                    pass
                # 其它阶段事件忽略
    except Exception as e:
        return {"error": str(e)}

    if not final_event:
        return {"error": "无 research_complete 事件", "captured": captured}

    # 从 final_event 组装评测字段
    return {
        "report": final_event.get("final_report", ""),
        "quality_score": final_event.get("quality_score", 0.0),
        "facts_count": final_event.get("facts_count", 0),
        "charts_count": final_event.get("charts_count", 0),
        "iterations": final_event.get("iterations", 0),
        "references_count": len(final_event.get("references", [])),
        "grounding_gate": captured["grounding_gate"],
        "session_id": session_id,
    }


async def main(n: int = None) -> None:
    dataset = load_dataset()
    if n:
        dataset = dataset[:n]

    results = []
    for item in dataset:
        print(f"[MultiAgent] id={item['id']} 开始...")
        r = await run_multi_agent(item["prompt"])
        if "error" in r:
            print(f"[MultiAgent] id={item['id']} 失败: {r['error']}")
            results.append({"id": item["id"], "prompt": item["prompt"], "error": r["error"]})
        else:
            print(f"[MultiAgent] id={item['id']} 完成, quality={r['quality_score']}, facts={r['facts_count']}")
            results.append({"id": item["id"], "prompt": item["prompt"], **r})

    path = save_result("multi_agent", {"results": results, "n": len(results)})
    print(f"保存: {path}")


if __name__ == "__main__":
    # 支持 --n N 只跑前 N 题
    n = None
    if len(sys.argv) > 1 and sys.argv[1] == "--n":
        n = int(sys.argv[2])
    asyncio.run(main(n=n))