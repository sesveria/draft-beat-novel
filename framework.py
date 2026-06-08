"""故事框架数据模型 v3 — Draft + Beat(层级) + Chapter + Outline"""
from dataclasses import dataclass, field, asdict
import json, os, time

# ============ 草稿箱 ============

@dataclass
class DraftItem:
    id: str = ""
    title: str = ""       # 自动提取的一句话梗概 → 作为文件名
    content: str = ""     # 全文
    source: str = "user"  # user | ai_suggestion
    created_at: float = 0.0

# ============ 框架层 · 节拍（支持父子层级） ============

@dataclass
class Character:
    name: str
    role: str = ""
    description: str = ""
    background: str = ""
    goal: str = ""
    relationship: str = ""
    relationships: list = field(default_factory=list)  # [{"with": "角色名", "type": "父子", "description": "..."}]

@dataclass
class Beat:
    id: str = ""
    title: str = ""
    description: str = ""
    location: str = ""
    characters: list = field(default_factory=list)
    order: int = 0
    parent_beat_id: str = ""   # 空=主节拍, 非空=次节拍
    status: str = "active"

# ============ 写作层 · 章节 ============

CHAPTER_STAGES = ["draft", "first_pass", "revising", "review", "published"]
CHAPTER_STAGE_LABELS = {
    "draft": "📝 草稿", "first_pass": "👀 初稿",
    "revising": "🔧 修改", "review": "✅ 审核", "published": "📖 发布"
}

@dataclass
class Chapter:
    id: str = ""
    title: str = ""
    order: int = 0
    summary: str = ""        # 自动提取的一句话梗概
    prose: str = ""
    beat_ids: list = field(default_factory=list)
    stage: str = "draft"

    def advance_stage(self):
        idx = CHAPTER_STAGES.index(self.stage)
        if idx < len(CHAPTER_STAGES) - 1:
            self.stage = CHAPTER_STAGES[idx + 1]
            return True
        return False

    def regress_stage(self):
        idx = CHAPTER_STAGES.index(self.stage)
        if idx > 0:
            self.stage = CHAPTER_STAGES[idx - 1]
            return True
        return False

# ============ 故事框架 ============

@dataclass
class StoryFramework:
    title: str = ""
    genre: str = ""
    tone: str = ""
    focused: bool = False          # 焦点作品，首页置顶展示
    tag: str = ""                  # 标签，如 "test" 标记测试数据
    characters: list = field(default_factory=list)
    drafts: list = field(default_factory=list)    # DraftItem[]
    beats: list = field(default_factory=list)     # Beat[]
    chapters: list = field(default_factory=list)  # Chapter[]

    # ── Draft ──

    def next_draft_id(self):
        return f"draft_{len(self.drafts) + 1}"

    def add_draft(self, title, content, source="user"):
        d = DraftItem(
            id=self.next_draft_id(), title=title,
            content=content, source=source, created_at=time.time()
        )
        self.drafts.append(d)
        return d

    def get_draft(self, draft_id):
        for d in self.drafts:
            if d.id == draft_id:
                return d
        return None

    def remove_draft(self, draft_id):
        self.drafts = [d for d in self.drafts if d.id != draft_id]

    # ── Beat ──

    def next_beat_id(self):
        return f"beat_{len(self.beats) + 1}"

    def add_beat(self, title, description="", location="", characters=None, parent_beat_id=""):
        b = Beat(
            id=self.next_beat_id(), title=title,
            description=description, location=location,
            characters=characters or [], parent_beat_id=parent_beat_id,
            order=len([x for x in self.beats if x.parent_beat_id == parent_beat_id])
        )
        self.beats.append(b)
        return b

    def remove_beat(self, beat_id):
        # 删除节拍及其子节拍
        self.beats = [b for b in self.beats if b.id != beat_id and b.parent_beat_id != beat_id]
        for ch in self.chapters:
            if beat_id in ch.beat_ids:
                ch.beat_ids.remove(beat_id)

    def reorder_beats(self, beat_ids):
        """beat_ids = [id1, id2, ...] 全部节拍的扁平顺序"""
        bmap = {b.id: b for b in self.beats}
        self.beats.sort(key=lambda b: beat_ids.index(b.id) if b.id in beat_ids else 999)

    def get_beat(self, beat_id):
        for b in self.beats:
            if b.id == beat_id:
                return b
        return None

    def get_beats_tree(self):
        """返回 [(master, [children])] 结构"""
        masters = [b for b in self.beats if not b.parent_beat_id]
        children = [b for b in self.beats if b.parent_beat_id]
        tree = []
        for m in sorted(masters, key=lambda x: x.order):
            tree.append((m, sorted([c for c in children if c.parent_beat_id == m.id], key=lambda x: x.order)))
        return tree

    # ── Chapter ──

    def next_chapter_id(self):
        return f"chapter_{len(self.chapters) + 1}"

    def add_chapter(self, title, beat_ids=None, summary=""):
        ch = Chapter(
            id=self.next_chapter_id(), title=title,
            order=len(self.chapters), beat_ids=beat_ids or [],
            summary=summary, stage="draft"
        )
        self.chapters.append(ch)
        return ch

    def remove_chapter(self, chapter_id):
        self.chapters = [c for c in self.chapters if c.id != chapter_id]

    def get_chapter(self, chapter_id):
        for c in self.chapters:
            if c.id == chapter_id:
                return c
        return None

    # ── Outline (auto from chapters) ──

    def get_outline(self):
        """从已确定章节自动生成大纲"""
        return [
            {"id": c.id, "title": c.title, "order": c.order,
             "summary": c.summary, "stage": c.stage,
             "word_count": len(c.prose)}
            for c in sorted(self.chapters, key=lambda x: x.order)
        ]

    # ── Serialization ──

    def to_dict(self):
        return {
            "title": self.title, "genre": self.genre, "tone": self.tone,
            "focused": self.focused, "tag": self.tag,
            "characters": [asdict(c) for c in self.characters],
            "drafts": [asdict(d) for d in self.drafts],
            "beats": [asdict(b) for b in self.beats],
            "chapters": [asdict(c) for c in self.chapters],
        }

    @classmethod
    def from_dict(cls, d):
        fw = cls(title=d.get("title", ""), genre=d.get("genre", ""), tone=d.get("tone", ""),
                 focused=d.get("focused", False), tag=d.get("tag", ""))
        fw.characters = [Character(**{k: v for k, v in c.items() if k in Character.__dataclass_fields__}) for c in d.get("characters", [])]
        for dd in d.get("drafts", []):
            fw.drafts.append(DraftItem(**{k: v for k, v in dd.items() if k in DraftItem.__dataclass_fields__}))
        for b in d.get("beats", []) or d.get("_legacy_scenes", d.get("scenes", [])):
            fw.beats.append(Beat(**{k: v for k, v in b.items() if k in Beat.__dataclass_fields__}))
        chapters_raw = d.get("chapters", [])
        old_prose = d.get("prose", {})
        if chapters_raw:
            for c in chapters_raw:
                ch = Chapter(**{k: v for k, v in c.items() if k in Chapter.__dataclass_fields__})
                # fill prose from old format if missing
                if not ch.prose and c.get("id") in old_prose:
                    ch.prose = old_prose[c["id"]]
                fw.chapters.append(ch)
        elif old_prose:
            # 旧版迁移
            scene_list = d.get("beats", []) or d.get("scenes", [])
            for scene in scene_list:
                sid = scene.get("id", "")
                text = old_prose.get(sid, "")
                ch = Chapter(
                    id=sid, title=scene.get("title", "未命名"),
                    order=len(fw.chapters), beat_ids=[sid] if sid else [],
                    summary="", prose=text,
                    stage="first_pass" if scene.get("status") == "done" else "draft"
                )
                fw.chapters.append(ch)
        return fw

    def get_stats(self):
        total = len(self.chapters)
        sc = {s: sum(1 for c in self.chapters if c.stage == s) for s in CHAPTER_STAGES}
        return {
            "total_chapters": total, "total_beats": len(self.beats),
            "total_drafts": len(self.drafts), "total_words": sum(len(c.prose) for c in self.chapters),
            "stage_counts": sc,
            "progress": f"{sc.get('published', 0)}/{total}" if total > 0 else "0/0"
        }
