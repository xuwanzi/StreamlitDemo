# Streamlit 看板：从本地分享到 GitHub / 腾讯云部署

本文以本仓库的 Streamlit 应用为例，按**真实需求**梳理部署方式，帮你搞清：

1. 本地跑着的看板，怎么发给别人一个链接？
2. 代码放到 GitHub 之后，怎么对外发布？GitHub 是不是只能托管静态站？有腾讯云的话能不能打通？能不能尽量全自动？

> **Cloudflare 专项路由**（Quick Tunnel / Named Tunnel / Pages / DNS·CDN、与 Streamlit 怎么搭配）：见 [`CLOUDFLARE.md`](./CLOUDFLARE.md)。

本地开发启动：

```bash
streamlit run app.py --server.port 8501
```

默认地址：`http://127.0.0.1:8501`（只有你自己电脑能打开）。

---

## 先建立三个关键认知

### 1. 「能打开链接」≠「代码在 GitHub 上」

| 环节 | 谁在做 | 例子 |
|------|--------|------|
| 存代码、版本管理 | GitHub | `git push` |
| 真正跑网站/看板 | 某一台一直在线的机器或托管平台 | 你的电脑、腾讯云、Streamlit Cloud |
| 给别人一个公网 HTTPS 地址 | 域名 / 隧道 / 平台自带域名 | `trycloudflare.com`、备案域名、`*.streamlit.app` |

别人能打开的链接，背后一定有一个**正在运行的服务**。GitHub 仓库页面本身并不会替你跑 Streamlit。

### 2. 「GitHub 只能托管静态网站」——这句话只说对了一半

- **对的部分：** GitHub 自带的 **GitHub Pages** 只适合静态内容（HTML/CSS/JS，或前端构建产物）。**不能**直接跑 Streamlit 这种常驻 Python 进程。
- **不完整的部分：** GitHub 还可以当「代码仓库 + 自动化扳机」。用 **GitHub Actions**，push 代码后可以自动部署到**腾讯云、Docker、各类云平台**。  
  → 所以：**不是「GitHub 不能部署动态站」，而是「GitHub Pages 不能跑 Streamlit」；动态站要跑在别的地方，GitHub 负责存代码并触发更新。**

### 3. Streamlit 属于「动态服务」，不是静态站

Streamlit 需要一台机器持续执行 Python，并保持 WebSocket 连接。因此：

- ✅ 适合：本机临时穿透、Streamlit Cloud、腾讯云 / Docker 等能跑进程的环境  
- ❌ 不适合：GitHub Pages、多数纯静态托管（见文末对照）

---

## 你的需求一：本地已在跑，想发给别人链接

**目标：** 电脑上 `localhost:8501` 已经能看了 → 马上生成一个公网链接分享。

### 推荐：Cloudflare Quick Tunnel（临时分享）

原理：本机安装的 `cloudflared` **主动连出去**到 Cloudflare，把本地端口映射成临时 HTTPS 域名。别人访问该域名时，流量转到你的电脑。

```bash
# 终端 1：照常启动看板
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

# 终端 2：映射公网
cloudflared tunnel --url http://127.0.0.1:8501
```

成功后终端会打印类似：

```text
https://xxxx.trycloudflare.com
```

把这个链接发给对方即可。

| 项 | 说明 |
|----|------|
| 优点 | 最快；本机就能分享；自动 HTTPS；不必开路由器端口 |
| 缺点 | 电脑关机 / 休眠 / 断网 → 链接立刻失效；临时域名无保障 |
| 国内访问 | `*.trycloudflare.com` **经常打不开或不稳**，不适合当国内正式入口 |
| 是否 Cursor 独有 | **否**，Cloudflare 是通用工具 |

**适用场景：** 临时演示、找同事看一眼、调试。  
**不适用：** 长期给客户用、要求国内稳定打开、电脑不能一直开机。

> 若演示环境在 Cursor Cloud Agent 等云端机器上，也可以用同一套 Tunnel；会话结束环境回收后，链接同样会失效。

### 需求一小结

| 你想要的 | 做法 |
|----------|------|
| 几分钟内给别人看 | Cloudflare Quick Tunnel |
| 链接要长期稳定、尤其国内用户 | 不要用本机穿透；改走下面「需求二」的正式部署 |

---

## 你的需求二：源码上 GitHub，再对外部署（可对接腾讯云、可全自动）

**目标：** 代码在 GitHub 上管理；对外有一个稳定网址；最好 push 之后网站自动更新。

这里有两条常见路，按「有没有自己的服务器」来选。

---

### 路线 A：没有服务器 / 不想运维 → Streamlit Community Cloud

官方托管，直接连 GitHub 仓库。

1. 仓库准备好 `app.py` + `requirements.txt`（至少含 `streamlit`）
2. 打开 [Streamlit Community Cloud](https://share.streamlit.io)
3. 登录并 Connect 你的 GitHub 仓库 → 选分支与入口 → Deploy
4. 之后每次 `git push`，平台可按配置自动重新部署

| 项 | 说明 |
|----|------|
| 优点 | 官方路径、配置少、和 GitHub 联动方便 |
| 缺点 | 免费档有配额 / 休眠；服务在境外 |
| 国内访问 | 不翻墙时**常不稳定** |
| 自动化 | 可以做到「push → 自动更新」 |

适合：公开 Demo、海外访问、先验证想法。

---

### 路线 B：已有腾讯云 → GitHub 存代码，服务器跑服务（推荐正式上线）

**可以打通，而且这是国内长期使用最稳妥的组合之一。**

#### 角色怎么分

```text
你本地改代码
    → git push 到 GitHub（存代码、留历史）
        → GitHub Actions 被触发（自动化）
            → SSH / 拉取代码到腾讯云
                → 安装依赖、重启 Streamlit
                    → 用户通过域名访问腾讯云上的服务
```

| 组件 | 职责 |
|------|------|
| GitHub | 存源码、触发 CI/CD |
| GitHub Actions | 自动执行「上传 / 拉取 + 部署」脚本 |
| 腾讯云 CVM | 真正运行 `streamlit`（或 Docker） |
| Nginx / Caddy | 反代到 8501，提供 80/443 与 HTTPS |
| 域名（建议备案） | 给用户一个好记、可长期用的地址 |

#### 服务器上服务怎么跑（示意）

```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

生产环境建议：

- 用 **systemd** 或 **Docker Compose** 保活（崩溃自动拉起、开机自启）
- 前面挂 **Nginx/Caddy**，安全组主要放行 `80/443`（不必长期把 `8501` 裸露公网）
- 面向中国大陆用户：优先选**大陆地域**机器 + **已备案域名** + HTTPS

#### 能不能全自动？——可以

「全自动」通常指这条闭环：

1. 本地改完代码  
2. `git push origin main`  
3. GitHub Actions 自动登录腾讯云（SSH 密钥放在 GitHub Secrets）  
4. 服务器 `git pull`（或同步制品）→ 更新依赖 → 重启服务  
5. 用户刷新域名，看到新版本  

你需要一次性搭好：服务器环境、进程保活、域名反代、Actions 工作流与密钥。搭好之后，日常就只剩 **改代码 → push**。

> 「代码上传」一般仍由你在本机 `git push`（或用 CI 从别处同步）。  
> 「网站部署和更新」可以由 Actions **全自动**完成。  
> 两者合在一起，就是常见的「GitOps / CI/CD」：人负责提交，机器负责上线。

#### Actions 在做什么（逻辑示意，非完整生产配置）

`main` 有新 commit 时：

1. SSH 到腾讯云  
2. 进入项目目录 `git pull`  
3. `pip install -r requirements.txt`（或 Docker 重新 build）  
4. `systemctl restart streamlit`（或 `docker compose up -d --build`）

主机 IP、SSH 私钥等放进 **GitHub Secrets**，不要写进仓库明文。

#### 手动版 vs 全自动版

| 阶段 | 半自动（先跑通） | 全自动（推荐最终形态） |
|------|------------------|------------------------|
| 改代码 | 本地编辑 | 同左 |
| 上传源码 | `git push` 到 GitHub | 同左 |
| 更新服务器 | 你 SSH 上去 `git pull` + 重启 | Actions 自动完成 |
| 用户访问 | 域名 / 服务器 IP | 同左 |

建议顺序：先在腾讯云手动部署跑通 → 再加 GitHub Actions，避免一上来同时调试太多环节。

---

## 需求二里常被问到的点

### Q：GitHub 和腾讯云能打通吗？

**能。** 典型打法就是：**GitHub = 代码源 + Actions；腾讯云 = 运行环境。**  
两者通过 SSH、Webhook 或容器镜像仓库连接，并不要求网站跑在 GitHub 上。

### Q：能不能实现全自动上传、部署、更新？

| 能力 | 是否可行 |
|------|----------|
| push 后自动部署到腾讯云 | ✅ 可以（Actions） |
| 网站自动重启并更新 | ✅ 可以 |
| 完全不碰 `git push`、改完文件就上线 | ⚠️ 一般不这么做；仍建议用 Git 提交作为上线依据 |
| 国内用户稳定访问 | ✅ 用大陆云 + 备案域名时较稳；单靠境外平台或 Tunnel 不保证 |

### Q：那 GitHub Pages / Vercel / Netlify 还能干什么？

它们适合**静态站或前端项目**，不适合原样部署 Streamlit：

| 项目类型 | GitHub Pages / Cloudflare Pages / Vercel / Netlify |
|----------|-----------------------------------------------------|
| 静态 HTML、文档站 | ✅ |
| Vite / React / 部分 Next 前端 | ✅（按平台构建要求） |
| Streamlit 看板 | ❌ 不能直接托管 |

若你以后做的是纯前端官网，可以用 Pages；看板继续用腾讯云或 Streamlit Cloud。

---

## 按需求怎么选（总表）

| 你的情况 | 建议 |
|----------|------|
| 本机已跑起来，临时给别人看一眼 | **Cloudflare Quick Tunnel** |
| 想最快从 GitHub 发布，暂无服务器 | **Streamlit Community Cloud** |
| 有腾讯云，要长期稳定（尤其国内） | **GitHub + 腾讯云**；再加 **Actions 全自动更新** |
| 只要静态官网 / 前端站 | **GitHub Pages 等**（不是 Streamlit） |
| 国内用户不翻墙也要稳 | **腾讯云大陆节点 + 备案域名**；Tunnel / 境外 SaaS 不保证 |

```text
只想临时分享本机画面？
  └─ 是 → Cloudflare Quick Tunnel
  └─ 否 → 需要长期网址？
              └─ 有腾讯云 → GitHub 存代码 + 服务器跑服务（可加 Actions）
              └─ 无服务器 → Streamlit Community Cloud（注意国内访问）
```

---

## 建议落地顺序（结合你的现状）

1. **本地开发**：`streamlit run app.py` 调通功能。  
2. **临时分享**：需要时用 Cloudflare Quick Tunnel 发链接（接受临时、境外不稳定）。  
3. **代码进 GitHub**：建仓库、`requirements.txt`、规范提交。  
4. **腾讯云手动上线**：装依赖、systemd/Docker、Nginx、域名与 HTTPS，确认别人能打开。  
5. **加 GitHub Actions**：实现 push 后自动拉取与重启，形成日常「改完就推、自动更新」。

---

## 本仓库相关

| 文件 | 说明 |
|------|------|
| `app.py` | Streamlit 示例入口 |
| `.devcontainer/` | 开发容器；容器内也可 `streamlit run app.py` |

正式走 Streamlit Cloud 或腾讯云部署前，建议补上 `requirements.txt`（至少包含 `streamlit`）。

---

## 附录：和 Cursor Cloud Agent 的关系

- **Cloud Agent**：Cursor 的云端编程环境（临时虚拟机里改代码、跑命令）。  
- **Streamlit / Cloudflare Tunnel**：通用工具，**不是 Cursor 独有功能**。  
- 在 Agent 里用 Tunnel 做演示，只是「临时环境 + 公网穿透」；会话结束后通常不可再用。正式对外仍应用上文需求二的方案。
