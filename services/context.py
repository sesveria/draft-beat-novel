"""上下文构建服务 — 为 AI 面板提供故事上下文"""
from framework import CHAPTER_STAGE_LABELS


def _draft_content(fw, draft_id):
    d = fw.get_draft(draft_id)
    if not d:
        return "（无草稿内容）"
    chars = "、".join(f"{c.name}({c.role})" for c in fw.characters) if fw.characters else "暂无"
    return f"故事：{fw.title}（{fw.genre}·{fw.tone}）\n角色：{chars}\n\n【{d.title}】\n{d.content}"


def _beat_context(fw):
    beats = fw.get_beats_tree()
    lines = [f"故事：{fw.title}（{fw.genre}·{fw.tone}）\n"]
    for master, children in beats:
        lines.append(f"■ {master.title}")
        if master.description:
            lines.append(f"  描述：{master.description}")
        if master.location:
            lines.append(f"  地点：{master.location}")
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
        lines.append(f"  状态：{o.get('stage_label', '?')} · {o.get('word_count', 0)}字")
    return "\n".join(lines)


def _char_dict(c):
    return {
        "name": c.name, "role": c.role, "description": c.description,
        "background": c.background, "goal": c.goal, "relationship": c.relationship,
        "relationships": c.relationships or [],
    }


def _detail(sid, fw):
    return {
        "story_id": sid, "title": fw.title, "genre": fw.genre, "tone": fw.tone,
        "focused": fw.focused,
        "characters": [{"name": c.name, "role": c.role, "description": c.description, "goal": c.goal}
                       for c in fw.characters],
        "drafts": [{"id": d.id, "title": d.title, "content": d.content, "source": d.source,
                    "created_at": d.created_at} for d in fw.drafts],
        "beats": [{"id": b.id, "title": b.title, "description": b.description, "location": b.location,
                   "characters": b.characters, "order": b.order, "parent_beat_id": b.parent_beat_id,
                   "status": b.status} for b in fw.beats],
        "chapters": [{"id": c.id, "title": c.title, "order": c.order, "summary": c.summary,
                      "prose": c.prose, "beat_ids": c.beat_ids, "stage": c.stage,
                      "stage_label": CHAPTER_STAGE_LABELS.get(c.stage, c.stage),
                      "word_count": len(c.prose)} for c in fw.chapters],
        "stats": fw.get_stats(),
        "outline": fw.get_outline(),
    }
