"""Configuration backup export / import schemas."""
from typing import Any

from pydantic import BaseModel, Field


class BackupSectionOut(BaseModel):
    key: str
    label: str


class BackupExportRequest(BaseModel):
    sections: list[str] = Field(default_factory=list)


class BackupImportRequest(BaseModel):
    sections: list[str] = Field(default_factory=list)
    payload: dict[str, Any]
