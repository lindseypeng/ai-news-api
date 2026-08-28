from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repository import get_all_news_items, get_news_item
from app.schemas.news import NewsItem

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/", response_model=list[NewsItem])
def list_news(db: Session = Depends(get_db)):
    rows = get_all_news_items(db)
    return [NewsItem.model_validate(row) for row in rows]


@router.get("/{item_id}", response_model=NewsItem)
def get_news(item_id: int, db: Session = Depends(get_db)):
    row = get_news_item(db, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="News item not found")
    return NewsItem.model_validate(row)
