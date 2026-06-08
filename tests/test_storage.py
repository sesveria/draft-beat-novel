"""持久化测试 — services/storage.py

所有持久化到磁盘的测试数据均使用 genre="测试" 标记。
"""

import pytest
import os
import json

from services.storage import _save, _load, _fw, STORAGE_DIR


def _save_test(fw, sid):
    """以测试标记保存（设置 genre="测试"）"""
    fw.genre = "测试"
    _save(fw, sid)


class TestSaveLoad:

    def test_save_and_load(self, empty_fw):
        sid = "test_save_load"
        _save_test(empty_fw, sid)
        loaded = _load(sid)
        assert loaded is not None
        assert loaded.title == empty_fw.title
        assert loaded.genre == "测试"
        # 清理
        os.remove(os.path.join(STORAGE_DIR, f"{sid}.json"))

    def test_save_and_load_with_data(self, fw_with_data, empty_fw):
        sid = "test_save_load_data"
        _save_test(fw_with_data, sid)
        loaded = _load(sid)
        assert len(loaded.drafts) == len(fw_with_data.drafts)
        assert len(loaded.beats) == len(fw_with_data.beats)
        assert len(loaded.chapters) == len(fw_with_data.chapters)
        assert loaded.drafts[0].content == fw_with_data.drafts[0].content
        os.remove(os.path.join(STORAGE_DIR, f"{sid}.json"))

    def test_load_nonexistent(self):
        assert _load("nonexistent_sid_xyz") is None

    def test_save_creates_file(self, empty_fw):
        sid = "test_file_created"
        filepath = os.path.join(STORAGE_DIR, f"{sid}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        _save_test(empty_fw, sid)
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
            assert data["story_id"] == sid
            assert data["framework"]["title"] == empty_fw.title
            assert data["framework"]["genre"] == "测试"
        os.remove(filepath)


class TestFrameworkCache:

    def test_fw_caches_in_memory(self, empty_fw):
        sid = "test_cache"
        _save_test(empty_fw, sid)
        # 首次加载会缓存
        fw1 = _fw(sid)
        # 直接从缓存返回
        from services.storage import active_stories
        assert sid in active_stories
        assert active_stories[sid] is fw1
        os.remove(os.path.join(STORAGE_DIR, f"{sid}.json"))
        # 清理缓存
        active_stories.pop(sid, None)

    def test_fw_returns_none_for_missing(self):
        assert _fw("definitely_not_exists") is None

    def test_fw_loads_from_disk_on_cache_miss(self, empty_fw):
        sid = "test_disk_load"
        _save_test(empty_fw, sid)
        from services.storage import active_stories
        active_stories.pop(sid, None)  # 清缓存
        fw = _fw(sid)
        assert fw is not None
        assert fw.title == empty_fw.title
        os.remove(os.path.join(STORAGE_DIR, f"{sid}.json"))
        active_stories.pop(sid, None)
