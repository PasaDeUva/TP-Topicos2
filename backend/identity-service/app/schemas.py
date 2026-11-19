from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

PASSWORD_MIN_LENGTH = 8


class Registration(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
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


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    expires_in: int


class RolesOut(BaseModel):
    roles: list[RoleOut]


class AccountRolesOut(RolesOut):
    account_id: UUID


class OrganizerStatusOut(BaseModel):
    account_id: UUID
    status: Literal["habilitado", "deshabilitado"]


class ErrorOut(BaseModel):
    code: str
    message: str
