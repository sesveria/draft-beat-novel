"""大纲路由 — 获取、更新、AI 编辑"""
from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from models import CreateReq
from llm import call_llm, summarize_text

router = APIRouter()


@router.get("/api/story/{sid}/outline")
def get_outline(sid: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    return {"outline": fw.get_outline()}


@router.post("/api/story/{sid}/outline/update")
def update_outline(sid: str):
    """从已确定章节重新生成大纲"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    # 为没有摘要的章节自动生成
    for ch in fw.chapters:
        if not ch.summary and len(ch.prose) > 20:
            try:
                ch.summary = summarize_text(ch.prose)
            except:
                pass
    _save(fw, sid)
    return {"outline": fw.get_outline()}


@router.post("/api/story/{sid}/outline/ai-edit")
def ai_edit_outline(sid: str, req: CreateReq):
    """AI 修改大纲"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    outline_text = "\n".join(
        f"{o['order']+1}. {o['title']}: {o['summary']}" for o in fw.get_outline()
    )
    sysp = "你是一个故事编辑。根据用户要求修改故事大纲。保持结构清晰。返回修改后的完整大纲，每行一个章节。"
    result = call_llm(
        sysp,
        f"当前大纲：\n{outline_text}\n\n修改要求：{req.raw_text}",
        temperature=0.5,
    )
    return {"result": result}
