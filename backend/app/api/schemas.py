from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    service: str
    database: Literal["ok", "unavailable", "not_checked"]
