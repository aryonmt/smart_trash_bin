from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Schema representing a login request."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema representing the successful authentication payload containing JWT."""

    access_token: str
    token_type: str
    role: str
    username: str
