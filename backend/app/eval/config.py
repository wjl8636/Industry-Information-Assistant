# -*- coding: utf-8 -*-
"""
Eval 共享配置与工具。

评测需要两类 API：
- Multi-Agent：DASHSCOPE_API_KEY（项目现有多智能体）
- Direct LLM / Judge：中转端点（OpenAI 兼容），可选

中转端点配置（backend/.env 新增，可选）：
    EVAL_LLM_BASE_URL=https://llm.goaichat.top/v1
    EVAL_LLM_API_KEY=sk-...         # 你的中转 key（必填才能跑 Direct/Judge）
    EVAL_LLM_MODEL=deepseek-v4-pro  # Direct 基座与 Judge 默认模型

安全：密钥只从环境变量/.env 读取，不落盘明文。
"""

import os
import json
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **k):
        pass

# 定位 backend 根目录（app 的上一级）
APP_DIR = Path(os.path.dirname(os.path.abspath(__file__)))  # .../app/eval
BACKEND_DIR = APP_DIR.parent.parent
load_dotenv(BACKEND_DIR / ".env")

# ---- 数据 ----
DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset", "cn_drb_5.jsonl")


def load_dataset(path: str = DATASET_PATH) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ---- API 配置 ----
def get_multi_agent_config() -> dict:
    """生成报告的配置（优先中转端点 MA_LLM_*，回退 DASHSCOPE）。"""
    return {
        "llm_api_key": os.getenv("MA_LLM_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", ""),
        "llm_base_url": os.getenv("MA_LLM_BASE_URL", "") or os.getenv(
            "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        "model": os.getenv("MA_LLM_MODEL", "qwen3.7-plus"),
        "search_api_key": os.getenv("BOCHA_API_KEY", ""),
    }


def get_eval_llm_config() -> dict:
    """独立 Judge 使用的中转端点配置（不用于生成报告）。"""
    return {
        "base_url": os.getenv("EVAL_LLM_BASE_URL", ""),
        "api_key": os.getenv("EVAL_LLM_API_KEY", ""),
        "model": os.getenv("EVAL_LLM_MODEL", "deepseek-v4-pro"),
    }


def eval_llm_available() -> bool:
    cfg = get_eval_llm_config()
    return bool(cfg["api_key"] and cfg["base_url"])


# ---- 结果保存 ----
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def save_result(name: str, data) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def ensure_ssl() -> None:
    """若 SSL_CERT_FILE 指向不存在文件，则 unset，避免 httpx 构造失败。"""
    cert = os.environ.get("SSL_CERT_FILE")
    if cert and not os.path.exists(cert):
        os.environ.pop("SSL_CERT_FILE", None)
        print("  [eval] 清理无效 SSL_CERT_FILE:", cert)