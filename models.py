from pydantic import BaseModel


class CreateReq(BaseModel):
    raw_text: str


class WriteReq(BaseModel):
    chapter_id: str = ""
    direction: str = ""
    mode: str = "continue"


class DraftCreate(BaseModel):
    title: str = ""
    content: str
    source: str = "user"


class DraftUpdate(BaseModel):
    title: str = ""
    content: str = ""


class BeatCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    characters: list = []
    parent_beat_id: str = ""


class BeatReorder(BaseModel):
    beat_ids: list


class ChCreate(BaseModel):
    title: str
    beat_ids: list = []


class ChUpdate(BaseModel):
    title: str = ""
    beat_ids: list = None
    summary: str = ""


class StageReq(BaseModel):
    action: str
    stage: str = ""


class GenBeats(BaseModel):
    draft_ids: list = []


class GenChapter(BaseModel):
    beat_ids: list = []
    prev_chapter_ids: list = []


class RefineReq(BaseModel):
    feedback: str = ""
    question: str = ""


class AiPanelQuery(BaseModel):
    action: str  # draft_continue, draft_brainstorm, draft_extract, beat_pacing, beat_check, outline_arc, outline_consistency
    context_id: str = ""  # draft_id, beat_id, etc.
    input: str = ""


class RelationItem(BaseModel):
    with_name: str = ""
    type: str = ""
    description: str = ""


class CharUpdate(BaseModel):
    name: str = ""
    role: str = ""
    description: str = ""
    background: str = ""
    goal: str = ""
    relationship: str = ""
    relationships: list = []


class SettingsUpdate(BaseModel):
    title: str = ""
    genre: str = ""
    tone: str = ""
