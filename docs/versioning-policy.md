# 버전 관리 및 릴리스 정책 (prod)

## 배경

`eks-practice-devops-manifest`(GitOps 매니페스트 레포)에서 Argo CD Image Updater로 **prod** 배포 자동화를 구성하면서 채택한 정책이다. prod는 배포 빈도가 낮아 dev의 `latest` 고정 태그 + digest 감지 전략 대신, **SemVer 기반 명시적 버전 태그 전략**(`updateStrategy: semver`)을 사용한다.

이 레포는 원래 MSA라면 서비스별 독립 레포를 가져야 하지만 실습 편의상 모놀리식 레포 하나에 gateway/catalog/order를 함께 둔다. 그래서 "브랜치명 = 버전"처럼 레포 전체에 하나뿐인 브랜치로 서비스별 버전을 표현하는 방식은 쓸 수 없다. 대신 **서비스별로 `services/{service}/app/VERSION` 파일을 버전의 단일 진실 공급원(source of truth)으로 둔다.**

## SemVer 버전 관리 규칙

- 형식: `MAJOR.MINOR.PATCH` (예: `1.4.2`, 파일에는 `v` 접두사 없이 저장)
- 증가 기준
  - 새 기능 포함 → `MINOR` 증가
  - 버그 수정만 있음 → `PATCH`만 증가
  - 하위 호환이 깨짐 → `MAJOR` 증가
- 변경사항이 없으면 배포도, 버전 증가도 하지 않는다

## Hotfix 처리 규칙

- hotfix는 `main`(현재 운영 버전)에서 분기한다. 브랜치명은 자유롭게 짓되(예: `fix/catalog-stock-bug`), **PR에 반드시 해당 서비스의 `app/VERSION` 파일 PATCH 버전 증가를 포함**시킨다
- 수정 완료 후 `main`에 병합한다
- 배포는 아래 "prod 배포 트리거" 방식대로 수동 실행한다

## prod 배포 트리거

prod 배포는 **항상 수동(`workflow_dispatch`)으로만 실행**한다. PR merge에 의한 자동 배포는 없다.

- GitHub Actions에서 `prod-{gateway,catalog,order}` 워크플로우를 직접 실행하고, 빌드할 git `ref`(기본값 `main`)를 지정한다
- 워크플로우는 그 ref 시점의 `services/{service}/app/VERSION` 파일 내용을 읽어 그 값을 배포 버전으로 사용한다 — 버전 값을 사람이 직접 입력하지 않는다

## CI 이미지 태깅 규칙

- 워크플로우가 읽은 `VERSION` 파일 값 그대로(`v1.4.2` 형태로 접두사만 붙여서) ECR 이미지 태그로 사용해 push한다
- 한 번 push된 태그는 재사용하지 않는다 — `VERSION` 파일을 올리지 않고 재배포를 시도하면 같은 태그로 다시 push하게 되는데, prod ECR 리포지토리의 `imageTagMutability: IMMUTABLE` 정책(별도 인프라 작업 예정)이 이를 자동으로 거부한다

## dev 환경과의 차이

| 구분 | dev | prod |
|---|---|---|
| 트리거 | 수동(`workflow_dispatch`), 빌드할 ref(브랜치명) 입력 | 수동(`workflow_dispatch`), 빌드할 ref 입력 |
| 태그 전략 | `latest` + 입력한 ref명 2개 태그 | `VERSION` 파일 값 기반 SemVer 태그 (`v1.4.2` 등) |
| Image Updater 전략 | digest | semver |
| ECR 태그 불변성 | `MUTABLE` (같은 태그 재push 허용) | `IMMUTABLE` (재push 차단 예정) |
| 변경 감지 기준 | 태그는 그대로, digest 변경 감지 | 새 버전 태그 자체가 곧 배포 트리거 |

이 정책이 지켜지지 않으면(예: `VERSION` 파일 증가 없이 재배포) prod push가 `IMMUTABLE` 정책에 막혀 실패하거나, Image Updater의 semver 감시가 새 버전을 인식하지 못한다.
