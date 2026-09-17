from fastapi import FastAPI

from app.api.routes import ask, health, news, search

app = FastAPI(title="AI News API")

app.include_router(news.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(health.router)
