import uuid
from typing import Any
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int


class Product(ProductCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class VersionedResponse(BaseModel):
    version: str
    service: str
    data: Any
