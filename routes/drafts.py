from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from models import DraftCreate, DraftUpdate
from llm import call_llm, summarize_text

router = APIRouter()


@router.post("/api/story/{sid}/drafts")
def create_draft(sid: str, req: DraftCreate):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    title = req.title or summarize_text(req.content) or "未命名草稿"
    d = fw.add_draft(title, req.content, req.source)
    _save(fw, sid)
    return {"id": d.id, "title": d.title, "content": d.content, "source": d.source}


@router.get("/api/story/{sid}/drafts")
def list_drafts(sid: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    return {
        "drafts": [
            {
                "id": d.id,
                "title": d.title,
                "content": d.content,
                "source": d.source,
                "created_at": d.created_at,
            }
            for d in fw.drafts
        ]
    }


@router.put("/api/story/{sid}/drafts/{did}")
def update_draft(sid: str, did: str, req: DraftUpdate):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    d = fw.get_draft(did)
    if not d:
        raise HTTPException(404)
    if req.title:
        d.title = req.title
    if req.content:
        d.content = req.content
    _save(fw, sid)
    return {"status": "ok"}


@router.delete("/api/story/{sid}/drafts/{did}")
def delete_draft(sid: str, did: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    fw.remove_draft(did)
    _save(fw, sid)
    return {"status": "ok"}


@router.post("/api/story/{sid}/drafts/ai-edit")
def ai_edit_draft(sid: str, req: DraftCreate):
    """AI 修改草稿"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    sysp = "你是一个写作助手。根据用户的修改要求修改草稿内容，保持核心信息不变，改进表达。直接输出修改后的完整内容。"
    result = call_llm(
        sysp, f"原文：\n{req.content}\n\n修改要求：{req.title}", temperature=0.7
    )
    if not result:
        raise HTTPException(500, "AI修改失败")
    return {"result": result}
