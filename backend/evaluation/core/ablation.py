# -*- coding: utf-8 -*-
"""
evaluation/core/ablation.py
================================================================================
消融实验通用框架。

适配本项目配置模型（代码配置 + max_iterations 控制审核轮数）：

模块消融:
    full              : 完整系统
    no_review         : 关闭对抗审核（max_iterations=0，即去掉 CriticMaster 审核闭环）
    no_web_search     : 关闭网络搜索（search_web=False）
    no_local_search   : 关闭本地知识库（search_local=False）

轮数消融:
    rounds 0..N      : 审核-修订循环轮数（与 max_iterations 对应）
================================================================================
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger("eval.ablation")

# 模块消融默认映射：name -> (描述, 运行时配置覆盖)
DEFAULT_MODULE_ABLATIONS: dict[str, tuple[str, dict]] = {
    "full": ("完整系统", {}),
    "no_review": ("关闭对抗审核(CriticMaster)", {"max_iterations": 0}),
    "no_web_search": ("关闭网络搜索", {"search_web": False}),
    "no_local_search": ("关闭本地知识库", {"search_local": True, "search_web": False}),
}


class AblationStudy:
    """消融实验框架。"""

    # ------------------------------------------------------------------
    # 配置覆盖
    # ------------------------------------------------------------------
    @staticmethod
    def override_config(config: dict, overrides: dict) -> dict:
        """深拷贝并覆盖配置（浅覆盖即可，本项目配置为扁平 dict）。"""
        cfg = copy.deepcopy(config)
        for k, v in overrides.items():
            cfg[k] = v
        return cfg

    # ------------------------------------------------------------------
    # 单个系统跑分
    # ------------------------------------------------------------------
    @classmethod
    def run_single_system(
        cls,
        system_name: str,
        config: dict,
        overrides: dict,
        questions: list[dict[str, Any]],
        scorer,
    ) -> dict[str, Any]:
        """运行单个系统配置，返回每道题评分。scorer 由调用方注入（注入规则/内部指标）。"""
        from .runner import initialize_modules, run_research_full

        cfg = cls.override_config(config, overrides)
        modules = initialize_modules(cfg)

        per_q: dict[str, float] = {}
        details: list[dict[str, Any]] = []

        for q in questions:
            qid = q["id"]
            query = q["query"]
            print(f"  [{qid}] {query[:50]}...")
            start = time.time()
            try:
                result = run_research_full(query, cfg, modules)
                elapsed = time.time() - start
                score = scorer(result, q) or 0.0
                per_q[qid] = float(score)
                details.append({
                    "question_id": qid,
                    "composite_score": float(score),
                    "elapsed_seconds": elapsed,
                    "report_length": len(result.get("final_report", "")),
                })
                print(f"    → score={score:.3f}, time={elapsed:.1f}s")
            except Exception as e:
                logger.warning(f"  FAILED {qid}: {e}")
                per_q[qid] = 0.0
                details.append({"question_id": qid, "error": str(e), "composite_score": 0.0})

        scores = list(per_q.values())
        return {
            "system_name": system_name,
            "average_composite_score": sum(scores) / len(scores) if scores else 0.0,
            "per_question_scores": per_q,
            "details": details,
        }

    # ------------------------------------------------------------------
    # 统计显著性
    # ------------------------------------------------------------------
    @staticmethod
    def compute_stats(full_result: dict, ablation_result: dict) -> dict:
        from evaluation.metrics.stats import bootstrap_ci_paired, cohens_d

        full_scores, abl_scores = [], []
        for qid in full_result["per_question_scores"]:
            if qid in ablation_result["per_question_scores"]:
                full_scores.append(full_result["per_question_scores"][qid])
                abl_scores.append(ablation_result["per_question_scores"][qid])

        diffs = [f - a for f, a in zip(full_scores, abl_scores)]
        stats = bootstrap_ci_paired(diffs)
        stats["cohens_d"] = round(cohens_d(full_scores, abl_scores), 4)
        stats["full_mean"] = round(sum(full_scores) / len(full_scores), 4) if full_scores else 0.0
        stats["ablation_mean"] = round(sum(abl_scores) / len(abl_scores), 4) if abl_scores else 0.0
        return stats

    # ------------------------------------------------------------------
    # 模块消融
    # ------------------------------------------------------------------
    @classmethod
    def run_module_ablation(
        cls,
        config: dict,
        questions: list[dict[str, Any]],
        scorer,
        systems: dict[str, tuple[str, dict]] | None = None,
    ) -> dict[str, Any]:
        systems = systems or DEFAULT_MODULE_ABLATIONS
        all_results: dict[str, dict] = {}
        for name, (desc, overrides) in systems.items():
            print(f"\n{'='*60}\n[模块消融] {name}: {desc}\n{'='*60}")
            all_results[name] = cls.run_single_system(name, config, overrides, questions, scorer)

        stats_report = {}
        full = all_results["full"]
        for name, res in all_results.items():
            if name != "full":
                stats_report[name] = cls.compute_stats(full, res)

        report = {
            "evaluation_name": "行业信息助手 模块消融实验（含统计显著性）",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "num_questions": len(questions),
            "systems": [
                {"system_name": r["system_name"], "description": systems[n][0],
                 "average_composite_score": r["average_composite_score"], "details": r["details"]}
                for n, r in all_results.items()
            ],
            "summary": {n: r["average_composite_score"] for n, r in all_results.items()},
            "statistical_tests": stats_report,
        }
        return report

    # ------------------------------------------------------------------
    # 审核轮数消融
    # ------------------------------------------------------------------
    @classmethod
    def run_rounds_ablation(
        cls,
        config: dict,
        questions: list[dict[str, Any]],
        scorer,
        max_rounds: int = 3,
    ) -> dict[str, Any]:
        all_results: dict[str, dict] = {}
        for rounds in range(max_rounds + 1):
            overrides = {"max_iterations": rounds}
            print(f"\n{'='*50}\n[轮数消融] max_iterations={rounds}\n{'='*50}")
            all_results[f"adv_{rounds}"] = cls.run_single_system(
                f"adv_{rounds}", config, overrides, questions, scorer)

        base = all_results["adv_0"]
        stats_report = {}
        for name, res in all_results.items():
            if name != "adv_0":
                stats_report[name] = cls.compute_stats(base, res)

        report = {
            "evaluation_name": "行业信息助手 审核轮数消融实验（含统计显著性）",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "num_questions": len(questions),
            "systems": [
                {"system_name": n, "description": f"审核轮数={n.split('_')[1]}",
                 "average_composite_score": r["average_composite_score"], "details": r["details"]}
                for n, r in all_results.items()
            ],
            "summary": {n: r["average_composite_score"] for n, r in all_results.items()},
            "statistical_tests": stats_report,
        }
        return report

    @staticmethod
    def save_results(data: dict, output_dir: str, prefix: str = "ablation") -> str:
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"{prefix}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path
