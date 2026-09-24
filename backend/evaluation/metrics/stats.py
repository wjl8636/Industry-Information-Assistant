# -*- coding: utf-8 -*-
"""
evaluation/metrics/stats.py
================================================================================
统计显著性检验工具：bootstrap 置信区间、效应量、配对 t 检验。

适用于小样本消融实验和 head-to-head benchmark 的统计严谨性验证。
================================================================================
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def bootstrap_ci_paired(diffs: list[float], n_bootstrap: int = 10000,
                        confidence: float = 0.95) -> dict[str, Any]:
    """配对差异的 bootstrap 置信区间。"""
    if not diffs:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0,
                "p_value": 1.0, "significant": False}
    diffs_arr = np.array(diffs)
    mean_diff = float(np.mean(diffs_arr))
    boot = [float(np.mean(np.random.choice(diffs_arr, size=len(diffs_arr), replace=True)))
            for _ in range(n_bootstrap)]
    boot = np.array(boot)
    alpha = 1 - confidence
    return {
        "mean_diff": round(mean_diff, 4),
        "ci_lower": round(float(np.percentile(boot, alpha / 2 * 100)), 4),
        "ci_upper": round(float(np.percentile(boot, (1 - alpha / 2) * 100)), 4),
        "p_value": round(float(np.mean(boot <= 0)), 4),
        "significant": float(np.percentile(boot, alpha / 2 * 100)) > 0,
        "n": len(diffs),
    }


def bootstrap_ci_two_sample(scores_a: list[float], scores_b: list[float],
                            n_bootstrap: int = 10000, confidence: float = 0.95) -> dict[str, Any]:
    """两组独立样本的 bootstrap 置信区间（非配对）。"""
    if not scores_a or not scores_b:
        return {"mean_diff": 0.0, "ci_lower": 0.0, "ci_upper": 0.0,
                "p_value": 1.0, "significant": False}
    a_arr, b_arr = np.array(scores_a), np.array(scores_b)
    mean_diff = float(np.mean(a_arr) - np.mean(b_arr))
    boot = []
    for _ in range(n_bootstrap):
        a = np.random.choice(a_arr, size=len(a_arr), replace=True)
        b = np.random.choice(b_arr, size=len(b_arr), replace=True)
        boot.append(float(np.mean(a) - np.mean(b)))
    boot = np.array(boot)
    alpha = 1 - confidence
    return {
        "mean_diff": round(mean_diff, 4),
        "ci_lower": round(float(np.percentile(boot, alpha / 2 * 100)), 4),
        "ci_upper": round(float(np.percentile(boot, (1 - alpha / 2) * 100)), 4),
        "p_value": round(float(np.mean(boot <= 0)), 4),
        "significant": float(np.percentile(boot, alpha / 2 * 100)) > 0,
        "n_a": len(scores_a),
        "n_b": len(scores_b),
    }


def cohens_d(scores_a: list[float], scores_b: list[float]) -> float:
    """计算 Cohen's d 效应量。"""
    a_arr, b_arr = np.array(scores_a), np.array(scores_b)
    pooled_std = math.sqrt((np.var(a_arr, ddof=1) + np.var(b_arr, ddof=1)) / 2)
    if pooled_std < 1e-9:
        return 0.0
    return float((np.mean(a_arr) - np.mean(b_arr)) / pooled_std)


def paired_t_test(scores_a: list[float], scores_b: list[float]) -> dict[str, Any]:
    """配对 t 检验（假设正态分布），作为 bootstrap 的补充。"""
    try:
        from scipy import stats
        diffs = np.array(scores_a) - np.array(scores_b)
        t_stat, p_value = stats.ttest_1samp(diffs, popmean=0)
        return {
            "t_statistic": round(float(t_stat), 4),
            "p_value": round(float(p_value), 4),
            "mean_diff": round(float(np.mean(diffs)), 4),
            "n": len(diffs),
        }
    except ImportError:
        return bootstrap_ci_paired([a - b for a, b in zip(scores_a, scores_b)])
