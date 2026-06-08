"""故事路由 — 创作、读取、精炼、追问"""
import os
import json

from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save, active_stories, STORAGE_DIR
from services.context import _detail
from models import CreateReq, RefineReq
from comprehension import understand_idea, build_framework, refine_understanding
from llm import call_llm
import uuid

router = APIRouter()


# ============ Story ============


@router.post("/api/story/create")
def create_story(req: CreateReq):
    data = understand_idea(req.raw_text)
    if not data:
        raise HTTPException(400, "无法理解你的想法")
    fw = build_framework(data)
    sid = str(uuid.uuid4())[:8]
    # 不自动创建节拍和章节，把原始想法存为草稿
    fw.add_draft(title="原始想法", content=req.raw_text, source="user")
    active_stories[sid] = fw
    _save(fw, sid)
    return _detail(sid, fw)


@router.get("/api/story/{sid}")
def get_story(sid: str):
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    return _detail(sid, fw)


@router.get("/api/stories")
def list_stories():
    res = []
    if os.path.exists(STORAGE_DIR):
        for f in sorted(os.listdir(STORAGE_DIR), reverse=True):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(STORAGE_DIR, f)) as fh:
                        d = json.load(fh)["framework"]
                    res.append({
                        "id": f.replace(".json", ""),
                        "title": d.get("title", "?"),
                        "chapters": len(d.get("chapters", [])),
                        "words": sum(len(c.get("prose", "")) for c in d.get("chapters", [])),
                    })
                except Exception:
                    pass
    return {"stories": res}


@router.post("/api/story/{sid}/refine")
def refine_story(sid: str, req: RefineReq):
    """Refine the story understanding with user feedback or answer a question"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    current = {
        "title": fw.title,
        "genre": fw.genre,
        "tone": fw.tone,
        "characters": [
            {"name": c.name, "role": c.role, "description": c.description, "goal": c.goal}
            for c in fw.characters
        ],
        "events": [
            {"title": b.title, "description": b.description, "characters": b.characters}
            for b in fw.beats
        ],
    }
    # Get original raw text from the first draft if available
    raw_text = ""
    if fw.drafts:
        raw_text = fw.drafts[0].content
    feedback = req.question or req.feedback
    if not feedback:
        # Generate clarifying questions
        sysp = "你是故事编辑。根据当前故事信息，生成3-5个能帮助完善故事大纲的追问。每个问题一句话。直接输出问题列表，每行一个。不要多余文字。"
        context = f"标题：{fw.title}\n题材：{fw.genre}\n基调：{fw.tone}\n角色：{', '.join(c.name+'('+c.role+')' for c in fw.characters)}\n节拍：{', '.join(b.title for b in fw.beats)}"
        result = call_llm(sysp, f"故事信息：\n{context}\n\n请生成追问：", temperature=0.5)
        return {"questions": [q.strip() for q in (result or "").split("\n") if q.strip()]}
    # Apply feedback
    refined = refine_understanding(raw_text, current, feedback)
    if not refined:
        raise HTTPException(400, "处理失败")
    fw.title = refined.get("title", fw.title)
    fw.genre = refined.get("genre", fw.genre)
    fw.tone = refined.get("tone", fw.tone)
    _save(fw, sid)
    return {"status": "ok", "title": fw.title, "genre": fw.genre, "tone": fw.tone}


@router.post("/api/story/{sid}/questions")
def generate_questions(sid: str):
    """Generate clarifying questions to help build a better outline"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)
    sysp = "你是故事编辑。根据当前故事信息，生成3-5个能帮助完善故事大纲的追问。每个问题一句话，要具体、有针对性。直接输出问题列表，每行一个。"
    context = f"标题：{fw.title}\n题材：{fw.genre}\n基调：{fw.tone}\n"
    context += f"角色：{', '.join(c.name+'('+c.role+')' for c in fw.characters)}\n"
    context += f"现有节拍：{', '.join(b.title for b in fw.beats)}"
    result = call_llm(sysp, f"故事信息：\n{context}\n\n请针对这个故事的薄弱环节提出追问：", temperature=0.5)
    questions = [q.strip() for q in (result or "").split("\n") if q.strip() and len(q.strip()) > 5]
    return {"questions": questions[:6]}
