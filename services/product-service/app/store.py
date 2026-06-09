import threading
from typing import Dict, Optional
from .models import Product


class ProductStore:
    def __init__(self):
        self._data: Dict[str, Product] = {}
        self._lock = threading.Lock()
        self._seed()

    def _seed(self):
        for p in [
            Product(id="prod-001", name="MacBook Pro", price=2000000.0, stock=10),
            Product(id="prod-002", name="iPhone 15", price=1200000.0, stock=25),
            Product(id="prod-003", name="AirPods Pro", price=350000.0, stock=50),
        ]:
            self._data[p.id] = p

    def get(self, product_id: str) -> Optional[Product]:
        with self._lock:
            return self._data.get(product_id)

    def list_all(self) -> list[Product]:
        with self._lock:
            return list(self._data.values())

    def create(self, product: Product) -> Product:
        with self._lock:
            self._data[product.id] = product
            return product

    def check_stock(self, product_id: str, quantity: int) -> bool:
        with self._lock:
            p = self._data.get(product_id)
            return p is not None and p.stock >= quantity


product_store = ProductStore()
