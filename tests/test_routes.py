"""API 端点测试 — FastAPI TestClient

所有通过 API 创建的故事均标记为 tag=test，
体裁会被后端强制设为「测试」，方便识别和清理。
"""

import pytest
from fastapi.testclient import TestClient
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from routes import create_app

client = TestClient(create_app())
TEST_TAG = "test"


class TestStoryEndpoints:

    def test_create_story(self):
        resp = client.post("/api/story/create", json={
            "raw_text": "一个程序员捡到漂流瓶，决定寻找写信人的女儿",
            "tag": TEST_TAG,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "story_id" in data
        assert data["title"]
        assert len(data["drafts"]) > 0

    def test_create_story_missing_input(self):
        resp = client.post("/api/story/create", json={})
        assert resp.status_code == 422  # Pydantic validation: missing required field

    def test_get_nonexistent_story(self):
        resp = client.get("/api/story/nonexist")
        assert resp.status_code == 404

    def test_create_then_get(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试故事，专门用来验证获取端点",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        resp = client.get(f"/api/story/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["story_id"] == sid
        assert "drafts" in data
        assert "beats" in data
        assert "chapters" in data

    def test_list_stories(self):
        resp = client.get("/api/stories")
        assert resp.status_code == 200
        data = resp.json()
        assert "stories" in data
        assert isinstance(data["stories"], list)

    def test_delete_created_story(self):
        create = client.post("/api/story/create", json={
            "raw_text": "即将被删除的测试故事",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        # Verify exists
        assert client.get(f"/api/story/{sid}").status_code == 200
        # Delete
        resp = client.delete(f"/api/story/{sid}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # Verify gone
        assert client.get(f"/api/story/{sid}").status_code == 404

    def test_delete_nonexistent(self):
        resp = client.delete("/api/story/nonexist_delete")
        assert resp.status_code == 404


class TestDraftEndpoints:

    def test_add_and_list_drafts(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试草稿功能",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]

        # Add drafts
        for text in ["第一份草稿的内容", "第二份草稿的内容"]:
            resp = client.post(f"/api/story/{sid}/drafts", json={"content": text})
            assert resp.status_code == 200

        # List
        resp = client.get(f"/api/story/{sid}/drafts")
        assert resp.status_code == 200
        assert len(resp.json()["drafts"]) >= 2  # 1 from creation + 2 added

    def test_update_draft(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试更新草稿",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        drafts = client.get(f"/api/story/{sid}/drafts").json()["drafts"]
        did = drafts[0]["id"]

        resp = client.put(f"/api/story/{sid}/drafts/{did}",
                          json={"title": "新标题", "content": "新内容"})
        assert resp.status_code == 200

        # Verify
        updated = client.get(f"/api/story/{sid}/drafts").json()["drafts"]
        u = [d for d in updated if d["id"] == did][0]
        assert u["title"] == "新标题"

    def test_delete_draft(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试删除草稿",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        # Add a draft
        add = client.post(f"/api/story/{sid}/drafts", json={"content": "要被删的草稿"})
        did = add.json()["id"]

        resp = client.delete(f"/api/story/{sid}/drafts/{did}")
        assert resp.status_code == 200

        drafts = client.get(f"/api/story/{sid}/drafts").json()["drafts"]
        assert all(d["id"] != did for d in drafts)


class TestBeatEndpoints:

    def test_create_beat(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试节拍功能",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]

        resp = client.post(f"/api/story/{sid}/beats", json={
            "title": "测试节拍", "description": "这是一个测试节拍"
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "测试节拍"

    def test_delete_beat(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试删除节拍",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        add = client.post(f"/api/story/{sid}/beats", json={"title": "待删除"})
        bid = add.json()["id"]

        resp = client.delete(f"/api/story/{sid}/beats/{bid}")
        assert resp.status_code == 200


class TestChapterEndpoints:

    def test_create_chapter(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试章节功能",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]

        resp = client.post(f"/api/story/{sid}/chapters", json={
            "title": "第一章"
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "第一章"

    def test_stage_advance(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试阶段推进",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        ch = client.post(f"/api/story/{sid}/chapters", json={"title": "章节"}).json()

        resp = client.post(f"/api/story/{sid}/chapters/{ch['id']}/stage",
                           json={"action": "advance"})
        assert resp.status_code == 200
        assert resp.json()["stage"] == "first_pass"


class TestCharacterEndpoints:

    def test_add_character(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试角色功能",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]

        resp = client.post(f"/api/story/{sid}/characters", json={
            "name": "测试角色", "role": "主角", "description": "一个测试角色"
        })
        assert resp.status_code == 200

        resp = client.get(f"/api/story/{sid}/characters")
        names = [c["name"] for c in resp.json()["characters"]]
        assert "测试角色" in names

    def test_delete_character(self):
        create = client.post("/api/story/create", json={
            "raw_text": "测试删除角色",
            "tag": TEST_TAG,
        })
        sid = create.json()["story_id"]
        client.post(f"/api/story/{sid}/characters", json={"name": "待删除"})

        # URL encode the name
        import urllib.parse
        resp = client.delete(f"/api/story/{sid}/characters/{urllib.parse.quote('待删除')}")
        assert resp.status_code == 200
