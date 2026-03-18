#!/bin/bash
# ============================================================
# 工科导航 - 一键部署脚本
# 使用方法: bash deploy.sh your-domain.com
# ============================================================

set -e

DOMAIN=${1:?"用法: bash deploy.sh <你的域名>"}
PROJECT_DIR="/opt/skill-agent"
REPO_URL="你的Git仓库地址"  # ← 改成你的仓库

echo "=========================================="
echo "  工科导航 部署脚本"
echo "  域名: $DOMAIN"
echo "=========================================="

# ---- 1. 安装基础软件 ----
echo "[1/6] 安装依赖..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose nginx certbot python3-certbot-nginx git

systemctl enable docker
systemctl start docker

# ---- 2. 拉取代码 ----
echo "[2/6] 拉取代码..."
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" && git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi
cd "$PROJECT_DIR/agent"

# ---- 3. 配置环境变量 ----
echo "[3/6] 配置环境变量..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# Claude API Key（必填，否则AI对话功能不可用）
ANTHROPIC_API_KEY=your-api-key-here

# 安全密钥（必须修改！）
SECRET_KEY=请替换为随机字符串

# 调试模式
DEBUG=false
ENVEOF
    echo "⚠️  请编辑 .env 文件填入 ANTHROPIC_API_KEY"
    echo "   vim $PROJECT_DIR/agent/.env"
fi

# ---- 4. Docker 构建启动 ----
echo "[4/6] 构建 Docker 镜像..."
docker-compose up -d --build

echo "等待服务启动..."
sleep 5
curl -sf http://localhost:8000/health > /dev/null && echo "服务启动成功" || echo "⚠️ 服务启动失败，请检查日志: docker-compose logs"

# ---- 5. 配置 Nginx ----
echo "[5/6] 配置 Nginx..."
cat > /etc/nginx/sites-available/skill-agent << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/skill-agent /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ---- 6. 申请 SSL 证书 ----
echo "[6/6] 申请 SSL 证书..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" || {
    echo "⚠️  SSL 证书申请失败，请手动执行："
    echo "   certbot --nginx -d $DOMAIN"
}

echo ""
echo "=========================================="
echo "  部署完成！"
echo ""
echo "  网页版:  https://$DOMAIN"
echo "  API文档: https://$DOMAIN/docs"
echo "  健康检查: https://$DOMAIN/health"
echo ""
echo "  ⚠️ 别忘了编辑 .env 填入 API Key："
echo "     vim $PROJECT_DIR/agent/.env"
echo "     docker-compose restart"
echo "=========================================="
