# -*- coding: utf-8 -*-
"""
evaluation/metrics/judge_based.py
================================================================================
基于 LLM-as-Judge 的深度评测指标。
================================================================================
"""
from __future__ import annotations

from typing import Any


class JudgeBasedMetrics:
    """研究报告质量评测指标集合（LLM Judge 版）。"""

    @staticmethod
    def judge_score(
        report: str,
        query: str,
        ground_truth: dict[str, Any] | None = None,
        backend: str = "judge",
        **llm_kwargs,
    ) -> dict[str, Any]:
        """对单篇报告进行 5 维度深度评分（0-10）。"""
        from evaluation.core.judge import LLMJudge
        judge = LLMJudge(backend=backend, **llm_kwargs)
        return judge.score_single(report, query, ground_truth)
