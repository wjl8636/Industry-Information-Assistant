# -*- coding: utf-8 -*-
"""
evaluation/metrics/rule_based.py
================================================================================
基于规则/统计的轻量级评测指标。

适用于批量运行、CI、消融实验等需要快速、免费、可复现评分的场景。
同时提供面向项目内部信号（facts / references / charts / knowledge_graph）的指标，
充分利用 DeepResearchState 中已有的结构化产物。
================================================================================
"""
from __future__ import annotations

import math
import re
from typing import Any


class RuleBasedMetrics:
    """研究报告质量评测指标集合（规则版）。"""

    # ------------------------------------------------------------------
    # 1. 事实准确性 — 字符串匹配版（快速但粗糙）
    # ------------------------------------------------------------------
    @staticmethod
    def fact_accuracy(report: str, ground_truth: dict[str, Any] | None = None) -> float:
        if not ground_truth or not report:
            return 0.0
        report_lower = report.lower()
        matched = 0
        for key_fact in ground_truth.keys():
            if key_fact.lower() in report_lower:
                matched += 1
        return matched / len(ground_truth)

    # ------------------------------------------------------------------
    # 1b. 语义事实准确性（可选，需嵌入模型）
    # ------------------------------------------------------------------
    @staticmethod
    def semantic_fact_accuracy(
        report: str,
        ground_truth: dict[str, Any] | None = None,
        threshold: float = 0.65,
    ) -> float:
        """基于 embedding 语义相似度的事实准确性验证（可选，未装嵌入模型时返回字符串版）。"""
        if not ground_truth or not report:
            return 0.0
        try:
            import numpy as np
            from service.embedding_service import generate_embedding
        except Exception:
            # 无嵌入模型时回退到字符串匹配
            return RuleBasedMetrics.fact_accuracy(report, ground_truth)

        chunks = [s.strip() for s in re.split(r"[。！？\n]", report) if len(s.strip()) > 10]
        if not chunks:
            return 0.0
        try:
            chunk_embs = np.array(generate_embedding(chunks))
        except Exception:
            return RuleBasedMetrics.fact_accuracy(report, ground_truth)

        matched = 0
        for key_fact, expected_desc in ground_truth.items():
            fact_text = f"{key_fact}：{expected_desc}"
            try:
                fact_emb = np.array(generate_embedding([fact_text]))[0]
            except Exception:
                if key_fact.lower() in report.lower():
                    matched += 1
                continue
            sims = chunk_embs.dot(fact_emb)
            max_sim = float(np.max(sims)) if sims.size > 0 else 0.0
            if max_sim > threshold:
                matched += 1
        return matched / len(ground_truth)

    # ------------------------------------------------------------------
    # 2. 幻觉率
    # ------------------------------------------------------------------
    @staticmethod
    def hallucination_rate(report: str) -> float:
        if not report:
            return 1.0
        sentences = [s.strip() for s in re.split(r"[。！？\n]", report) if s.strip()]
        if not sentences:
            return 1.0

        indicators = [
            r"\d+[\d,]*\.?\d*\s*(%|倍|个|人|元|美元|亿|万)",
            r"毫无疑问|绝对|必然|一定|众所周知",
            r"据我所知|据了解|研究显示[^【\[（(]",
        ]
        suspicious = 0
        for sentence in sentences:
            if not re.search(r"[\[【（(].*?[\]）)]", sentence):
                for pat in indicators:
                    if re.search(pat, sentence):
                        suspicious += 1
                        break
        return min(1.0, suspicious / max(len(sentences), 1))

    # ------------------------------------------------------------------
    # 3. 引用覆盖率
    # ------------------------------------------------------------------
    @staticmethod
    def citation_coverage(report: str) -> float:
        if not report:
            return 0.0
        paragraphs = [p.strip() for p in report.split("\n") if p.strip()]
        if not paragraphs:
            return 0.0
        patterns = [
            r"\[\d+\]", r"\[来源[：:]", r"【来源[：:]", r"\(来源[：:]",
            r"https?://", r"arxiv\.org",
        ]
        cited = 0
        for para in paragraphs:
            if any(re.search(p, para) for p in patterns):
                cited += 1
        return cited / len(paragraphs)

    # ------------------------------------------------------------------
    # 4. 逻辑一致性
    # ------------------------------------------------------------------
    @staticmethod
    def logical_consistency(report: str) -> float:
        if not report:
            return 0.0
        pairs = [("是", "不是"), ("可以", "不可以"), ("会", "不会"),
                 ("支持", "反对"), ("增加", "减少")]
        sentences = [s.strip() for s in re.split(r"[。！？\n]", report) if s.strip()]
        if not sentences:
            return 0.0
        contradiction = 0
        for sentence in sentences:
            if any(a in sentence and b in sentence for a, b in pairs):
                contradiction += 1
        connectives = ["因此", "所以", "然而", "但是", "首先", "其次", "综上所述"]
        bonus = min(0.1, sum(1 for c in connectives if c in report) * 0.01)
        base = 1.0 - (contradiction / max(len(sentences), 1))
        return min(1.0, max(0.0, base + bonus))

    # ------------------------------------------------------------------
    # 5. 完备性
    # ------------------------------------------------------------------
    @staticmethod
    def comprehensiveness(report: str, expected_topics: list[str] | None = None) -> float:
        if not expected_topics or not report:
            return 0.0
        report_lower = report.lower()
        covered = sum(1 for t in expected_topics if t.lower() in report_lower)
        return covered / len(expected_topics)

    # ------------------------------------------------------------------
    # 6. 引用闭环率（利用项目 facts/references）
    # ------------------------------------------------------------------
    @staticmethod
    def reference_closure(facts: list[dict[str, Any]], references: list[dict[str, Any]]) -> float:
        """每条 reference 是否都能在 facts 中找到对应 source_url。"""
        if not references:
            return 1.0  # 无引用视为空但不算失分（或可调整）
        fact_urls = {f.get("source_url", "") for f in (facts or [])}
        if not fact_urls:
            return 0.0
        closed = sum(1 for r in references if r.get("url") in fact_urls)
        return closed / len(references)

    # ------------------------------------------------------------------
    # 7. 结构化产出完整性（内部信号）
    # ------------------------------------------------------------------
    @staticmethod
    def structure_completeness(result: dict[str, Any]) -> float:
        """基于 final_report / facts / charts / references 是否齐备的综合完整性（0-1）。"""
        checks = [
            bool(result.get("final_report")),
            len(result.get("facts", [])) > 0,
            len(result.get("references", [])) > 0,
        ]
        return sum(1 for c in checks if c) / len(checks)

    # ------------------------------------------------------------------
    # 8. 综合得分
    # ------------------------------------------------------------------
    @staticmethod
    def composite_score(metrics: dict[str, float], weights: dict[str, float] | None = None) -> float:
        default_weights = {
            "factual_accuracy": 0.25,
            "logical_consistency": 0.20,
            "citation_coverage": 0.20,
            "bias": 0.20,
            "comprehensiveness": 0.15,
        }
        w = weights if weights is not None else default_weights
        total_score = 0.0
        total_weight = 0.0
        for key, weight in w.items():
            total_score += metrics.get(key, 0.0) * weight
            total_weight += weight
        return total_score / total_weight if total_weight > 0 else 0.0

    # ------------------------------------------------------------------
    # 9. 效率指标
    # ------------------------------------------------------------------
    @staticmethod
    def efficiency_score(num_turns: int, target_turns: float = 8.0, slope: float = 0.5,
                         max_bonus: float = 0.5) -> float:
        sigmoid = 1.0 / (1.0 + math.exp(-slope * (target_turns - num_turns)))
        return max_bonus * sigmoid


# =============================================================================
# 便捷：对一份结构化 research_sync 结果计算全部规则指标
# =============================================================================
def evaluate_rule_metrics(
    result: dict[str, Any],
    question: dict[str, Any],
) -> dict[str, float]:
    """对单个 research_sync 结果计算规则指标。question 含 expected_topics / ground_truth。"""
    report = result.get("final_report", "")
    expected_topics = question.get("expected_topics", [])
    ground_truth = question.get("ground_truth", {})

    factual = RuleBasedMetrics.fact_accuracy(report, ground_truth)
    hallucination = RuleBasedMetrics.hallucination_rate(report)
    citation = RuleBasedMetrics.citation_coverage(report)
    logic = RuleBasedMetrics.logical_consistency(report)
    comprehensive = RuleBasedMetrics.comprehensiveness(report, expected_topics)
    bias = max(0.0, 1.0 - hallucination)
    closure = RuleBasedMetrics.reference_closure(result.get("facts", []), result.get("references", []))
    struct = RuleBasedMetrics.structure_completeness(result)

    metrics = {
        "factual_accuracy": round(factual, 4),
        "logical_consistency": round(logic, 4),
        "citation_coverage": round(citation, 4),
        "bias": round(bias, 4),
        "comprehensiveness": round(comprehensive, 4),
        "reference_closure": round(closure, 4),
        "structure_completeness": round(struct, 4),
        "hallucination_rate": round(hallucination, 4),
    }
    composite = RuleBasedMetrics.composite_score({
        "factual_accuracy": factual,
        "logical_consistency": logic,
        "citation_coverage": citation,
        "bias": bias,
        "comprehensiveness": comprehensive,
    })
    metrics["composite_score"] = round(composite, 4)
    return metrics
