<#
.SYNOPSIS
    一键构建 FairyReport 官方网站（VitePress）并上传部署至腾讯云轻量应用服务器（默认 101.42.9.223）。

.EXAMPLE
    # 1. 仅在本地打包生成 site_dist.tar.gz（适合用宝塔面板 / 1Panel / 腾讯云 OrcaTerm 网页拖拽上传）
    powershell -NoProfile -File scripts\deploy_site.ps1 -BuildOnly

    # 2. 通过 SSH 一键编译并自动上传替换服务器站点目录（默认 root@101.42.9.223:/var/www/html）
    powershell -NoProfile -File scripts\deploy_site.ps1 -ServerIp 101.42.9.223 -User ubuntu -RemoteDir /var/www/fairyreport
#>
param(
    [string]$ServerIp = "101.42.9.223",
    [string]$User = "ubuntu",
    [string]$RemoteDir = "/var/www/html",
    [int]$Port = 22,
    [string]$IdentityFile = "",
    [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==> [1/3] 构建 VitePress 静态官网 (site/.vitepress/dist) ..." -ForegroundColor Cyan
if (-not (Test-Path "site\node_modules")) {
    npm --prefix site ci
    if ($LASTEXITCODE -ne 0) { throw "site 依赖安装失败" }
}
npm --prefix site run docs:build
if ($LASTEXITCODE -ne 0) { throw "VitePress 站点构建失败" }

$DistDir = Join-Path $RepoRoot "site\.vitepress\dist"
$ArchivePath = Join-Path $RepoRoot "dist\fairyreport-site-dist.tar.gz"
New-Item -ItemType Directory -Force -Path (Split-Path $ArchivePath) | Out-Null
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }

Write-Host "==> [2/3] 打包静态产物为 $ArchivePath ..." -ForegroundColor Cyan
tar -czf $ArchivePath -C $DistDir .
if ($LASTEXITCODE -ne 0) { throw "tar 打包失败" }

$SizeKB = [math]::Round((Get-Item $ArchivePath).Length / 1KB, 1)
Write-Host "    已生成压缩包: $ArchivePath ($SizeKB KB)" -ForegroundColor Green

if ($BuildOnly) {
    Write-Host "`n✅ 本地打包完成（-BuildOnly 模式）！你可以通过以下任意方式上传至 $ServerIp ：" -ForegroundColor Green
    Write-Host "   - 宝塔面板 / 1Panel：进入网站根目录，上传 $ArchivePath 并在线解压覆盖；"
    Write-Host "   - 腾讯云控制台 OrcaTerm：拖拽上传该压缩包后执行 tar -xzf fairyreport-site-dist.tar.gz -C <你的Nginx网站目录>"
    exit 0
}

Write-Host "==> [3/3] 通过 SCP/SSH 上传并部署至 ${User}@${ServerIp}:${RemoteDir} ..." -ForegroundColor Cyan
$SshOpts = @("-p", "$Port")
$ScpOpts = @("-P", "$Port")
if ($IdentityFile -and (Test-Path $IdentityFile)) {
    $SshOpts += @("-i", $IdentityFile)
    $ScpOpts += @("-i", $IdentityFile)
}

$RemoteTmp = "/tmp/fairyreport-site-dist.tar.gz"
& scp @ScpOpts $ArchivePath "${User}@${ServerIp}:${RemoteTmp}"
if ($LASTEXITCODE -ne 0) { throw "SCP 上传失败，请检查用户名（ubuntu / root / lighthouse）、SSH 端口或密钥" }

$RemoteCmd = "sudo mkdir -p '$RemoteDir' && sudo find '$RemoteDir' -mindepth 1 -maxdepth 1 -exec rm -rf {} + && sudo tar -xzf '$RemoteTmp' -C '$RemoteDir' && rm -f '$RemoteTmp'"
& ssh @SshOpts "${User}@${ServerIp}" $RemoteCmd
if ($LASTEXITCODE -ne 0) { throw "远端解压部署失败" }

Write-Host "`n✅ 部署成功！请访问 http://$ServerIp/ 验证最新官网内容。" -ForegroundColor Green
