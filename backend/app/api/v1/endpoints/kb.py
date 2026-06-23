"""
旅行助手 源码组件。


"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import files, rag_service
from app.core.config import get_settings
from app.core.response import success
from app.core.security import require_admin
from app.rag.retriever import RagService
from app.services.file_service import ALLOWED_PDF_TYPES, FileService
from app.services.kb_governance import KnowledgeGovernanceService, parse_tags

router = APIRouter()


class GovernanceAnalyzeRequest(BaseModel):
    """GovernanceAnalyzeRequest"""
    title: str = Field(min_length=1)
    city: str = ""
    theme: str = ""
    tags: list[str] = Field(default_factory=list)
    summary: str = ""


class GovernanceTextRegisterRequest(GovernanceAnalyzeRequest):
    """GovernanceTextRegisterRequest"""
    content: str = Field(min_length=1)
    source_note: str = ""
    trust_level: str = "medium"
    action: str = "new_document"


class MergePlanRequest(BaseModel):
    """MergePlanRequest"""
    source_doc_ids: list[str] = Field(default_factory=list)
    target_title: str = Field(min_length=1)
    strategy: str = "merge"
    notes: str = ""


@router.get("/documents")
async def documents() -> dict:
    """说明：documents 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    docs = [
        {"doc_id": path.name, "name": path.name, "size": path.stat().st_size}
        for path in _iter_dataset_docs(settings.dataset_dir)
    ]
    return success({"documents": docs, "count": len(docs)})


@router.post("/upload", dependencies=[Depends(require_admin)])
async def upload_document(upload: UploadFile, file_service: FileService = Depends(files)) -> dict:
    """说明：upload_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    saved = await file_service.save_upload(upload, "kb", ALLOWED_PDF_TYPES)
    suffix = Path(upload.filename or "document.pdf").suffix.lower() or ".pdf"
    target = settings.dataset_dir / f"{Path(upload.filename or 'document').stem}_{uuid4().hex[:8]}{suffix}"
    shutil.copyfile(saved, target)
    return success({"doc_id": target.name, "name": target.name, "size": target.stat().st_size})


@router.post("/reindex", dependencies=[Depends(require_admin)])
async def reindex(rag: RagService = Depends(rag_service)) -> dict:
    """说明：reindex 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(await rag.indexer.rebuild())


@router.delete("/documents/{doc_id}", dependencies=[Depends(require_admin)])
async def delete_document(doc_id: str) -> dict:
    """说明：delete_document 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    target = settings.dataset_dir / Path(doc_id).name
    if not target.exists() or target.suffix.lower() not in {".pdf", ".md", ".txt"}:
        raise HTTPException(status_code=404, detail="Document not found.")
    target.unlink()
    return success({"doc_id": doc_id, "deleted": True})


@router.get("/governance/records")
async def governance_records() -> dict:
    """说明：governance_records 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success(KnowledgeGovernanceService().list_records())


@router.post("/governance/analyze")
async def governance_analyze(payload: GovernanceAnalyzeRequest) -> dict:
    """说明：governance_analyze 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    service = KnowledgeGovernanceService()
    return success(service.analyze_candidate(title=payload.title, city=payload.city, theme=payload.theme, tags=payload.tags, summary=payload.summary))


@router.post("/governance/upload", dependencies=[Depends(require_admin)])
async def governance_upload(
    upload: UploadFile,
    city: str = Form(""),
    theme: str = Form(""),
    tags: str = Form(""),
    source_note: str = Form(""),
    trust_level: str = Form("medium"),
    action: str = Form("new_document"),
    summary: str = Form(""),
    file_service: FileService = Depends(files),
) -> dict:
    """说明：governance_upload 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    service = KnowledgeGovernanceService(settings)
    original_name = Path(upload.filename or "document.pdf").name
    analysis = service.analyze_candidate(title=original_name, city=city, theme=theme, tags=parse_tags(tags), summary=summary)
    saved = await file_service.save_upload(upload, "kb", ALLOWED_PDF_TYPES)
    suffix = Path(original_name).suffix.lower() or ".pdf"
    target = settings.dataset_dir / f"{Path(original_name).stem}_{uuid4().hex[:8]}{suffix}"
    shutil.copyfile(saved, target)
    record = service.register_document(
        doc_id=target.name,
        name=target.name,
        city=city,
        theme=theme,
        tags=parse_tags(tags),
        source_note=source_note,
        trust_level=trust_level,
        action=action,
        analysis=analysis,
    )
    return success(
        {
            "doc": {"doc_id": target.name, "name": target.name, "size": target.stat().st_size},
            "analysis": analysis,
            "record": record,
            "needs_reindex": True,
        }
    )


@router.post("/governance/register-text", dependencies=[Depends(require_admin)])
async def governance_register_text(payload: GovernanceTextRegisterRequest) -> dict:
    """说明：governance_register_text 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    settings = get_settings()
    service = KnowledgeGovernanceService(settings)
    content = payload.content.strip()
    summary = payload.summary or content[:500]
    analysis = service.analyze_candidate(title=payload.title, city=payload.city, theme=payload.theme, tags=payload.tags, summary=summary)
    settings.dataset_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_stem(payload.title)}_{uuid4().hex[:8]}.md"
    target = settings.dataset_dir / filename
    target.write_text(_format_text_guide(payload, content), encoding="utf-8")
    record = service.register_document(
        doc_id=target.name,
        name=target.name,
        city=payload.city,
        theme=payload.theme,
        tags=payload.tags,
        source_note=payload.source_note,
        trust_level=payload.trust_level,
        action=payload.action,
        analysis=analysis,
    )
    return success(
        {
            "doc": {"doc_id": target.name, "name": target.name, "size": target.stat().st_size},
            "analysis": analysis,
            "record": record,
            "needs_reindex": True,
        }
    )


@router.post("/governance/merge-plan")
async def governance_merge_plan(payload: MergePlanRequest) -> dict:
    """说明：governance_merge_plan 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    service = KnowledgeGovernanceService()
    return success(service.create_merge_plan(source_doc_ids=payload.source_doc_ids, target_title=payload.target_title, strategy=payload.strategy, notes=payload.notes))


def _iter_dataset_docs(dataset_dir: Path) -> list[Path]:
    """说明：_iter_dataset_docs 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    docs: list[Path] = []
    for pattern in ("*.pdf", "*.md", "*.txt"):
        docs.extend(dataset_dir.glob(pattern))
    return sorted(docs, key=lambda path: path.name)


def _safe_stem(title: str) -> str:
    """说明：_safe_stem 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", title, flags=re.UNICODE).strip("_")
    return stem[:48] or "guide"


def _format_text_guide(payload: GovernanceTextRegisterRequest, content: str) -> str:
    """说明：_format_text_guide 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    tags = ", ".join(payload.tags)
    return "\n".join(
        [
            f"# {payload.title}",
            "",
            f"- city: {payload.city}",
            f"- theme: {payload.theme}",
            f"- tags: {tags}",
            f"- source_note: {payload.source_note}",
            f"- trust_level: {payload.trust_level}",
            "",
            content,
            "",
        ]
    )
