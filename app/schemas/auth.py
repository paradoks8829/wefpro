from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LibrarianCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LibrarianRead(BaseModel):
    id: int
    username: str
    is_active: bool

    model_config = {"from_attributes": True}
