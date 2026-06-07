"""故事创作工具 Web 后端 v3 — Draft → Beat → Chapter → Outline"""
import sys, os, json, uuid, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from framework import StoryFramework, CHAPTER_STAGES, CHAPTER_STAGE_LABELS
from comprehension import understand_idea, build_framework
from llm import generate_prose, call_llm, summarize_text, generate_from_drafts
from urllib.parse import unquote

app = FastAPI(title="故事创作助手 v3")
STORAGE_DIR = os.path.expanduser("~/hermes_workspace/story_tool/stories")
os.makedirs(STORAGE_DIR, exist_ok=True)
active_stories = {}

# ============ Models ============

class CreateReq(BaseModel): raw_text: str
class WriteReq(BaseModel): chapter_id: str = ""; direction: str = ""; mode: str = "continue"
class DraftCreate(BaseModel): title: str = ""; content: str; source: str = "user"
class DraftUpdate(BaseModel): title: str = ""; content: str = ""
class BeatCreate(BaseModel): title: str; description: str = ""; location: str = ""; characters: list = []; parent_beat_id: str = ""
class BeatReorder(BaseModel): beat_ids: list
class ChCreate(BaseModel): title: str; beat_ids: list = []
class ChUpdate(BaseModel): title: str = ""; beat_ids: list = None; summary: str = ""
class StageReq(BaseModel): action: str; stage: str = ""
class GenBeats(BaseModel): draft_ids: list = []
class GenChapter(BaseModel): beat_ids: list = []; prev_chapter_ids: list = []
class RefineReq(BaseModel): feedback: str = ""; question: str = ""
class AiPanelQuery(BaseModel): 
    action: str  # draft_continue, draft_brainstorm, draft_extract, beat_pacing, beat_check, outline_arc, outline_consistency
    context_id: str = ""  # draft_id, beat_id, etc.
    input: str = ""

class RelationItem(BaseModel): with_name: str = ""; type: str = ""; description: str = ""
class CharUpdate(BaseModel): name: str = ""; role: str = ""; description: str = ""; background: str = ""; goal: str = ""; relationship: str = ""; relationships: list = []

# ============ Persist ============

def _save(fw, sid):
    with open(os.path.join(STORAGE_DIR, f"{sid}.json"), "w", encoding="utf-8") as f:
        json.dump({"story_id": sid, "framework": fw.to_dict()}, f, ensure_ascii=False, indent=2)

def _load(sid):
    p = os.path.join(STORAGE_DIR, f"{sid}.json")
    if not os.path.exists(p): return None
    with open(p) as f: return StoryFramework.from_dict(json.load(f)["framework"])

def _fw(sid):
    if sid not in active_stories:
        fw = _load(sid)
        if fw: active_stories[sid] = fw
    return active_stories.get(sid)

# ============ Story ============

@app.post("/api/story/create")
def create_story(req: CreateReq):
    data = understand_idea(req.raw_text)
    if not data: raise HTTPException(400, "无法理解你的想法")
    fw = build_framework(data)
    sid = str(uuid.uuid4())[:8]
    # 不自动创建节拍和章节，把原始想法存为草稿
    fw.add_draft(title="原始想法", content=req.raw_text, source="user")
    active_stories[sid] = fw
    _save(fw, sid)
    return _detail(sid, fw)

@app.get("/api/story/{sid}")
def get_story(sid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    return _detail(sid, fw)

@app.get("/api/stories")
def list_stories():
    res = []
    if os.path.exists(STORAGE_DIR):
        for f in sorted(os.listdir(STORAGE_DIR), reverse=True):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(STORAGE_DIR, f)) as fh:
                        d = json.load(fh)["framework"]
                    res.append({"id": f.replace(".json",""), "title": d.get("title","?"),
                                "chapters": len(d.get("chapters",[])), "words": sum(len(c.get("prose","")) for c in d.get("chapters",[]))})
                except: pass
    return {"stories": res}


@app.post("/api/story/{sid}/refine")
def refine_story(sid: str, req: RefineReq):
    """Refine the story understanding with user feedback or answer a question"""
    # Re-run understanding with additional info
    from comprehension import refine_understanding
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    current = {
        "title": fw.title, "genre": fw.genre, "tone": fw.tone,
        "characters": [{"name": c.name, "role": c.role, "description": c.description, "goal": c.goal} for c in fw.characters],
        "events": [{"title": b.title, "description": b.description, "characters": b.characters} for b in fw.beats],
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
    if not refined: raise HTTPException(400, "处理失败")
    fw.title = refined.get("title", fw.title)
    fw.genre = refined.get("genre", fw.genre)
    fw.tone = refined.get("tone", fw.tone)
    _save(fw, sid)
    return {"status": "ok", "title": fw.title, "genre": fw.genre, "tone": fw.tone}


@app.post("/api/story/{sid}/questions")
def generate_questions(sid: str):
    """Generate clarifying questions to help build a better outline"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    sysp = "你是故事编辑。根据当前故事信息，生成3-5个能帮助完善故事大纲的追问。每个问题一句话，要具体、有针对性。直接输出问题列表，每行一个。"
    context = f"标题：{fw.title}\n题材：{fw.genre}\n基调：{fw.tone}\n"
    context += f"角色：{', '.join(c.name+'('+c.role+')' for c in fw.characters)}\n"
    context += f"现有节拍：{', '.join(b.title for b in fw.beats)}"
    result = call_llm(sysp, f"故事信息：\n{context}\n\n请针对这个故事的薄弱环节提出追问：", temperature=0.5)
    questions = [q.strip() for q in (result or "").split("\n") if q.strip() and len(q.strip()) > 5]
    return {"questions": questions[:6]}

# ============ Drafts ============

@app.post("/api/story/{sid}/drafts")
def create_draft(sid: str, req: DraftCreate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    title = req.title or summarize_text(req.content) or "未命名草稿"
    d = fw.add_draft(title, req.content, req.source)
    _save(fw, sid)
    return {"id": d.id, "title": d.title, "content": d.content, "source": d.source}

@app.get("/api/story/{sid}/drafts")
def list_drafts(sid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    return {"drafts": [{"id": d.id, "title": d.title, "content": d.content, "source": d.source, "created_at": d.created_at} for d in fw.drafts]}

@app.put("/api/story/{sid}/drafts/{did}")
def update_draft(sid: str, did: str, req: DraftUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    d = fw.get_draft(did)
    if not d: raise HTTPException(404)
    if req.title: d.title = req.title
    if req.content: d.content = req.content
    _save(fw, sid)
    return {"status": "ok"}

@app.delete("/api/story/{sid}/drafts/{did}")
def delete_draft(sid: str, did: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.remove_draft(did)
    _save(fw, sid)
    return {"status": "ok"}

@app.post("/api/story/{sid}/drafts/ai-edit")
def ai_edit_draft(sid: str, req: DraftCreate):
    """AI 修改草稿"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    sysp = "你是一个写作助手。根据用户的修改要求修改草稿内容，保持核心信息不变，改进表达。直接输出修改后的完整内容。"
    result = call_llm(sysp, f"原文：\n{req.content}\n\n修改要求：{req.title}", temperature=0.7)
    if not result: raise HTTPException(500, "AI修改失败")
    return {"result": result}

# ============ Beats ============

@app.post("/api/story/{sid}/edit-beat")
def ai_edit_beat_content(sid: str, req: RefineReq):
    """AI 修改单个节拍的内容"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    bid = req.question  # reuse question field as beat_id
    beat = fw.get_beat(bid)
    if not beat: raise HTTPException(404)
    context = f"当前节拍：{beat.title}\n描述：{beat.description}\n地点：{beat.location}\n角色：{', '.join(beat.characters)}"
    sysp = "你是一个故事结构师。根据用户要求修改故事节拍。返回修改后的节拍信息，格式：\n标题：...\n描述：...\n地点：...\n角色：..."
    result = call_llm(sysp, f"{context}\n\n修改要求：{req.feedback or req.question}\n请返回修改后的节拍信息。", temperature=0.5)
    return {"result": result}

@app.post("/api/story/{sid}/beats")
def create_beat(sid: str, req: BeatCreate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    b = fw.add_beat(req.title, req.description, req.location, req.characters, req.parent_beat_id)
    _save(fw, sid)
    return {"id": b.id, "title": b.title, "order": b.order, "parent_beat_id": b.parent_beat_id}

@app.delete("/api/story/{sid}/beats/{bid}")
def delete_beat(sid: str, bid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.remove_beat(bid)
    _save(fw, sid)
    return {"status": "ok"}

@app.put("/api/story/{sid}/beats/reorder")
def reorder_beats(sid: str, req: BeatReorder):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.reorder_beats(req.beat_ids)
    _save(fw, sid)
    return {"status": "ok"}

@app.post("/api/story/{sid}/beats/generate")
def generate_beats_from_drafts(sid: str, req: GenBeats):
    """从选中的草稿生成节拍"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    # 收集草稿内容
    drafts_text = ""
    for did in req.draft_ids:
        d = fw.get_draft(did)
        if d: drafts_text += f"【{d.title}】\n{d.content}\n\n"
    if not drafts_text: raise HTTPException(400, "未找到草稿")
    # 收集已有节拍
    existing_text = "\n".join(f"{b.order+1}. {b.title} {'(次: '+b.parent_beat_id+')' if b.parent_beat_id else ''}" for b in fw.beats)
    chars_text = "\n".join(f"{c.name}({c.role}): {c.description}" for c in fw.characters)
    result = generate_from_drafts(drafts_text, existing_text or "无", chars_text or "无")
    if not result: raise HTTPException(500, "生成失败")
    # Try to parse JSON from result
    content = result
    if "```json" in content: content = content.split("```json")[1].split("```")[0]
    elif "```" in content: content = content.split("```")[1].split("```")[0]
    try:
        import json as j
        data = j.loads(content.strip())
        beats = data.get("beats", [])
        if not beats: raise ValueError("no beats")
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
                parent_beat_id=parent_id
            )
            new_beats.append({"id": beat.id, "title": beat.title, "parent_beat_id": parent_id})
        _save(fw, sid)
        return {"beats": new_beats, "raw": result}
    except Exception as e:
        # 解析失败，返回原始结果让前端展示
        return {"beats": [], "raw": result, "parse_error": str(e)}

@app.post("/api/story/{sid}/beats/ai-edit")
def ai_edit_beat(sid: str, req: BeatCreate):
    """AI 修改节拍"""
    fw = _fw(sid)
    sysp = "你是一个故事结构师。根据用户要求修改故事节拍。返回JSON：{\"title\":\"...\",\"description\":\"...\",\"location\":\"...\"}"
    context = f"当前节拍：{req.title} - {req.description} [地点:{req.location}]\n"
    result = call_llm(sysp, context + f"修改要求：{req.title}\n请返回JSON。", temperature=0.5)
    return {"result": result}

# ============ Chapters ============

@app.post("/api/story/{sid}/chapters")
def create_chapter(sid: str, req: ChCreate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    ch = fw.add_chapter(req.title, req.beat_ids)
    _save(fw, sid)
    return {"id": ch.id, "title": ch.title, "order": ch.order, "stage": ch.stage}

@app.delete("/api/story/{sid}/chapters/{cid}")
def delete_chapter(sid: str, cid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.remove_chapter(cid)
    _save(fw, sid)
    return {"status": "ok"}

@app.put("/api/story/{sid}/chapters/{cid}")
def update_chapter(sid: str, cid: str, req: ChUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch: raise HTTPException(404)
    if req.title: ch.title = req.title
    if req.beat_ids is not None: ch.beat_ids = req.beat_ids
    if req.summary: ch.summary = req.summary
    _save(fw, sid)
    return {"status": "ok"}

@app.post("/api/story/{sid}/chapters/{cid}/stage")
def chapter_stage(sid: str, cid: str, req: StageReq):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch: raise HTTPException(404)
    ok = False
    if req.action == "advance": ok = ch.advance_stage()
    elif req.action == "regress": ok = ch.regress_stage()
    elif req.action == "set" and req.stage in CHAPTER_STAGES: ch.stage = req.stage; ok = True
    if not ok: raise HTTPException(400, f"无效操作: {req.action}")
    _save(fw, sid)
    return {"status": "ok", "stage": ch.stage, "stage_label": CHAPTER_STAGE_LABELS.get(ch.stage, ch.stage)}

@app.post("/api/story/{sid}/chapters/{cid}/save")
def save_chapter(sid: str, cid: str, req: WriteReq):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    ch = fw.get_chapter(cid)
    if not ch: raise HTTPException(404)
    if req.direction: ch.prose = req.direction
    # Auto-summarize
    if ch.prose and len(ch.prose) > 20:
        try: ch.summary = summarize_text(ch.prose) or ch.summary
        except: pass
    _save(fw, sid)
    return {"status": "ok", "word_count": len(ch.prose), "summary": ch.summary}

@app.post("/api/story/{sid}/chapters/generate")
def generate_chapter(sid: str, req: GenChapter):
    """从选中的节拍生成章节，注入前几章梗概"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    # 构建上下文
    beats_text = "\n".join(f"{b.title}: {b.description}" for b in fw.beats if b.id in (req.beat_ids or []))
    prev_text = ""
    if req.prev_chapter_ids:
        for pid in req.prev_chapter_ids:
            pc = fw.get_chapter(pid)
            if pc: prev_text += f"【{pc.title}】{pc.summary}\n"
    chars_text = "\n".join(f"{c.name}({c.role}): {c.description}" for c in fw.characters)
    # 用生成prose的方式创建新章节
    context = f"故事：{fw.title} ({fw.genre}·{fw.tone})\n角色：\n{chars_text}\n参考节拍：\n{beats_text}\n前章梗概：\n{prev_text}"
    sysp = f"""你是一个小说作家。根据故事设定和选中的节拍，写出一章正文。
{context}
要求：中文，有画面感，300-800字。直接输出正文，不要多余文字。"""
    result = call_llm(sysp, f"请写出这一章的内容。", temperature=0.7)
    if not result: raise HTTPException(500, "生成失败")
    # 自动提取梗概
    summary = ""
    try: summary = summarize_text(result)
    except: pass
    # 创建新章节
    ch = fw.add_chapter(f"新章节 {len(fw.chapters)+1}", req.beat_ids, summary)
    ch.prose = result
    _save(fw, sid)
    return {"id": ch.id, "title": ch.title, "summary": summary, "prose": result, "order": ch.order}

# ============ Outline ============

@app.get("/api/story/{sid}/outline")
def get_outline(sid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    return {"outline": fw.get_outline()}

@app.post("/api/story/{sid}/outline/update")
def update_outline(sid: str):
    """从已确定章节重新生成大纲"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    # 为没有摘要的章节自动生成
    for ch in fw.chapters:
        if not ch.summary and len(ch.prose) > 20:
            try: ch.summary = summarize_text(ch.prose)
            except: pass
    _save(fw, sid)
    return {"outline": fw.get_outline()}

@app.post("/api/story/{sid}/outline/ai-edit")
def ai_edit_outline(sid: str, req: CreateReq):
    """AI 修改大纲"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    outline_text = "\n".join(f"{o['order']+1}. {o['title']}: {o['summary']}" for o in fw.get_outline())
    sysp = "你是一个故事编辑。根据用户要求修改故事大纲。保持结构清晰。返回修改后的完整大纲，每行一个章节。"
    result = call_llm(sysp, f"当前大纲：\n{outline_text}\n\n修改要求：{req.raw_text}", temperature=0.5)
    return {"result": result}

# ============ Characters ============

@app.get("/api/story/{sid}/characters")
def list_characters(sid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    return {"characters": [_char_dict(c) for c in fw.characters]}

@app.post("/api/story/{sid}/characters")
def add_character(sid: str, req: CharUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    # Check duplicate
    if any(c.name == req.name for c in fw.characters):
        raise HTTPException(400, f"角色 '{req.name}' 已存在")
    from dataclasses import fields
    c = Character(name=req.name, role=req.role or "配角", description=req.description,
                  background=req.background, goal=req.goal, relationships=req.relationships or [])
    fw.characters.append(c)
    _save(fw, sid)
    return {"status": "ok", "character": _char_dict(c)}

@app.put("/api/story/{sid}/characters/{name}")
def update_character(sid: str, name: str, req: CharUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    c = next((x for x in fw.characters if x.name == name), None)
    if not c: raise HTTPException(404, f"角色 '{name}' 不存在")
    if req.name: c.name = req.name
    if req.role: c.role = req.role
    if req.description: c.description = req.description
    if req.background: c.background = req.background
    if req.goal: c.goal = req.goal
    if req.relationship: c.relationship = req.relationship
    if req.relationships: c.relationships = req.relationships
    _save(fw, sid)
    return {"status": "ok", "character": _char_dict(c)}

@app.delete("/api/story/{sid}/characters/{name}")
def delete_character(sid: str, name: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.characters = [c for c in fw.characters if c.name != name]
    _save(fw, sid)
    return {"status": "ok"}

def _char_dict(c):
    return {
        "name": c.name, "role": c.role, "description": c.description,
        "background": c.background, "goal": c.goal, "relationship": c.relationship,
        "relationships": c.relationships or []
    }

# ============ AI Panel Query (通用面板AI) ============

@app.post("/api/story/{sid}/ai-panel")
def ai_panel_query(sid: str, req: AiPanelQuery):
    """通用AI面板查询 — 根据action类型自动构建上下文"""
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    
    actions = {
        "draft_continue": {
            "sys": "你是一个创意写作伙伴。根据已有草稿内容，自然地续写下去，保持风格和语气一致。直接输出续写内容，不要加评论。",
            "ctx": lambda: _draft_content(fw, req.context_id),
        },
        "draft_brainstorm": {
            "sys": "你是一个创意头脑风暴助手。根据用户的想法，从不同角度生成3-5个可以拓展的方向。每个方向一句话。不要评价，直接给出方向。",
            "ctx": lambda: _draft_content(fw, req.context_id),
        },
        "draft_extract": {
            "sys": "你是一个内容分析师。从草稿中提取关键元素：核心事件、主要角色、关键场景。以简洁的列表形式输出。",
            "ctx": lambda: _draft_content(fw, req.context_id),
        },
        "draft_rewrite": {
            "sys": "你是一名写作教练。根据用户的改写要求改进草稿的表达方式。保持核心信息不变，改进语言和结构。直接输出改写后的内容。",
            "ctx": lambda: f"原文：\n{_draft_content(fw, req.context_id)}\n\n修改要求：{req.input}",
        },
        "beat_pacing": {
            "sys": "你是一个故事结构分析师。分析给定的故事节拍，评估叙事节奏：哪些部分太快、哪些太慢、哪里需要过渡、整体张力曲线如何。给出具体建议。",
            "ctx": lambda: _beat_context(fw),
        },
        "beat_check": {
            "sys": "你是一个逻辑审查员。检查故事节拍中的逻辑漏洞、因果关系断裂、角色动机不一致。列出问题并给出修复建议。",
            "ctx": lambda: _beat_context(fw),
        },
        "beat_fill": {
            "sys": "你是一个故事架构师。分析已有节拍之间的缺口，建议补充哪些中间节拍让故事更连贯。每个建议一句话。",
            "ctx": lambda: _beat_context(fw) + f"\n用户关注：{req.input}",
        },
        "outline_arc": {
            "sys": "你是一个故事分析专家。分析故事大纲的整体弧线：开篇设定、冲突升级、高潮、结局。评估弧线是否完整、张力是否足够。给出改进建议。",
            "ctx": lambda: _outline_context(fw),
        },
        "outline_consistency": {
            "sys": "你是一个连续性审查员。检查大纲中的时间线一致性、角色连续性、地点一致性。列出潜在的矛盾点。",
            "ctx": lambda: _outline_context(fw),
        },
    }
    
    if req.action not in actions:
        raise HTTPException(400, f"未知动作: {req.action}")
    
    config = actions[req.action]
    context = config["ctx"]()
    result = call_llm(config["sys"], context, temperature=0.5)
    if not result:
        raise HTTPException(500, "AI处理失败")
    return {"result": result}

def _draft_content(fw, draft_id):
    d = fw.get_draft(draft_id)
    if not d: return "（无草稿内容）"
    chars = "、".join(f"{c.name}({c.role})" for c in fw.characters) if fw.characters else "暂无"
    return f"故事：{fw.title}（{fw.genre}·{fw.tone}）\n角色：{chars}\n\n【{d.title}】\n{d.content}"

def _beat_context(fw):
    beats = fw.get_beats_tree()
    lines = [f"故事：{fw.title}（{fw.genre}·{fw.tone}）\n"]
    for master, children in beats:
        lines.append(f"■ {master.title}")
        if master.description: lines.append(f"  描述：{master.description}")
        if master.location: lines.append(f"  地点：{master.location}")
        for child in children:
            lines.append(f"  └ {child.title}: {child.description}")
    return "\n".join(lines)

def _outline_context(fw):
    outline = fw.get_outline()
    chars = "、".join(f"{c.name}({c.role})" for c in fw.characters) if fw.characters else "暂无"
    lines = [f"故事：{fw.title}（{fw.genre}·{fw.tone}）", f"角色：{chars}", ""]
    for o in outline:
        lines.append(f"第{o['order']+1}章 {o['title']}")
        lines.append(f"  梗概：{o['summary'] or '（无）'}")
        lines.append(f"  状态：{o.get('stage_label','?')} · {o.get('word_count',0)}字")
    return "\n".join(lines)

# ============ Writing (kept for backward compatibility) ============

@app.post("/api/story/{sid}/write")
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

# ============ Helper ============

def _detail(sid, fw):
    return {
        "story_id": sid, "title": fw.title, "genre": fw.genre, "tone": fw.tone,
        "characters": [{"name":c.name,"role":c.role,"description":c.description,"goal":c.goal} for c in fw.characters],
        "drafts": [{"id":d.id,"title":d.title,"content":d.content,"source":d.source,"created_at":d.created_at} for d in fw.drafts],
        "beats": [{"id":b.id,"title":b.title,"description":b.description,"location":b.location,
                    "characters":b.characters,"order":b.order,"parent_beat_id":b.parent_beat_id,"status":b.status} for b in fw.beats],
        "chapters": [{"id":c.id,"title":c.title,"order":c.order,"summary":c.summary,
                       "prose":c.prose,"beat_ids":c.beat_ids,"stage":c.stage,
                       "stage_label":CHAPTER_STAGE_LABELS.get(c.stage,c.stage),"word_count":len(c.prose)} for c in fw.chapters],
        "stats": fw.get_stats(),
        "outline": fw.get_outline(),
    }

# Static files
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    print("🚀 故事创作助手 v3")
    print("🌐 http://localhost:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888, log_level="info")
