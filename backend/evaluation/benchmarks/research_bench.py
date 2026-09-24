# -*- coding: utf-8 -*-
"""
evaluation/benchmarks/research_bench.py
================================================================================
自建行业深度研究评测集 (IndustryResearchBench)。

面向本项目的四大行业（智慧交通 / 金融科技 / 医疗健康 / 能源电力），
与项目 config/industry_config.py 的行业定义对齐。
每道题附带:
    - expected_topics: 期望覆盖的子主题（用于 comprehensiveness）
    - ground_truth :   关键事实（用于 fact_accuracy）
题目可按行业过滤，也可从外部 JSON 加载自定义题库。
================================================================================
"""
from __future__ import annotations

import json
import os
from typing import Any

# 与 backend/app/config/industry_config.py 中的行业关键词对齐
DEFAULT_QUESTIONS: list[dict[str, Any]] = [
    # ============ 智慧交通 ============
    {
        "id": "traffic_001",
        "domain": "智慧交通",
        "query": "分析 2024-2025 年中国智慧交通行业的市场规模、政策环境与技术路线（车路协同、智能网联汽车），并给出主要挑战与发展趋势。",
        "expected_topics": ["车路协同", "智能网联汽车", "自动驾驶", "智慧交通", "政策", "市场规模", "交通大数据"],
        "ground_truth": {
            "车路协同": "V2X 车路协同是智慧交通核心技术路线",
            "智能网联汽车": "中国智能网联汽车产业进入规模落地期",
            "政策": "交通运输部等多部门出台智慧交通相关政策",
        },
    },
    {
        "id": "traffic_002",
        "domain": "智慧交通",
        "query": "对比分析车路协同（V2X）与单车智能（纯视觉/多传感器）在自动驾驶商业化落地中的技术路线差异、成本结构与政策支持。",
        "expected_topics": ["V2X", "车路协同", "单车智能", "自动驾驶", "激光雷达", "纯视觉", "成本"],
        "ground_truth": {
            "V2X": "车路协同依赖路侧基础设施与通信网络",
            "纯视觉": "特斯拉 FSD 采用纯视觉端到端方案",
            "激光雷达": "多传感器融合方案成本较高",
        },
    },
    # ============ 金融科技 ============
    {
        "id": "fintech_001",
        "domain": "金融科技",
        "query": "分析 2024-2025 年中国金融科技行业在数字人民币、银行数字化转型、智能风控方向的发展现状与监管趋势。",
        "expected_topics": ["数字人民币", "银行数字化转型", "智能风控", "金融科技", "监管", "支付"],
        "ground_truth": {
            "数字人民币": "数字人民币试点范围持续扩大",
            "智能风控": "AI 风控在银行信贷与反欺诈中广泛应用",
            "监管": "金融科技面临强监管与合规要求",
        },
    },
    {
        "id": "fintech_002",
        "domain": "金融科技",
        "query": "评估大模型（LLM）在金融行业的理赔、量化投研与智能客服场景中的应用现状、落地难点与合规风险。",
        "expected_topics": ["大模型", "金融", "理赔", "量化投研", "智能客服", "合规", "幻觉"],
        "ground_truth": {
            "理赔": "大模型可提升理赔审核效率但需人工复核",
            "幻觉": "金融大模型面临幻觉导致的信息风险",
            "合规": "金融生成式 AI 需满足监管合规要求",
        },
    },
    # ============ 医疗健康 ============
    {
        "id": "health_001",
        "domain": "医疗健康",
        "query": "分析 2024-2025 年中国医疗信息化与智慧医院建设的发展现状、政策驱动（互联网医疗、医保）与关键技术（医疗大数据、AI 医疗）。",
        "expected_topics": ["智慧医院", "医疗信息化", "互联网医疗", "AI医疗", "医疗大数据", "医保", "政策"],
        "ground_truth": {
            "智慧医院": "电子病历与互联互通是智慧医院建设基础",
            "互联网医疗": "互联网医院加速落地",
            "医保": "医保支付改革推动医院信息化升级",
        },
    },
    {
        "id": "health_002",
        "domain": "医疗健康",
        "query": "评价生成式 AI 在医学影像辅助诊断、药物研发和临床决策支持中的应用进展、准确性与伦理监管挑战。",
        "expected_topics": ["医学影像", "辅助诊断", "药物研发", "临床决策", "准确性", "伦理", "监管"],
        "ground_truth": {
            "辅助诊断": "AI 医学影像辅助诊断已进入部分医院临床",
            "药物研发": "生成式 AI 加速药物靶点发现",
            "伦理": "AI 医疗面临责任归属与数据伦理问题",
        },
    },
    # ============ 能源电力 ============
    {
        "id": "energy_001",
        "domain": "能源电力",
        "query": "分析 2024-2025 年中国新能源产业（光伏、风电、储能）的市场格局与碳中和政策驱动，评估行业产能过剩与出海挑战。",
        "expected_topics": ["光伏", "风电", "储能", "碳中和", "新能源", "产能过剩", "出海"],
        "ground_truth": {
            "碳中和": "双碳目标是新能源发展的核心驱动",
            "储能": "新型储能是电力系统灵活性的关键",
            "产能过剩": "光伏行业面临阶段性产能过剩",
        },
    },
    {
        "id": "energy_002",
        "domain": "能源电力",
        "query": "评估智能电网、虚拟电厂与电力市场改革（市场化交易、现货市场）的进展，分析其对电力系统高效运行与新能源消纳的支撑作用。",
        "expected_topics": ["智能电网", "虚拟电厂", "电力市场化", "现货市场", "新能源消纳", "储能"],
        "ground_truth": {
            "智能电网": "数字化与智能化是电网升级方向",
            "虚拟电厂": "虚拟电厂聚合需求侧与储能资源",
            "电力市场化": "电力现货市场推进市场化交易",
        },
    },
    # ============ 交叉/数据技术 ============
    {
        "id": "cross_001",
        "domain": "交叉",
        "query": "分析大模型 Agent（智能体）在行业研究、信息检索与报告生成中的应用现状，比较不同实现范式的优劣，并给出工程落地的关键挑战（上下文管理、评测、幻觉）。",
        "expected_topics": ["大模型", "Agent", "智能体", "信息检索", "幻觉", "评测", "多智能体", "工具调用"],
        "ground_truth": {
            "多智能体": "多智能体协作可分解复杂研究任务",
            "工具调用": "Agent 通过工具调用获取外部信息",
            "评测": "深度研究报告需要端到端评测体系",
        },
    },
]


class IndustryResearchBench:
    """行业深度研究评测集。"""

    def __init__(self, data_path: str | None = None) -> None:
        if data_path and os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                self.questions = json.load(f)
        else:
            self.questions = DEFAULT_QUESTIONS

    def get_questions(self, domain: str | None = None, n: int | None = None) -> list[dict[str, Any]]:
        result = self.questions
        if domain:
            result = [q for q in result if q.get("domain") == domain]
        if n is not None:
            result = result[:n]
        return result

    def get_question(self, question_id: str) -> dict[str, Any]:
        q = next((x for x in self.questions if x["id"] == question_id), None)
        if q is None:
            raise ValueError(f"未找到题目 ID: {question_id}")
        return q

    def get_domains(self) -> list[str]:
        return sorted({q.get("domain", "") for q in self.questions})

    # ------------------------------------------------------------------
    # 单篇 / 批量评测
    # ------------------------------------------------------------------
    def evaluate_report(self, report: str, question_id: str,
                        metrics_weights: dict[str, float] | None = None) -> dict[str, Any]:
        """对单篇研究报告进行规则评测。"""
        from evaluation.metrics.rule_based import RuleBasedMetrics

        q = self.get_question(question_id)
        metrics = evaluate_question(RuleBasedMetrics, report, q)
        return {
            "question_id": question_id,
            "domain": q.get("domain", ""),
            "metrics": metrics,
            "composite_score": metrics["composite_score"],
            "hallucination_rate": metrics["hallucination_rate"],
        }

    def batch_evaluate(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """批量评测。results: [{question_id, report}]。返回聚合结果。"""
        all_scores: list[dict] = []
        by_domain: dict[str, list[float]] = {}
        for item in results:
            r = self.evaluate_report(item["report"], item["question_id"])
            all_scores.append(r)
            by_domain.setdefault(r["domain"], []).append(r["composite_score"])

        if not all_scores:
            return {"average_composite": 0.0, "by_domain": {}, "details": []}
        avg = sum(s["composite_score"] for s in all_scores) / len(all_scores)
        return {
            "average_composite": round(avg, 4),
            "by_domain": {d: round(sum(scores) / len(scores), 4)
                          for d, scores in by_domain.items()},
            "details": all_scores,
        }


def evaluate_question(RuleBasedMetrics, report: str, q: dict[str, Any]) -> dict[str, float]:
    """对单题的规则指标计算。"""
    expected_topics = q.get("expected_topics", [])
    ground_truth = q.get("ground_truth", {})

    factual = RuleBasedMetrics.fact_accuracy(report, ground_truth)
    hallucination = RuleBasedMetrics.hallucination_rate(report)
    citation = RuleBasedMetrics.citation_coverage(report)
    logic = RuleBasedMetrics.logical_consistency(report)
    comprehensive = RuleBasedMetrics.comprehensiveness(report, expected_topics)
    bias = max(0.0, 1.0 - hallucination)

    metrics = {
        "factual_accuracy": round(factual, 4),
        "logical_consistency": round(logic, 4),
        "citation_coverage": round(citation, 4),
        "bias": round(bias, 4),
        "comprehensiveness": round(comprehensive, 4),
        "hallucination_rate": round(hallucination, 4),
    }
    metrics["composite_score"] = RuleBasedMetrics.composite_score({
        "factual_accuracy": factual,
        "logical_consistency": logic,
        "citation_coverage": citation,
        "bias": bias,
        "comprehensiveness": comprehensive,
    })
    return metrics


# 便捷别名
ResearchBench = IndustryResearchBench


if __name__ == "__main__":
    bench = IndustryResearchBench()
    print(f"内置题目数: {len(bench.questions)}")
    print("行业:", bench.get_domains())
    r = bench.evaluate_report("车路协同是智慧交通的重要方向[1]。", "traffic_001")
    print(json.dumps(r, ensure_ascii=False, indent=2))