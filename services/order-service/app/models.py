import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    product_id: str
    quantity: int
    priority: Literal["normal", "urgent"] = "normal"


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    quantity: int
    status: str = "confirmed"
    priority: str = "normal"


class VersionedResponse(BaseModel):
    version: str
    service: str
    data: Any
