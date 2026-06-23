"""
旅行助手 源码组件。


"""

from __future__ import annotations

import re


class Verifier:
    """Verifier"""
    def verify_trip_plan(self, answer: str, days: int) -> tuple[bool, list[str]]:
        """说明：verify_trip_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        warnings: list[str] = []
        day_mentions = len(set(re.findall(r"Day\s*\d+|D\s*\d+", answer, flags=re.IGNORECASE)))
        if day_mentions and day_mentions < days:
            warnings.append(f"Detected {day_mentions} planned days, fewer than the requested {days} days.")
        return not warnings, warnings

    def verify_rag_answer(self, answer: str, sources_count: int) -> tuple[bool, list[str]]:
        """说明：verify_rag_answer 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        warnings: list[str] = []
        lower_answer = answer.lower()
        if sources_count == 0:
            warnings.append("RAG answer has no traceable sources.")
        if sources_count and not any(marker in lower_answer for marker in ["source", "citation", "pdf", "reference"]):
            warnings.append("Answer does not explicitly mention its source or citation trail.")
        return not warnings, warnings
