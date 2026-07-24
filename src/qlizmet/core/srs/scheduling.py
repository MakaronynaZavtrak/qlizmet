"""План занятия: что из набора стоит показать сегодня.

Разделяем два непохожих случая. **Просроченные** — карточки, которые уже
изучались и которым по расписанию SM-2 пора на повтор; откладывать их вредно,
именно на них держится вся система интервалов. **Новые** — те, которых человек
ещё не видел; их можно спокойно отложить на завтра.

Отсюда и порядок: сначала повторы, потом новые, причём новых не больше
``new_limit`` за раз — иначе набор из пятисот свежих карточек обрушится на
человека целиком и отобьёт желание заниматься.

Модуль чистый: сюда приходят готовые списки идентификаторов, а откуда они
взялись — забота хранилища.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: Сколько новых карточек показывать за одно занятие по умолчанию.
DEFAULT_NEW_LIMIT = 20


@dataclass(frozen=True, slots=True)
class ReviewPlan:
    """Что набор предлагает изучить прямо сейчас."""

    due_ids: tuple[str, ...] = ()
    new_ids: tuple[str, ...] = ()

    @classmethod
    def of(cls, due: Iterable[str], new: Iterable[str]) -> "ReviewPlan":
        return cls(tuple(due), tuple(new))

    @property
    def due_count(self) -> int:
        return len(self.due_ids)

    @property
    def new_count(self) -> int:
        return len(self.new_ids)

    @property
    def total(self) -> int:
        """Сколько карточек ждёт внимания — и повторов, и новых."""
        return self.due_count + self.new_count

    @property
    def is_empty(self) -> bool:
        return self.total == 0

    def study_order(self, *, new_limit: int = DEFAULT_NEW_LIMIT) -> tuple[str, ...]:
        """Очередь на занятие: сначала все повторы, затем новые до предела.

        ``new_limit`` меньше нуля трактуется как ноль: «сегодня только повторы».
        """
        limit = max(new_limit, 0)
        return self.due_ids + self.new_ids[:limit]


@dataclass(frozen=True, slots=True)
class PendingCounts:
    """Сколько карточек ждёт в наборе — для значков в списке наборов."""

    due: int = 0
    new: int = 0

    @property
    def total(self) -> int:
        return self.due + self.new

    @property
    def is_empty(self) -> bool:
        return self.total == 0
