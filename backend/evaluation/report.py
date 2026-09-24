# -*- coding: utf-8 -*-
"""
evaluation/report.py
================================================================================
统一评测报告容器：聚合多维度评测结果，输出 JSON + Markdown。
================================================================================
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class EvaluationReport:
    """统一评测报告容器。"""

    def __init__(self, name: str, num_questions: int = 0) -> None:
        self.name = name
        self.num_questions = num_questions
        self.timestamp = datetime.now().isoformat()
        self.details: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}

    def add_detail(self, detail: dict[str, Any]) -> None:
        self.details.append(detail)

    def set_summary(self, summary: dict[str, Any]) -> None:
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_name": self.name,
            "timestamp": self.timestamp,
            "num_questions": self.num_questions,
            "summary": self.summary,
            "details": self.details,
        }

    def save(self, output_dir: str, filename: str | None = None) -> str:
        os.makedirs(output_dir, exist_ok=True)
        if filename is None:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return filepath

    def to_markdown(self) -> str:
        """生成 Markdown 格式摘要。"""
        lines = [
            f"# {self.name}",
            "",
            f"- **评测时间**: {self.timestamp}",
            f"- **题目数量**: {self.num_questions}",
            "",
            "## 汇总",
            "",
        ]
        for key, value in self.summary.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        lines.append("## 明细")
        lines.append("")
        for d in self.details:
            title = d.get("question_id", d.get("query_id", "unknown"))
            lines.append(f"### {title}")
            for k, v in d.items():
                if k not in ("question_id", "query_id"):
                    lines.append(f"- {k}: {v}")
            lines.append("")
        return "\n".join(lines)

    def save_markdown(self, output_dir: str, filename: str | None = None) -> str:
        os.makedirs(output_dir, exist_ok=True)
        if filename is None:
            filename = f"{self.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        return filepath
