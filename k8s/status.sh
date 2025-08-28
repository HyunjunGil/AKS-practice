#!/bin/bash

echo "📊 AKS Demo Status Check"
echo "========================"

# 네임스페이스 확인
echo "📦 Namespace Status:"
kubectl get namespace hyunjun 2>/dev/null || echo "❌ Namespace 'hyunjun' not found"

echo ""

# Pods 상태
echo "🐳 Pods Status:"
kubectl get pods -n hyunjun 2>/dev/null || echo "❌ No pods found in namespace 'hyunjun'"

echo ""

# Services 상태
echo "🔌 Services Status:"
kubectl get services -n hyunjun 2>/dev/null || echo "❌ No services found in namespace 'hyunjun'"

echo ""

# Ingress 상태
echo "🌐 Ingress Status:"
kubectl get ingress -n hyunjun 2>/dev/null || echo "❌ No ingress found in namespace 'hyunjun'"

echo ""

# HPA 상태
echo "📈 HPA Status:"
kubectl get hpa -n hyunjun 2>/dev/null || echo "❌ No HPA found in namespace 'hyunjun'"

echo ""

# PVC 상태
echo "💾 PVC Status:"
kubectl get pvc -n hyunjun 2>/dev/null || echo "❌ No PVC found in namespace 'hyunjun'"

echo ""

# Helm releases 상태
echo "📦 Helm Releases:"
helm list -n hyunjun 2>/dev/null || echo "❌ No Helm releases found in namespace 'hyunjun'"

echo ""

# 로그 확인 (최근 5줄)
echo "📝 Recent Logs:"
echo "Backend logs (last 5 lines):"
kubectl logs -n hyunjun -l app=backend --tail=5 2>/dev/null || echo "❌ No backend logs found"

echo ""
echo "Frontend logs (last 5 lines):"
kubectl logs -n hyunjun -l app=frontend --tail=5 2>/dev/null || echo "❌ No frontend logs found"

echo ""
echo "========================"
echo "✅ Status check completed!"
