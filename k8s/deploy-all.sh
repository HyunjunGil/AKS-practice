#!/bin/bash

echo "🚀 Starting complete deployment of AKS Demo..."

# 네임스페이스 생성
echo "📦 Creating namespace..."
kubectl create namespace hyunjun --dry-run=client -o yaml | kubectl apply -f -

# Storage 리소스 배포
echo "💾 Deploying storage resources..."
kubectl apply -f storage.yaml

# ConfigMap 배포
echo "⚙️ Deploying ConfigMap..."
kubectl apply -f configmap.yaml

# Secret 배포
echo "🔐 Deploying Secrets..."
kubectl apply -f backend-secret.yaml

# 데이터베이스 초기화
echo "🗄️ Initializing database..."
kubectl apply -f db-init-job.yaml

# 백엔드 배포
echo "🔧 Deploying Backend..."
kubectl apply -f backend-deployment.yaml

# 프론트엔드 배포
echo "🎨 Deploying Frontend..."
kubectl apply -f frontend-deployment.yaml

# Ingress 배포
echo "🌐 Deploying Ingress..."
kubectl apply -f ingress.yaml

# HPA 배포
echo "📈 Deploying HPA..."
kubectl apply -f hpa.yaml

# 배포 상태 확인
echo "✅ Checking deployment status..."
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
echo "🎉 Complete deployment finished!"
echo ""
echo "Access your application:"
echo "  Frontend: http://localhost:30082"
echo "  Backend API: http://localhost:30082/api"
echo ""
echo "To check logs:"
echo "  kubectl logs -n hyunjun -l app=backend"
echo "  kubectl logs -n hyunjun -l app=frontend"
