"""章节路由 — 创建、删除、更新、阶段推进、保存、生成"""
from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from models import ChCreate, ChUpdate, StageReq, WriteReq, GenChapter
from llm import summarize_text, call_llm, generate_prose
from framework import CHAPTER_STAGES, CHAPTER_STAGE_LABELS

router = APIRouter()


@router.post("/api/story/{sid}/chapters")
def create_chapter(sid: str, req: ChCreate):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    ch = fw.add_chapter(req.title, req.beat_ids)
    _save(fw, sid)
    return {"id": ch.id, "title": ch.title, "order": ch.order, "stage": ch.stage}


@router.delete("/api/story/{sid}/chapters/{cid}")
def delete_chapter(sid: str, cid: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    fw.remove_chapter(cid)
    _save(fw, sid)
    return {"status": "ok"}


@router.put("/api/story/{sid}/chapters/{cid}")
def update_chapter(sid: str, cid: str, req: ChUpdate):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch:
        raise HTTPException(404)
    if req.title:
        ch.title = req.title
    if req.beat_ids is not None:
        ch.beat_ids = req.beat_ids
    if req.summary:
        ch.summary = req.summary
    _save(fw, sid)
    return {"status": "ok"}


@router.post("/api/story/{sid}/chapters/{cid}/stage")
def chapter_stage(sid: str, cid: str, req: StageReq):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch:
        raise HTTPException(404)
    ok = False
    if req.action == "advance":
        ok = ch.advance_stage()
    elif req.action == "regress":
        ok = ch.regress_stage()
    elif req.action == "set" and req.stage in CHAPTER_STAGES:
        ch.stage = req.stage
        ok = True
    if not ok:
        raise HTTPException(400, f"无效操作: {req.action}")
    _save(fw, sid)
    return {
        "status": "ok",
        "stage": ch.stage,
        "stage_label": CHAPTER_STAGE_LABELS.get(ch.stage, ch.stage),
    }


@router.post("/api/story/{sid}/chapters/{cid}/save")
def save_chapter(sid: str, cid: str, req: WriteReq):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch:
        raise HTTPException(404)
    if req.direction:
        ch.prose = req.direction
    # Auto-summarize
    if ch.prose and len(ch.prose) > 20:
        try:
            ch.summary = summarize_text(ch.prose) or ch.summary
        except:
            pass
    _save(fw, sid)
    return {"status": "ok", "word_count": len(ch.prose), "summary": ch.summary}


@router.post("/api/story/{sid}/chapters/generate")
def generate_chapter(sid: str, req: GenChapter):
    """从选中的节拍生成章节，注入前几章梗概"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    # 构建上下文
    beats_text = "\n".join(
        f"{b.title}: {b.description}" for b in fw.beats if b.id in (req.beat_ids or [])
    )
    prev_text = ""
    if req.prev_chapter_ids:
        for pid in req.prev_chapter_ids:
            pc = fw.get_chapter(pid)
            if pc:
                prev_text += f"【{pc.title}】{pc.summary}\n"
    chars_text = "\n".join(
        f"{c.name}({c.role}): {c.description}" for c in fw.characters
    )
    # 用生成prose的方式创建新章节
    context = f"故事：{fw.title} ({fw.genre}·{fw.tone})\n角色：\n{chars_text}\n参考节拍：\n{beats_text}\n前章梗概：\n{prev_text}"
    sysp = f"""你是一个小说作家。根据故事设定和选中的节拍，写出一章正文。
{context}
要求：中文，有画面感，300-800字。直接输出正文，不要多余文字。"""
    result = call_llm(sysp, f"请写出这一章的内容。", temperature=0.7)
    if not result:
        raise HTTPException(500, "生成失败")
    # 自动提取梗概
    summary = ""
    try:
        summary = summarize_text(result)
    except:
        pass
    # 创建新章节
    ch = fw.add_chapter(f"新章节 {len(fw.chapters)+1}", req.beat_ids, summary)
    ch.prose = result
    _save(fw, sid)
    return {
        "id": ch.id,
        "title": ch.title,
        "summary": summary,
        "prose": result,
        "order": ch.order,
    }
