"""
FairyReport Documentation Website Packaging & 101 Deployment Generator
Version: v1.6.2
"""

import os
import sys
import shutil
import zipfile
import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = REPO_ROOT / "site"
DIST_DIR = REPO_ROOT / "dist"
SITE_DIST_DIR = SITE_DIR / ".vitepress" / "dist"
OUTPUT_ZIP = DIST_DIR / "fairyreport-site-v1.6.2.zip"
PORTABLE_ZIP = DIST_DIR / "FairyReport-Local-v1.6.2-Windows-x64.zip"


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest().upper()


def build_site():
    print(f"[1/4] Building VitePress site in {SITE_DIR}...")
    subprocess.run(["npm", "run", "docs:build"], cwd=SITE_DIR, shell=True, check=True)
    if not (SITE_DIST_DIR / "index.html").exists():
        raise RuntimeError("Build failed: index.html not found in dist")
    print("  -> VitePress build completed successfully.")


def package_site():
    print(f"[2/4] Packaging site dist into {OUTPUT_ZIP}...")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in SITE_DIST_DIR.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(SITE_DIST_DIR)
                zf.write(file, arcname=str(rel_path))
    
    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"  -> Generated {OUTPUT_ZIP.name} ({size_mb:.2f} MB)")


def generate_deployment_assets():
    print("[3/4] Generating 101 server deployment scripts...")

    # Nginx config
    nginx_conf = """# FairyReport Official Portal & API Gateway Nginx Configuration
# Target Server: 101.42.9.223

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    client_max_body_size 500m;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 1024;

    server {
        listen 80;
        server_name 101.42.9.223;

        # 1. 账号认证与通用规程服务
        location /api/ {
            proxy_pass http://api:8010;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;
        }

        # 2. 客户端安装包/便携包下载通道
        location /downloads/ {
            alias /usr/share/nginx/downloads/;
            autoindex off;
            sendfile on;
            sendfile_max_chunk 1m;
            tcp_nopush on;
            tcp_nodelay on;
            keepalive_timeout 65;
            add_header Content-Disposition "attachment";
        }

        # 3. 官方文档宣传网站
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
            expires 1d;
            add_header Cache-Control "public, no-transform";
        }
    }
}
"""
    nginx_path = DIST_DIR / "fairyreport_101_nginx.conf"
    nginx_path.write_text(nginx_conf, encoding="utf-8")
    print(f"  -> Generated {nginx_path.name}")

    # Deploy shell script
    deploy_sh = """#!/bin/bash
# 101 Server Deployment Script for FairyReport
# Target: 101.42.9.223

set -e

echo "=== [1/4] Checking environment ==="
FRL_BACKEND="/opt/frl/backend"

if [ -d "$FRL_BACKEND" ]; then
    echo "Detected FairyReport Docker deployment at $FRL_BACKEND"
    cd "$FRL_BACKEND"

    echo "=== [2/4] Deploying documentation website ==="
    mkdir -p site downloads
    if [ -f "/tmp/fairyreport-site-v1.5.0.zip" ]; then
        rm -rf site/*
        unzip -q -o /tmp/fairyreport-site-v1.5.0.zip -d site/
        chmod -R 755 site/
        echo "Site static assets successfully unpacked into $FRL_BACKEND/site"
    else
        echo "Error: /tmp/fairyreport-site-v1.5.0.zip not found!"
        exit 1
    fi

    echo "=== [3/4] Checking client download binary ==="
    if [ -f "/tmp/FairyReport-Local-v1.5.0-Windows-x64.zip" ]; then
        cp /tmp/FairyReport-Local-v1.5.0-Windows-x64.zip downloads/
        chmod 644 downloads/*
        echo "Client portable binary deployed to $FRL_BACKEND/downloads/"
    else
        echo "Notice: /tmp/FairyReport-Local-v1.5.0-Windows-x64.zip omitted (skipped client upload)"
    fi

    echo "=== [4/4] Updating Nginx configuration & Reloading ==="
    if [ -f "/tmp/fairyreport_101_nginx.conf" ]; then
        cp /tmp/fairyreport_101_nginx.conf nginx/nginx.conf
    fi

    # Ensure docker-compose.yml has site & downloads volumes
    if ! grep -q "./site:/usr/share/nginx/html" docker-compose.yml; then
        echo "Updating docker-compose.yml volumes for nginx..."
        sed -i '/nginx.conf:ro/a \\      - ./site:/usr/share/nginx/html:ro\\n      - ./downloads:/usr/share/nginx/downloads:ro' docker-compose.yml
    fi

    docker compose up -d nginx
    echo "Docker Nginx reloaded successfully!"

else
    echo "Detected standard host Nginx environment"
    mkdir -p /var/www/fairyreport-site
    mkdir -p /var/www/fairyreport-downloads

    echo "=== [2/4] Deploying documentation website ==="
    if [ -f "/tmp/fairyreport-site-v1.5.0.zip" ]; then
        rm -rf /var/www/fairyreport-site/*
        unzip -q -o /tmp/fairyreport-site-v1.5.0.zip -d /var/www/fairyreport-site/
        chmod -R 755 /var/www/fairyreport-site/
        echo "Site files unpacked to /var/www/fairyreport-site"
    else
        echo "Error: /tmp/fairyreport-site-v1.5.0.zip not found!"
        exit 1
    fi

    echo "=== [3/4] Checking client download binary ==="
    if [ -f "/tmp/FairyReport-Local-v1.5.0-Windows-x64.zip" ]; then
        cp /tmp/FairyReport-Local-v1.5.0-Windows-x64.zip /var/www/fairyreport-downloads/
        chmod 644 /var/www/fairyreport-downloads/*
        echo "Binary deployed to /var/www/fairyreport-downloads/"
    else
        echo "Notice: /tmp/FairyReport-Local-v1.5.0-Windows-x64.zip omitted (skipped client upload)"
    fi

    echo "=== [4/4] Configuring Nginx ==="
    if [ -f "/tmp/fairyreport_101_nginx.conf" ]; then
        sed 's#/usr/share/nginx/html#/var/www/fairyreport-site#g; s#/usr/share/nginx/downloads#/var/www/fairyreport-downloads#g' /tmp/fairyreport_101_nginx.conf > /etc/nginx/conf.d/fairyreport.conf
        nginx -t
        systemctl reload nginx
        echo "Host Nginx reloaded successfully!"
    fi
fi

echo "=== Health check ==="
curl -s -I http://127.0.0.1/ | head -n 3
curl -s http://127.0.0.1/api/health || true
echo ""
echo "=== FairyReport v1.5.0 Deployed Successfully! ==="
echo "Access: http://101.42.9.223/"
"""
    deploy_path = DIST_DIR / "deploy_101.sh"
    deploy_path.write_text(deploy_sh, encoding="utf-8", newline="\n")
    print(f"  -> Generated {deploy_path.name}")


def summarize():
    print("[4/4] Verification Summary:")
    if PORTABLE_ZIP.exists():
        size_mb = PORTABLE_ZIP.stat().st_size / (1024 * 1024)
        sha256 = calculate_sha256(PORTABLE_ZIP)
        print(f"  - Client Portable Zip: {PORTABLE_ZIP.name} ({size_mb:.2f} MB)")
        print(f"    SHA-256: {sha256}")
    else:
        print(f"  - Warning: {PORTABLE_ZIP.name} not found")

    if OUTPUT_ZIP.exists():
        size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
        print(f"  - Website Bundle: {OUTPUT_ZIP.name} ({size_mb:.2f} MB)")

    print("\nTo deploy to 101 server:")
    print("  scp dist/fairyreport-site-v1.5.0.zip root@101.42.9.223:/tmp/")
    print("  scp dist/fairyreport_101_nginx.conf root@101.42.9.223:/tmp/")
    print("  scp dist/deploy_101.sh root@101.42.9.223:/tmp/")
    print("  # Optional: upload 370MB client binary")
    print("  scp dist/FairyReport-Local-v1.5.0-Windows-x64.zip root@101.42.9.223:/tmp/")
    print("  ssh root@101.42.9.223 'bash /tmp/deploy_101.sh'")


if __name__ == "__main__":
    build_site()
    package_site()
    generate_deployment_assets()
    summarize()
