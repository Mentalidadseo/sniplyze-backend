from fastapi import FastAPI
from app.routers import ia_results

app = FastAPI()

app.include_router(ia_results.router)