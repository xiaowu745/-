#!/bin/bash
# ============================================================
# 荆工智匠 - 一键部署脚本（兼容 Ubuntu / CentOS / 阿里云）
# 使用方法: bash deploy.sh <你的域名> <Git仓库地址>
# ============================================================

set -e

DOMAIN=${1:?"用法: bash deploy.sh <域名> <Git仓库地址>"}
REPO_URL=${2:?"用法: bash deploy.sh <域名> <Git仓库地址>"}
PROJECT_DIR="/opt/skill-agent"

echo "=========================================="
echo "  荆工智匠 一键部署"
echo "  域名:   $DOMAIN"
echo "  仓库:   $REPO_URL"
echo "=========================================="

# ---- 检测系统 ----
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "检测到系统: $OS"

# ---- 1. 安装基础软件 ----
echo ""
echo "[1/7] 安装 Docker + Nginx + Git..."

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    apt-get update -qq
    apt-get install -y -qq docker.io docker-compose nginx certbot python3-certbot-nginx git curl
elif [ "$OS" = "centos" ] || [ "$OS" = "alinux" ] || [ "$OS" = "aliyun" ]; then
    yum install -y yum-utils
    # Docker
    yum install -y docker
    # docker-compose
    if ! command -v docker-compose &> /dev/null; then
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    yum install -y nginx certbot python3-certbot-nginx git curl
else
    echo "⚠️  未识别的系统($OS)，尝试 apt-get..."
    apt-get update -qq && apt-get install -y -qq docker.io docker-compose nginx certbot python3-certbot-nginx git curl
fi

systemctl enable docker
systemctl start docker
echo "Docker 版本: $(docker --version)"

# ---- 2. 拉取代码 ----
echo ""
echo "[2/7] 拉取项目代码..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi
cd "$PROJECT_DIR/agent"
echo "代码目录: $(pwd)"

# ---- 3. 配置环境变量 ----
echo ""
echo "[3/7] 配置环境变量..."
if [ ! -f .env ]; then
    SECRET=$(openssl rand -hex 32)
    cat > .env << ENVEOF
# Claude API Key（必填，否则AI对话功能不可用）
ANTHROPIC_API_KEY=your-api-key-here

# 安全密钥（已自动生成）
SECRET_KEY=$SECRET

# 域名
ALLOWED_DOMAIN=$DOMAIN

# 生产模式
DEBUG=false

# ==== 私域转化 / 线索管理 ====
# 管理后台登录密码（访问 https://${DOMAIN}/admin），请务必改掉
ADMIN_PASSWORD=change-this-admin-password

# 企业微信群机器人 webhook，有新线索会自动推送通知
# 获取方法：企微群聊 → 群设置 → 群机器人 → 添加机器人 → 复制 webhook
# 留空则不推送
WECOM_WEBHOOK_URL=
LEAD_NOTIFY_ENABLED=true

# ==== 微信小程序配置 ====
# 在微信公众平台注册小程序后获取
WECHAT_APP_ID=
WECHAT_APP_SECRET=
ENVEOF
    echo "✅ .env 已创建（SECRET_KEY 已自动生成）"
    echo "⚠️  请稍后编辑 .env 填入 ANTHROPIC_API_KEY"
else
    echo "✅ .env 已存在，跳过"
fi

# ---- 4. 安全组检查提醒 ----
echo ""
echo "[4/7] 安全组检查..."
echo "📌 请确认阿里云安全组已开放以下端口："
echo "   - 80  (HTTP)"
echo "   - 443 (HTTPS)"
echo ""

# ---- 5. Docker 构建启动 ----
echo "[5/7] 构建并启动 Docker 容器..."
docker-compose down 2>/dev/null || true
docker-compose up -d --build

echo "等待服务启动..."
for i in 1 2 3 4 5; do
    sleep 2
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 服务启动成功"
        break
    fi
    if [ "$i" = "5" ]; then
        echo "⚠️  服务启动超时，查看日志: docker-compose logs"
    fi
done

# ---- 6. 配置 Nginx ----
echo ""
echo "[6/7] 配置 Nginx 反向代理..."

# 兼容 CentOS（没有 sites-available）和 Ubuntu
if [ -d /etc/nginx/sites-available ]; then
    NGINX_CONF="/etc/nginx/sites-available/skill-agent"
    NGINX_LINK="/etc/nginx/sites-enabled/skill-agent"
else
    NGINX_CONF="/etc/nginx/conf.d/skill-agent.conf"
    NGINX_LINK=""
fi

cat > "$NGINX_CONF" << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # 超时设置（AI对话可能较慢）
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /static/ {
        proxy_pass http://127.0.0.1:8000/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINXEOF

if [ -n "$NGINX_LINK" ]; then
    ln -sf "$NGINX_CONF" "$NGINX_LINK"
    rm -f /etc/nginx/sites-enabled/default
fi

nginx -t && systemctl reload nginx
echo "✅ Nginx 配置完成"

# ---- 7. 申请 SSL 证书 ----
echo ""
echo "[7/7] 申请 Let's Encrypt SSL 证书..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" 2>/dev/null || {
    echo ""
    echo "⚠️  自动申请失败（可能域名DNS还没生效）"
    echo "   请确认域名 A 记录指向本机IP后，手动执行："
    echo "   certbot --nginx -d $DOMAIN"
}

# ---- 完成 ----
echo ""
echo "=========================================="
echo "  🎉 部署完成！"
echo ""
echo "  网页版:   https://$DOMAIN"
echo "  API文档:  https://$DOMAIN/docs"
echo "  健康检查: https://$DOMAIN/health"
echo ""
echo "  📝 下一步："
echo "  1. 编辑 .env 填入 ANTHROPIC_API_KEY："
echo "     vim $PROJECT_DIR/agent/.env"
echo "  2. 重启使 API Key 生效："
echo "     cd $PROJECT_DIR/agent && docker-compose restart"
echo "  3. 在阿里云安全组开放 80 和 443 端口"
echo "  4. 确认域名 A 记录指向本服务器IP"
echo ""
echo "  常用命令："
echo "  查看日志:  cd $PROJECT_DIR/agent && docker-compose logs -f"
echo "  重启服务:  cd $PROJECT_DIR/agent && docker-compose restart"
echo "  停止服务:  cd $PROJECT_DIR/agent && docker-compose stop"
echo "=========================================="
