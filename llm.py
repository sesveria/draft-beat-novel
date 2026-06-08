"""DeepSeek API 调用 - 支持多种写作模式"""
import json
import os
import requests

def _get_api_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        env_file = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY"):
                        key = line.split("=", 1)[1].strip().strip("\"'")
                        break
    return key

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"

def call_llm(system_prompt, user_prompt, temperature=0.7):
    """通用 LLM 调用"""
    api_key = _get_api_key()
    if not api_key:
        return ""

    payload = {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": 4096
    }

    try:
        resp = requests.post(
            DEEPSEEK_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[llm] API 调用失败: {e}")
        return ""

def generate_prose(framework, scene_id=None, direction="", mode="continue", extra_context=""):
    """根据模式生成正文"""
    context = extra_context or _build_context(framework, scene_id)

    mode_configs = {
        "continue": {
            "system": "你是一个故事作家。根据故事设定和当前写作方向，续写一段生动的故事正文。\n要求：中文，有画面感，加入感官细节，适当对话，保持角色性格，300-500字。",
            "user": f"故事设定：\n{context}\n\n当前写作方向：{direction if direction else '继续往下写'}\n\n请续写："
        },
        "direct": {
            "system": "你是一个执行导演。根据用户的导演指令，写出一段符合要求的故事正文。用户说的方向你要准确执行。\n要求：中文，生动有画面感，300-500字。",
            "user": f"故事设定：\n{context}\n\n导演指令：{direction}\n\n请按指令写出这段："
        },
        "polish_vivid": {
            "system": "你是一个文字润色师。把原文改写得更生动、更有画面感。增加感官细节（视觉、听觉、嗅觉、触觉）。保持原意和情节不变。",
            "user": f"原文：\n{direction}\n\n请改写得更生动："
        },
        "polish_emotional": {
            "system": "你是一个情感描写专家。把原文改写得更感人、更有情感冲击力。加深情绪渲染，增加心理描写。保持原意不变。",
            "user": f"原文：\n{direction}\n\n请改写得更感人："
        },
        "polish_tense": {
            "system": "你是一个悬疑紧张气氛专家。把原文改写得更紧张刺激。加快节奏，增加悬念，压缩句式。保持原意不变。",
            "user": f"原文：\n{direction}\n\n请改写得更紧张："
        },
        "brainstorm": {
            "system": "你是一个创意顾问。根据故事当前进展，提供3-5个接下来可能的剧情发展方向。每个方向用一句话描述，加上一个emoji。直接输出选项，不要多余文字。",
            "user": f"故事设定：\n{context}\n\n当前进展：{direction}\n\n请给出接下来可能的剧情方向："
        },
        "critique": {
            "system": "你是一个故事编辑。分析这段文字的优缺点，指出：1.角色是否OOC 2.逻辑是否有漏洞 3.节奏是否合适 4.改进建议。简洁，每条一行。",
            "user": f"故事设定：\n{context}\n\n正文：\n{direction}\n\n请分析："
        }
    }

    config = mode_configs.get(mode, mode_configs["continue"])
    return call_llm(config["system"], config["user"],
                    temperature=0.8 if mode in ["continue", "direct", "brainstorm"] else 0.4)

def _build_context(framework, scene_id=None):
    """构建故事上下文"""
    parts = [f"故事：{framework.title}", f"题材：{framework.genre}", f"基调：{framework.tone}"]

    if framework.characters:
        parts.append("\n角色：")
        for c in framework.characters:
            parts.append(f"  {c.name}（{c.role}）：{c.description} 目标：{c.goal}")

    # Legacy scene support — only used if no chapters/beats
    scenes = getattr(framework, 'scenes', None) or getattr(framework, '_legacy_scenes', None)
    if scenes:
        parts.append("\n故事场景：")
        for s in scenes:
            marker = "【当前】" if getattr(s, 'id', None) == scene_id else ""
            status_icon = {"draft": "📝", "writing": "✍️", "done": "✅"}.get(getattr(s, 'status', 'draft'), "📝")
            parts.append(f"  {status_icon} {getattr(s, 'order', 0)+1}. {getattr(s, 'title', '?')} — {getattr(s, 'description', '')} {marker}")

    return "\n".join(parts)


def summarize_text(text):
    """提取一句话梗概（20字以内）"""
    if not text or len(text) < 10:
        return ""
    system = "你是一个摘要助手。用一句话（不超过20个字）概括以下内容的核心。只输出摘要，不要多余文字。"
    result = call_llm(system, f"内容：\n{text[:800]}\n\n一句话摘要：", temperature=0.3)
    return result[:50] if result else text[:30]


def generate_from_drafts(drafts_text, existing_beats_context, characters_context):
    """从草稿生成节拍列表"""
    system = """你是故事结构师。根据用户提供的草稿内容、已有的节拍信息和角色设定，
生成新的故事节拍列表。每个节拍包含：标题、描述、地点、涉及角色。
注意：
1. 节拍按时间先后排列
2. 区分主节拍和次节拍（主节拍是核心事件，次节拍是细节展开）
3. 次节拍用 parent 字段标识所属的主节拍
4. 如果已有节拍，新增节拍应插入合适位置
返回JSON格式：{"beats": [{"title":"...","description":"...","location":"...","characters":[...],"parent":"主节拍标题或空"}, ...]}"""
    user = f"已有角色设定：\n{characters_context}\n\n已有节拍：\n{existing_beats_context}\n\n草稿内容：\n{drafts_text}\n\n请生成节拍列表："
    result = call_llm(system, user, temperature=0.5)
    return result
