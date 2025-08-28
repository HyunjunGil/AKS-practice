#!/bin/bash

# Helm 배포 스크립트 - OCI 레지스트리 방식 사용

echo "Starting Helm deployment for MariaDB, Kafka, and Redis..."

# 네임스페이스 생성 (이미 존재하면 무시)
kubectl create namespace hyunjun --dry-run=client -o yaml | kubectl apply -f -

# MariaDB 배포
echo "Deploying MariaDB..."
helm upgrade --install hyunjun-mariadb oci://registry-1.docker.io/bitnamicharts/mariadb \
  --namespace hyunjun \
  --values charts/mariadb/values.yaml \
  --wait \
  --timeout=10m

if [ $? -eq 0 ]; then
    echo "✅ MariaDB deployed successfully!"
else
    echo "❌ MariaDB deployment failed!"
    exit 1
fi

# Kafka 배포
echo "Deploying Kafka..."
helm upgrade --install hyunjun-kafka oci://registry-1.docker.io/bitnamicharts/kafka \
  --namespace hyunjun \
  --values charts/kafka/values.yaml \
  --wait \
  --timeout=10m

if [ $? -eq 0 ]; then
    echo "✅ Kafka deployed successfully!"
else
    echo "❌ Kafka deployment failed!"
    echo "Checking Kafka status..."
    kubectl get pods -n hyunjun | grep kafka
    kubectl get events -n hyunjun --sort-by='.lastTimestamp' | tail -10
    exit 1
fi

# Redis 배포
echo "Deploying Redis..."
helm upgrade --install hyunjun-redis oci://registry-1.docker.io/bitnamicharts/redis \
  --namespace hyunjun \
  --values charts/redis/values.yaml \
  --wait \
  --timeout=10m

if [ $? -eq 0 ]; then
    echo "✅ Redis deployed successfully!"
else
    echo "❌ Redis deployment failed!"
    exit 1
fi

# 배포 상태 확인
echo "Checking deployment status..."
echo "--- Pods ---"
kubectl get pods -n hyunjun
echo ""
echo "--- Services ---"
kubectl get services -n hyunjun
echo ""
echo "--- Persistent Volumes ---"
kubectl get pvc -n hyunjun

echo ""
echo "🎉 Helm deployment completed successfully!"
echo ""
echo "To check logs:"
echo "  kubectl logs -n hyunjun -l app.kubernetes.io/instance=hyunjun-mariadb"
echo "  kubectl logs -n hyunjun -l app.kubernetes.io/instance=hyunjun-kafka"
echo "  kubectl logs -n hyunjun -l app.kubernetes.io/instance=hyunjun-redis"
