"""持久化服务 — 故事数据的保存、加载和缓存"""
import os
import json

from framework import StoryFramework

STORAGE_DIR = os.path.expanduser("~/hermes_workspace/story_tool/stories")
os.makedirs(STORAGE_DIR, exist_ok=True)

# 内存缓存：sid → StoryFramework
active_stories = {}


def _save(fw, sid):
    with open(os.path.join(STORAGE_DIR, f"{sid}.json"), "w", encoding="utf-8") as f:
        json.dump({"story_id": sid, "framework": fw.to_dict()}, f, ensure_ascii=False, indent=2)


def _load(sid):
    p = os.path.join(STORAGE_DIR, f"{sid}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return StoryFramework.from_dict(json.load(f)["framework"])


def _fw(sid):
    if sid not in active_stories:
        fw = _load(sid)
        if fw:
            active_stories[sid] = fw
    return active_stories.get(sid)
