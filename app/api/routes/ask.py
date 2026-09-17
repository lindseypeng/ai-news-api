from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.answer_agent import answer_from_context
from app.agents.embedding_agent import create_embedding
from app.database.connection import get_db
from app.database.repository import search_similar_chunks
from app.schemas.news import AnswerCitation, AskRequest, AskResponse

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("/", response_model=AskResponse)
def ask_news(request: AskRequest, db: Session = Depends(get_db)):
    """Retrieve relevant news chunks and answer from that evidence only."""

    query_embedding = create_embedding(request.question)
    results = search_similar_chunks(db, query_embedding, limit=request.limit)
    if not results:
        return AskResponse(
            question=request.question,
            answer="Not enough information",
            supported=False,
            citations=[],
        )
    grounded = answer_from_context(
        request.question,
        [chunk.content for chunk, _news_item, _distance in results],
    )
    citations = [
        AnswerCitation(
            news_item_id=news_item.id,
            source_id=news_item.source_id,
            title=news_item.title,
            url=news_item.url,
            chunk_content=chunk.content,
        )
        for chunk, news_item, _distance in results
    ]
    return AskResponse(
        question=request.question,
        answer=grounded.answer,
        supported=grounded.supported,
        citations=citations,
    )
