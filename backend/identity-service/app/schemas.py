from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Registration(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["cliente", "organizador"]


class RoleOut(BaseModel):
    role: str
    status: str


class AccountOut(BaseModel):
    account_id: UUID
    email: str
    roles: list[RoleOut]


class Login(BaseModel):
    email: EmailStr
    password: str


class RoleRequest(BaseModel):
    role: Literal["cliente", "organizador"]


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class OrganizerStatus(BaseModel):
    status: Literal["habilitado", "deshabilitado"]
