"""Подключение к SQLite и инициализация схемы.

``connect`` открывает соединение, включает внешние ключи (по умолчанию в SQLite
они выключены!) и создаёт таблицы, если их ещё нет. Путь ``":memory:"`` даёт базу
в оперативной памяти — на ней и гоняются тесты.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS decks (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    modified_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    id           TEXT PRIMARY KEY,
    deck_id      TEXT NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    front        TEXT NOT NULL,
    back         TEXT NOT NULL,
    tags         TEXT NOT NULL DEFAULT '[]',
    created_at   TEXT NOT NULL,
    modified_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards(deck_id, position);

CREATE TABLE IF NOT EXISTS card_progress (
    card_id           TEXT PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
    ease              REAL NOT NULL,
    interval_days     INTEGER NOT NULL,
    repetitions       INTEGER NOT NULL,
    lapses            INTEGER NOT NULL,
    due_at            TEXT,
    last_reviewed_at  TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id      TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    reviewed_at  TEXT NOT NULL,
    mode         TEXT NOT NULL,
    is_correct   INTEGER NOT NULL,
    quality      INTEGER,
    response_ms  INTEGER,
    user_answer  TEXT
);
CREATE INDEX IF NOT EXISTS idx_reviews_card ON reviews(card_id, reviewed_at);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Открыть соединение с включёнными внешними ключами и готовой схемой."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn