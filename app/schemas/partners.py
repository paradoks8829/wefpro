from pydantic import BaseModel, Field


class PartnerBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    logo_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    sort_order: int = 0
    is_published: bool = True


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    logo_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    sort_order: int | None = None
    is_published: bool | None = None


class PartnerRead(PartnerBase):
    id: int

    model_config = {"from_attributes": True}
