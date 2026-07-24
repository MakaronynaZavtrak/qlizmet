"""Согласование числительных с существительными по-русски.

«1 карточка», «2 карточки», «5 карточек» — без этого уведомления выглядели бы
машинно. Правило зависит от последней цифры, но числа 11–14 составляют
исключение: они всегда требуют форму множественного числа.
"""
from __future__ import annotations


def plural(count: int, one: str, few: str, many: str) -> str:
    """Выбрать форму слова для числа ``count``."""
    number = abs(count)
    if number % 100 in (11, 12, 13, 14):
        return many
    last = number % 10
    if last == 1:
        return one
    if last in (2, 3, 4):
        return few
    return many


def cards(count: int) -> str:
    """«карточка» / «карточки» / «карточек»."""
    return plural(count, "карточка", "карточки", "карточек")


def new_cards(count: int) -> str:
    """«новая» / «новые» / «новых» — прилагательное к «карточке»."""
    return plural(count, "новая", "новые", "новых")
