from contextlib import asynccontextmanager
import uvicorn

from fastapi import FastAPI
from common.config import settings
from common.db_helper import db_helper
from auth import router as auth_router
from profile import router as profile_router
from admin.views import router as admin_router
from s3.views import router as s3_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await db_helper.dispose()


main_app = FastAPI(lifespan=lifespan)

main_app.include_router(profile_router)
main_app.include_router(auth_router)
main_app.include_router(admin_router)
main_app.include_router(s3_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:main_app",
        port=settings.run.port,
        host=settings.run.host,
        reload=True,
    )
