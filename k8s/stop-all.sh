#!/bin/bash

echo "🛑 Stopping and cleaning up AKS Demo deployment..."

# HPA 삭제
echo "📉 Removing HPA..."
kubectl delete hpa -n hyunjun --all --ignore-not-found=true

# Ingress 삭제
echo "🌐 Removing Ingress..."
kubectl delete ingress -n hyunjun --all --ignore-not-found=true

# Frontend 삭제
echo "🎨 Removing Frontend..."
kubectl delete -f frontend-deployment.yaml --ignore-not-found=true

# Backend 삭제
echo "🔧 Removing Backend..."
kubectl delete -f backend-deployment.yaml --ignore-not-found=true

# Database initialization job 삭제
echo "🗄️ Removing database init job..."
kubectl delete -f db-init-job.yaml --ignore-not-found=true

# Secret 삭제
echo "🔐 Removing Secrets..."
kubectl delete -f backend-secret.yaml --ignore-not-found=true

# ConfigMap 삭제
echo "⚙️ Removing ConfigMap..."
kubectl delete -f configmap.yaml --ignore-not-found=true

# Storage 리소스 삭제
echo "💾 Removing storage resources..."
kubectl delete -f storage.yaml --ignore-not-found=true

# Helm으로 배포된 서비스들 삭제
echo "📦 Removing Helm deployments..."
helm uninstall hyunjun-redis -n hyunjun --ignore-not-found=true
helm uninstall hyunjun-kafka -n hyunjun --ignore-not-found=true
helm uninstall hyunjun-mariadb -n hyunjun --ignore-not-found=true

# 네임스페이스 내 모든 리소스 강제 삭제 (선택사항)
echo "🧹 Force cleaning namespace..."
kubectl delete all --all -n hyunjun --ignore-not-found=true
kubectl delete pvc --all -n hyunjun --ignore-not-found=true
kubectl delete pv --all --ignore-not-found=true

# 네임스페이스 삭제 (선택사항)
read -p "Do you want to delete the namespace 'hyunjun' as well? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️ Deleting namespace..."
    kubectl delete namespace hyunjun --ignore-not-found=true
    echo "✅ Namespace deleted!"
else
    echo "ℹ️ Namespace 'hyunjun' kept for future use"
fi

echo ""
echo "🎉 Cleanup completed!"
echo ""
echo "Remaining resources:"
echo "--- Namespaces ---"
kubectl get namespaces | grep hyunjun || echo "No hyunjun namespace found"
echo ""
echo "--- PVs ---"
kubectl get pv | grep -E "(mariadb|kafka|redis)" || echo "No related PVs found"
echo ""
echo "--- Helm releases ---"
helm list -n hyunjun || echo "No Helm releases in hyunjun namespace"
