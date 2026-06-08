"""角色路由 — CRUD"""
from fastapi import APIRouter, HTTPException
from services.storage import _fw, _save
from services.context import _char_dict
from models import CharUpdate
from framework import Character

router = APIRouter()


@router.get("/api/story/{sid}/characters")
def list_characters(sid: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    return {"characters": [_char_dict(c) for c in fw.characters]}


@router.post("/api/story/{sid}/characters")
def add_character(sid: str, req: CharUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    # Check duplicate
    if any(c.name == req.name for c in fw.characters):
        raise HTTPException(400, f"角色 '{req.name}' 已存在")
    from dataclasses import fields
    c = Character(name=req.name, role=req.role or "配角", description=req.description,
                  background=req.background, goal=req.goal, relationships=req.relationships or [])
    fw.characters.append(c)
    _save(fw, sid)
    return {"status": "ok", "character": _char_dict(c)}


@router.put("/api/story/{sid}/characters/{name}")
def update_character(sid: str, name: str, req: CharUpdate):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    c = next((x for x in fw.characters if x.name == name), None)
    if not c: raise HTTPException(404, f"角色 '{name}' 不存在")
    if req.name: c.name = req.name
    if req.role: c.role = req.role
    if req.description: c.description = req.description
    if req.background: c.background = req.background
    if req.goal: c.goal = req.goal
    if req.relationship: c.relationship = req.relationship
    if req.relationships: c.relationships = req.relationships
    _save(fw, sid)
    return {"status": "ok", "character": _char_dict(c)}


@router.delete("/api/story/{sid}/characters/{name}")
def delete_character(sid: str, name: str):
    fw = _fw(sid)
    if not fw: raise HTTPException(404)
    fw.characters = [c for c in fw.characters if c.name != name]
    _save(fw, sid)
    return {"status": "ok"}
