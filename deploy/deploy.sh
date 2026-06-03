#!/bin/bash
set -euo pipefail

REMOTE_HOST="192.168.139.219"
REMOTE_USER="${DEPLOY_USER:-root}"
REMOTE_DIR="/opt/wave"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================="
echo "  Wave 量化分析系统部署"
echo "  目标: ${REMOTE_USER}@${REMOTE_HOST}"
echo "========================================="

echo ""
echo "[1/5] 同步项目文件到远程服务器..."
rsync -avz --delete \
    --exclude='.git' \
    --exclude='build/' \
    --exclude='node_modules/' \
    --exclude='__pycache__/' \
    --exclude='.DS_Store' \
    --exclude='002484/' \
    --exclude='.claude/' \
    "$PROJECT_DIR/" \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

echo ""
echo "[2/5] 同步数据文件（增量）..."
rsync -avz \
    "$PROJECT_DIR/002484/" \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/002484/"

echo ""
echo "[3/5] 构建 Docker 镜像..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR}/deploy && docker compose build --no-cache"

echo ""
echo "[4/5] 启动服务..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR}/deploy && docker compose down 2>/dev/null; docker compose up -d"

echo ""
echo "[5/5] 等待服务就绪..."
for i in $(seq 1 30); do
    if ssh "${REMOTE_USER}@${REMOTE_HOST}" "curl -sf http://localhost:8000/api/health" > /dev/null 2>&1; then
        echo "  后端服务就绪!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  警告: 后端服务未在预期时间内就绪，请手动检查"
        ssh "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_DIR}/deploy && docker compose logs --tail=20"
        exit 1
    fi
    echo "  等待中... ($i/30)"
    sleep 5
done

echo ""
echo "========================================="
echo "  部署完成!"
echo "  前端: http://${REMOTE_HOST}"
echo "  后端 API: http://${REMOTE_HOST}:8000/api"
echo "========================================="
