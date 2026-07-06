# 인프라 계정 구조

## AWS 계정 분리

이 프로젝트는 워크로드와 모니터링을 별도의 AWS 계정으로 분리한다.

| 계정 | Account ID | 역할 |
|---|---|---|
| workload | `657231015203` | 실제 애플리케이션(gateway/catalog/order)이 배포되는 계정. 워크로드 전용 EKS 클러스터가 존재하며, **ECR도 이 계정을 사용**한다 |
| monitoring | `157325288431` | LGTM(Loki-Grafana-Tempo-Mimir) 스택이 배포되는 계정. 모니터링 전용 EKS 클러스터가 존재한다 |

## ArgoCD 배치

- **최초 계획**: 워크로드 환경(계정)별 클러스터에 ArgoCD를 각각 설치
- **변경된 계획**: 클러스터마다 ArgoCD를 중복 운영하는 것이 비효율적이라고 판단하여, **monitoring 계정에 중앙 집중식 ArgoCD를 구성**하고 여기서 워크로드 클러스터들을 원격으로 관리하는 방식으로 전환

즉, monitoring 계정 = LGTM 스택 + 중앙 ArgoCD가 함께 위치하는 계정이다.

## AWS 인증 (SSO)

AWS 자격 증명은 IAM 사용자/액세스 키 방식에서 **AWS SSO**로 전환되었다. `~/.aws/config`에 아래 프로파일이 설정되어 있다.

| 프로파일 | Account ID | 용도 |
|---|---|---|
| `terraform-workload` | `657231015203` | 워크로드 계정 작업 (ECR 푸시 포함) |
| `terraform-monitoring` | `157325288431` | 모니터링 계정 작업 |

로그인 예시:
```bash
aws sso login --profile terraform-workload
```

이 레포에서 ECR에 이미지를 푸시할 때는 항상 `terraform-workload` 프로파일을 사용한다.
