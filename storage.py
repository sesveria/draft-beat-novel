"""故事存储"""
import json
import os
from datetime import datetime

STORAGE_DIR = os.path.expanduser("~/hermes_workspace/story_tool/stories")

def save_story(framework, prose_text=""):
    """保存故事到文件"""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    data = framework.to_dict()
    if prose_text:
        data["prose"] = {"0": prose_text}
    data["saved_at"] = datetime.now().isoformat()
    
    filename = f"{framework.title or '未命名故事'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(STORAGE_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已保存: {filename}")
    return filepath

def list_stories():
    """列出所有保存的故事"""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    files = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    
    if not files:
        print("暂无保存的故事")
        return
    
    print(f"\n📚 已保存的故事（{len(files)}个）：")
    for i, f in enumerate(files, 1):
        filepath = os.path.join(STORAGE_DIR, f)
        size = os.path.getsize(filepath)
        print(f"  {i}. {f.replace('.json', '')} ({size // 1024}KB)")
