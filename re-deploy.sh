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
echo "Step 2: Deploying MariaDB and Kafka with Helm..."
# Helm 차트로 MariaDB와 Kafka 배포
./helm-deploy.sh

if [ $? -ne 0 ]; then
    echo "❌ Helm deployment failed! Exiting..."
    exit 1
fi

echo ""
echo "Step 3: Deploying application components..."

# 기존 애플리케이션 배포
kubectl apply -f k8s/db-init-job.yaml
kubectl apply -f k8s/backend-secret.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

echo ""
echo "✅ All deployments completed successfully!"
echo ""
echo "To check application status:"
echo "  kubectl get all -n hyunjun"
echo ""
echo "To check application logs:"
echo "  kubectl logs -l app=backend -n hyunjun"
echo "  kubectl logs -l app=frontend -n hyunjun"
echo ""
echo "To check Docker images:"
echo "  docker images | grep hyunjun-aks-demo"