# K8s 배포 가이드

## 배포 순서

### 1. 데이터베이스 초기화 (필요시)
```bash
# 데이터베이스와 테이블이 없는 경우에만 실행
kubectl apply -f db-init-job.yaml

# Job 완료 확인
kubectl get jobs -n hyunjun
kubectl logs job/db-init-job -n hyunjun

# Job 완료 후 삭제 (선택사항)
kubectl delete job db-init-job -n hyunjun
```

### 2. 백엔드 서비스 배포
```bash
kubectl apply -f backend-deployment.yaml
kubectl get pods -n hyunjun -l app=backend
kubectl logs -l app=backend -n hyunjun
```

### 3. 프론트엔드 서비스 배포
```bash
kubectl apply -f frontend-deployment.yaml
kubectl get pods -n hyunjun -l app=frontend
kubectl logs -l app=frontend -n hyunjun
```

### 4. 서비스 상태 확인
```bash
# 모든 서비스 상태 확인
kubectl get all -n hyunjun

# 서비스 엔드포인트 확인
kubectl get endpoints -n hyunjun

# 프론트엔드 접근 (NodePort: 30082)
kubectl get nodes -o wide
# 위 명령어로 노드 IP 확인 후 http://<노드IP>:30082 접근
```

## 주의사항

1. **데이터베이스 초기화 Job**은 한 번만 실행하면 됩니다.
2. **backend-secrets**가 미리 생성되어 있어야 합니다.
3. **hyunjun-mariadb** 서비스가 실행 중이어야 합니다.
4. 프론트엔드는 NodePort 30082로 외부 접근이 가능합니다.

## 문제 해결

### 데이터베이스 연결 오류
```bash
# MariaDB Pod 상태 확인
kubectl get pods -n hyunjun | grep mariadb

# MariaDB 로그 확인
kubectl logs -n hyunjun <mariadb-pod-name>
```

### 백엔드 서비스 오류
```bash
# 백엔드 Pod 로그 확인
kubectl logs -l app=backend -n hyunjun

# 환경변수 확인
kubectl describe pod -l app=backend -n hyunjun
```

### 프론트엔드 서비스 오류
```bash
# 프론트엔드 Pod 로그 확인
kubectl logs -l app=frontend -n hyunjun

# nginx 설정 확인
kubectl exec -it <frontend-pod-name> -n hyunjun -- cat /etc/nginx/nginx.conf
```
