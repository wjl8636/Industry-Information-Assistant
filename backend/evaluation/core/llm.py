# -*- coding: utf-8 -*-
"""
evaluation/core/llm.py
================================================================================
评测用 LLM 统一后端。

复用项目的 OpenAI 兼容客户端（DashScope / OpenRouter 等），提供与参考项目
`ModelRouter.create_backend()` 一致的可调用策略接口：

    policy = EvalLLM.create(backend="judge")
    resp = policy(messages)          # -> {"content": "..."}

后端来源（优先级从高到低）：
  1. 显式传入的 api_key / base_url / model
  2. 环境变量 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL / OPENAI_MODEL
  3. 项目配置 llm_config.get_config()
================================================================================
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("eval.llm")

# 项目配置路径（backend/app 下的 config.llm_config）
try:
    from config.llm_config import get_config as _get_project_config
except Exception:  # pragma: no cover
    _get_project_config = None


class EvalLLM:
    """评测用 LLM 策略。接口兼容参考项目的 policy(messages) -> {"content": str}。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        backend_name: str = "eval",
    ) -> None:
        self.backend_name = backend_name
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    # ------------------------------------------------------------------
    # 客户端构造
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_credentials():
        """解析评测 LLM 的凭据。"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = os.getenv("OPENAI_MODEL") or os.getenv("DEFAULT_EVAL_MODEL")

        if _get_project_config is not None:
            try:
                cfg = _get_project_config()
                api_key = api_key or cfg.api_key or None
                base_url = base_url or cfg.base_url or None
                model = model or cfg.default_model or None
            except Exception as e:  # pragma: no cover
                logger.warning(f"读取项目配置失败: {e}")

        return api_key, base_url, model

    @classmethod
    def create(
        cls,
        backend: str = "judge",
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> "EvalLLM":
        """工厂方法。backend 仅用于命名（可区分 judge / baseline 等）。"""
        a, b, m = cls._resolve_credentials()
        return cls(
            api_key=api_key or a,
            base_url=base_url or b,
            model=model or m,
            temperature=temperature,
            max_tokens=max_tokens,
            backend_name=backend,
        )

    def _ensure_client(self):
        if self._client is not None:
            return
        if not self.api_key:
            raise ValueError(
                "评测需要配置 LLM API Key。请设置 DASHSCOPE_API_KEY 环境变量，"
                "或在 backend/.env 中配置 DASHSCOPE_API_KEY。"
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    # ------------------------------------------------------------------
    # 调用接口
    # ------------------------------------------------------------------
    def __call__(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """与参考项目 policy(messages) -> {"content": ...} 兼容。"""
        self._ensure_client()
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return {"content": resp.choices[0].message.content or ""}
        except Exception as e:
            logger.error(f"LLM 调用失败 ({self.backend_name}): {e}")
            raise

    async def acall(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """异步调用（内部用线程池）。"""
        import asyncio
        return await asyncio.to_thread(self.__call__, messages)


# 便捷访问
def get_judge_policy(**kwargs) -> EvalLLM:
    """获取 Judge 策略。"""
    return EvalLLM.create(backend="judge", **kwargs)


def get_baseline_policy(**kwargs) -> EvalLLM:
    """获取单轮 LLM baseline 策略（对话型，温度略高）。"""
    kwargs.setdefault("temperature", 0.7)
    return EvalLLM.create(backend="baseline", **kwargs)
