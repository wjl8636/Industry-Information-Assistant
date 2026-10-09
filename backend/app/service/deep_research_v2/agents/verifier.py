# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
DeepResearch V2.0 - 独立事实核验 Agent (VerifierAgent)

职责（对标标杆的独立 Verifier）：
1. 对每条 (claim, evidence_ids) 输出 grounded 判定：supported / unsupported / ambiguous / contradicted
2. 对未支撑的 claim 生成待补搜清单
3. 输出 grounding 记录写入 state["grounding"]，供 Grounding 门禁与评测使用

设计：与 CriticMaster 分离——Critic 负责报告整体质量与路由，Verifier 专司
"报告中的每一句主张是否有证据支撑"。二者互补而非重复。

可用性：claim 级证据绑定在写作阶段由 writer 输出 claims（含 evidence_fact_ids）。
若写作侧未输出 claims，Verifier 会退化为"从正文提取引用链接并与来源池比对"
的轻量校验，保证不阻断主流程。
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseAgent
from ..state import ResearchState, ResearchPhase

# 证据链路工具
try:
    from service.evidence_link import extract_markdown_links, normalize_url
except ImportError:
    try:
        from app.service.evidence_link import extract_markdown_links, normalize_url
    except ImportError:
        def extract_markdown_links(text: str) -> list:
            return []
        def normalize_url(url: str) -> str:
            return url


class VerifierAgent(BaseAgent):
    """
    事实核验 Agent - claim 级 grounding 判定
    """

    VERIFY_PROMPT = """你是一位严谨的事实核验专家。对研究报告中的每一条主张（claim），判断它是否有证据支撑。

## 研究问题
{query}

## 判定维度（每个 claim 单独判断）
- supported    → 有明确证据（引用了本轮事实库中的事实，且事实内容与 claim 一致）
- unsupported  → 无任何证据绑定，或证据内容与 claim 不符
- ambiguous    → 证据存在但语义模糊、不足以完全支撑
- contradicted → 证据内容与 claim 互相矛盾

## 需要核验的 claims
{claims}

## 可用的证据池（facts）
{facts}

## 输出格式
```json
{{
    "verdicts": [
        {{
            "claim_id": "claim 的 id",
            "verdict": "supported/unsupported/ambiguous/contradicted",
            "reason": "一句话理由",
            "evidence_ids_used": ["fact id"],
            "needs_new_search": true/false,
            "search_query": "如果需要补搜，建议的关键词"
        }}
    ],
    "grounding_coverage": 0.0-1.0,
    "summary": "总体 grounding 摘要"
}}
```

注意：
- verdict 只能从 supported/unsupported/ambiguous/contradicted 中选择
- grounding_coverage = supported claims / total claims
- 对 unsupported/contradicted 的 claim，若需要补搜则 needs_new_search=true

开始核验："""

    def __init__(self, llm_api_key: str, llm_base_url: str, model: str = "qwen-max"):
        super().__init__(
            name="VerifierAgent",
            role="事实核验师",
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            model=model
        )

    async def process(self, state: ResearchState) -> ResearchState:
        """处理入口：对 state["grounding"] 中未判定的 claim 做核验"""
        # 收集待判定 claims
        claims_to_verify = [g for g in state.get("grounding", [])
                            if not g.get("verdict") or g.get("verdict") in ("", "pending")]
        if not claims_to_verify:
            return state

        # 从正文兜底提取 claims（若写作未输出 claims）
        if not claims_to_verify:
            return state

        self.logger.info(f"[VerifierAgent] 核验 {len(claims_to_verify)} 条 claim")

        self.add_message(state, "thought", {
            "agent": self.name,
            "content": f"开始核验 {len(claims_to_verify)} 条主张的证据支撑..."
        })

        # 格式化 claims
        claims_text = []
        for g in claims_to_verify:
            claims_text.append(
                f"- claim_id: {g.get('claim_id')}, section: {g.get('section_id')}, "
                f"text: {g.get('claim_text', '')[:300]}, evidence: {g.get('evidence_ids', [])}"
            )

        # 格式化事实池
        facts = state.get("facts", [])
        facts_text = []
        for f in facts[:40]:
            facts_text.append(f"- [{f.get('id')}] {f.get('content', '')[:200]} (来源: {f.get('source_name')})")

        prompt = self.VERIFY_PROMPT.format(
            query=state.get("query", ""),
            claims="\n".join(claims_text) if claims_text else "（无 claims）",
            facts="\n".join(facts_text) if facts_text else "（暂无事实库）"
        )

        try:
            response = await self.call_llm(
                system_prompt="你是严谨的事实核验专家。",
                user_prompt=prompt,
                json_mode=True,
                temperature=0.2
            )
            result = self.parse_json_response(response)
        except Exception as e:
            self.logger.warning(f"[VerifierAgent] 核验调用失败，降级: {e}")
            result = {}

        verdicts = result.get("verdicts", [])
        verdict_map = {v.get("claim_id"): v for v in verdicts if v.get("claim_id")}

        # 回写 grounding
        for g in state["grounding"]:
            v = verdict_map.get(g.get("claim_id"))
            if v:
                g["verdict"] = v.get("verdict", "unsupported")
                g["reason"] = v.get("reason", "")
                g["evidence_ids_used"] = v.get("evidence_ids_used", g.get("evidence_ids", []))
                if v.get("needs_new_search"):
                    g["needs_new_search"] = True
                    g["search_query"] = v.get("search_query", "")
                g["verified_at"] = datetime.now().isoformat()
            else:
                g["verdict"] = g.get("verdict") or "unsupported"

        # grounding 覆盖率
        total = len(state["grounding"])
        supported = len([g for g in state["grounding"] if g.get("verdict") == "supported"])
        coverage = supported / total if total else 0.0
        state["grounding_coverage"] = coverage

        self.add_message(state, "verifier_result", {
            "agent": self.name,
            "claims_verified": len(state["grounding"]),
            "supported": supported,
            "unsupported": len([g for g in state["grounding"] if g.get("verdict") in ("unsupported", "ambiguous")]),
            "contradicted": len([g for g in state["grounding"] if g.get("verdict") == "contradicted"]),
            "grounding_coverage": coverage,
        })

        return state

    async def verify_from_report(self, state: ResearchState) -> ResearchState:
        """兜底路径：若写作未绑定 claims，从正文提取引用链接做轻量 grounding"""
        report = state.get("final_report", "")
        links = extract_markdown_links(report)
        if not links:
            return state

        source_pool = {}
        for f in state.get("facts", []):
            u = normalize_url(f.get("source_url", ""))
            if u:
                source_pool.setdefault(u, f.get("id"))
        for r in state.get("references", []):
            u = normalize_url(r.get("url", ""))
            if u:
                source_pool.setdefault(u, r.get("title") or r.get("source"))

        # 为每个链接生成一条 grounding 记录（轻量）
        existing_ids = {g.get("claim_id") for g in state.get("grounding", [])}
        new_records = []
        for link in links:
            cid = f"claim_{uuid.uuid4().hex[:8]}"
            if cid in existing_ids:
                continue
            u = normalize_url(link.get("url", ""))
            matched = source_pool.get(u)
            new_records.append({
                "claim_id": cid,
                "section_id": "",
                "claim_text": link.get("title", ""),
                "evidence_ids": [matched] if matched else [],
                "verdict": "supported" if matched else "orphan_link",
                "reason": "引用链接与来源库比对" if matched else "引用链接未在来源库",
                "evidence_ids_used": [matched] if matched else [],
            })
        if new_records:
            state["grounding"] = state.get("grounding", []) + new_records
            total = len(state["grounding"])
            supported = len([g for g in state["grounding"] if g.get("verdict") == "supported"])
            state["grounding_coverage"] = supported / total if total else 0.0

        return state


def get_verifier(llm_api_key: str, llm_base_url: str, model: str = "qwen-max") -> VerifierAgent:
    return VerifierAgent(llm_api_key, llm_base_url, model)