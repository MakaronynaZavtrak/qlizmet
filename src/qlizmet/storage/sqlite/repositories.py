"""Репозитории на SQLite: наборы (с карточками) и прогресс (с историей ответов)."""
from __future__ import annotations

import sqlite3

from qlizmet.core.models import Card, CardProgress, Deck, ReviewRecord
from qlizmet.storage.serialization import (
    dt_from_iso,
    dt_to_iso,
    face_from_json,
    face_to_json,
    tags_from_json,
    tags_to_json,
)


class SqliteDeckRepository:
    """Хранит наборы вместе с их карточками, сохраняя порядок карточек."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, deck: Deck) -> None:
        """Сохранить набор (upsert).

        Карточки обновляются по ``id``, а не стираются и создаются заново —
        поэтому прогресс и история ответов по уцелевшим карточкам не теряются.
        Удаляются только те карточки набора, которых в нём больше нет.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO decks(id, title, description, created_at, modified_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                modified_at=excluded.modified_at
            """,
            (
                deck.id,
                deck.title,
                deck.description,
                dt_to_iso(deck.created_at),
                dt_to_iso(deck.modified_at),
            ),
        )

        kept_ids: list[str] = []
        for position, card in enumerate(deck.cards):
            kept_ids.append(card.id)
            cur.execute(
                """
                INSERT INTO cards(id, deck_id, position, front, back, tags,
                                  created_at, modified_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    deck_id=excluded.deck_id,
                    position=excluded.position,
                    front=excluded.front,
                    back=excluded.back,
                    tags=excluded.tags,
                    modified_at=excluded.modified_at
                """,
                (
                    card.id,
                    deck.id,
                    position,
                    face_to_json(card.front),
                    face_to_json(card.back),
                    tags_to_json(card.tags),
                    dt_to_iso(card.created_at),
                    dt_to_iso(card.modified_at),
                ),
            )

        if kept_ids:
            placeholders = ",".join("?" * len(kept_ids))
            cur.execute(
                f"DELETE FROM cards WHERE deck_id=? AND id NOT IN ({placeholders})",
                (deck.id, *kept_ids),
            )
        else:
            cur.execute("DELETE FROM cards WHERE deck_id=?", (deck.id,))

        self.conn.commit()

    def get(self, deck_id: str) -> Deck | None:
        row = self.conn.execute(
            "SELECT * FROM decks WHERE id=?", (deck_id,)
        ).fetchone()
        if row is None:
            return None

        cards = [
            Card(
                front=face_from_json(c["front"]),
                back=face_from_json(c["back"]),
                id=c["id"],
                tags=tags_from_json(c["tags"]),
                created_at=dt_from_iso(c["created_at"]),
                modified_at=dt_from_iso(c["modified_at"]),
            )
            for c in self.conn.execute(
                "SELECT * FROM cards WHERE deck_id=? ORDER BY position", (deck_id,)
            )
        ]
        return Deck(
            title=row["title"],
            id=row["id"],
            description=row["description"],
            cards=cards,
            created_at=dt_from_iso(row["created_at"]),
            modified_at=dt_from_iso(row["modified_at"]),
        )

    def list_deck_ids(self) -> list[str]:
        return [r["id"] for r in self.conn.execute("SELECT id FROM decks ORDER BY title")]

    def delete(self, deck_id: str) -> bool:
        """Удалить набор. Карточки, прогресс и история уходят каскадом."""
        cur = self.conn.execute("DELETE FROM decks WHERE id=?", (deck_id,))
        self.conn.commit()
        return cur.rowcount > 0


class SqliteProgressRepository:
    """Хранит SRS-состояние карточек и историю ответов."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save(self, progress: CardProgress) -> None:
        self.conn.execute(
            """
            INSERT INTO card_progress(card_id, ease, interval_days, repetitions,
                                      lapses, due_at, last_reviewed_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(card_id) DO UPDATE SET
                ease=excluded.ease,
                interval_days=excluded.interval_days,
                repetitions=excluded.repetitions,
                lapses=excluded.lapses,
                due_at=excluded.due_at,
                last_reviewed_at=excluded.last_reviewed_at
            """,
            (
                progress.card_id,
                progress.ease,
                progress.interval_days,
                progress.repetitions,
                progress.lapses,
                dt_to_iso(progress.due_at),
                dt_to_iso(progress.last_reviewed_at),
            ),
        )
        self.conn.commit()

    def get(self, card_id: str) -> CardProgress | None:
        row = self.conn.execute(
            "SELECT * FROM card_progress WHERE card_id=?", (card_id,)
        ).fetchone()
        if row is None:
            return None
        return CardProgress(
            card_id=row["card_id"],
            ease=row["ease"],
            interval_days=row["interval_days"],
            repetitions=row["repetitions"],
            lapses=row["lapses"],
            due_at=dt_from_iso(row["due_at"]),
            last_reviewed_at=dt_from_iso(row["last_reviewed_at"]),
        )

    def add_review(self, record: ReviewRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO reviews(card_id, reviewed_at, mode, is_correct,
                                quality, response_ms, user_answer)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.card_id,
                dt_to_iso(record.reviewed_at),
                record.mode,
                int(record.is_correct),
                record.quality,
                record.response_ms,
                record.user_answer,
            ),
        )
        self.conn.commit()

    def reviews_for(self, card_id: str) -> list[ReviewRecord]:
        rows = self.conn.execute(
            "SELECT * FROM reviews WHERE card_id=? ORDER BY reviewed_at, id",
            (card_id,),
        )
        return [
            ReviewRecord(
                card_id=r["card_id"],
                reviewed_at=dt_from_iso(r["reviewed_at"]),
                mode=r["mode"],
                is_correct=bool(r["is_correct"]),
                quality=r["quality"],
                response_ms=r["response_ms"],
                user_answer=r["user_answer"],
            )
            for r in rows
        ]