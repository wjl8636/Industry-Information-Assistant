"""
Fact Deduplication - 语义级事实去重

在现有精确指纹去重之上，增加语义级去重：
1. 保留指纹快筛（低成本，精确重复直接判重）
2. canonical_url 比对（同源页面算重复）
3. 语义去重：对未命中指纹、且不同来源的候选，用向量化 + 余弦相似度
   判断是否同一语义（阈值可配置）

用途：降低事实库被同源/同义信息灌水，配合 URL 规范化。
可用性：embedding 不可用时不阻塞，自动退回"仅指纹"。
"""

import logging
from typing import List, Dict, Any, Optional

from .evidence_link import normalize_url, is_same_canonical_url

logger = logging.getLogger("FactDedup")

try:
    from .embedding_service import generate_embedding
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False


# 快速余弦相似度（numpy 可选，纯列表回退）
def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    try:
        import numpy as np
        va = np.asarray(a, dtype="float32")
        vb = np.asarray(b, dtype="float32")
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)
    except ImportError:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


class FactDedup:
    """语义去重器"""

    def __init__(self, semantic_threshold: float = 0.85):
        self.semantic_threshold = semantic_threshold
        self._embedding_cache: Dict[str, List[float]] = {}
        # embedding 可用性熔断：连续失败 N 次后本轮跳过语义去重，避免无效请求拖慢流程
        self._embedding_fail_count = 0
        self._embedding_max_fail = 2
        self._embedding_unavailable = False
        self.metrics = {
            "fingerprint_hits": 0,
            "canonical_url_hits": 0,
            "semantic_hits": 0,
            "semantic_miss": 0,
            "semantic_skipped": 0,
        }

    async def is_duplicate(
        self,
        content: str,
        source_url: str,
        existing_facts: List[Dict[str, Any]],
    ) -> bool:
        """
        判断一条候选事实是否与已有事实重复。

        Args:
            content: 候选事实内容
            source_url: 候选事实来源 URL
            existing_facts: 既有事实列表（list of dict）

        Returns:
            True 如果判定重复
        """
        if not existing_facts:
            return False

        candidates = existing_facts[-20:]  # 只与近期事实比对，控制成本

        # 1. canonical_url 比对（同源页面）
        cand_canonical = normalize_url(source_url)
        for f in candidates:
            if is_same_canonical_url(source_url, f.get("source_url", "")) or (
                f.get("canonical_url") and cand_canonical == f.get("canonical_url")
            ):
                self.metrics["canonical_url_hits"] += 1
                logger.debug(f"[FactDedup] canonical_url 重复: {source_url}")
                return True

        # 2. 语义去重（需要 embedding；熔断后跳过）
        if not EMBEDDING_AVAILABLE or self._embedding_unavailable:
            self.metrics["semantic_skipped"] += 1
            return False

        cand_vec = self._get_embedding(content)
        if not cand_vec:
            self.metrics["semantic_skipped"] += 1
            return False

        for f in candidates:
            f_content = f.get("content", "")
            if not f_content or len(f_content) < 20 or len(content) < 20:
                continue
            existing_vec = f.get("_vec") or self._get_embedding(f_content)
            if not existing_vec:
                continue
            sim = _cosine(cand_vec, existing_vec)
            if sim >= self.semantic_threshold:
                # 同义但来源不同才算重复；同名来源可能是更详细版本，交给下游
                self.metrics["semantic_hits"] += 1
                logger.debug(f"[FactDedup] 语义重复 sim={sim:.2f}")
                return True

        self.metrics["semantic_miss"] += 1
        return False

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        key = text[:120]  # 截断 key
        if key in self._embedding_cache:
            return self._embedding_cache[key]
        vec = generate_embedding(text)
        if vec:
            self._embedding_cache[key] = vec
            if len(self._embedding_cache) > 200:
                # 简单 LRU：清空，避免无限增长
                self._embedding_cache.clear()
                self._embedding_cache[key] = vec
        else:
            # embedding 失败：熔断计数
            self._embedding_fail_count += 1
            if self._embedding_fail_count >= self._embedding_max_fail:
                self._embedding_unavailable = True
                logger.warning("[FactDedup] embedding 连续失败，本轮跳过语义去重")
        return vec

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.metrics)


dedup = FactDedup()


def get_fact_dedup() -> FactDedup:
    return dedup