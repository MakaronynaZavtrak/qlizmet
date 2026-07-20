"""Сериализация доменных объектов в примитивы, пригодные для хранения.

Слой хранения знает, как превратить ``CardFace`` и его блоки в JSON и обратно,
а также как записать даты. Доменные модели про JSON и БД не знают ничего — это
и есть смысл границы между слоями.
"""
from __future__ import annotations

import json
from datetime import datetime

from qlizmet.core.models import (
    CardFace,
    ContentBlock,
    ImageBlock,
    LatexBlock,
    TextBlock,
)


def block_to_dict(block: ContentBlock) -> dict:
    match block:
        case TextBlock(text=text):
            return {"type": "text", "text": text}
        case LatexBlock(latex=latex):
            return {"type": "latex", "latex": latex}
        case ImageBlock(path=path, alt=alt):
            return {"type": "image", "path": path, "alt": alt}
    raise TypeError(f"неизвестный тип блока: {block!r}")


def block_from_dict(data: dict) -> ContentBlock:
    kind = data.get("type")
    if kind == "text":
        return TextBlock(data["text"])
    if kind == "latex":
        return LatexBlock(data["latex"])
    if kind == "image":
        return ImageBlock(data["path"], data.get("alt", ""))
    raise ValueError(f"неизвестный тип блока в данных: {kind!r}")


def face_to_json(face: CardFace) -> str:
    return json.dumps([block_to_dict(b) for b in face.blocks], ensure_ascii=False)


def face_from_json(raw: str) -> CardFace:
    return CardFace(tuple(block_from_dict(d) for d in json.loads(raw)))


def tags_to_json(tags: tuple[str, ...]) -> str:
    return json.dumps(list(tags), ensure_ascii=False)


def tags_from_json(raw: str) -> tuple[str, ...]:
    return tuple(json.loads(raw))


def dt_to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def dt_from_iso(raw: str | None) -> datetime | None:
    return datetime.fromisoformat(raw) if raw is not None else None