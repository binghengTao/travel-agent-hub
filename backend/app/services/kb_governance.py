"""
旅行助手 源码组件。


"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings, get_settings


class KnowledgeGovernanceService:
    """KnowledgeGovernanceService"""
    def __init__(self, settings: Settings | None = None):
        """说明：__init__ 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings = settings or get_settings()
        self.path = self.settings.storage_dir / "kb_governance.json"

    def analyze_candidate(self, *, title: str, city: str = "", theme: str = "", tags: list[str] | None = None, summary: str = "") -> dict:
        """说明：analyze_candidate 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        candidate_text = " ".join([title, city, theme, " ".join(tags or []), summary])
        candidates = self._document_candidates()
        scored = []
        for doc in candidates:
            doc_text = " ".join([doc["name"], doc.get("city", ""), doc.get("theme", ""), " ".join(doc.get("tags", []))])
            score = _similarity(candidate_text, doc_text)
            if score >= 0.18:
                scored.append({**doc, "score": round(score, 3)})
        similar_docs = sorted(scored, key=lambda item: item["score"], reverse=True)[:5]
        top_score = similar_docs[0]["score"] if similar_docs else 0
        if top_score >= 0.72:
            recommendation = "replace_or_merge"
        elif top_score >= 0.42:
            recommendation = "merge"
        elif top_score >= 0.22:
            recommendation = "supplement"
        else:
            recommendation = "new_document"
        return {
            "candidate": {"title": title, "city": city, "theme": theme, "tags": tags or [], "summary": summary},
            "recommendation": recommendation,
            "similar_docs": similar_docs,
            "merge_options": [
                {"action": "new_document", "label": "new"},
                {"action": "supplement", "label": "supplement"},
                {"action": "merge", "label": "merge"},
                {"action": "replace_or_merge", "label": "replace_or_merge"},
            ],
        }

    def register_document(
        self,
        *,
        doc_id: str,
        name: str,
        city: str,
        theme: str,
        tags: list[str],
        source_note: str,
        trust_level: str,
        action: str,
        analysis: dict,
    ) -> dict:
        """说明：register_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        payload = self._load()
        version = 1 + sum(1 for record in payload["records"] if record.get("city") == city and record.get("theme") == theme)
        record = {
            "record_id": f"kg_{uuid4().hex[:12]}",
            "doc_id": doc_id,
            "name": name,
            "city": city,
            "theme": theme,
            "tags": tags,
            "source_note": source_note,
            "trust_level": trust_level,
            "action": action,
            "status": "active" if action == "new_document" else "pending_merge",
            "version": version,
            "similar_docs": analysis.get("similar_docs", []),
            "recommendation": analysis.get("recommendation", "new_document"),
            "created_at": _now(),
        }
        payload["records"].append(record)
        self._save(payload)
        return record

    def list_records(self) -> dict:
        """说明：list_records 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        payload = self._load()
        return {
            "records": sorted(payload["records"], key=lambda item: item.get("created_at", ""), reverse=True),
            "merge_plans": sorted(payload["merge_plans"], key=lambda item: item.get("created_at", ""), reverse=True),
        }

    def create_merge_plan(self, *, source_doc_ids: list[str], target_title: str, strategy: str, notes: str = "") -> dict:
        """说明：create_merge_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        payload = self._load()
        docs = [doc for doc in self._document_candidates() if doc["doc_id"] in source_doc_ids or doc["name"] in source_doc_ids]
        plan = {
            "plan_id": f"merge_{uuid4().hex[:12]}",
            "target_title": target_title,
            "strategy": strategy,
            "source_doc_ids": source_doc_ids,
            "source_docs": docs,
            "sections": ["transport", "attractions", "food", "hotel", "budget", "pitfalls", "latest_policy"],
            "conflict_checks": ["ticket_or_price_conflict", "opening_hours_conflict", "route_distance_conflict", "source_trust_conflict"],
            "next_steps": ["review_sources", "generate_structured_summary", "archive_old_versions", "rebuild_chroma_and_bm25"],
            "notes": notes,
            "created_at": _now(),
        }
        payload["merge_plans"].append(plan)
        self._save(payload)
        return plan

    def _document_candidates(self) -> list[dict]:
        """说明：_document_candidates 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        docs = [
            {
                "doc_id": path.name,
                "name": path.name,
                "city": _city_from_name(path.stem),
                "theme": "",
                "tags": [],
                "source": "dataset",
            }
            for path in _iter_guide_files(self.settings.dataset_dir)
        ]
        payload = self._load()
        for record in payload["records"]:
            docs.append(
                {
                    "doc_id": record["doc_id"],
                    "name": record["name"],
                    "city": record.get("city", ""),
                    "theme": record.get("theme", ""),
                    "tags": record.get("tags", []),
                    "source": "governance",
                    "status": record.get("status", ""),
                    "version": record.get("version", 1),
                }
            )
        return docs

    def _load(self) -> dict:
        """说明：_load 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        if not self.path.exists():
            return {"records": [], "merge_plans": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"records": [], "merge_plans": []}
        data.setdefault("records", [])
        data.setdefault("merge_plans", [])
        return data

    def _save(self, payload: dict) -> None:
        """说明：_save 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_tags(raw: str | list[str] | None) -> list[str]:
    """说明：parse_tags 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item.strip() for item in raw if item and item.strip()]
    return [item.strip() for item in re.split(r"[,\uFF0C\u3001;\s]+", raw) if item.strip()]


def _similarity(left: str, right: str) -> float:
    """说明：_similarity 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    left = left.lower()
    right = right.lower()
    sequence_score = SequenceMatcher(None, left, right).ratio()
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    overlap_score = 0.0
    if left_tokens and right_tokens:
        overlap_score = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    return max(sequence_score, overlap_score)


def _tokens(text: str) -> set[str]:
    """说明：_tokens 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    words = {token for token in re.findall(r"[a-zA-Z0-9_]+", text) if token}
    cjk = {char for char in text if "\u4e00" <= char <= "\u9fff"}
    return words | cjk


def _city_from_name(name: str) -> str:
    """说明：_city_from_name 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return name.replace("\u65c5\u6e38\u653b\u7565", "").replace("\u653b\u7565", "").strip()


def _now() -> str:
    """说明：_now 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return datetime.now(timezone.utc).isoformat()


def _iter_guide_files(dataset_dir: Path) -> list[Path]:
    """说明：_iter_guide_files 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    files: list[Path] = []
    for pattern in ("*.pdf", "*.md", "*.txt"):
        files.extend(dataset_dir.glob(pattern))
    return sorted(files, key=lambda path: path.name)
