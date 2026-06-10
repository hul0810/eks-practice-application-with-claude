import threading
from typing import Dict, Optional
from .models import Order


class OrderStore:
    def __init__(self):
        self._data: Dict[str, Order] = {}
        self._lock = threading.Lock()

    def get(self, order_id: str) -> Optional[Order]:
        with self._lock:
            return self._data.get(order_id)

    def list_all(self) -> list[Order]:
        with self._lock:
            return list(self._data.values())

    def create(self, order: Order) -> Order:
        with self._lock:
            self._data[order.id] = order
            return order


order_store = OrderStore()
