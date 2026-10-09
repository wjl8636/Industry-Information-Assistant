"""
Supervisor Budget Controller - 调用预算与失败降级

目标：让单次研究在 token 预算内运行，不因单个调用失败整体崩溃。

职责：
1. 记录 session 级 token_used / call_count（统一在 base.call_llm 挂载）
2. 超额处理：token/调用数超限时返回降级信号，由 caller 决定缩减上下文或跳过
3. 失败分类降级：
   - rate_limit / 429       → 退避重试（可配重试次数）
   - timeout / 500 / 502    → 读缓存（若实现）或降级
   - 其它                    → 快速失败信号，不放任异常冒泡杀死整个流程
4. 把 budget 状态回写 state["budget"]，供 SSE / 评测可见

设计原则：budget_controller 是纯逻辑层，不持 LLM 客户端；由 base.call_llm
在调用前/后调用它记账与决策，避免改动各 Agent。
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("BudgetController")


class BudgetError(Exception):
    """预算超限或降级触发的异常（可在 call_llm 内捕获并按降级策略处理）"""
    def __init__(self, reason: str, stage: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.stage = stage


class BudgetController:
    def __init__(
        self,
        cpu_token_limit: int = 0,          # 0 = 不限制 token 总量
        cpu_call_limit: int = 0,           # 0 = 不限制调用次数
        degraded_retry_times: int = 1,     # rate_limit 退避重试次数
    ):
        self.token_used = 0
        self.call_count = 0
        self.cpu_token_limit = cpu_token_limit
        self.cpu_call_limit = cpu_call_limit
        self.degraded_retry_times = degraded_retry_times
        self.degraded_steps: list = []
        self.budget_exceeded = False

    # ---------- 记账 ----------
    def before_call(self) -> None:
        self.call_count += 1

    def after_call(self, tokens_used: int = 0) -> None:
        self.token_used += tokens_used

    # ---------- 预算检查 ----------
    def check_token(self, model: str = "", stage: str = "") -> bool:
        """返回是否允许继续。超限时记录 degraded，并抛 BudgetError。"""
        if self.cpu_token_limit and self.token_used >= self.cpu_token_limit:
            self.budget_exceeded = True
            reason = f"token 预算已达上限 {self.cpu_token_limit} (当前 {self.token_used})"
            self.degraded_steps.append({"stage": stage, "reason": reason})
            logger.warning(reason)
            raise BudgetError(reason, stage)
        return True

    def check_call(self, stage: str = "") -> bool:
        if self.cpu_call_limit and self.call_count >= self.cpu_call_limit:
            self.budget_exceeded = True
            reason = f"调用次数预算已达上限 {self.cpu_call_limit} (当前 {self.call_count})"
            self.degraded_steps.append({"stage": stage, "reason": reason})
            logger.warning(reason)
            raise BudgetError(reason, stage)
        return True

    # ---------- 失败分类与降级 ----------
    @staticmethod
    def classify_error(exc: Exception) -> str:
        """把异常分类为 rate_limit / timeout / transient / other"""
        text = str(exc).lower()
        if "rate" in text or "429" in text or "qps" in text or "limit" in text or "quota" in text:
            return "rate_limit"
        if "timeout" in text or "timed out" in text or "connection" in text or "503" in text or "502" in text:
            return "transient"
        if "server" in text or "500" in text or "internal" in text:
            return "transient"
        return "other"

    async def handle_failure(self, exc: Exception, stage: str = "") -> str:
        """处理调用失败。

        Returns:
            "retry"     → caller 应退避重试
            "degraded"  → caller 应降级（缩减上下文或跳过）
            "raise"     → caller 应放行异常（预算严重超限等）
        """
        kind = self.classify_error(exc)

        if isinstance(exc, BudgetError):
            self.degraded_steps.append({"stage": stage, "reason": exc.reason})
            return "raise"

        if kind == "rate_limit":
            # 触发退避重试策略
            if self.degraded_retry_times > 0:
                self.degraded_retry_times -= 1
                logger.warning(f"[Budget][rate_limit] stage={stage}, 退避重试（剩余 {self.degraded_retry_times} 次）: {exc}")
                return "retry"
            self.degraded_steps.append({"stage": stage, "reason": f"rate_limit 重试耗尽: {exc}"})
            return "degraded"

        if kind == "transient":
            # 短暂抖动：给一次退避重试机会，否则降级
            logger.warning(f"[Budget][transient] stage={stage}: {exc}")
            self.degraded_steps.append({"stage": stage, "reason": f"transient 失败降级: {exc}"})
            return "retry" if self.degraded_retry_times > 0 else "degraded"

        # unknown error
        self.degraded_steps.append({"stage": stage, "reason": f"未分类失败: {exc}"})
        return "degraded"

    # ---------- 状态导出 ----------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_used": self.token_used,
            "call_count": self.call_count,
            "degraded_steps": self.degraded_steps,
            "budget_exceeded": self.budget_exceeded,
        }

    def sync_to_state(self, state: Dict[str, Any]) -> None:
        if "budget" in state:
            state["budget"] = self.to_dict()


async def wait_backoff(attempt: int, base_ms: int = 500) -> None:
    """指数退避（attempt 从 0 开始）"""
    await asyncio.sleep(base_ms * (2 ** attempt) / 1000)


# 全局便捷单例（进程内），也可按 research session 绑定到 state
_budget: Optional[BudgetController] = None


def get_budget() -> BudgetController:
    global _budget
    if _budget is None:
        _budget = BudgetController()
    return _budget