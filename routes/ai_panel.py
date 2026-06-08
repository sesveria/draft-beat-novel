"""AI Panel路由 — 通用面板AI查询"""

from fastapi import APIRouter, HTTPException
from services.storage import _fw
from services.context import _draft_content, _beat_context, _outline_context
from models import AiPanelQuery
from llm import call_llm

router = APIRouter()


# ============ AI Panel Query (通用面板AI) ============


@router.post("/api/story/{sid}/ai-panel")
def ai_panel_query(sid: str, req: AiPanelQuery):
    """通用AI面板查询 — 根据action类型自动构建上下文"""
    fw = _fw(sid)
    if not fw:
        raise HTTPException(404)

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
