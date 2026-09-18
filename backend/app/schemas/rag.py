from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str]
