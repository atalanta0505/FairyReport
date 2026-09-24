"""
FairyReport Documentation Website Packaging & 101 Deployment Generator
Version: v1.5.0
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
OUTPUT_ZIP = DIST_DIR / "fairyreport-site-v1.5.0.zip"
PORTABLE_ZIP = DIST_DIR / "FairyReport-Local-v1.5.0-Windows-x64.zip"


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
    nginx_conf = """# FairyReport Official Portal & Download Center Nginx Configuration
# Target Server: 101.42.9.223

server {
    listen 80;
    server_name 101.42.9.223;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 1024;

    # Site Static Files
    location / {
        root /var/www/fairyreport-site;
        index index.html;
        try_files $uri $uri/ /index.html;
        expires 1d;
        add_header Cache-Control "public, no-transform";
    }

    # High-Speed Download Route for Portable Packages
    location /downloads/ {
        alias /var/www/fairyreport-downloads/;
        autoindex off;
        sendfile on;
        sendfile_max_chunk 1m;
        tcp_nopush on;
        tcp_nodelay on;
        keepalive_timeout 65;
        add_header Content-Disposition "attachment";
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

echo "=== [1/4] Preparing directories ==="
mkdir -p /var/www/fairyreport-site
mkdir -p /var/www/fairyreport-downloads

echo "=== [2/4] Deploying documentation website ==="
if [ -f "/tmp/fairyreport-site-v1.5.0.zip" ]; then
    rm -rf /var/www/fairyreport-site/*
    unzip -q /tmp/fairyreport-site-v1.5.0.zip -d /var/www/fairyreport-site/
    chmod -R 755 /var/www/fairyreport-site/
    echo "Site files unpacked to /var/www/fairyreport-site"
else
    echo "Warning: /tmp/fairyreport-site-v1.5.0.zip not found"
fi

echo "=== [3/4] Deploying client download binaries ==="
if [ -f "/tmp/FairyReport-Local-v1.5.0-Windows-x64.zip" ]; then
    cp /tmp/FairyReport-Local-v1.5.0-Windows-x64.zip /var/www/fairyreport-downloads/
    chmod 644 /var/www/fairyreport-downloads/*
    echo "Binary deployed to /var/www/fairyreport-downloads/"
fi

echo "=== [4/4] Configuring Nginx ==="
if [ -f "/tmp/fairyreport_101_nginx.conf" ]; then
    cp /tmp/fairyreport_101_nginx.conf /etc/nginx/conf.d/fairyreport.conf
    nginx -t
    systemctl reload nginx
    echo "Nginx reloaded successfully!"
fi

echo "=== FairyReport v1.5.0 Deployed Successfully! ==="
echo "Access: http://101.42.9.223/"
echo "Download: http://101.42.9.223/downloads/FairyReport-Local-v1.5.0-Windows-x64.zip"
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
