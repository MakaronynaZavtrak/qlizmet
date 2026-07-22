"""Тесты игровых экранов «Подбор пар» и «Гравитация».

Реальный таймер здесь не запускается (``autostart=False``): экраны вынесли шаг
времени в публичный ``tick()``, поэтому тесты шагают по времени вручную и
проходят мгновенно, ничего не дожидаясь.
"""
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from qlizmet.core.models import Card, CardFace, LatexBlock  # noqa: E402
from qlizmet.core.study import MatchOutcome  # noqa: E402
from qlizmet.ui.views.gravity_view import GravityView, steps_for_level  # noqa: E402
from qlizmet.ui.views.match_view import MatchView  # noqa: E402


def _card(front: str, back: str) -> Card:
    return Card.create(CardFace.from_text(front), CardFace.from_text(back))


CARDS = [
    _card("Франция", "Париж"),
    _card("Италия", "Рим"),
    _card("Испания", "Мадрид"),
]
ANSWERS = {c.front.plain_text: c.back.plain_text for c in CARDS}


# --- «Подбор пар» ---


@pytest.fixture
def match(qt_host) -> MatchView:
    view = MatchView(parent=qt_host)
    view.start(CARDS, autostart=False)
    return view


def _pair_of(view: MatchView, card: Card) -> tuple[str, str]:
    return f"{card.id}:front", f"{card.id}:back"


def test_match_board_has_two_tiles_per_card(match) -> None:
    assert len(match.tile_ids()) == 2 * len(CARDS)


def test_match_first_click_selects(match) -> None:
    front, _ = _pair_of(match, CARDS[0])
    assert match.select_tile(front) is MatchOutcome.FIRST_PICK
    assert match.selected_tile() == front


def test_match_correct_pair_disappears(match) -> None:
    front, back = _pair_of(match, CARDS[0])
    match.select_tile(front)
    assert match.select_tile(back) is MatchOutcome.MATCH
    assert len(match.tile_ids()) == 2 * len(CARDS) - 2
    assert match.selected_tile() is None


def test_match_mismatch_keeps_tiles(match) -> None:
    front, _ = _pair_of(match, CARDS[0])
    _, other_back = _pair_of(match, CARDS[1])
    match.select_tile(front)
    assert match.select_tile(other_back) is MatchOutcome.MISMATCH
    assert len(match.tile_ids()) == 2 * len(CARDS)


def test_match_deselect_by_second_click(match) -> None:
    front, _ = _pair_of(match, CARDS[0])
    match.select_tile(front)
    assert match.select_tile(front) is MatchOutcome.DESELECT
    assert match.selected_tile() is None


def test_match_clock_advances_on_tick(match) -> None:
    assert match.elapsed_seconds == 0
    for _ in range(10):
        match.tick()
    assert match.elapsed_seconds == pytest.approx(1.0)
    assert "1.0" in match.clock_text()


def test_match_clock_stops_after_finish(match) -> None:
    for card in CARDS:
        front, back = _pair_of(match, card)
        match.select_tile(front)
        match.select_tile(back)
    assert match.is_finished

    before = match.elapsed_seconds
    match.tick()
    assert match.elapsed_seconds == before  # секундомер больше не идёт


def test_match_summary_reports_time_and_mistakes(match) -> None:
    front, _ = _pair_of(match, CARDS[0])
    _, other_back = _pair_of(match, CARDS[1])
    match.select_tile(front)
    match.select_tile(other_back)  # промах

    for card in CARDS:
        f, b = _pair_of(match, card)
        match.select_tile(f)
        match.select_tile(b)

    assert match.is_finished
    assert "промахов: 1" in match.summary_text()


def test_match_ignores_clicks_after_finish(match) -> None:
    for card in CARDS:
        front, back = _pair_of(match, card)
        match.select_tile(front)
        match.select_tile(back)
    assert match.select_tile(f"{CARDS[0].id}:front") is None


def test_match_pairs_limit(qt_host) -> None:
    view = MatchView(parent=qt_host)
    view.start(CARDS, pairs=2, autostart=False)
    assert len(view.tile_ids()) == 4


def test_match_tiles_show_formula_marks(qt_host) -> None:
    """Плитка с формулой не должна оказаться пустой кнопкой."""
    cards = [
        Card.create(CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),))),
        _card("Италия", "Рим"),
    ]
    view = MatchView(parent=qt_host)
    view.start(cards, autostart=False)
    texts = [
        view.findChild(object, f"tile_{i}").text() for i in range(len(view.tile_ids()))
    ]
    assert all(text.strip() for text in texts)


# --- «Гравитация» ---


@pytest.fixture
def gravity(qt_host) -> GravityView:
    view = GravityView(parent=qt_host)
    view.start(CARDS, lives=3, autostart=False)
    return view


def _current_answer(view: GravityView) -> str:
    prompt = view.findChild(object, "termFace").face.plain_text
    return ANSWERS[prompt]


def _type(view: GravityView, text: str) -> None:
    view.findChild(object, "answerEdit").setText(text)


def test_gravity_starts_with_full_lives(gravity) -> None:
    assert gravity.lives == 3
    assert gravity.score == 0
    assert gravity.level == 1
    assert "♥♥♥" in gravity.status_text()


def test_gravity_correct_answer_scores(gravity) -> None:
    _type(gravity, _current_answer(gravity))
    gravity.submit()
    assert gravity.score == 100
    assert gravity.lives == 3
    assert gravity.flash_text() == "Верно!"


def test_gravity_wrong_answer_costs_life(gravity) -> None:
    _type(gravity, "заведомо неверно")
    gravity.submit()
    assert gravity.lives == 2
    assert "Неверно" in gravity.flash_text()


def test_gravity_term_falls_with_ticks(gravity) -> None:
    assert gravity.fall_step == 0
    gravity.tick()
    gravity.tick()
    assert gravity.fall_step == 2


def test_gravity_reaching_bottom_costs_life(gravity) -> None:
    for _ in range(steps_for_level(1)):
        gravity.tick()
    assert gravity.lives == 2
    assert gravity.fall_step == 0  # следующий термин начинает сверху
    assert "Не успел" in gravity.flash_text()


def test_gravity_answer_resets_fall(gravity) -> None:
    gravity.tick()
    gravity.tick()
    _type(gravity, _current_answer(gravity))
    gravity.submit()
    assert gravity.fall_step == 0


def test_gravity_game_over_after_three_misses(gravity) -> None:
    for _ in range(3):
        _type(gravity, "мимо")
        gravity.submit()
    assert gravity.is_over
    assert gravity.lives == 0
    assert "Игра окончена" in gravity.summary_text()


def test_gravity_ignores_input_after_game_over(gravity) -> None:
    for _ in range(3):
        _type(gravity, "мимо")
        gravity.submit()
    score_before = gravity.score
    gravity.tick()
    _type(gravity, "что-нибудь")
    gravity.submit()
    assert gravity.score == score_before


def test_gravity_finishes_when_terms_run_out(gravity) -> None:
    while not gravity.is_over:
        _type(gravity, _current_answer(gravity))
        gravity.submit()
    assert gravity.is_over
    assert gravity.lives == 3  # ни одной ошибки
    assert "верно: 3" in gravity.summary_text()


def test_gravity_speeds_up_with_level() -> None:
    assert steps_for_level(2) < steps_for_level(1)
    assert steps_for_level(99) >= 5  # но не быстрее предела


def test_gravity_skips_non_text_answers(qt_host) -> None:
    latex = Card.create(
        CardFace.from_text("производная sin x"), CardFace((LatexBlock(r"\cos x"),))
    )
    view = GravityView(parent=qt_host)
    view.start([CARDS[0], latex], autostart=False)
    # печатать формулу нельзя, поэтому в игру попала одна карточка
    _type(view, ANSWERS["Франция"])
    view.submit()
    assert view.is_over