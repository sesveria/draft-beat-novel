"""写作路由"""
from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from models import WriteReq
from llm import generate_prose

router = APIRouter()


@router.post("/api/story/{sid}/write")
def write_story(sid: str, req: WriteReq):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    ch = fw.get_chapter(req.chapter_id) if req.chapter_id else None
    context = ""
    if ch:
        prev_summaries = "\n".join(
            f"【{c.title}】{c.summary}" for c in fw.chapters
            if c.order < ch.order and c.summary
        )
        chars = "\n".join(f"{c.name}({c.role}): {c.description}" for c in fw.characters)
        context = f"前章梗概：\n{prev_summaries}\n角色：\n{chars}"
    result = generate_prose(fw, req.chapter_id, req.direction, req.mode, extra_context=context)
    if not result: raise HTTPException(500, "生成失败")
    return {"result": result}
