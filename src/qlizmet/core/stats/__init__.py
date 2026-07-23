"""Агрегаты и статистика прогресса обучения."""
from qlizmet.core.stats.deck_stats import (
    MATURE_INTERVAL_DAYS,
    DeckStats,
    compute_deck_stats,
)

__all__ = ["DeckStats", "compute_deck_stats", "MATURE_INTERVAL_DAYS"]