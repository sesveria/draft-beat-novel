"""信息传递层 - 理解用户原始输入"""
from framework import StoryFramework, Character
from llm import call_llm
import json

def understand_idea(raw_text):
    """理解用户的想法，返回结构化信息"""
    
    system_prompt = """你是故事理解助手。你的任务是从用户的原始想法中提取关键信息。
请严格按照JSON格式回复，不要有多余的文字。

提取的信息包括：
- title: 故事标题（如果用户没提，根据内容生成一个）
- genre: 题材（奇幻/科幻/悬疑/言情/武侠/都市/其他）
- tone: 基调（你可以用几个词描述，如"温暖治愈"、"悬疑紧张"）
- characters: 角色列表，每个角色包含 name, role(主角/配角/反派), description, goal
- events: 关键事件列表，每个事件包含 title, description, characters(涉及的角色名列表)
- questions: 你对用户想法的疑问列表（比如"他"指谁？这里是什么意思？）
"""

    user_prompt = f"""以下是用户对故事的原始想法，请帮我提取信息：

{raw_text}

请严格按照JSON格式回复：
{{
  "title": "...",
  "genre": "...",
  "tone": "...",
  "characters": [
    {{"name": "...", "role": "...", "description": "...", "goal": "..."}}
  ],
  "events": [
    {{"title": "...", "description": "...", "characters": ["..."]}}
  ],
  "questions": [
    "这里不太确定..."
  ]
}}

注意：
1. characters 里的 goal 如果没有明确提到，可以写"待定"
2. events 按照故事发展顺序排列
3. questions 列出你对用户想法的疑问，比如角色关系不明确的地方
4. questions 里的文字不要使用双引号，用【】代替引号
"""

    result = call_llm(system_prompt, user_prompt, temperature=0.3)

    try:
        # 提取 JSON（可能被 markdown 包裹）
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        # 修复 LLM 可能输出的智能引号 → 直引号
        result = result.replace("\u201c", '"').replace("\u201d", '"')
        result = result.replace("\u2018", "'").replace("\u2019", "'")

        # 用括号匹配提取最外层 JSON 对象（鲁棒解析）
        data = _robust_json_parse(result)
        if data:
            return data

        # 最后尝试直接解析
        data = json.loads(result.strip())
        return data
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"解析失败: {e}")
        print(f"原始响应: {result[:500]}")
        return None


def _robust_json_parse(text):
    """鲁棒的 JSON 解析：通过括号匹配找到最外层 {}，再尝试解析"""
    text = text.strip()
    start = text.find("{")
    if start < 0:
        return None

    # 括号匹配找到最外层对象
    depth = 0
    end = -1
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end < 0:
        return None

    candidate = text[start:end]

    # 尝试直接解析
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 移除 questions 字段再试（它是唯一可能含未转义引号的字段）
    import re
    cleaned = re.sub(r',?\s*"questions"\s*:\s*\[.*?\]', '', candidate, count=1, flags=re.DOTALL)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 如果失败，尝试转义字符串中未转义的双引号
    # 策略：逐字符处理，在字符串内部时，遇到未转义的双引号就转义
    fixed = []
    in_string = False
    escape = False
    for ch in candidate:
        if escape:
            fixed.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            fixed.append(ch)
            escape = True
            continue
        if ch == '"':
            # 切换字符串状态
            in_string = not in_string
            fixed.append(ch)
            continue
        if in_string and ch == "\n":
            fixed.append("\\n")
            continue
        fixed.append(ch)

    try:
        return json.loads("".join(fixed))
    except json.JSONDecodeError:
        pass

    # 如果还失败，尝试更暴力的方法：在字符串内部将未转义的引号替换为中文引号
    result2 = []
    i = 0
    in_str = False
    chars = list(candidate)
    while i < len(chars):
        ch = chars[i]
        if ch == "\\":
            result2.append(ch)
            if i + 1 < len(chars):
                result2.append(chars[i + 1])
                i += 2
            continue
        if ch == '"':
            result2.append(ch)
            in_str = not in_str
            i += 1
            continue
        if in_str and (ch == "'" or ch == "\\'"):
            # 将字符串内部的单引号保留
            result2.append(ch)
            i += 1
            continue
        result2.append(ch)
        i += 1

    candidate2 = "".join(result2)
    # 将字符串内部的未匹配引号替换为中文引号
    # 这种简单粗暴的方法可能破坏结构，所以仅做最后尝试
    try:
        return json.loads(candidate2)
    except json.JSONDecodeError:
        return None

def present_understanding(data):
    """把理解呈现给用户看"""
    if not data:
        return False
    
    print(f"\n📖 故事：{data.get('title', '未命名')}")
    print(f"📂 题材：{data.get('genre', '未定')}")
    print(f"🎨 基调：{data.get('tone', '未定')}")
    
    chars = data.get("characters", [])
    if chars:
        print(f"\n👤 角色（{len(chars)}个）：")
        for c in chars:
            role_symbol = {"主角": "⭐", "配角": "🔹", "反派": "💀"}.get(c.get("role", ""), "👤")
            print(f"  {role_symbol} {c['name']} — {c.get('description', '')}")
            if c.get("goal"):
                print(f"     目标：{c['goal']}")
    
    events = data.get("events", [])
    if events:
        print(f"\n📅 关键事件（{len(events)}个）：")
        for i, e in enumerate(events, 1):
            print(f"  {i}. {e['title']} — {e.get('description', '')}")
    
    questions = data.get("questions", [])
    if questions:
        print(f"\n❓ 我还有一些疑问：")
        for q in questions:
            print(f"   • {q}")
    
    return True

def refine_understanding(raw_text, current_data, feedback):
    """根据用户的反馈优化理解"""
    system_prompt = """你是一个故事理解助手。用户对你之前提取的故事信息给出了反馈，
请根据反馈修改故事信息，回复JSON格式。"""

    user_prompt = f"""原始故事想法：
{raw_text}

之前提取的信息：
{json.dumps(current_data, ensure_ascii=False, indent=2)}

用户的反馈：
{feedback}

请根据反馈修改信息，回复同样的JSON结构。"""

    result = call_llm(system_prompt, user_prompt, temperature=0.3)
    
    try:
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        return json.loads(result.strip())
    except:
        return None

def build_framework(data):
    """把理解到的信息转化为故事框架"""
    framework = StoryFramework(
        title=data.get("title", "未命名故事"),
        genre=data.get("genre", ""),
        tone=data.get("tone", "")
    )
    
    for c in data.get("characters", []):
        framework.characters.append(Character(
            name=c["name"],
            role=c.get("role", ""),
            description=c.get("description", ""),
            goal=c.get("goal", "")
        ))
    
    for i, e in enumerate(data.get("events", [])):
        framework.add_beat(
            title=e["title"],
            description=e.get("description", ""),
            characters=e.get("characters", [])
        )
    
    return framework
