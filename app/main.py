from fastapi import FastAPI

from app.api.routes import health, news

app = FastAPI(title="AI News API")

app.include_router(news.router)
app.include_router(health.router)
