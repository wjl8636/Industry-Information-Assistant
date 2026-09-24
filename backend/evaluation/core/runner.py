# -*- coding: utf-8 -*-
"""
evaluation/core/runner.py
================================================================================
评测运行器 —— 将项目 DeepResearch V2 服务接入统一评测入口。

对外接口（与参考项目 src/core/runner.py 对齐）:
    - setup_logging(level)          -> None
    - load_config(config_path=None) -> dict    （轻量，返回运行参数）
    - initialize_modules(config)    -> dict    （初始化 DeepResearchV2Service）
    - run_research(query, config, modules) -> str  （返回最终报告 Markdown）

关键解耦：评测只依赖 run_research 的签名，不关心 Agent 内部实现。
也提供 run_research_full 返回结构化 dict，供内部信号指标使用。
================================================================================
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# 项目 import 根 = backend/app
APP_DIR = Path(__file__).resolve().parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

logger = logging.getLogger("eval.runner")


def setup_logging(level: str = "INFO") -> None:
    """配置全局日志。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(config_path: str | None = None) -> dict:
    """加载运行参数。

    项目用代码配置（llm_config），此处仅返回一组可在消融时覆盖的默认参数。
    config_path 兼容传入（若为 YAML/JSON 文件则加载）。
    """
    defaults = {
        "model": None,               # None -> 使用配置默认模型
        "max_iterations": None,      # None -> 使用配置默认迭代次数
        "search_web": True,
        "search_local": False,
    }
    if config_path and Path(config_path).exists():
        import json
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.endswith((".json", ".jsonl")):
                    data = json.load(f)
                else:
                    import yaml
                    data = yaml.safe_load(f)
            if isinstance(data, dict):
                defaults.update({k: v for k, v in data.items() if k in defaults})
        except Exception as e:  # pragma: no cover
            logger.warning(f"加载评测配置失败，使用默认值: {e}")
    return defaults


def initialize_modules(config: dict) -> dict[str, Any]:
    """初始化 DeepResearchV2Service。"""
    from service.deep_research_v2.service import DeepResearchV2Service

    service = DeepResearchV2Service(
        llm_api_key=config.get("llm_api_key"),
        llm_base_url=config.get("llm_base_url"),
        search_api_key=config.get("search_api_key"),
        model=config.get("model"),
        max_iterations=config.get("max_iterations"),
    )
    return {"service": service, "config": config}


def run_research(query: str, config: dict, modules: dict[str, Any]) -> str:
    """执行研究，返回最终报告文本（Markdown）。"""
    result = run_research_full(query, config, modules)
    return result.get("final_report", "") if result else ""


def run_research_full(
    query: str,
    config: dict,
    modules: dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    """执行研究，返回结构化结果（含 final_report / quality_score / facts / references 等）。"""
    import uuid

    service = modules["service"]
    sid = session_id or f"eval_{uuid.uuid4().hex[:12]}"

    start = time.time()
    try:
        result = service.research_sync(
            query,
            session_id=sid,
        )
        # research_sync 返回 dict，包含 final_report / quality_score / facts / references ...
        if not isinstance(result, dict):
            result = {"final_report": str(result)}
    except Exception as e:
        logger.warning(f"研究失败 ({sid}): {e}")
        result = {"final_report": "", "error": str(e)}

    result["session_id"] = sid
    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


def save_report(report: str, query: str, output_dir: str = "outputs/eval_reports") -> str:
    """保存报告到文件。"""
    from datetime import datetime

    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in query[:20])
    path = os.path.join(output_dir, f"report_{ts}_{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path
