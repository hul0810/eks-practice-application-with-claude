from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.b3 import B3MultiFormat
from fastapi import FastAPI


def init_telemetry(app: FastAPI, service_name: str, service_version: str, otlp_endpoint: str) -> None:
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "deployment.environment": "production",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    set_global_textmap(CompositePropagator([
        TraceContextTextMapPropagator(),
        B3MultiFormat(),
    ]))

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
