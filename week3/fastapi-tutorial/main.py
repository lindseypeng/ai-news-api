from fastapi import FastAPI
from router import router as process_router

app = FastAPI()
app.include_router(process_router)
