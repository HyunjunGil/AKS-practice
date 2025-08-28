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

# Storage 리소스 삭제 (애플리케이션 관련만)
echo "💾 Removing application storage resources..."
kubectl delete -f storage.yaml --ignore-not-found=true

# 인프라 컴포넌트는 보존
echo "🔄 Preserving infrastructure components..."
echo "   - MariaDB: Keeping (data preservation)"
echo "   - Kafka: Keeping (message queue preservation)"
echo "   - Redis: Keeping (cache preservation)"

# 애플리케이션 관련 리소스만 강제 삭제
echo "🧹 Force cleaning application resources..."
kubectl delete all --all -n hyunjun --ignore-not-found=true

# PVC는 애플리케이션 관련만 삭제 (인프라 관련은 보존)
echo "💾 Cleaning application PVCs (preserving infrastructure PVCs)..."
kubectl get pvc -n hyunjun -o name | grep -v -E "(mariadb|kafka|redis)" | xargs -r kubectl delete --ignore-not-found=true

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
echo "--- Infrastructure PVs (preserved) ---"
kubectl get pv | grep -E "(mariadb|kafka|redis)" || echo "No infrastructure PVs found"
echo ""
echo "--- Helm releases (preserved) ---"
helm list -n hyunjun || echo "No Helm releases in hyunjun namespace"
echo ""
echo "💡 Infrastructure components (MariaDB, Kafka, Redis) have been preserved."
echo "   You can reuse them in future deployments without data loss."
