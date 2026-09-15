# Streamlit 看板部署途径梳理

本文以本仓库的 Streamlit 应用为例，梳理常见的「从代码到别人能打开链接」的部署途径。  
GitHub 主要负责**存代码**；真正跑起 Python 进程、对外提供访问，需要依赖下方某一类平台或自有服务器。

本地开发启动示例：

```bash
streamlit run app.py --server.port 8501
```

默认本地地址：`http://127.0.0.1:8501`

---

## 途径一：Streamlit Community Cloud（官方路径）

**适合：** 最快公开 Demo、小流量看板、不想自己管服务器。

### 做法概要

1. 将代码推送到 GitHub（需包含入口文件如 `app.py`，以及 `requirements.txt` 等依赖声明）
2. 登录 [Streamlit Community Cloud](https://share.streamlit.io)
3. Connect 对应仓库 → 选择分支与入口文件 → Deploy

### 特点

| 项 | 说明 |
|----|------|
| 优点 | 官方支持、配置少、与 GitHub 联动方便 |
| 缺点 | 免费档有配额与休眠限制；服务在境外 |
| 国内访问 | 不翻墙时**常不稳定**，不适合作为国内正式入口 |

### 仓库侧最少准备

- `app.py`（或其他入口）
- `requirements.txt`（至少包含 `streamlit`）

---

## 途径二：Cloudflare Quick Tunnel（临时公网映射）

**适合：** 本机或临时环境已经跑起来了，想**马上**发一个 HTTPS 链接给别人看一眼。  
**不适合：** 正式长期上线、国内稳定访问。

### 原理

本机（或云端开发机）上的 `cloudflared` **主动连出**到 Cloudflare，把本地 `8501` 映射成公网临时 HTTPS 域名（形如 `https://xxxx.trycloudflare.com`）。  
不需要给机器开公网入站端口。

### 操作步骤

```bash
# 1. 先在本机启动 Streamlit
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

# 2. 另开终端，用 Quick Tunnel 暴露
cloudflared tunnel --url http://127.0.0.1:8501
```

终端会打印临时链接，例如：

```text
https://xxxx.trycloudflare.com
```

### 特点

| 项 | 说明 |
|----|------|
| 优点 | 极快、本机也能分享、自动 HTTPS |
| 缺点 | 进程/电脑关机即失效；临时域名无稳定 SLA |
| 国内访问 | `*.trycloudflare.com` 在大陆**经常打不开或不稳** |
| 是否 Cursor 独有 | **否**。Cloudflare 是独立公司；Quick Tunnel 是通用工具 |

> 说明：在 Cursor Cloud Agent 等云端环境里也可以用同一套方式做临时演示；本质仍是「某处在跑 Streamlit + cloudflared」，不是 Cursor 专属部署产品。

---

## 途径三：GitHub Actions 自动部署到自有服务器（如腾讯云）

**适合：** 已有腾讯云等服务器、需要**长期在线**、希望 push 代码后自动更新。  
对国内用户而言，这通常是**最稳妥**的正式方案之一。

### 架构分工

| 角色 | 职责 |
|------|------|
| GitHub | 存代码、触发 CI/CD |
| 腾讯云服务器 | 实际运行 `streamlit`（或 Docker） |
| Nginx / Caddy（推荐） | 反代、域名、HTTPS |
| GitHub Actions | push 后 SSH 到服务器拉代码并重启服务 |

### 服务器侧（简化示意）

```bash
# 安装依赖并启动（可用 systemd 保活）
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

生产环境建议：

- 用 **systemd** 或 **Docker Compose** 保活
- 前面挂 **Nginx/Caddy**，对外只开 `80/443`
- 安全组放行 `80/443`（不必长期裸开 `8501`）
- 若面向中国大陆公网正式访问：优先**大陆地域机器 + 已备案域名 + HTTPS**

### GitHub Actions 思路（示意）

`main` 分支 push 后：

1. SSH 登录腾讯云
2. `git pull`（或 rsync/制品包）
3. 安装/更新依赖
4. `systemctl restart streamlit`（或 `docker compose up -d --build`）

密钥与主机信息放在 GitHub Secrets，不要写入仓库明文。

### 特点

| 项 | 说明 |
|----|------|
| 优点 | 可控、可长期运行；国内访问可做到稳定 |
| 缺点 | 要自己维护机器、域名、证书、进程保活 |
| 国内访问 | 大陆节点 + 备案域名时，一般最可靠 |

---

## 途径四：静态网站托管（GitHub Pages / Cloudflare Pages / Vercel / Netlify）

**适合：** HTML/CSS/JS 静态站，或 Next.js / Vite / React 等可构建为前端的项目。

**不适合：直接部署 Streamlit。**

### 原因

Streamlit 是**常驻 Python 服务进程**，每个会话需要后端实时计算与 WebSocket 通信。  
GitHub Pages、Cloudflare Pages、Vercel/Netlify 的静态托管（以及多数「只跑构建产物」的前端托管）**不会**为你长期跑这个 Python 进程，因此：

> **不能把 Streamlit 应用直接丢到 GitHub Pages 这类静态托管上。**

若业务可以改成纯前端或「前端 + 独立 API」，再考虑 Pages / Vercel 等；那已不是「原样部署 Streamlit」。

### 对照

| 项目类型 | 能否用 Pages / Cloudflare Pages / Vercel / Netlify |
|----------|-----------------------------------------------------|
| 静态 HTML / 文档站 | 可以 |
| Vite / React / Next 等前端 | 通常可以（按平台要求构建） |
| Streamlit 看板 | **不可以直接托管**；需途径一 / 二 / 三这类能跑 Python 的方案 |

---

## 怎么选（对照表）

| 目标 | 更推荐 |
|------|--------|
| 最快公开一个 Demo | 途径一：Streamlit Community Cloud |
| 本机已跑起来，临时给别人看一眼 | 途径二：Cloudflare Quick Tunnel |
| 长期在线、自己可控，且已有腾讯云 | 途径三：GitHub + 腾讯云（可选 Actions） |
| 纯前端 / 静态站 | 途径四：Pages / Vercel 等（**不是 Streamlit**） |
| 国内用户不翻墙也能稳定打开 | **途径三（大陆云 + 备案域名）**；途径一、二不保证 |

---

## 补充：和「Cursor Cloud Agent」的关系

- **Cloud Agent**：Cursor 提供的云端编程环境（临时虚拟机里改代码、跑命令）。
- **Streamlit / Cloudflare Tunnel**：开源或第三方通用工具，**不是 Cursor 独有**。
- 在 Cloud Agent 里用 Quick Tunnel 做演示，只是「临时环境 + 通用隧道」的组合；会话结束后链接通常会失效。

---

## 本仓库相关文件

| 文件 | 说明 |
|------|------|
| `app.py` | Streamlit 示例入口 |
| `.devcontainer/` | 开发容器配置，可在容器内 `streamlit run app.py` |

若走途径一或途径三，建议补充 `requirements.txt`（至少包含 `streamlit`）。
