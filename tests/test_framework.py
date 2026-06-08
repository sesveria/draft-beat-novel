"""数据模型测试 — framework.py

覆盖：
1. 序列化/反序列化双向循环
2. 旧数据兼容性
3. Draft / Beat / Chapter CRUD
4. 节拍父子层级
5. 章节阶段流转
6. 大纲自动生成
7. 统计信息
"""

from framework import StoryFramework, Chapter, DraftItem, Beat, Character, CHAPTER_STAGES


# ========== 序列化 ==========

class TestSerialization:
    """写入 → 读出 → 数据一致"""

    def test_roundtrip_basic(self, fw_with_data):
        data = fw_with_data.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert fw2.title == fw_with_data.title
        assert fw2.genre == fw_with_data.genre
        assert fw2.tone == fw_with_data.tone

    def test_roundtrip_drafts(self, fw_with_data):
        data = fw_with_data.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert len(fw2.drafts) == 2
        assert fw2.drafts[0].title == "原始想法"
        assert fw2.drafts[1].content == "程序员打开瓶塞，里面有一封信"

    def test_roundtrip_beats(self, fw_with_data):
        data = fw_with_data.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert len(fw2.beats) == 3
        master = [b for b in fw2.beats if not b.parent_beat_id]
        child = [b for b in fw2.beats if b.parent_beat_id]
        assert len(master) == 2
        assert len(child) == 1
        assert child[0].parent_beat_id == master[0].id

    def test_roundtrip_chapters(self, fw_with_data):
        data = fw_with_data.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert len(fw2.chapters) == 2
        assert fw2.chapters[0].prose == "林远在海边散步，夕阳洒在海面上。"
        assert fw2.chapters[1].summary == "启程"
        assert fw2.chapters[0].order == 0
        assert fw2.chapters[1].order == 1

    def test_roundtrip_empty_framework(self, empty_fw):
        data = empty_fw.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert fw2.title == "测试故事"
        assert fw2.characters == []
        assert fw2.drafts == []
        assert fw2.beats == []

    def test_roundtrip_focused(self, fw_with_data):
        fw_with_data.focused = True
        data = fw_with_data.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert fw2.focused is True
        assert data["focused"] is True

    def test_focused_default_false(self, empty_fw):
        assert empty_fw.focused is False

    def test_focused_roundtrip_false(self, empty_fw):
        data = empty_fw.to_dict()
        assert data["focused"] is False
        fw2 = StoryFramework.from_dict(data)
        assert fw2.focused is False

    def test_focused_legacy_data(self):
        """旧数据没有 focused 字段，应该默认为 False"""
        data = {"title": "旧故事", "genre": "科幻", "tone": "悬疑"}
        fw = StoryFramework.from_dict(data)
        assert fw.focused is False

    def test_focused_serialize_toggle(self, empty_fw):
        empty_fw.focused = True
        data = empty_fw.to_dict()
        assert data["focused"] is True
        fw2 = StoryFramework.from_dict(data)
        assert fw2.focused is True
        fw2.focused = False
        data2 = fw2.to_dict()
        assert data2["focused"] is False

    def test_roundtrip_empty_framework_chapters(self, empty_fw):
        data = empty_fw.to_dict()
        fw2 = StoryFramework.from_dict(data)
        assert fw2.chapters == []


# ========== 兼容性 ==========

class TestBackwardCompatibility:
    """旧数据加载不能崩溃"""

    def test_ignores_unknown_character_fields(self):
        """Character 有不认识的字段不会崩"""
        old = {
            "title": "旧故事", "genre": "", "tone": "",
            "characters": [
                {"name": "小明", "role": "主角", "description": "好人",
                 "old_field_1": "x", "old_field_2": "y"},
            ],
            "drafts": [], "beats": [], "chapters": [],
        }
        fw = StoryFramework.from_dict(old)
        assert len(fw.characters) == 1
        assert fw.characters[0].name == "小明"
        assert fw.characters[0].relationships == []

    def test_ignores_unknown_beat_fields(self):
        old = {
            "title": "T", "genre": "", "tone": "",
            "characters": [], "drafts": [], "beats": [
                {"id": "b1", "title": "节拍", "description": "描述",
                 "obsolete": True},
            ], "chapters": [],
        }
        fw = StoryFramework.from_dict(old)
        assert len(fw.beats) == 1
        assert fw.beats[0].title == "节拍"

    def test_handles_missing_sections(self):
        """缺少某些 section 不崩溃"""
        fw = StoryFramework.from_dict({"title": "最小"})
        assert fw.characters == []
        assert fw.drafts == []
        assert fw.beats == []
        assert fw.chapters == []

    def test_handles_empty_characters(self):
        old = {
            "title": "T", "genre": "", "tone": "",
            "characters": [], "drafts": [], "beats": [], "chapters": [],
        }
        fw = StoryFramework.from_dict(old)
        assert fw.characters == []

    def test_handles_legacy_scenes_field(self):
        """兼容旧版 beats 字段名为 scenes 的情况"""
        old = {
            "title": "T", "genre": "", "tone": "",
            "characters": [], "drafts": [],
            "scenes": [{"id": "s1", "title": "旧场景", "description": "desc"}],
            "chapters": [],
        }
        fw = StoryFramework.from_dict(old)
        # scenes 在从旧版迁移时会被转为 beats
        assert len(fw.beats) >= 1


# ========== Draft CRUD ==========

class TestDraftCRUD:

    def test_add_draft(self, empty_fw):
        d = empty_fw.add_draft("标题", "内容")
        assert d.id == "draft_1"
        assert d.title == "标题"
        assert d.content == "内容"
        assert d.source == "user"

    def test_add_draft_auto_increments_id(self, empty_fw):
        empty_fw.add_draft("A", "a")
        d2 = empty_fw.add_draft("B", "b")
        assert d2.id == "draft_2"

    def test_get_draft_found(self, empty_fw):
        d = empty_fw.add_draft("标题", "内容")
        assert empty_fw.get_draft(d.id) is d

    def test_get_draft_not_found(self, empty_fw):
        assert empty_fw.get_draft("不存在") is None

    def test_remove_draft(self, empty_fw):
        d = empty_fw.add_draft("标题", "内容")
        empty_fw.remove_draft(d.id)
        assert len(empty_fw.drafts) == 0

    def test_remove_nonexistent_draft(self, empty_fw):
        empty_fw.remove_draft("不存在")
        assert len(empty_fw.drafts) == 0  # 不应崩溃


# ========== Beat CRUD ==========

class TestBeatCRUD:

    def test_add_beat(self, empty_fw):
        b = empty_fw.add_beat("发现", "在海边发现漂流瓶")
        assert b.title == "发现"
        assert b.description == "在海边发现漂流瓶"
        assert b.parent_beat_id == ""

    def test_add_beat_with_location_and_characters(self, empty_fw):
        b = empty_fw.add_beat("对话", "两人交谈", location="咖啡馆", characters=["A", "B"])
        assert b.location == "咖啡馆"
        assert b.characters == ["A", "B"]

    def test_beat_parent_child_relationship(self, empty_fw):
        m = empty_fw.add_beat("主线", "核心事件")
        c = empty_fw.add_beat("细节", "展开", parent_beat_id=m.id)
        assert c.parent_beat_id == m.id
        assert c.order == 0

    def test_beat_order_within_parent(self, empty_fw):
        m = empty_fw.add_beat("主线")
        c1 = empty_fw.add_beat("细节A", parent_beat_id=m.id)
        c2 = empty_fw.add_beat("细节B", parent_beat_id=m.id)
        assert c1.order == 0
        assert c2.order == 1

    def test_get_beats_tree(self, empty_fw):
        m1 = empty_fw.add_beat("主线1")
        m2 = empty_fw.add_beat("主线2")
        c1 = empty_fw.add_beat("子1", parent_beat_id=m1.id)
        c2 = empty_fw.add_beat("子2", parent_beat_id=m1.id)
        tree = empty_fw.get_beats_tree()
        assert len(tree) == 2
        assert tree[0][0].id == m1.id
        assert len(tree[0][1]) == 2
        assert tree[1][0].id == m2.id
        assert len(tree[1][1]) == 0

    def test_remove_beat_cascades_to_children(self, empty_fw):
        m = empty_fw.add_beat("主线")
        empty_fw.add_beat("子", parent_beat_id=m.id)
        empty_fw.remove_beat(m.id)
        assert len(empty_fw.beats) == 0

    def test_remove_beat_cleans_chapter_refs(self, empty_fw):
        b = empty_fw.add_beat("节拍")
        ch = empty_fw.add_chapter("章节", beat_ids=[b.id])
        empty_fw.remove_beat(b.id)
        assert b.id not in ch.beat_ids

    def test_remove_child_beat_keeps_parent(self, empty_fw):
        m = empty_fw.add_beat("主线")
        c = empty_fw.add_beat("子", parent_beat_id=m.id)
        empty_fw.remove_beat(c.id)
        assert len(empty_fw.beats) == 1
        assert empty_fw.beats[0].id == m.id

    def test_reorder_beats(self, empty_fw):
        b1 = empty_fw.add_beat("A")
        b2 = empty_fw.add_beat("B")
        b3 = empty_fw.add_beat("C")
        empty_fw.reorder_beats([b3.id, b1.id, b2.id])
        orders = [b.order for b in empty_fw.beats]
        # 检查排序后的顺序
        ids = [b.id for b in empty_fw.beats]
        assert ids == [b3.id, b1.id, b2.id]

    def test_get_beat(self, empty_fw):
        b = empty_fw.add_beat("查找我")
        assert empty_fw.get_beat(b.id) is b
        assert empty_fw.get_beat("不存在") is None


# ========== Chapter CRUD ==========

class TestChapterCRUD:

    def test_add_chapter(self, empty_fw):
        ch = empty_fw.add_chapter("第一章")
        assert ch.title == "第一章"
        assert ch.stage == "draft"
        assert ch.order == 0

    def test_add_chapter_with_summary_and_beats(self, empty_fw):
        b = empty_fw.add_beat("节拍")
        ch = empty_fw.add_chapter("第一章", beat_ids=[b.id], summary="开篇")
        assert ch.summary == "开篇"
        assert b.id in ch.beat_ids

    def test_chapter_order_auto_increments(self, empty_fw):
        empty_fw.add_chapter("第一章")
        ch2 = empty_fw.add_chapter("第二章")
        assert ch2.order == 1

    def test_remove_chapter(self, empty_fw):
        ch = empty_fw.add_chapter("第一章")
        empty_fw.remove_chapter(ch.id)
        assert len(empty_fw.chapters) == 0

    def test_get_chapter(self, empty_fw):
        ch = empty_fw.add_chapter("第一章")
        assert empty_fw.get_chapter(ch.id) is ch
        assert empty_fw.get_chapter("不存在") is None


# ========== 章节阶段 ==========

class TestChapterStage:

    def test_initial_stage_is_draft(self, empty_fw):
        ch = empty_fw.add_chapter("章节")
        assert ch.stage == "draft"

    def test_advance_full_cycle(self):
        ch = Chapter(stage="draft")
        expected = ["first_pass", "revising", "review", "published"]
        for exp in expected:
            assert ch.advance_stage() is True
            assert ch.stage == exp
        # 不能再前进
        assert ch.advance_stage() is False
        assert ch.stage == "published"

    def test_regress_full_cycle(self):
        ch = Chapter(stage="published")
        expected = ["review", "revising", "first_pass", "draft"]
        for exp in expected:
            assert ch.regress_stage() is True
            assert ch.stage == exp
        assert ch.regress_stage() is False
        assert ch.stage == "draft"

    def test_advance_at_each_stage(self):
        """在每个阶段都能正确前进"""
        for stage in CHAPTER_STAGES[:-1]:
            ch = Chapter(stage=stage)
            assert ch.advance_stage() is True

    def test_regress_at_each_stage(self):
        """在每个阶段都能正确回退"""
        for stage in CHAPTER_STAGES[1:]:
            ch = Chapter(stage=stage)
            assert ch.regress_stage() is True

    def test_advance_beyond_last(self):
        ch = Chapter(stage="published")
        assert ch.advance_stage() is False

    def test_regress_beyond_first(self):
        ch = Chapter(stage="draft")
        assert ch.regress_stage() is False


# ========== 大纲 ==========

class TestOutline:

    def test_outline_from_chapters(self, fw_with_data):
        outline = fw_with_data.get_outline()
        assert len(outline) == 2
        assert outline[0]["title"] == "第一章"
        assert outline[1]["title"] == "第二章"
        assert "summary" in outline[0]
        assert "word_count" in outline[0]

    def test_outline_empty_when_no_chapters(self, empty_fw):
        assert empty_fw.get_outline() == []

    def test_outline_order_by_chapter_order(self, empty_fw):
        c2 = empty_fw.add_chapter("第二章")
        c1 = empty_fw.add_chapter("第一章")
        # 手动调整 order 后，大纲按 order 排序
        c1.order = 0
        c2.order = 1
        outline = empty_fw.get_outline()
        assert outline[0]["title"] == "第一章"  # order=0 的先
        assert outline[1]["title"] == "第二章"

    def test_outline_contains_word_count(self, empty_fw):
        ch = empty_fw.add_chapter("章节")
        ch.prose = "一二三四五六七八九十"
        outline = empty_fw.get_outline()
        assert outline[0]["word_count"] == 10


# ========== 统计 ==========

class TestStats:

    def test_stats_basic(self, fw_with_data):
        s = fw_with_data.get_stats()
        assert s["total_chapters"] == 2
        assert s["total_beats"] == 3
        assert s["total_drafts"] == 2
        assert s["total_words"] > 0
        assert "stage_counts" in s
        assert "progress" in s

    def test_stats_empty(self, empty_fw):
        s = empty_fw.get_stats()
        assert s["total_chapters"] == 0
        assert s["total_beats"] == 0
        assert s["total_drafts"] == 0
        assert s["total_words"] == 0
        assert s["progress"] == "0/0"

    def test_stats_word_count_from_prose(self, empty_fw):
        ch = empty_fw.add_chapter("章节")
        ch.prose = "Hello World"
        assert empty_fw.get_stats()["total_words"] == 11

    def test_stats_stage_counts(self, empty_fw):
        c1 = empty_fw.add_chapter("C1")
        c1.stage = "draft"
        c2 = empty_fw.add_chapter("C2")
        c2.stage = "published"
        s = empty_fw.get_stats()
        assert s["stage_counts"]["draft"] == 1
        assert s["stage_counts"]["published"] == 1

    def test_stats_progress(self, empty_fw):
        empty_fw.add_chapter("C1")
        c2 = empty_fw.add_chapter("C2")
        c2.stage = "published"
        assert empty_fw.get_stats()["progress"] == "1/2"


# ========== 边界情况 ==========

class TestEdgeCases:

    def test_minimal_framework(self):
        """最小化的框架也能正常工作"""
        fw = StoryFramework()
        assert fw.title == ""
        assert len(fw.get_outline()) == 0
        s = fw.get_stats()
        assert s["progress"] == "0/0"

    def test_large_number_of_drafts(self, empty_fw):
        for i in range(100):
            empty_fw.add_draft(f"草稿{i}", f"内容{i}")
        assert len(empty_fw.drafts) == 100
        assert empty_fw.drafts[-1].id == "draft_100"

    def test_beat_with_empty_title(self, empty_fw):
        b = empty_fw.add_beat("")
        assert b.title == ""

    def test_chapter_with_empty_prose(self, empty_fw):
        ch = empty_fw.add_chapter("空章节")
        assert ch.prose == ""
        outline = empty_fw.get_outline()
        assert outline[0]["word_count"] == 0

    def test_remove_beat_from_chapter_with_no_beats(self, empty_fw):
        b = empty_fw.add_beat("节拍")
        ch = empty_fw.add_chapter("章节")  # 没有 beat_ids
        empty_fw.remove_beat(b.id)
        assert ch.beat_ids == []
