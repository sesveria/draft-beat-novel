#!/usr/bin/env python3
"""故事创作工具 - CLI 入口"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comprehension import understand_idea, present_understanding, refine_understanding, build_framework
from framework import StoryFramework
from llm import call_llm
from storage import save_story, list_stories
import storage
import json

BANNER = """
╔══════════════════════════════════════╗
║          📖 故事创作助手             ║
║  把你的想法变成故事，就这么简单      ║
╚══════════════════════════════════════╝
"""

def generate_prose(framework, user_input=""):
    """生成正文"""
    # 构建故事上下文
    context_parts = [f"故事：{framework.title}", f"题材：{framework.genre}", f"基调：{framework.tone}"]
    
    if framework.characters:
        context_parts.append("\n角色：")
        for c in framework.characters:
            context_parts.append(f"  {c.name}（{c.role}）：{c.description}")
    
    if framework.scenes:
        context_parts.append("\n故事大纲：")
        for s in framework.scenes:
            context_parts.append(f"  {s.order+1}. {s.title} — {s.description}")
    
    context = "\n".join(context_parts)
    
    system_prompt = """你是一个故事作家。根据用户的故事设定和当前写作方向，生成一段生动的故事正文。

写作要求：
1. 使用中文，语言生动有画面感
2. 加入感官细节（视觉、听觉、嗅觉、触觉）
3. 适当使用对话推进剧情
4. 保持角色性格一致
5. 单次生成300-500字左右
6. 不要写"第一章"之类的标题，直接写内容"""

    user_prompt = f"""故事设定：
{context}

当前写作方向：{user_input if user_input else "写一个吸引人的开头"}

请根据以上信息，写一段故事正文。直接写内容，不要加标题。"""

    return call_llm(system_prompt, user_prompt, temperature=0.8)

def interactive_loop(framework):
    """交互式写作循环"""
    print(f"\n{'='*50}")
    print(f"📝 开始写作：《{framework.title}》")
    print(f"{'='*50}\n")
    
    while True:
        print("\n--- 选项 ---")
        print("1. ✍️  写一段（给方向，AI帮你写）")
        print("2. 📖 看目前写了什么")
        print("3. 💾 保存")
        print("4. 📋 查看故事设定")
        print("5. 🚪 退出")
        
        choice = input("\n> ").strip()
        
        if choice == "1":
            print("\n你想写什么？（直接回车就写开头/继续往下写）")
            direction = input("> ").strip()
            
            print("\n🤖 正在写...\n")
            prose = generate_prose(framework, direction)
            
            if prose:
                print(f"\n{'─'*50}")
                print(prose)
                print(f"{'─'*50}")
                
                # 保存到框架
                if "0" not in framework.prose:
                    framework.prose["0"] = ""
                framework.prose["0"] += "\n\n" + prose
                
                print("\n这段怎么样？")
                print("1. 👍 不错，继续")
                print("2. 🔄 重写")
                print("3. ✏️  我说说哪里要改")
                
                sub = input("> ").strip()
                if sub == "3":
                    feedback = input("\n想怎么改？> ").strip()
                    revised = call_llm(
                        "你是一个故事作家。请根据反馈修改这段文字。",
                        f"原文：\n{prose}\n\n修改意见：\n{feedback}\n\n请直接输出修改后的版本。",
                        temperature=0.5
                    )
                    if revised:
                        print(f"\n{'─'*50}")
                        print(revised)
                        print(f"{'─'*50}")
                        framework.prose["0"] = framework.prose["0"].replace(prose, revised)
        
        elif choice == "2":
            text = framework.prose.get("0", "")
            if text.strip():
                print(f"\n{'─'*50}")
                print(text.strip())
                print(f"{'─'*50}")
                print(f"\n📊 已写 {len(text)} 字")
            else:
                print("\n还没有写任何内容")
        
        elif choice == "3":
            save_story(framework)
        
        elif choice == "4":
            print(f"\n📖 故事：{framework.title}")
            print(f"📂 题材：{framework.genre}")
            print(f"🎨 基调：{framework.tone}")
            print(f"\n👤 角色：")
            for c in framework.characters:
                print(f"  {c.name} — {c.description}")
            print(f"\n📅 故事大纲：")
            for s in framework.scenes:
                print(f"  {s.order+1}. {s.title}")
        
        elif choice == "5":
            save_story(framework)
            print("\n👋 下次继续写！")
            break

def main():
    print(BANNER)
    
    while True:
        print("\n你想做什么？")
        print("1. ✨ 开始一个新故事")
        print("2. 📚 继续之前的故事")
        print("3. 🚪 退出")
        
        choice = input("\n> ").strip()
        
        if choice == "1":
            new_story()
        elif choice == "2":
            list_stories()
            print("\n输入故事编号加载（直接回车返回）")
            idx = input("> ").strip()
            if idx.isdigit():
                files = sorted(os.listdir(storage.STORAGE_DIR), reverse=True)
                files = [f for f in files if f.endswith(".json")]
                if 1 <= int(idx) <= len(files):
                    filepath = os.path.join(storage.STORAGE_DIR, files[int(idx)-1])
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    from framework import StoryFramework
                    framework = StoryFramework.from_dict(data)
                    print(f"\n📖 已加载：{framework.title}")
                    interactive_loop(framework)
        elif choice == "3":
            print("\n👋 再见！")
            break

def new_story():
    """创建一个新故事"""
    import json
    
    print("\n✍️  把你脑中的故事想法写下来：")
    print("  （可以是一段话、几个关键词、或者一个场景）")
    print("  （输入 /e 结束）")
    
    lines = []
    while True:
        line = input()
        if line.strip() == "/e":
            break
        lines.append(line)
    
    raw_text = "\n".join(lines)
    if not raw_text.strip():
        print("没有输入任何内容")
        return
    
    print("\n🤖 正在理解你的想法...\n")
    
    data = understand_idea(raw_text)
    if not data:
        print("抱歉，我暂时无法理解你的想法，能再描述得清楚一些吗？")
        return
    
    # 呈现给用户确认
    present_understanding(data)
    
    print("\n我理解得对吗？")
    print("1. ✅ 没错，开始写吧！")
    print("2. ✏️  我补充/修改一下")
    print("3. ❌ 完全不对，重新来")
    
    choice = input("\n> ").strip()
    
    if choice == "1":
        framework = build_framework(data)
        interactive_loop(framework)
    elif choice == "2":
        feedback = input("\n请补充或修改：\n> ").strip()
        refined = refine_understanding(raw_text, data, feedback)
        if refined:
            print("\n📋 更新后的理解：")
            present_understanding(refined)
            print("\n现在可以了吗？[y/n]")
            if input("> ").strip().lower() == "y":
                framework = build_framework(refined)
                interactive_loop(framework)
            else:
                print("好的，下次再继续")
        else:
            print("处理失败，请重试")
    else:
        print("好的，重新来试试吧")

if __name__ == "__main__":
    main()
