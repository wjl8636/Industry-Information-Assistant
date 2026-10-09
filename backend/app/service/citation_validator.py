# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
Citation Validator - 引用校验

在最终报告 `research_complete` 前执行：
1. 从 final_report 提取行内引用链接（markdown 形式 [title](url)）
2. 与当轮 references / facts 的 URL 做 canonical 归一化比对
3. 判定每条引用：valid / invalid / orphan
   - valid    → URL 存在且能在本轮来源库中找到对应 canonical_url
   - invalid  → URL 空/无 title/无法归一化
   - orphan   → 报告中引用了但不在本轮来源库
4. 输出 citation_validation 结构，供 Quality Gate / 评测使用

可用性设计：本模块不依赖网络回源（避免评测时对外请求不可控），只做
"报告内引用 → 本轮证据库"的本底校验。网络回源验证作为可选扩展点。
"""

import logging
from typing import Dict, List, Any

from .evidence_link import normalize_url, extract_markdown_links

logger = logging.getLogger("CitationValidator")


class CitationValidator:
    """引用校验器"""

    def validate_report(
        self,
        final_report: str,
        references: List[Dict[str, Any]],
        facts: List[Dict[str, Any]] = None,
        raw_sources: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        校验报告引用。

        Args:
            final_report: 最终报告文本
            references: state["references"]（list of dict）
            facts: state["facts"]（可选，用于补充来源池）
            raw_sources: state["raw_sources"]（可选）

        Returns:
            citation_validation dict:
            {
              "total": int,
              "valid": int,
              "invalid": int,
              "orphan": int,
              "records": [
                 {"title", "url", "canonical", "status", "matched_source"}
              ]
            }
        """
        # 构建来源池的 canonical url 集合
        source_pool: Dict[str, str] = {}  # canonical -> 来源名/标题
        for ref in references or []:
            u = normalize_url(ref.get("url", ""))
            if u:
                source_pool.setdefault(u, ref.get("title") or ref.get("source") or ref.get("marker") or "来源")
        for f in facts or []:
            u = normalize_url(f.get("source_url", ""))
            if u:
                source_pool.setdefault(u, f.get("source_name") or "来源")
        for rs in raw_sources or []:
            u = normalize_url(rs.get("url", ""))
            if u:
                source_pool.setdefault(u, rs.get("title") or "来源")

        links = extract_markdown_links(final_report or "")

        records = []
        valid = invalid = orphan = 0
        for link in links:
            title = link["title"]
            url = link["url"]
            canonical = normalize_url(url)
            matched = source_pool.get(canonical)

            if not url or not title or not canonical:
                status = "invalid"
                invalid += 1
            elif matched:
                status = "valid"
                valid += 1
            else:
                # 尝试宽松匹配：报告里的链接可能比源池多了 query（去掉 query 再看）
                base_canonical = normalize_url(url.split("?")[0]) if "?" in url else canonical
                if base_canonical in source_pool:
                    status = "valid"
                    matched = source_pool[base_canonical]
                    valid += 1
                else:
                    status = "orphan"
                    orphan += 1

            records.append({
                "title": title,
                "url": url,
                "canonical": canonical,
                "status": status,
                "matched_source": matched,
            })

        result = {
            "total": len(links),
            "valid": valid,
            "invalid": invalid,
            "orphan": orphan,
            "records": records,
        }
        logger.info(
            f"Citation validation: total={valid + invalid + orphan}, "
            f"valid={valid}, invalid={invalid}, orphan={orphan}, "
            f"valid_rate={(valid / max(valid + invalid + orphan, 1)):.2f}"
        )
        return result


validator = CitationValidator()


def get_citation_validator() -> CitationValidator:
    return validator