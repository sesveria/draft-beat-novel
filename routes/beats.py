from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from models import BeatCreate, BeatReorder, GenBeats, RefineReq
from llm import generate_from_drafts, call_llm
import json

router = APIRouter()


# ============ Beats ============


@router.post("/api/story/{sid}/edit-beat")
def ai_edit_beat_content(sid: str, req: RefineReq):
    """AI 修改单个节拍的内容"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    bid = req.question  # reuse question field as beat_id
    beat = fw.get_beat(bid)
    if not beat:
        raise HTTPException(404)
    context = f"当前节拍：{beat.title}\n描述：{beat.description}\n地点：{beat.location}\n角色：{', '.join(beat.characters)}"
    sysp = "你是一个故事结构师。根据用户要求修改故事节拍。返回修改后的节拍信息，格式：\n标题：...\n描述：...\n地点：...\n角色：..."
    result = call_llm(
        sysp,
        f"{context}\n\n修改要求：{req.feedback or req.question}\n请返回修改后的节拍信息。",
        temperature=0.5,
    )
    return {"result": result}


@router.post("/api/story/{sid}/beats")
def create_beat(sid: str, req: BeatCreate):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    b = fw.add_beat(
        req.title, req.description, req.location, req.characters, req.parent_beat_id
    )
    _save(fw, sid)
    return {
        "id": b.id,
        "title": b.title,
        "order": b.order,
        "parent_beat_id": b.parent_beat_id,
    }


@router.delete("/api/story/{sid}/beats/{bid}")
def delete_beat(sid: str, bid: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    fw.remove_beat(bid)
    _save(fw, sid)
    return {"status": "ok"}


@router.put("/api/story/{sid}/beats/reorder")
def reorder_beats(sid: str, req: BeatReorder):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    fw.reorder_beats(req.beat_ids)
    _save(fw, sid)
    return {"status": "ok"}


@router.post("/api/story/{sid}/beats/generate")
def generate_beats_from_drafts(sid: str, req: GenBeats):
    """从选中的草稿生成节拍"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    # 收集草稿内容
    drafts_text = ""
    for did in req.draft_ids:
        d = fw.get_draft(did)
        if d:
            drafts_text += f"【{d.title}】\n{d.content}\n\n"
    if not drafts_text:
        raise HTTPException(400, "未找到草稿")
    # 收集已有节拍
    existing_text = "\n".join(
        f"{b.order+1}. {b.title} {'(次: '+b.parent_beat_id+')' if b.parent_beat_id else ''}"
        for b in fw.beats
    )
    chars_text = "\n".join(
        f"{c.name}({c.role}): {c.description}" for c in fw.characters
    )
    result = generate_from_drafts(drafts_text, existing_text or "无", chars_text or "无")
    if not result:
        raise HTTPException(500, "生成失败")
    # Try to parse JSON from result
    content = result
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    try:
        data = json.loads(content.strip())
        beats = data.get("beats", [])
        if not beats:
            raise ValueError("no beats")
        # 找已有主节拍标题到ID的映射
        master_map = {b.title: b.id for b in fw.beats if not b.parent_beat_id}
        new_beats = []
        for bd in beats:
            parent_id = ""
            if bd.get("parent"):
                parent_title = bd["parent"]
                if parent_title in master_map:
                    parent_id = master_map[parent_title]
            beat = fw.add_beat(
                title=bd.get("title", "未命名"),
                description=bd.get("description", ""),
                location=bd.get("location", ""),
                characters=bd.get("characters", []),
                parent_beat_id=parent_id,
            )
            new_beats.append(
                {"id": beat.id, "title": beat.title, "parent_beat_id": parent_id}
            )
        _save(fw, sid)
        return {"beats": new_beats, "raw": result}
    except Exception as e:
        # 解析失败，返回原始结果让前端展示
        return {"beats": [], "raw": result, "parse_error": str(e)}


@router.post("/api/story/{sid}/beats/ai-edit")
def ai_edit_beat(sid: str, req: BeatCreate):
    """AI 修改节拍"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    sysp = '你是一个故事结构师。根据用户要求修改故事节拍。返回JSON：{"title":"...","description":"...","location":"..."}'
    context = f"当前节拍：{req.title} - {req.description} [地点:{req.location}]\n"
    result = call_llm(
        sysp, context + f"修改要求：{req.title}\n请返回JSON。", temperature=0.5
    )
    return {"result": result}
