#!/bin/bash

echo "🔄 Restarting AKS Demo services..."

# Backend 재시작
echo "🔧 Restarting Backend..."
kubectl rollout restart deployment/backend -n hyunjun

# Frontend 재시작
echo "🎨 Restarting Frontend..."
kubectl rollout restart deployment/frontend -n hyunjun

# 재시작 상태 확인
echo "⏳ Waiting for rollouts to complete..."
kubectl rollout status deployment/backend -n hyunjun
kubectl rollout status deployment/frontend -n hyunjun

echo ""
echo "✅ Services restarted successfully!"
echo ""
echo "Current status:"
echo "--- Pods ---"
kubectl get pods -n hyunjun
echo ""
echo "--- Services ---"
kubectl get services -n hyunjun
