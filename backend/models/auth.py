from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    id: str
    email: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=8, max_length=128)