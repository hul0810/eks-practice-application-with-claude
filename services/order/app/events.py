import json

import boto3
import structlog

from .config import settings

logger = structlog.get_logger()

_sqs_client = None


def _get_client():
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs", region_name=settings.aws_region)
    return _sqs_client


def publish_order_created(order: dict) -> None:
    if not settings.sqs_queue_url:
        return

    try:
        _get_client().send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps({"event": "order.created", "order": order}),
        )
    except Exception:
        # 이벤트 발행 실패로 주문 자체를 롤백하지 않는다 (fire-and-forget)
        logger.warning("sqs_publish_failed", order_id=order.get("id"))
