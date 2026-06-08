"""共享测试 fixture"""
import pytest
import sys, os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from framework import StoryFramework


@pytest.fixture
def empty_fw():
    """一个空的故事框架"""
    return StoryFramework(title="测试故事", genre="悬疑", tone="紧张")


@pytest.fixture
def fw_with_data(empty_fw):
    """包含各类数据的故事框架"""
    fw = empty_fw
    fw.add_draft("原始想法", "一个程序员在海边捡到漂流瓶")
    fw.add_draft("第二版", "程序员打开瓶塞，里面有一封信")
    m = fw.add_beat("发现漂流瓶", "程序员在海边散步时发现")
    fw.add_beat("阅读信件", "信中写道...", parent_beat_id=m.id)
    fw.add_beat("决定出发", "程序员决定踏上旅程")
    ch1 = fw.add_chapter("第一章", summary="海边发现")
    ch1.prose = "林远在海边散步，夕阳洒在海面上。"
    ch2 = fw.add_chapter("第二章", beat_ids=[m.id], summary="启程")
    ch2.prose = "林远背上背包，踏上了旅程。"
    return fw
