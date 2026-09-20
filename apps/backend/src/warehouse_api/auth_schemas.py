from uuid import UUID

from pydantic import BaseModel, Field

from warehouse_api.auth import Role


class LoginRequest(BaseModel):
    login_identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class ActorResponse(BaseModel):
    id: UUID
    login_identifier: str
    role: Role
