# -*- coding: utf-8 -*-
"""
evaluation/metrics/composite.py
================================================================================
综合得分计算工具：合并规则指标与 Judge 指标。
================================================================================
"""
from __future__ import annotations

from typing import Any


def compute_composite_score(
    rule_metrics: dict[str, float] | None = None,
    judge_result: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """综合评分：默认规则指标 60% + Judge 指标 40%。"""
    default_weights = {"rule": 0.6, "judge": 0.4}
    w = weights if weights is not None else default_weights

    rule_score = 0.0
    if rule_metrics:
        vals = [v for v in rule_metrics.values() if isinstance(v, (int, float))]
        rule_score = sum(vals) / len(vals) if vals else 0.0

    judge_score = 0.0
    judge_dims = {}
    if judge_result:
        dims = judge_result.get("dimensions", {})
        judge_dims = {k: v["score"] / 10.0 for k, v in dims.items()
                      if isinstance(v, dict) and "score" in v}
        judge_score = sum(judge_dims.values()) / len(judge_dims) if judge_dims else 0.0

    composite = w.get("rule", 0.6) * rule_score + w.get("judge", 0.4) * judge_score

    return {
        "composite_score": round(composite, 4),
        "rule_score": round(rule_score, 4),
        "judge_score": round(judge_score, 4),
        "rule_metrics": rule_metrics or {},
        "judge_dimensions": judge_dims,
    }
