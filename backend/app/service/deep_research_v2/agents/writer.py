# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
DeepResearch V2.0 - 首席笔杆 Agent (LeadWriter)

职责：
1. 深度写作 - 将零散信息串联成逻辑严密的报告
2. Markdown排版 - 专业的格式排版
3. 图文混排 - 整合文字、图表、数据
4. 参考文献 - 规范的引用格式
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseAgent
from ..state import ResearchState, ResearchPhase


class LeadWriter(BaseAgent):
    """
    首席笔杆 - 最终输出的打磨者

    特点：
    - 深度写作能力
    - 专业的行业研究报告风格
    - 逻辑严密的叙述结构
    - 规范的引用和排版
    """

    SECTION_WRITING_PROMPT = """你是一位顶级投行研究部的首席分析师，擅长撰写深度行业研究报告。

## 研究主题
{query}

## 当前章节信息
标题: {section_title}
描述: {section_description}
类型: {section_type}

## 可用素材

### 相关事实
{facts}

### 数据点
{data_points}

### 已有洞察
{insights}

### 相关图表
{charts_info}

## 写作要求
1. **专业性**：使用行业术语，体现专业深度
2. **逻辑性**：论点清晰，论据充分，层层递进
3. **数据支撑**：关键观点必须有数据或事实支撑
4. **引用规范**：使用可点击链接格式 [来源名称](URL)，如 [艾瑞咨询](https://www.iresearch.cn)
5. **图表整合**：在合适位置插入图表引用 ![图表标题](chart_id)
6. **字数控制**：本章节 500-1000 字
7. **不要重复标题**：正文开头不要再写章节标题

## 输出格式
```json
{{
    "content": "章节正文内容（Markdown格式，不包含章节标题）",
    "key_points": ["本章节的核心要点"],
    "claims": [
        {{
            "claim_id": "claim_1",
            "text": "该主张的一句话描述",
            "evidence_fact_ids": ["fact_xxx", "fact_yyy"],
            "citation_url": "支撑该主张的URL（可选）"
        }}
    ],
    "citations": [
        {{"source": "来源名称", "url": "完整URL"}}
    ],
    "suggested_improvements": ["如果有更多信息可以改进的地方"]
}}
```

## claims 绑定要求
- 每个数据性/观点性主张都尽量绑定一条 claim，并给出支撑它的事实 id（evidence_fact_ids）
- 证据 id 必须来自"相关事实"列表中列出的 fact id（形如 fact_xxxxxxxx）
- 如果某观点没有对应事实支撑，evidence_fact_ids 留空数组，并在 claims 中保留（供核验阶段标记 unsupported）

## 写作风格示例
- 好的开头："2024年，中国AI芯片市场正经历深刻变革。根据[IDC数据](https://www.idc.com)，市场规模达到..."
- 避免的开头："关于AI芯片，首先我们来看..."
- 数据引用示例："市场规模达5000亿元（[艾瑞咨询报告](https://www.iresearch.cn/report)）"

开始撰写："""

    SYNTHESIS_PROMPT = """你是首席笔杆，需要将各章节整合成完整的研究报告。

## 研究主题
{query}

## 各章节内容
{sections_content}

## 收集的所有引用来源
{all_sources}

## 任务
1. 撰写报告摘要（Executive Summary）
2. 整合各章节，确保逻辑连贯，使用层级编号
3. 撰写结论与展望
4. 整理参考文献列表（确保链接可点击）

## 关键要求

### 1. 标题编号规则（必须严格遵守）
- 一级标题：1、2、3...（如：1 市场概况）
- 二级标题：1.1、1.2、2.1...（如：1.1 市场规模）
- 三级标题：1.1.1、1.1.2...（如：1.1.1 全球市场）
- **禁止标题重复**：每个标题必须唯一，不要在正文中重复章节标题

### 2. 引用格式规则（确保可点击）
- 行内引用：使用 [来源名称](URL) 格式，如 [艾瑞咨询](https://www.iresearch.cn)
- 数据引用：在数据后标注来源，如"市场规模达5000亿元（[IDC报告](https://www.idc.com)）"
- 文末参考文献：使用有序列表 + 可点击链接格式

### 3. 报告结构规范
- 不要在报告开头使用 # 一级标题
- 直接从"执行摘要"开始
- 各章节使用 ## 二级标题
- 子章节使用 ### 三级标题

## 输出格式
```json
{{
    "executive_summary": "执行摘要（300-500字）",
    "full_report": "完整报告（Markdown格式，按下方结构生成）",
    "conclusions": ["核心结论1", "核心结论2"],
    "outlook": "未来展望",
    "references": [
        {{"id": 1, "title": "来源标题", "url": "完整URL", "author": "作者/机构", "date": "日期"}}
    ]
}}
```

## 报告结构模板
```markdown
## 执行摘要

[300-500字的研究摘要]

---

## 1 [第一章标题]

[章节引言段落]

### 1.1 [子章节标题]

[内容，包含数据引用如：根据[来源名](URL)，...]

### 1.2 [子章节标题]

#### 1.2.1 [三级标题]

[更详细的内容]

---

## 2 [第二章标题]

### 2.1 [子章节标题]

...

---

## 结论与展望

### 核心结论
1. [结论1]
2. [结论2]

### 未来展望
[展望内容]

---

## 参考文献

1. [来源标题1](URL1) - 作者/机构, 日期
2. [来源标题2](URL2) - 作者/机构, 日期
...
```"""

    REVISION_PROMPT = """你是首席笔杆，需要根据审核反馈修订报告。

## 原始报告
{original_content}

## 审核反馈
{feedback}

## 补充的新信息
{new_info}

## 任务
根据反馈修订报告，解决指出的问题。

## 修订原则
1. 针对性修改：只修改有问题的部分
2. 补充来源：对缺少来源的观点补充引用
3. 修正错误：纠正事实错误或逻辑漏洞
4. 保持风格：修订后保持报告整体风格一致

输出JSON：
```json
{{
    "revised_content": "修订后的内容",
    "changes_made": ["修改1", "修改2"],
    "addressed_issues": ["已解决的问题ID"],
    "unable_to_address": ["无法解决的问题及原因"]
}}
```"""

    SECTION_REVISION_PROMPT = """你是首席笔杆，需要根据审核反馈**只修订一个章节**。

## 章节标题
{section_title}

## 该章节当前内容
{section_content}

## 针对该章节的审核反馈
{feedback}

## 该章节可用素材
{facts}

## 数据点
{data_points}

## 任务
只重写本章节，解决反馈中指出的问题。**只输出修订后的章节正文（Markdown），不要输出章节标题。**

## 修订原则
1. 只改有问题的部分，保持其它内容
2. 对缺少来源的表述补充引用（用 [来源](URL) 格式）
3. 修正事实错误或逻辑漏洞
4. 保持整体风格一致

输出JSON：
```json
{{
    "revised_content": "修订后的章节正文（不含标题）",
    "changes_made": ["修改1", "修改2"],
    "addressed_issues": ["已解决的问题ID"],
    "unable_to_address": ["无法解决的问题及原因"]
}}
```"""

    def __init__(self, llm_api_key: str, llm_base_url: str, model: str = "qwen-max"):
        super().__init__(
            name="LeadWriter",
            role="首席笔杆",
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            model=model
        )

    async def process(self, state: ResearchState) -> ResearchState:
        """处理入口"""
        if state["phase"] == ResearchPhase.WRITING.value:
            return await self._write_report(state)
        elif state["phase"] == ResearchPhase.REVISING.value:
            return await self._revise_sections(state)
        else:
            return state

    async def _write_report(self, state: ResearchState) -> ResearchState:
        """撰写报告"""
        # 发送 research_step 开始事件
        # 注意: step_type 必须是 "writing" 以匹配 graph.py 发送的 phase 事件
        self.add_message(state, "research_step", {
            "step_id": f"step_writing_{uuid.uuid4().hex[:8]}",
            "step_type": "writing",
            "title": "内容生成",
            "subtitle": "撰写研究报告",
            "status": "running",
            "stats": {"sections_count": len(state["outline"]), "word_count": 0}
        })

        self.add_message(state, "thought", {
            "agent": self.name,
            "content": "开始撰写深度研究报告..."
        })

        # 逐章节撰写
        for section in state["outline"]:
            if section.get("status") not in ["final", "drafted"]:
                await self._write_section(state, section)

        # 整合报告
        await self._synthesize_report(state)

        # 发送 research_step 完成事件
        word_count = len(state.get("final_report", ""))
        self.add_message(state, "research_step", {
            "step_type": "writing",
            "title": "内容生成",
            "subtitle": "撰写研究报告",
            "status": "completed",
            "stats": {
                "sections_count": len(state["outline"]),
                "word_count": word_count,
                "references_count": len(state.get("references", []))
            }
        })

        # 更新阶段
        state["phase"] = ResearchPhase.REVIEWING.value

        return state

    async def _write_section(self, state: ResearchState, section: Dict) -> None:
        """撰写单个章节"""
        section_id = section["id"]
        self.logger.info(f"Writing section: {section.get('title')}")

        self.add_message(state, "action", {
            "agent": self.name,
            "tool": "writing_section",
            "section": section.get("title")
        })

        # 收集相关素材
        related_facts = [f for f in state["facts"] if section_id in f.get("related_sections", [])]
        if not related_facts:
            # 如果没有特定关联，使用所有事实
            related_facts = state["facts"][:10]

        # 格式化事实
        facts_text = []
        for fact in related_facts:
            facts_text.append(f"- {fact.get('content')} (来源: {fact.get('source_name')}, 可信度: {fact.get('credibility_score')})")

        # 格式化数据点
        data_text = []
        for dp in state["data_points"][:10]:
            data_text.append(f"- {dp.get('name')}: {dp.get('value')} {dp.get('unit', '')} ({dp.get('year', 'N/A')})")

        # 格式化图表信息
        charts_info = []
        for chart in state["charts"]:
            if chart.get("section_id") == section_id:
                charts_info.append(f"- 图表: {chart.get('title')} (ID: {chart.get('id')})")

        prompt = self.SECTION_WRITING_PROMPT.format(
            query=state["query"],
            section_title=section.get("title", ""),
            section_description=section.get("description", ""),
            section_type=section.get("section_type", "mixed"),
            facts="\n".join(facts_text) if facts_text else "（暂无相关事实）",
            data_points="\n".join(data_text) if data_text else "（暂无数据点）",
            insights="\n".join([f"- {i}" for i in state["insights"][:5]]) if state["insights"] else "（暂无洞察）",
            charts_info="\n".join(charts_info) if charts_info else "（暂无图表）"
        )

        response = await self.call_llm(
            system_prompt="你是顶级的行业研究分析师，擅长撰写专业的研究报告。",
            user_prompt=prompt,
            json_mode=True,
            temperature=0.4,
            max_tokens=16000  # 拉满到最大值
        )

        result = self.parse_json_response(response)

        if result and result.get("content"):
            section_content = result["content"]
            state["draft_sections"][section_id] = section_content
            section["status"] = "drafted"

            # 记录 claim-evidence 绑定（供独立 Verifier 核验）
            claims = result.get("claims", [])
            if claims:
                for c in claims:
                    state["grounding"].append({
                        "claim_id": c.get("claim_id") or f"claim_{uuid.uuid4().hex[:8]}",
                        "section_id": section_id,
                        "claim_text": c.get("text", ""),
                        "evidence_ids": c.get("evidence_fact_ids", []) or [],
                        "citation_url": c.get("citation_url", ""),
                        "verdict": "",  # 待 verifier 判定
                    })

            # 收集引用
            for citation in result.get("citations", []):
                state["references"].append({
                    "id": len(state["references"]) + 1,
                    "marker": citation.get("marker"),
                    "source": citation.get("source"),
                    "url": citation.get("url", "")
                })

            # 发送章节内容到"过程报告" - 包含完整内容用于流式显示
            self.add_message(state, "section_content", {
                "agent": self.name,
                "section_id": section_id,
                "section_title": section.get("title"),
                "content": section_content,  # 完整章节内容
                "word_count": len(section_content),
                "key_points": result.get("key_points", [])
            })

            # 发送观察消息（显示在左侧步骤流程）
            self.add_message(state, "observation", {
                "agent": self.name,
                "content": f"章节「{section.get('title')}」撰写完成\n字数: {len(section_content)}\n要点: {', '.join(result.get('key_points', [])[:2]) if result.get('key_points') else '无'}"
            })

    async def _synthesize_report(self, state: ResearchState) -> None:
        """整合完整报告"""
        self.add_message(state, "thought", {
            "agent": self.name,
            "content": "正在整合各章节，生成完整研究报告..."
        })

        # 准备各章节内容
        sections_content = []
        for section in state["outline"]:
            section_id = section["id"]
            content = state["draft_sections"].get(section_id, "")
            if content:
                sections_content.append(f"## {section.get('title')}\n{content}")

        # 收集所有来源
        all_sources = []
        for ref in state["references"]:
            all_sources.append(f"- {ref.get('source')} ({ref.get('url', 'N/A')})")

        for fact in state["facts"]:
            source_entry = f"- {fact.get('source_name')} ({fact.get('source_url', 'N/A')})"
            if source_entry not in all_sources:
                all_sources.append(source_entry)

        prompt = self.SYNTHESIS_PROMPT.format(
            query=state["query"],
            sections_content="\n\n".join(sections_content) if sections_content else "（暂无章节内容）",
            all_sources="\n".join(all_sources[:30]) if all_sources else "（暂无来源）"
        )

        self.logger.info(f"[LeadWriter] 调用 LLM 整合报告...")
        result = None
        try:
            response = await self.call_llm(
                system_prompt="你是资深的研究报告主编，擅长整合和打磨最终报告。",
                user_prompt=prompt,
                json_mode=True,
                temperature=0.3,
                max_tokens=16000  # 拉满到最大值
            )
            result = self.parse_json_response(response)
            self.logger.info(f"[LeadWriter] JSON 解析结果: {bool(result)}, keys: {result.keys() if result else 'N/A'}")
        except Exception as e:
            self.logger.error(f"[LeadWriter] 报告整合 LLM 调用失败，使用章节 fallback: {e}")

        executive_summary = ""
        conclusions = []

        if result and result.get("full_report"):
            state["final_report"] = result.get("full_report", "")
            executive_summary = result.get("executive_summary", "")
            conclusions = result.get("conclusions", [])
            self.logger.info(f"[LeadWriter] ✅ 报告整合成功，长度: {len(state['final_report'])}")

            # 更新参考文献
            for ref in result.get("references", []):
                if ref not in state["references"]:
                    state["references"].append(ref)
        else:
            # JSON 解析失败时的备选方案：使用已有章节内容组装报告
            self.logger.warning(f"[LeadWriter] ⚠️ JSON 解析失败，使用章节内容作为备选")
            fallback_report = f"# {state['query']} 研究报告\n\n"
            for section in state["outline"]:
                section_id = section["id"]
                content = state["draft_sections"].get(section_id, "")
                if content:
                    fallback_report += f"## {section.get('title', section_id)}\n\n{content}\n\n"
            state["final_report"] = fallback_report
            self.logger.info(f"[LeadWriter] 使用备选报告，长度: {len(state['final_report'])}")

        # 发送报告完成事件 - 包含完整报告内容用于前端流式显示
        self.add_message(state, "report_draft", {
            "agent": self.name,
            "content": state["final_report"],  # 完整报告内容
            "executive_summary": executive_summary,
            "conclusions": conclusions,
            "word_count": len(state["final_report"]),
            "references_count": len(state["references"])
        })

    async def _revise_report(self, state: ResearchState) -> ResearchState:
        """根据反馈修订报告"""
        self.add_message(state, "thought", {
            "agent": self.name,
            "content": "根据审核反馈修订报告..."
        })

        # 收集未解决的问题
        unresolved = [f for f in state["critic_feedback"] if not f.get("resolved")]
        feedback_text = []
        for issue in unresolved:
            feedback_text.append(f"- [{issue.get('severity')}] {issue.get('description')}\n  建议: {issue.get('suggestion')}")

        # 收集新信息（如果有补充搜索）
        new_facts = state["facts"][-5:] if state["facts"] else []
        new_info = "\n".join([f"- {f.get('content', '')[:200]}" for f in new_facts])

        prompt = self.REVISION_PROMPT.format(
            original_content=state.get("final_report", "")[:6000],
            feedback="\n".join(feedback_text) if feedback_text else "无具体反馈",
            new_info=new_info if new_info else "无补充信息"
        )

        response = await self.call_llm(
            system_prompt="你是负责修订报告的资深编辑。",
            user_prompt=prompt,
            json_mode=True,
            temperature=0.3,
            max_tokens=16000  # 拉满到最大值
        )

        result = self.parse_json_response(response)

        if result and result.get("revised_content"):
            state["final_report"] = result["revised_content"]

            # 标记已解决的问题
            for issue_id in result.get("addressed_issues", []):
                for feedback in state["critic_feedback"]:
                    if feedback.get("id") == issue_id:
                        feedback["resolved"] = True

            self.add_message(state, "revision_complete", {
                "agent": self.name,
                "changes_count": len(result.get("changes_made", [])),
                "addressed_issues": result.get("addressed_issues", []),
                "unable_to_address": result.get("unable_to_address", [])
            })

        # 回到审核阶段
        state["phase"] = ResearchPhase.REVIEWING.value

        return state

    async def _revise_sections(self, state: ResearchState) -> ResearchState:
        """章节级修订 + 自动回滚。

        相对整篇改写：
        1. 只重写审核反馈中定位到目标章节的章节
        2. 记录 revision_history[section_id]，并在复检后若分数下降则回滚到历史最高分版本
        3. 没有 target_section 的全局问题走整篇修订兜底
        """
        # 收集未解决问题
        unresolved = [f for f in state["critic_feedback"] if not f.get("resolved")]

        # 按目标章节分组
        section_issues: Dict[str, list] = {}
        global_issues = []
        for issue in unresolved:
            ts = issue.get("target_section", "")
            if ts and ts in state["draft_sections"]:
                section_issues.setdefault(ts, []).append(issue)
            else:
                global_issues.append(issue)

        # 记录本轮修订前的质量分基线（用于回滚）
        baseline_score = state.get("quality_score", 0.0)

        revised_any = False
        # 1) 章节级修订
        for section_id, issues in section_issues.items():
            revised = await self._revise_single_section(state, section_id, issues)
            if revised:
                revised_any = True

        # 2) 全局问题：若存在，走整篇修订
        if global_issues:
            revised_any = await self._revise_full_report_async(state, global_issues) or revised_any

        # 3) 自动回滚：本轮修订后，章节版本得分若低于历史最高分则回滚
        self._auto_rollback(state, baseline_score)

        # 标记本轮已解决的 issue（由 revise_single_section / fallback 内部处理）

        if revised_any:
            self.add_message(state, "revision_complete", {
                "agent": self.name,
                "sections_revised": list(section_issues.keys()),
                "rolled_back_sections": state.get("rolled_back_sections", []),
                "mode": "section_level" if section_issues else "full_report",
            })

        state["phase"] = ResearchPhase.REVIEWING.value
        return state

    async def _revise_single_section(
        self,
        state: ResearchState,
        section_id: str,
        issues: list
    ) -> bool:
        """重写单个章节（仅该章节），并记录修订历史"""
        section = next((s for s in state["outline"] if s.get("id") == section_id), None)
        if not section:
            return False
        current_content = state["draft_sections"].get(section_id, "")
        if not current_content:
            return False

        # 收集该章节素材
        related_facts = [f for f in state["facts"] if section_id in f.get("related_sections", [])]
        facts_text = "\n".join([f"- {f.get('content')} (来源: {f.get('source_name')})" for f in related_facts[:10]])
        data_text = "\n".join([
            f"- {dp.get('name')}: {dp.get('value')} {dp.get('unit', '')} ({dp.get('year', 'N/A')})"
            for dp in state["data_points"][:8]
        ])

        feedback_text = "\n".join([
            f"- [{i.get('severity')}] {i.get('description')}\n  建议: {i.get('suggestion')}"
            for i in issues
        ])

        prompt = self.SECTION_REVISION_PROMPT.format(
            section_title=section.get("title", section_id),
            section_content=current_content,
            feedback=feedback_text if feedback_text else "无具体反馈",
            facts=facts_text if facts_text else "（暂无素材）",
            data_points=data_text if data_text else "（暂无数据点）",
        )

        try:
            response = await self.call_llm(
                system_prompt="你是负责修订报告章节的资深编辑。",
                user_prompt=prompt,
                json_mode=True,
                temperature=0.3,
                max_tokens=16000
            )
        except Exception as e:
            self.logger.warning(f"[LeadWriter] 章节修订调用失败，跳过该章节: {e}")
            return False

        result = self.parse_json_response(response)
        if not result or not result.get("revised_content"):
            self.logger.warning(f"[LeadWriter] 章节 {section_id} 修订无有效输出")
            return False

        # 记录修订历史（用于回滚）
        revision_history = state.setdefault("revision_history", {})
        history = revision_history.setdefault(section_id, [])
        history.append({
            "section_id": section_id,
            "content": current_content,  # 旧版本（用于回滚）
            "quality_score": state.get("quality_score", 0.0),
            "verifier_pass_rate": state.get("grounding_coverage", 0.0),
            "timestamp": datetime.now().isoformat(),
        })

        # 写入新版本
        state["draft_sections"][section_id] = result["revised_content"]

        # 标记该章节相关 issue 已解决
        for issue in issues:
            issue["resolved"] = True

        # 标记已处理
        for issue_id in result.get("addressed_issues", []):
            for fb in state["critic_feedback"]:
                if fb.get("id") == issue_id:
                    fb["resolved"] = True

        # 同步章节到 final_report（重组装）
        self._reassemble_final_report(state)

        return True

    def _reassemble_final_report(self, state: ResearchState) -> None:
        """用最新 draft_sections 重新组装 final_report（保留摘要/结论骨架不丢）"""
        # 若已有 final_report，尝试替换章节内容
        report = state.get("final_report", "")
        if report:
            for section in state["outline"]:
                section_id = section["id"]
                new_content = state["draft_sections"].get(section_id, "")
                if not new_content:
                    continue
                # 尝试定位章节标题并替换（宽松匹配）
                title = section.get("title", section_id)
                # 简单替换：找到 "## title" 到下一个 "## " 的段落
                import re
                pattern = re.compile(
                    rf"(## {re.escape(title)}[^\n]*\n)(.*?)(?=\n## |\Z)",
                    re.DOTALL
                )
                if pattern.search(report):
                    report = pattern.sub(lambda m: m.group(1) + "\n" + new_content + "\n", report, count=1)
            state["final_report"] = report

    def _revise_full_report_fallback(
        self,
        state: ResearchState,
        global_issues: list
    ) -> bool:
        """整篇修订兜底（无 target_section 的全局问题）

        复用原整篇修订逻辑（REVISION_PROMPT + _revise_report 的正文部分）。
        """
        if not global_issues:
            return False

        feedback_text = "\n".join([
            f"- [{i.get('severity')}] {i.get('description')}\n  建议: {i.get('suggestion')}"
            for i in global_issues
        ])
        new_facts = state["facts"][-5:] if state["facts"] else []
        new_info = "\n".join([f"- {f.get('content', '')[:200]}" for f in new_facts])

        prompt = self.REVISION_PROMPT.format(
            original_content=state.get("final_report", "")[:6000],
            feedback=feedback_text if feedback_text else "无具体反馈",
            new_info=new_info if new_info else "无补充信息"
        )

        try:
            import asyncio
            # 由于本方法可能是同步上下文，用 asyncio.run 或由调用方异步调用
            # 这里保持同步设计：直接同步调用一次
            response = asyncio.get_event_loop().is_running() or None
        except RuntimeError:
            pass

        # 复用 _revise_report 的实现：让调用方异步执行
        # 为兼容，这里直接调用异步逻辑
        return False

    async def _revise_full_report_async(
        self,
        state: ResearchState,
        global_issues: list
    ) -> bool:
        """整篇修订的异步实现"""
        if not global_issues:
            return False
        feedback_text = "\n".join([
            f"- [{i.get('severity')}] {i.get('description')}\n  建议: {i.get('suggestion')}"
            for i in global_issues
        ])
        new_facts = state["facts"][-5:] if state["facts"] else []
        new_info = "\n".join([f"- {f.get('content', '')[:200]}" for f in new_facts])

        prompt = self.REVISION_PROMPT.format(
            original_content=state.get("final_report", "")[:6000],
            feedback=feedback_text if feedback_text else "无具体反馈",
            new_info=new_info if new_info else "无补充信息"
        )
        try:
            response = await self.call_llm(
                system_prompt="你是负责修订报告的资深编辑。",
                user_prompt=prompt,
                json_mode=True,
                temperature=0.3,
                max_tokens=16000
            )
        except Exception as e:
            self.logger.warning(f"[LeadWriter] 整篇修订调用失败: {e}")
            return False

        result = self.parse_json_response(response)
        if result and result.get("revised_content"):
            state["final_report"] = result["revised_content"]
            for issue_id in result.get("addressed_issues", []):
                for fb in state["critic_feedback"]:
                    if fb.get("id") == issue_id:
                        fb["resolved"] = True
            return True
        return False

    def _auto_rollback(self, state: ResearchState, baseline_score: float) -> None:
        """自动回滚：若本轮修订后综合分低于修订前基线，回滚所有被改章节到历史最高分版本"""
        current_score = state.get("quality_score", 0.0)
        if current_score >= baseline_score:
            return  # 分数未下降，不回滚

        revision_history = state.get("revision_history", {})
        rolled_back = []
        for section_id, history in revision_history.items():
            if not history:
                continue
            # 找历史最高分版本
            best = max(history, key=lambda h: h.get("quality_score", 0))
            if best["quality_score"] >= current_score:
                state["draft_sections"][section_id] = best["content"]
                rolled_back.append(section_id)
        if rolled_back:
            state["rolled_back_sections"] = list(set(state.get("rolled_back_sections", [])) | set(rolled_back))
            self.add_message(state, "auto_rollback", {
                "agent": self.name,
                "rolled_back_sections": rolled_back,
                "reason": f"quality_score 由 {baseline_score} 下降至 {current_score}"
            })
        self._reassemble_final_report(state)
