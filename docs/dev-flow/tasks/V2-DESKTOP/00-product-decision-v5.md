# 产品决定记录 — V2 桌面正式版 v5（发行与签名定案）

- 状态：已确认
- 记录日期：2026-08-20

## 1. 本轮决定

| # | 决定 | 依据 |
|---|---|---|
| D21 | T10 发行形态 = **Portable zip 优先**（解压即用 + 首运"解除锁定"一行说明）；MSI 移入正式发布包 | 产品负责人提议参照 goose 发行方式；Planner 评估 portable 可省去 MSI 工艺 |
| D22 | 代码签名证书于**正式发布前**购买，补齐零弹窗体验；MVP 接受首运一次 SmartScreen + 解锁操作 | 本机实测：Goose.exe/goose.exe 签名 Valid（LF Open Source, LLC）、OpenCode.exe（Anomaly）、codex.exe（OpenAI）均签名；**无弹窗体验来自签名而非 portable**；三家均只签主程序、附带第三方工具裸奔（uv.exe/rg.exe 未签名） |

## 2. 对路线图的影响

- V2-T10 估算下调（无需 MSI 工艺）；MSI + 签名 + 自动更新与"更大服务器、收费"同列正式版包议题
- 其余维持 v4 路线图
