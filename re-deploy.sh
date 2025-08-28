#!/bin/bash

echo "Starting complete deployment process..."

# Docker 이미지 빌드
echo "Step 1: Building Docker images..."

# Backend 이미지 빌드
echo "Building backend image..."
cd backend
docker build -t hyunjun-aks-demo-backend:latest .
if [ $? -ne 0 ]; then
    echo "❌ Backend image build failed! Exiting..."
    exit 1
fi
echo "✅ Backend image built successfully!"

# Frontend 이미지 빌드
echo "Building frontend image..."
cd ../frontend
docker build -t hyunjun-aks-demo-frontend:latest .
if [ $? -ne 0 ]; then
    echo "❌ Frontend image build failed! Exiting..."
    exit 1
fi
echo "✅ Frontend image built successfully!"

# 프로젝트 루트로 돌아가기
cd ..

echo ""
echo "Step 2: Checking existing infrastructure components..."

# MariaDB, Kafka, Redis가 이미 존재하는지 확인 (Pod 존재 여부로 확인)
MARIA_EXISTS=$(kubectl get pods -n hyunjun -l app.kubernetes.io/name=mariadb --no-headers 2>/dev/null | wc -l)
KAFKA_EXISTS=$(kubectl get pods -n hyunjun -l app.kubernetes.io/name=kafka --no-headers 2>/dev/null | wc -l)
REDIS_EXISTS=$(kubectl get pods -n hyunjun -l app.kubernetes.io/name=redis --no-headers 2>/dev/null | wc -l)

if [ $MARIA_EXISTS -gt 0 ] && [ $KAFKA_EXISTS -gt 0 ] && [ $REDIS_EXISTS -gt 0 ]; then
    echo "✅ MariaDB, Kafka, and Redis are already deployed. Skipping infrastructure deployment."
    echo "   - MariaDB: Already exists"
    echo "   - Kafka: Already exists" 
    echo "   - Redis: Already exists"
else
    echo "🔄 Some infrastructure components are missing. Deploying with Helm..."
    # Helm 차트로 MariaDB와 Kafka 배포
    ./helm-deploy.sh

    if [ $? -ne 0 ]; then
        echo "❌ Helm deployment failed! Exiting..."
        exit 1
    fi
fi

echo ""
echo "Step 3: Cleaning up existing application resources..."

# 기존 애플리케이션 리소스들 삭제
echo "Removing existing application resources..."

# HPA 삭제
echo "Removing HPA..."
kubectl delete hpa -n hyunjun --all --ignore-not-found=true

# Ingress 삭제
echo "Removing Ingress..."
kubectl delete ingress -n hyunjun --all --ignore-not-found=true

# Frontend 삭제
echo "Removing Frontend..."
kubectl delete -f k8s/frontend-deployment.yaml --ignore-not-found=true

# Backend 삭제
echo "Removing Backend..."
kubectl delete -f k8s/backend-deployment.yaml --ignore-not-found=true

# Database initialization job 삭제
echo "Removing database init job..."
kubectl delete -f k8s/db-init-job.yaml --ignore-not-found=true

# Secret 삭제
echo "Removing Secrets..."
kubectl delete -f k8s/backend-secret.yaml --ignore-not-found=true

# OpenTelemetry Collector 삭제
echo "Removing OpenTelemetry Collector..."
kubectl delete -f k8s/otel-collector-deployment.yaml --ignore-not-found=true
kubectl delete -f k8s/otel-collector-config.yaml --ignore-not-found=true

# ConfigMap 삭제
echo "Removing ConfigMap..."
kubectl delete -f k8s/configmap.yaml --ignore-not-found=true

# Storage 리소스 삭제 (애플리케이션 관련만)
echo "Removing application storage resources..."
kubectl delete -f k8s/storage.yaml --ignore-not-found=true

# 애플리케이션 관련 리소스만 선택적으로 삭제 (인프라 Pod는 건드리지 않음)
echo "Cleaning application resources (preserving infrastructure)..."
kubectl delete deployment backend -n hyunjun --ignore-not-found=true
kubectl delete deployment frontend -n hyunjun --ignore-not-found=true
kubectl delete deployment otel-collector -n hyunjun --ignore-not-found=true
kubectl delete service backend-service -n hyunjun --ignore-not-found=true
kubectl delete service frontend-service -n hyunjun --ignore-not-found=true
kubectl delete service otel-collector -n hyunjun --ignore-not-found=true
kubectl delete ingress -n hyunjun --all --ignore-not-found=true
kubectl delete hpa -n hyunjun --all --ignore-not-found=true
kubectl delete job db-init-job -n hyunjun --ignore-not-found=true

# PVC는 애플리케이션 관련만 삭제 (인프라 관련은 보존)
echo "Cleaning application PVCs (preserving infrastructure PVCs)..."
kubectl get pvc -n hyunjun -o name | grep -v -E "(mariadb|kafka|redis)" | xargs -r kubectl delete --ignore-not-found=true

echo "✅ Existing application resources cleaned up!"

# 잠깐 멈추고 사용자 확인
echo ""
echo "🔄 All existing application resources have been removed."
echo "   Infrastructure components (MariaDB, Kafka, Redis) are preserved."
echo ""
read -p "Press Enter to continue with fresh deployment, or Ctrl+C to abort..."

echo ""
echo "Step 4: Deploying application components..."

# Storage 리소스 배포
echo "Deploying storage resources..."
kubectl apply -f k8s/storage.yaml

# ConfigMap 배포
echo "Deploying ConfigMap..."
kubectl apply -f k8s/configmap.yaml

# Secret 배포
echo "Deploying Secrets..."
kubectl apply -f k8s/backend-secret.yaml

# OpenTelemetry Collector 배포
echo "Deploying OpenTelemetry Collector..."
kubectl apply -f k8s/otel-collector-config.yaml
kubectl apply -f k8s/otel-collector-deployment.yaml

# 데이터베이스 초기화
echo "Initializing database..."
kubectl apply -f k8s/db-init-job.yaml

# 백엔드 배포
echo "Deploying Backend..."
kubectl apply -f k8s/backend-deployment.yaml

# 프론트엔드 배포
echo "Deploying Frontend..."
kubectl apply -f k8s/frontend-deployment.yaml

# Ingress 배포
echo "Deploying Ingress..."
kubectl apply -f k8s/ingress.yaml

# HPA 배포
echo "Deploying HPA..."
kubectl apply -f k8s/hpa.yaml

echo ""
echo "✅ All deployments completed successfully!"
echo ""
echo "📊 Deployment Status:"
echo "--- Pods ---"
kubectl get pods -n hyunjun
echo ""
echo "--- Services ---"
kubectl get services -n hyunjun
echo ""
echo "--- Ingress ---"
kubectl get ingress -n hyunjun
echo ""
echo "--- HPA ---"
kubectl get hpa -n hyunjun
echo ""
echo "--- PVC ---"
kubectl get pvc -n hyunjun
echo ""
echo "🌐 Access your application:"
echo "  Frontend: http://localhost:30082"
echo "  Backend API: http://localhost:30082/api"
echo ""
echo "📝 Useful commands:"
echo "  kubectl get all -n hyunjun"
echo "  kubectl logs -l app=backend -n hyunjun"
echo "  kubectl logs -l app=frontend -n hyunjun"
echo "  kubectl get helmrelease -n hyunjun"