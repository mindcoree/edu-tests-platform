from fastapi import APIRouter
from .teacher.views import router as teacher_router
from .student.views import router as student_router

router = APIRouter(prefix="/profile")

router.include_router(teacher_router)
router.include_router(student_router)
