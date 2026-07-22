"""Рендер LaTeX-формул в картинку через matplotlib mathtext.

Полный TeX не требуется: mathtext — это встроенный в matplotlib парсер
математики, покрывающий подмножество LaTeX, которого карточкам хватает с
запасом. Результат кэшируется, потому что одна и та же формула перерисовывается
при каждом показе карточки.
"""
from __future__ import annotations

import io
from functools import lru_cache

import matplotlib

matplotlib.use("Agg")  # рендерим в картинку, окно matplotlib не нужно

from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.mathtext import math_to_image  # noqa: E402

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
    """Отрисовать формулу и вернуть PNG в виде байтов.

    ``latex`` передаётся без ``$``-разделителей — они добавляются сами.
    Поднимает ``LatexRenderError``, если выражение некорректно.
    """
    buffer = io.BytesIO()
    try:
        math_to_image(
            f"${latex}$",
            buffer,
            prop=FontProperties(size=font_size),
            dpi=dpi,
            format="png",
            color=color,
        )
    except Exception as exc:  # mathtext бросает ValueError и производные
        raise LatexRenderError(f"не удалось разобрать формулу: {latex!r}") from exc
    return buffer.getvalue()