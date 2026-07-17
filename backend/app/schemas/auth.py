from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    is_active: bool


class ChangeUsernameRequest(BaseModel):
    current_password: str
    new_username: str = Field(..., min_length=3, max_length=64)

    @field_validator("new_username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("用户名不能为空")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if not all(ch in allowed for ch in username):
            raise ValueError("用户名仅支持字母、数字、下划线和连字符")
        return username


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)
