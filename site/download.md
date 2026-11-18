# 下载

**FairyReport** 是一款完全开源免费的智能报告编制工具。Windows 版本提供完全自包含的 **绿色免安装便携版**，无需管理员权限、无需配置 Python 环境、无需注册登录，解压后双击 `FairyReport.exe` 即可使用。

---

## 💻 客户端下载（v1.6.5）

我们提供 **百度网盘** 与 **夸克网盘** 两条分流通道，两个网盘内的压缩包 **100% 一致**，请任选您习惯的网盘下载：

<div style="margin: 28px 0;">
  <DownloadCards />
</div>

| 渠道 | 链接 | 提取码 / 说明 | 包体大小 |
| :--- | :--- | :--- | :--- |
| **百度网盘** | [下载](https://pan.baidu.com/s/1XG5DlAl6zpCWEoWfXmtvTg?pwd=i56v) | 提取码：`i56v` | `396 MB` |
| **夸克网盘** | [下载](https://pan.quark.cn/s/893e062482e6?pwd=DymL) | 提取码：`DymL` | `396 MB` |
| **GitHub 开源仓库** | [访问仓库源码](https://github.com/atalanta0505/FairyReport) | 查看前后端完整源码、提交 Issue 或自行编译 | 源码仓库 |

> [!TIP]
> **绿色免安装便携版包含什么？**
> - **零环境依赖**：压缩包内已打包 Tauri 2 桌面客户端、独立 Python 引擎、离线向量嵌入模型与 **15 类报告标准模板（`generic_knowledge/templates/` & `pattern/`）**。
> - **本地存储**：所有项目底稿与生成的报告均保存在本地目录，不写系统注册表，也可放在移动硬盘或 U 盘随身携带。

---

## 🚀 三步启动说明

### 第一步：解压便携包
将下载好的 `FairyReport-Local-v1.6.5-Windows-x64.zip`（`396 MB`）右键解压至任意磁盘目录（例如 `D:\FairyReport\`）。

### 第二步：双击启动程序
打开解压后的文件夹，直接双击运行 **`FairyReport.exe`**。程序会在后台自动拉起本地引擎，直接进入五步工作台（免注册、免登录）。

### 第三步：配置大模型 API Key
首次使用时，点击主界面右上角的 **「设置」** 按钮：
1. 填入你自己的 **DeepSeek API Key**；
2. 接口地址保持默认官方地址 `https://api.deepseek.com`；
3. 点击 **「保存配置」**，即可开始新建项目、导入底稿或直接留空创作智库专报。

---

## 🔒 完整性校验（SHA-256）

如需核对网盘下载的压缩包是否完整无损，可在 Windows PowerShell 中运行以下命令：

```powershell
Get-FileHash -Path "FairyReport-Local-v1.6.5-Windows-x64.zip" -Algorithm SHA256
```

确认输出的 `Hash` 值与以下校验码一致即可：

```text
97B214137B32D1A7A4CC191FE34629487CE1E9A95588565ADA372A6D22B52D09
```

---

## 📖 相关文档

- [🚀 快速上手操作指南](/guide/getting-started)
- [📦 绿色免安装版运行与数据备份指南](/docs/portable)
- [⚙️ 五步工作台深度解析](/docs/pipeline)
- [🛡️ 系统架构与本地存储说明](/docs/architecture)
- [💬 常见问题解答 (FAQ)](/guide/faq)
