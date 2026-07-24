"""Тесты плана занятия — чистой логики без хранилища."""
from qlizmet.core.srs import DEFAULT_NEW_LIMIT, PendingCounts, ReviewPlan


def test_empty_plan() -> None:
    plan = ReviewPlan()
    assert plan.is_empty
    assert plan.total == 0
    assert plan.study_order() == ()


def test_counts() -> None:
    plan = ReviewPlan.of(due=["a", "b"], new=["c"])
    assert plan.due_count == 2
    assert plan.new_count == 1
    assert plan.total == 3
    assert not plan.is_empty


def test_due_cards_go_first() -> None:
    """Просроченные повторы важнее новых карточек: расписание держится на них."""
    plan = ReviewPlan.of(due=["повтор1", "повтор2"], new=["новая"])
    assert plan.study_order() == ("повтор1", "повтор2", "новая")


def test_new_cards_are_limited() -> None:
    plan = ReviewPlan.of(due=["п"], new=[f"н{i}" for i in range(50)])
    order = plan.study_order(new_limit=3)
    assert len(order) == 4
    assert order[0] == "п"


def test_zero_new_limit_keeps_only_reviews() -> None:
    plan = ReviewPlan.of(due=["п1", "п2"], new=["н1", "н2"])
    assert plan.study_order(new_limit=0) == ("п1", "п2")


def test_negative_limit_is_treated_as_zero() -> None:
    plan = ReviewPlan.of(due=["п"], new=["н"])
    assert plan.study_order(new_limit=-5) == ("п",)


def test_limit_larger_than_available_is_fine() -> None:
    plan = ReviewPlan.of(due=[], new=["н1", "н2"])
    assert plan.study_order(new_limit=100) == ("н1", "н2")


def test_default_limit_is_sane() -> None:
    assert 5 <= DEFAULT_NEW_LIMIT <= 50


def test_reviews_are_never_cut() -> None:
    """Ограничение касается только новых — повторы показываем все."""
    plan = ReviewPlan.of(due=[f"п{i}" for i in range(40)], new=[])
    assert len(plan.study_order(new_limit=1)) == 40


def test_pending_counts() -> None:
    counts = PendingCounts(due=3, new=2)
    assert counts.total == 5
    assert not counts.is_empty
    assert PendingCounts().is_empty
