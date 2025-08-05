from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Depends, status
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request

from .postgres.service import db
from .auth.service import is_valid_api_key, validate_api_key, NO_AUTH_DETAIL
from .schemas import ErrorResponse
from .projects.router import router as project_router
from .user.router import router as user_router
from .costs.router import router as costs_router
from fastapi import FastAPI


async def _raise_403_if_no_auth(request: Request, 
                                exc: StarletteHTTPException | Exception):
    '''Mask 404 and 500s in production if there's no valid auth'''
    api_key = request.headers.get("x-api-key")
    if await is_valid_api_key(api_key=api_key): 
        if isinstance(exc, StarletteHTTPException): # 404
            return JSONResponse( # return original exception
                status_code=exc.status_code,
                content={"msg":str(exc.detail)}
            )
        else: # assumed to be 500
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"msg": "Internal server error"}
            )
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"msg": NO_AUTH_DETAIL}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()

    yield

    await db.close_pool()


app = FastAPI(
    title="Cheqr API",
    version="0.1.0",
    lifespan=lifespan
    )


app.mount("/static", 
          StaticFiles(directory="src/project_context/static/assets"), 
          name="static")


@app.exception_handler(404) # Mask in production
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    return await _raise_403_if_no_auth(request=request, exc=exc)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return await _raise_403_if_no_auth(request=request, exc=exc)


api_router = APIRouter(
    default_response_class=JSONResponse,
    # Protect API routes with the validate_api_key dependency. App-level
    # routes (like /visualise) will not be affected and can remain public.
    dependencies=[Depends(validate_api_key)],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    })
api_router.include_router(router=user_router)
api_router.include_router(router=project_router)
api_router.include_router(router=costs_router)

app.include_router(router=api_router, prefix="/api/v1")
