"""Рендер LaTeX-формул в картинку через matplotlib mathtext.

Полный TeX не требуется: mathtext — это встроенный в matplotlib парсер
математики, покрывающий подмножество LaTeX, которого карточкам хватает с
запасом. Результат кэшируется, потому что одна и та же формула перерисовывается
при каждом показе карточки.

Фон картинки прозрачный: формула ложится на карточку любой темы, а не тащит за
собой белый прямоугольник (на тёмной теме он торчал бы светлым пятном).
``math_to_image`` так не умеет — он всегда рисует на непрозрачном белом фоне,
поэтому рендерим через ``Figure`` с ``savefig(transparent=True)``.
"""
from __future__ import annotations

import io
from functools import lru_cache

import matplotlib

matplotlib.use("Agg")  # рендерим в картинку, окно matplotlib не нужно

from matplotlib.figure import Figure  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

DEFAULT_DPI = 120
DEFAULT_FONT_SIZE = 14


class LatexRenderError(ValueError):
    """Формулу не удалось разобрать."""


@lru_cache(maxsize=256)
def render_latex_png(
    latex: str,
    *,
    font_size: int = DEFAULT_FONT_SIZE,
    dpi: int = DEFAULT_DPI,
    color: str = "#1a1a1a",
) -> bytes:
    """Отрисовать формулу и вернуть PNG (с прозрачным фоном) в виде байтов.

    ``latex`` передаётся без ``$``-разделителей — они добавляются сами.
    Поднимает ``LatexRenderError``, если выражение некорректно.
    """
    figure = Figure()
    figure.patch.set_alpha(0.0)  # прозрачный фон самой фигуры
    try:
        figure.text(
            0.0,
            0.0,
            f"${latex}$",
            fontproperties=FontProperties(size=font_size),
            color=color,
        )
        buffer = io.BytesIO()
        figure.savefig(
            buffer,
            format="png",
            dpi=dpi,
            transparent=True,      # без белой подложки
            bbox_inches="tight",   # обрезаем по самой формуле
            pad_inches=0.05,
        )
    except Exception as exc:  # mathtext бросает ValueError и производные
        raise LatexRenderError(f"не удалось разобрать формулу: {latex!r}") from exc
    return buffer.getvalue()
