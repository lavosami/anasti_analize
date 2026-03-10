from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from app.api.routes.type_parameters import router as type_parameters_router
from app.api.routes.analysis import router as analysis_router
from app.messaging.rpc import analysis_rpc_server


@asynccontextmanager
async def lifespan(_: FastAPI):
    await analysis_rpc_server.start()
    try:
        yield
    finally:
        await analysis_rpc_server.close()

app = FastAPI(title="Anasti Analize Service", version="1.0.0", lifespan=lifespan)

app.include_router(type_parameters_router)
app.include_router(analysis_router)

@app.get("/")
async def root():
    return {"message": "Data Analize Service is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
