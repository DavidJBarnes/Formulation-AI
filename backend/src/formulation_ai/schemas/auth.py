import uuid

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    # The "email" column doubles as a login identifier — accept bare usernames
    # too, not just RFC-valid email addresses.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    abilities: list[str] = []


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
