# -*- coding: utf-8 -*-
"""
Judge - 统一判分器（RACE 四维 + FACT 引用可信度，用 deepseek-v4-pro）

RACE 四维（对齐 DRB）：
  - comprehensiveness  信息完整性
  - depth              研究深度
  - instruction_following 指令遵循
  - readability        可读性
FACT：
  - citation_accuracy   引用准确率
  - effective_citations 有效引用数

设计：
- temperature=0，输出 JSON
- 同一报告判 2 次做自一致性（cohen-free：两次分差大则该样本被判不确定）
- 用量化打分 0-1，便于配对对比与聚合

用法：
    python app/eval/judge.py
    # 需要 EVAL_LLM_API_KEY 等（见 config.py）
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
    eval_llm_available, get_eval_llm_config, load_dataset, save_result
)

JUDGE_PROMPT = """你是一位严格的行业研究报告质量评估专家。请对给定研究报告打分。

## 研究问题
{query}

## 报告内容
{report}

## 评分维度（每项 0-1）
1. comprehensiveness（信息完整性）：报告覆盖研究问题涉及的关键方面与要点
2. depth（研究深度）：分析是否有洞察、是否深入，而非罗列
3. instruction_following（指令遵循）：是否按要求结构输出、是否遵循引用格式要求
4. readability（可读性）：结构清晰、层级合理、表达流畅

## 引用质量（FACT）
检查报告中的行内引用 [标题](URL)：
- citation_accuracy（引用准确率 0-1）：有多少引用 URL 存在且像真实来源（不编造）
- effective_citations（有效引用数 int）：可验证支撑的引用条数（近似，统计含真实http(s) URL 的引用）

## 输出
```json
{{
    "dimensions": {{
        "comprehensiveness": 0.0-1.0,
        "depth": 0.0-1.0,
        "instruction_following": 0.0-1.0,
        "readability": 0.0-1.0
    }},
    "fact": {{
        "citation_accuracy": 0.0-1.0,
        "effective_citations": int
    }},
    "overall_score": 0.0-1.0,
    "comment": "简短评语"
}}
```

规则：
- 各维度独立打分，overall_score 可视为四维加权（建议 comprehensiveness 0.3, depth 0.4, instruction 0.15, readability 0.15）
- 对无引用的报告，citation_accuracy 给 0
- 报告越完整、越有深度、引用越真实，分数越高

开始评分："""


def dimension_weight() -> dict:
    return {"comprehensiveness": 0.3, "depth": 0.4, "instruction_following": 0.15, "readability": 0.15}


async def judge_report(query: str, report: str, model: str = None) -> dict:
    from openai import OpenAI
    cfg = get_eval_llm_config()
    model = model or cfg["model"]
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    resp = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": "你是报告质量评估专家，只输出合法 JSON。"},
            {"role": "user", "content": JUDGE_PROMPT.format(query=query, report=report[:8000])},
        ],
        temperature=0,
        max_tokens=4000,  # 推理模型需预留输出空间
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    # 提取 JSON：优先直接找 {...}，失败则剥离 markdown 代码块后重试
    import re
    # 先剥掉 ```json 代码块
    cleaned = content
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if m:
        cleaned = m.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Judge 未输出 JSON: {content[:120]!r}")
    return json.loads(cleaned[start:end + 1])


def overall_from_dimensions(dims: dict) -> float:
    wts = dimension_weight()
    total = 0.0
    for k, w in wts.items():
        total += w * float(dims.get(k, 0.0))
    return round(total, 4)


def judge_report_sync(query: str, report: str, model: str = None) -> dict:
    """同步判分（供 run_comparison 使用）"""
    import asyncio
    return asyncio.run(judge_report(query, report, model))


if __name__ == "__main__":
    # 不直接判分：由 run_comparison.py 编排
    print("Judge 库入口：请使用 app/eval/run_comparison.py 编排评测。")