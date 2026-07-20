"""Расстояние Левенштейна — минимальное число правок (вставка, удаление, замена)
одного символа, превращающих одну строку в другую.
"""
from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            current.append(
                min(
                    previous[j] + 1,        # удаление
                    current[j - 1] + 1,     # вставка
                    previous[j - 1] + cost,  # замена
                )
            )
        previous = current
    return previous[-1]