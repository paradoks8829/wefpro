from datetime import datetime

from pydantic import BaseModel, Field


class NewsBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_published: bool = True


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    is_published: bool | None = None


class NewsRead(NewsBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
