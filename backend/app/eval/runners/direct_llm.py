# -*- coding: utf-8 -*-
"""
Direct LLM Runner - 单次直出报告（基线 A）

用项目生成模型（默认 qwen3.7-plus）直接生成研究报告，不接入多智能体。
用于与 Multi-Agent 做配对对比；Judge 模型单独由 EVAL_LLM_MODEL 配置。

用法：
    python -m app.eval.runners.direct_llm.py
    # 或
    python app/eval/runners/direct_llm.py
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

from app.eval.config import (
    load_dataset, get_multi_agent_config, get_eval_llm_config,
    eval_llm_available, save_result, ensure_ssl
)

# 清理无效 SSL_CERT_FILE（conda env 遗留）
ensure_ssl()

DIRECT_PROMPT = """你是资深行业研究分析师。请针对以下研究问题，撰写一份完整、专业、带数据支撑与引用来源的中文研究报告。

要求：
1. 结构完整：执行摘要 + 分章节正文 + 结论与展望 + 参考文献
2. 数据支撑：关键观点必须给出数据或事实，并标注来源（用 [来源名称](URL) 可点击格式）
3. 引用规范：报告中的数字与关键结论都要有行内引用链接
4. 篇幅：1500-3000 字
5. 只输出报告本身，不要输出其他解释

研究问题：
{query}
"""


async def run_direct(query: str, model: str = None) -> dict:
    """单题直出报告（使用项目生成模型配置 MA_LLM_*，默认 qwen3.7-plus）"""
    from openai import OpenAI

    cfg = get_multi_agent_config()
    model = model or cfg["model"]

    client = OpenAI(api_key=cfg["llm_api_key"], base_url=cfg["llm_base_url"])
    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": "你是严谨的行业研究分析师，只输出报告。"},
            {"role": "user", "content": DIRECT_PROMPT.format(query=query)},
        ],
        temperature=0.2,
        max_tokens=8000,
    )
    content = resp.choices[0].message.content
    return {
        "report": content,
        "model": model,
        "usage": getattr(resp, "usage", None).total_tokens if getattr(resp, "usage", None) else 0,
    }


async def main() -> None:
    if not eval_llm_available():
        print("错误: 未配置 EVAL_LLM_API_KEY / EVAL_LLM_BASE_URL（backend/.env）。")
        print("  需要：EVAL_LLM_BASE_URL=https://llm.goaichat.top/v1")
        print("        EVAL_LLM_API_KEY=sk-...")
        sys.exit(1)

    dataset = load_dataset()
    model = get_multi_agent_config()["model"]
    results = []
    for item in dataset:
        print(f"[Direct] id={item['id']} 开始...")
        try:
            r = await run_direct(item["prompt"], model)
            results.append({
                "id": item["id"],
                "prompt": item["prompt"],
                "report": r["report"],
                "model": r["model"],
                "usage_tokens": r["usage"],
            })
            print(f"[Direct] id={item['id']} 完成, tokens={r['usage']}")
        except Exception as e:
            print(f"[Direct] id={item['id']} 失败: {e}")
            results.append({"id": item["id"], "prompt": item["prompt"], "error": str(e)})

    path = save_result("direct_llm", {"model": model, "results": results, "n": len(results)})
    print(f"保存: {path}")

if __name__ == "__main__":
    asyncio.run(main())