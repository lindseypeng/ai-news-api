from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agents.embedding_agent import create_embedding
from app.database.connection import get_db
from app.database.repository import search_similar_chunks
from app.schemas.news import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[SearchResult])
def search_news(
    q: str = Query(..., min_length=1),
    limit: int = 5,
    db: Session = Depends(get_db),
):
    query_embedding = create_embedding(q)
    results = search_similar_chunks(db, query_embedding, limit=limit)

    return [
        SearchResult(
            news_item_id=news_item.id,
            title=news_item.title,
            url=news_item.url,
            chunk_content=chunk.content,
            similarity=-distance,
        )
        for chunk, news_item, distance in results
    ]
