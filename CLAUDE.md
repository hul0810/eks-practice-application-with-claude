# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

EKS 실습용 MSA FastAPI 애플리케이션. **이 레포는 앱 코드와 Dockerfile만 관리한다.**

- **이 레포**: https://github.com/hul0810/eks-practice-application-with-claude
- K8s 매니페스트 → `eks-gitops-with-claude` 레포 (ArgoCD가 감시)
- EKS 인프라/ArgoCD 설치 → `eks-terraform-practice-with-claude` 레포

배포 흐름: 로컬에서 이미지 빌드 → ECR 수동 푸시 → gitops 레포 image tag 업데이트 → ArgoCD 자동 배포

## 개발 명령어

### 로컬 전체 스택 실행
```bash
docker compose up --build        # 빌드 + 실행
docker compose up -d             # 백그라운드 실행
docker compose logs -f           # 로그 스트림
docker compose down              # 종료
```

### 단일 서비스 재빌드
```bash
docker compose build --no-cache catalog
docker compose up -d catalog
```

### ECR 배포 (수동)

서비스별로 별도 ECR 리포지토리를 사용한다 (단일 리포지토리에서 분리됨):

| 서비스 (폴더) | ECR 리포지토리 |
|---|---|
| `gateway` | `eks-practice-api-gateway-develop` |
| `catalog` | `eks-practice-catalog-develop` |
| `order` | `eks-practice-order-develop` |

```bash
ECR_HOST=891396992584.dkr.ecr.ap-northeast-2.amazonaws.com

# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 \
  | docker login --username AWS --password-stdin $ECR_HOST

# 빌드 & 푸시 (버전을 태그로 사용)
docker build -t $ECR_HOST/eks-practice-catalog-develop:v1 services/catalog/
docker push $ECR_HOST/eks-practice-catalog-develop:v1

# v2 예시
docker build --build-arg APP_VERSION=v2 -t $ECR_HOST/eks-practice-catalog-develop:v2 services/catalog/
docker push $ECR_HOST/eks-practice-catalog-develop:v2
```

이미지 태그 규칙: 리포지토리는 `eks-practice-{service}-develop`, 태그는 버전 (`v1`, `v2`)

### 로컬 API 테스트
```bash
curl http://localhost:8000/api/v1/products          # gateway 경유
curl http://localhost:8001/api/v1/products          # catalog 직접
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": "prod-001", "quantity": 1}'
curl http://localhost:8001/metrics                  # Prometheus 메트릭
curl http://localhost:8001/health
```

## 아키텍처

### 서비스 구성
```
Client → gateway:8000 → catalog:8001
                      → order:8002 → catalog:8001 (재고 검증)
```

| 서비스 | 포트 | 역할 |
|---|---|---|
| `gateway` | 8000 | 외부 진입점. 자체 비즈니스 로직 없이 `/api/v1/products`, `/api/v1/orders` 요청을 각각 catalog, order로 프록시(`_proxy()`). 헤더 필터링 후 X-Request-ID 전파. v2에서 `GZipMiddleware` 추가 |
| `catalog` | 8001 | 상품 도메인. 인메모리 `ProductStore`로 CRUD. 다른 서비스를 호출하지 않는 leaf 서비스이며, order의 재고 검증 요청을 받음 |
| `order` | 8002 | 주문 도메인. `POST /api/v1/orders` 시 `_verify_product()`로 catalog를 호출해 상품 존재/재고를 확인(없으면 404, 부족하면 400) 후 주문 생성. `/ready`에서도 catalog 연결 상태 확인 |

서비스 간 통신: `httpx` AsyncClient. `HTTPXClientInstrumentor`가 모든 httpx 요청에 OTel trace context(`traceparent`)와 X-Request-ID(correlation_id)를 자동 전파하므로 명시적 헤더 삽입 불필요. 주문 생성 흐름(client → gateway → order → catalog)은 하나의 trace로 연결되어 분산 트레이싱 검증에 사용된다.

### 공통 모듈 패턴 (3개 서비스 동일 구조)

각 서비스는 동일한 5개 공통 모듈을 가진다:

| 파일 | 역할 |
|---|---|
| `config.py` | pydantic-settings 기반 환경변수. `settings` 싱글턴 노출 |
| `telemetry.py` | OTel SDK 초기화. `FastAPIInstrumentor` + `HTTPXClientInstrumentor` 자동 계측 |
| `logging_config.py` | structlog JSON 포맷. 모든 로그에 `trace_id`/`span_id` 자동 삽입 |
| `middleware.py` | `CorrelationIdMiddleware` (X-Request-ID 생성/전파) + `AccessLogMiddleware` |
| `routes/health.py` | `/health` (liveness), `/ready` (readiness) |

`main.py`에서 미들웨어 등록 순서: `add_middleware(AccessLog)` → `add_middleware(CorrelationId)`. Starlette에서 나중에 추가된 미들웨어가 먼저 실행되므로 CorrelationId가 요청 최외부에서 동작한다.

### v1/v2 버전 전략

환경변수 `APP_VERSION`으로 분기. 이미지 태그 `:v1` / `:v2` 로 분리하되 동일 코드베이스 사용.

- 응답 body에 항상 `{"version": "v1", "service": "...", "data": {...}}` 구조 반환
- catalog v2: `data`에 `discount_rate: 0.1` 추가
- order v2: `data`에 `priority` 필드 포함 (v1은 제거)
- gateway v2: `GZipMiddleware` 추가

### Observability (코드 레벨)

앱은 3가지만 담당하고, 수집/시각화 인프라는 gitops/terraform 레포에서 처리:

1. **메트릭**: `prometheus-fastapi-instrumentator` → `/metrics` 엔드포인트 (Prometheus 스크레이프)
2. **트레이싱**: OTel SDK → OTLP gRPC → `OTLP_ENDPOINT` 환경변수로 OTel Collector 주소 주입
3. **로그**: structlog JSON → stdout. `trace_id` 포함으로 Loki-Tempo 연계 가능

OTel Resource 태그에 `service.name`, `service.version` 포함 → Grafana Tempo에서 v1/v2 필터 가능.

### 인메모리 저장소

`store.py`의 `ProductStore` / `OrderStore`는 `threading.Lock`으로 thread-safe하게 구현. `uvicorn --workers 1` 기준이므로 프로세스 간 공유 불필요. Pod 재시작 시 초기 seed 데이터로 리셋된다.

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_VERSION` | `v1` | v1/v2 분기 |
| `APP_PORT` | 서비스별 상이 | uvicorn 포트 |
| `OTLP_ENDPOINT` | `http://localhost:4317` | OTel Collector gRPC 주소 |
| `CATALOG_URL` | `http://localhost:8001` | order, gateway에서 사용 |
| `ORDER_URL` | `http://localhost:8002` | gateway에서 사용 |

## OTel 패키지 버전 주의사항

setuptools 72+ 에서 `pkg_resources`가 분리되었기 때문에 반드시 다음 버전 세트를 사용해야 한다. 0.46b0 이하는 `ModuleNotFoundError: No module named 'pkg_resources'` 오류 발생.

```
opentelemetry-api==1.42.1
opentelemetry-sdk==1.42.1
opentelemetry-exporter-otlp-proto-grpc==1.42.1
opentelemetry-instrumentation-fastapi==0.63b1
opentelemetry-instrumentation-httpx==0.63b1
opentelemetry-propagator-b3==1.42.1
```
