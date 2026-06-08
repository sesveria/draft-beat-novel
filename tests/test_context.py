"""上下文构建测试 — services/context.py"""

from services.context import _draft_content, _beat_context, _outline_context, _char_dict
from framework import Character


class TestDraftContent:

    def test_draft_content_basic(self, fw_with_data):
        did = fw_with_data.drafts[0].id
        content = _draft_content(fw_with_data, did)
        assert "测试故事" in content
        assert "程序员在海边捡到漂流瓶" in content
        assert "程序员" in content  # 角色名

    def test_draft_content_nonexistent(self, empty_fw):
        content = _draft_content(empty_fw, "不存在")
        assert content == "（无草稿内容）"


class TestBeatContext:

    def test_beat_context_contains_structure(self, fw_with_data):
        ctx = _beat_context(fw_with_data)
        assert "测试故事" in ctx
        assert "发现漂流瓶" in ctx
        assert "阅读信件" in ctx
        assert "决定出发" in ctx

    def test_beat_context_empty(self, empty_fw):
        ctx = _beat_context(empty_fw)
        assert "测试故事" in ctx


class TestOutlineContext:

    def test_outline_context_basic(self, fw_with_data):
        ctx = _outline_context(fw_with_data)
        assert "测试故事" in ctx
        assert "第一章" in ctx
        assert "第二章" in ctx

    def test_outline_context_empty(self, empty_fw):
        ctx = _outline_context(empty_fw)
        assert "测试故事" in ctx


class TestCharDict:

    def test_char_dict_basic(self):
        c = Character(name="小明", role="主角", description="好人",
                       background="出生在普通家庭", goal="拯救世界")
        d = _char_dict(c)
        assert d["name"] == "小明"
        assert d["role"] == "主角"
        assert d["goal"] == "拯救世界"
        assert d["relationships"] == []

    def test_char_dict_with_relationships(self):
        c = Character(name="小明", role="主角",
                       relationships=[{"with_name": "小红", "type": "朋友"}])
        d = _char_dict(c)
        assert len(d["relationships"]) == 1
        assert d["relationships"][0]["with_name"] == "小红"

    def test_char_dict_minimal(self):
        c = Character(name="路人甲")
        d = _char_dict(c)
        assert d["name"] == "路人甲"
        assert d["role"] == ""
        assert d["background"] == ""
        assert d["relationships"] == []
