"""Прикладной слой: сервисы и use-cases, оркестрируют ядро и хранилище."""
from qlizmet.app.study_service import StudyService, grade_from_verdict

__all__ = ["StudyService", "grade_from_verdict"]