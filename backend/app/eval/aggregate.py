# -*- coding: utf-8 -*-
"""
聚合：从 results/comparison.json 计算配对指标。

输出：
- 综合质量分（Direct / Multi-Agent）均值
- 四维子分均值（信息完整性 / 研究深度 / 逻辑完整性[近似] / 可读性）
- 配对 Δ（Multi-Agent 相对 Direct）
- 引用指标（FACT：citation_accuracy）
- 配对显著性（配对 t 检验近似；小样本输出 bootstrapped CI 简化版）
- 附加：Multi-Agent 内部指标（quality_score, grounding_gate, citation_validation）

用法：
    python app/eval/aggregate.py
"""

import os
import sys
import json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from config import RESULTS_DIR


def _mean(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def main() -> None:
    path = os.path.join(RESULTS_DIR, "comparison.json")
    if not os.path.exists(path):
        print(f"未找到 {path}，请先运行 run_comparison.py")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])
    dims = ["comprehensiveness", "depth", "instruction_following", "readability"]

    agg = {"n": len(samples), "direct": {}, "multi": {}, "paired": {}, "multi_internal": {}}

    # 收集 paired 数据
    direct_overall, multi_overall = [], []
    direct_dims = {k: [] for k in dims}
    multi_dims = {k: [] for k in dims}
    direct_cite_acc, multi_cite_acc = [], []
    diffs_overall = []

    for s in samples:
        d = s.get("direct_judge") or {}
        m = s.get("multi_judge") or {}

        if d.get("overall_score") is not None:
            direct_overall.append(d["overall_score"])
        if m.get("overall_score") is not None:
            multi_overall.append(m["overall_score"])
        if d.get("overall_score") is not None and m.get("overall_score") is not None:
            diffs_overall.append(m["overall_score"] - d["overall_score"])

        for k in dims:
            if d.get("dimensions") and d["dimensions"].get(k) is not None:
                direct_dims[k].append(d["dimensions"][k])
            if m.get("dimensions") and m["dimensions"].get(k) is not None:
                multi_dims[k].append(m["dimensions"][k])

        if d.get("fact") and d["fact"].get("citation_accuracy") is not None:
            direct_cite_acc.append(d["fact"]["citation_accuracy"])
        if m.get("fact") and m["fact"].get("citation_accuracy") is not None:
            multi_cite_acc.append(m["fact"]["citation_accuracy"])

    agg["direct"]["overall_mean"] = _mean(direct_overall)
    agg["multi"]["overall_mean"] = _mean(multi_overall)
    agg["direct"]["dimension_means"] = {k: _mean(direct_dims[k]) for k in dims}
    agg["multi"]["dimension_means"] = {k: _mean(multi_dims[k]) for k in dims}
    agg["direct"]["citation_accuracy_mean"] = _mean(direct_cite_acc)
    agg["multi"]["citation_accuracy_mean"] = _mean(multi_cite_acc)

    # 配对差
    if direct_overall and multi_overall:
        agg["paired"]["overall_diff_multi_minus_direct"] = round(
            (agg["multi"]["overall_mean"] or 0) - (agg["direct"]["overall_mean"] or 0), 4
        )
        agg["paired"]["n_paired"] = len(diffs_overall)
        if diffs_overall:
            agg["paired"]["diff_mean"] = round(sum(diffs_overall) / len(diffs_overall), 4)
            # 简化显著性：差值均值±std（小样本不做正式检验）
            import statistics
            std = statistics.stdev(diffs_overall) if len(diffs_overall) > 1 else 0.0
            agg["paired"]["diff_std"] = round(std, 4)

    # Multi-Agent 内部指标
    multi_quality = [s["multi"]["quality_score"] for s in samples if s.get("multi") and s["multi"].get("quality_score") is not None]
    gate_pass = [s for s in samples if s.get("multi") and s["multi"].get("grounding_gate") and s["multi"]["grounding_gate"].get("gate_passed") is True]
    agg["multi_internal"]["quality_score_mean"] = _mean(multi_quality)
    agg["multi_internal"]["grounding_gate_pass_count"] = len(gate_pass)
    agg["multi_internal"]["grounding_gate_total"] = len(samples)

    # 每维相对提升（Multi - Direct）/ Direct
    pct = {}
    for k in dims:
        dd = agg["direct"]["dimension_means"].get(k)
        md = agg["multi"]["dimension_means"].get(k)
        if dd and dd > 0 and md is not None:
            pct[k] = round((md - dd) / dd * 100, 2)
    agg["paired"]["dimension_pct_change"] = pct

    print(json.dumps(agg, ensure_ascii=False, indent=2))
    out = os.path.join(RESULTS_DIR, "aggregate.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    print(f"\n保存: {out}")


if __name__ == "__main__":
    main()