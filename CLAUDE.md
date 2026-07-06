# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

EKS 실습용 MSA FastAPI 애플리케이션. **이 레포는 앱 코드와 Dockerfile만 관리한다.**

- **이 레포**: https://github.com/hul0810/eks-practice-application-with-claude
- K8s 매니페스트 → `eks-gitops-with-claude` 레포 (ArgoCD가 감시)
- EKS 인프라/ArgoCD 설치 → `eks-terraform-practice-with-claude` 레포

배포 흐름: 로컬에서 이미지 빌드 → ECR 수동 푸시 → gitops 레포 image tag 업데이트 → ArgoCD 자동 배포

### 계정 구조 (AWS)

workload 계정과 monitoring 계정으로 분리되어 있다. 자세한 내용은 [docs/infrastructure.md](docs/infrastructure.md) 참고.

- **workload 계정 (`657231015203`)**: 실제 애플리케이션이 배포되는 계정. 워크로드 전용 EKS 클러스터 존재. **ECR도 이 계정 사용**
- **monitoring 계정 (`157325288431`)**: LGTM 스택이 배포되는 계정. 모니터링 전용 EKS 클러스터 존재. 각 워크로드 클러스터별 ArgoCD 설치 계획에서 변경되어, **중앙 집중식 ArgoCD가 이 계정에 구성됨**

AWS 자격 증명은 SSO 방식이다. `~/.aws/config`의 `terraform-workload` 프로파일(계정 `657231015203`)을 사용해 ECR에 접근한다.

### 버전 관리 정책 (prod)

dev는 `latest` 고정 태그 + digest 감지 전략을, prod는 SemVer 명시적 버전 태그 전략(`v1.4.2` 등)을 사용한다. hotfix 브랜치 규칙, CI 이미지 태깅 규칙 등 자세한 내용은 [docs/versioning-policy.md](docs/versioning-policy.md) 참고.

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

**workload 계정(`657231015203`)의 ECR**을 사용한다. 서비스별로 별도 ECR 리포지토리를 사용한다 (단일 리포지토리에서 분리됨):

| 서비스 (폴더) | ECR 리포지토리 |
|---|---|
| `gateway` | `eks-practice-api-gateway-dev` |
| `catalog` | `eks-practice-catalog-dev` |
| `order` | `eks-practice-order-dev` |

```bash
ECR_HOST=657231015203.dkr.ecr.ap-northeast-2.amazonaws.com

# SSO 로그인 (세션 만료 시)
aws sso login --profile terraform-workload

# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 --profile terraform-workload \
  | docker login --username AWS --password-stdin $ECR_HOST

# 빌드 & 푸시
docker build -t $ECR_HOST/eks-practice-catalog-dev:latest services/catalog/
docker push $ECR_HOST/eks-practice-catalog-dev:latest
```

dev/prod 태깅 전략(브랜치명, `VERSION` 파일 기반 등)은 자동화된 GitHub Actions(`.github/workflows/`)에서 처리한다. 자세한 내용은 [docs/versioning-policy.md](docs/versioning-policy.md) 참고.

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
| `gateway` | 8000 | 외부 진입점. 자체 비즈니스 로직 없이 `/api/v1/products`, `/api/v1/orders` 요청을 각각 catalog, order로 프록시(`_proxy()`). 헤더 필터링 후 X-Request-ID 전파. `GZipMiddleware` 적용 |
| `catalog` | 8001 | 상품 도메인. 인메모리 `ProductStore`로 CRUD. 다른 서비스를 호출하지 않는 leaf 서비스이며, order의 재고 검증 요청을 받음 |
| `order` | 8002 | 주문 도메인. `POST /api/v1/orders` 시 `_verify_product()`로 catalog를 호출해 상품 존재/재고를 확인(없으면 404, 부족하면 400) 후 주문 생성. `/ready`에서도 catalog 연결 상태 확인. 주문 생성 성공 시 `events.py`가 SQS로 `order.created` 이벤트를 fire-and-forget으로 발행 (IRSA/Pod Identity 실습용) |

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

### 릴리즈 버전 (release_version)

서비스별 `app/VERSION` 파일(`0.1.0` 형태, `v` 접두사 없음)이 버전의 단일 진실 공급원이다. 이미지 빌드 시 Dockerfile의 `COPY app/ ./app/`로 자동 포함되며, `config.py`가 이 파일을 읽어 `settings.release_version`으로 노출한다. `/version` 엔드포인트를 포함해 모든 응답 body의 `version` 필드가 이 값을 사용한다.

`discount_rate`(catalog), `priority`(order), `GZipMiddleware`(gateway)는 예전엔 `APP_VERSION`(v1/v2) 환경변수로 켜고 껐지만, 지금은 버전 분기 없이 항상 적용되는 정상 동작이다. 카나리 배포를 실습하려면 서로 다른 커밋에서 빌드한, `release_version`이 다른 이미지 두 개를 나란히 배포한다 (런타임 토글이 아니라 실제 이미지가 다른 방식).

CI 워크플로우(`prod-{gateway,catalog,order}.yml`)도 이 파일을 읽어 이미지 태그를 결정한다. 자세한 내용은 [docs/versioning-policy.md](docs/versioning-policy.md) 참고.

### Observability (코드 레벨)

앱은 3가지만 담당하고, 수집/시각화 인프라는 gitops/terraform 레포에서 처리:

1. **메트릭**: `prometheus-fastapi-instrumentator` → `/metrics` 엔드포인트 (Prometheus 스크레이프)
2. **트레이싱**: OTel SDK → OTLP gRPC → `OTLP_ENDPOINT` 환경변수로 OTel Collector 주소 주입
3. **로그**: structlog JSON → stdout. `trace_id` 포함으로 Loki-Tempo 연계 가능

OTel Resource 태그에 `service.name`, `service.version` 포함 → Grafana Tempo에서 release_version별 필터 가능.

### 인메모리 저장소

`store.py`의 `ProductStore` / `OrderStore`는 `threading.Lock`으로 thread-safe하게 구현. `uvicorn --workers 1` 기준이므로 프로세스 간 공유 불필요. Pod 재시작 시 초기 seed 데이터로 리셋된다.

### 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_PORT` | 서비스별 상이 | uvicorn 포트 |
| `OTLP_ENDPOINT` | `http://localhost:4317` | OTel Collector gRPC 주소 |
| `CATALOG_URL` | `http://localhost:8001` | order, gateway에서 사용 |
| `ORDER_URL` | `http://localhost:8002` | gateway에서 사용 |
| `AWS_REGION` | `ap-northeast-2` | order에서 사용 (SQS) |
| `SQS_QUEUE_URL` | `""` (빈 문자열) | order에서 사용. 비어있으면 이벤트 발행을 건너뜀 (로컬 실행 시 기본값) |

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
