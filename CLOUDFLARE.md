# Cloudflare 网站部署：完整方法路由

按「你想达成什么」选路。Cloudflare 不是只有临时链接；不同产品对应不同场景。

本文以常见网站（含 Streamlit 看板）为例；静态站 / 前端 / 本机服务会分开说明。

---

## 0. 先选路（总路由图）

```text
你要对外提供一个网站
│
├─ A. 本机或服务器上已经跑着服务，只想映射成公网 HTTPS
│     │
│     ├─ 临时给人看一眼、可接受链接会变/会断
│     │     → 【路线 1】Quick Tunnel（免费、最快、临时）
│     │
│     └─ 长期用、要绑自己的域名
│           → 【路线 2】Named Tunnel（账号 + 命名隧道 + 域名）
│
├─ B. 网站是静态 HTML / 前端构建产物（Vite、React 等）
│     → 【路线 3】Cloudflare Pages（官方静态/前端托管）
│
├─ C. 是 Streamlit 等常驻 Python 服务
│     │
│     ├─ 只是临时演示
│     │     → 路线 1（本机跑 Streamlit + Quick Tunnel）
│     │
│     ├─ 想长期挂在 Cloudflare「前面」
│     │     → 机器上跑 Streamlit + 路线 2（Tunnel 反代）
│     │     （Cloudflare 不负责跑 Python，只负责入口）
│     │
│     └─ 想少运维、或不想自己开机/开服务器
│           → 不走 Cloudflare 托管进程：用 Streamlit Cloud 或腾讯云
│             （详见 DEPLOYMENT.md）
│
└─ D. 只要 CDN / HTTPS / 防护，源站在腾讯云或其他主机
      → 【路线 4】域名接入 Cloudflare（DNS + 代理橙色云）
```

**一句话对照**

| 路线 | Cloudflare 扮演的角色 | 网站程序跑在哪 |
|------|----------------------|----------------|
| 1 Quick Tunnel | 临时入口 | 你的电脑 / 临时机器 |
| 2 Named Tunnel | 长期入口 | 你的电脑或服务器（需常开） |
| 3 Pages | 托管 + HTTPS + 发布 | Cloudflare 边缘（静态/前端） |
| 4 DNS/CDN | 加速与防护 | 你的源站（如腾讯云） |

---

## 路线 1：Quick Tunnel（临时公开本地网站）

### 适合

- 本地 `localhost` 已能打开
- 马上发链接给别人看
- 不要求长期稳定、不要求固定域名

### 不适合

- 正式上线、国内稳定访问、电脑经常关机

### 步骤

```bash
# 1）先启动你的网站（示例：Streamlit）
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

# 2）另开终端，安装并运行 cloudflared（若未安装）
# 下载：https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

cloudflared tunnel --url http://127.0.0.1:8501
```

终端会给出类似：

```text
https://随机名.trycloudflare.com
```

### 要点

- 关掉 `cloudflared` 或关电脑 → 链接失效  
- 每次新建 Quick Tunnel，域名常会变  
- 国内访问 `trycloudflare.com` **经常不稳**  
- **无需** Cloudflare 账号即可试用；也**无**生产级保障  

---

## 路线 2：Named Tunnel（长期隧道 + 自己的域名）

### 适合

- 服务跑在家里电脑 / 公司机 / 腾讯云等，希望长期用固定域名访问  
- 不想（或不能）对公网裸开端口，希望由 Cloudflare 做入口  

### 不适合

- 机器经常关机（关机则站点不可用）  
- 指望 Cloudflare「替你运行」Streamlit 进程（它不会）  

### 步骤概要

1. **注册并登录** [Cloudflare Dashboard](https://dash.cloudflare.com)  
2. **域名接入 Cloudflare**（把域名的 NS 改到 Cloudflare 提供的 nameserver）  
3. 本机或服务器安装 `cloudflared`，并登录：
   ```bash
   cloudflared tunnel login
   ```
4. **创建命名隧道**：
   ```bash
   cloudflared tunnel create my-site
   ```
5. **写配置**（示例 `~/.cloudflared/config.yml`）：
   ```yaml
   tunnel: <隧道ID>
   credentials-file: /path/to/<隧道ID>.json

   ingress:
     - hostname: app.example.com
       service: http://127.0.0.1:8501
     - service: http_status:404
   ```
6. **把域名指到隧道**（Dashboard 里为该隧道加 Public Hostname，或用命令创建 DNS）：
   ```bash
   cloudflared tunnel route dns my-site app.example.com
   ```
7. **常驻运行**：
   ```bash
   cloudflared tunnel run my-site
   ```
   生产环境建议把 `cloudflared` 装成系统服务（开机自启）。

### 要点

- Cloudflare = **网关**；Streamlit/Nginx 等仍在你机器上跑  
- 可配合腾讯云：源站在 CVM，不开 80/443 入站，只出站连 Cloudflare 也可以（视网络策略而定）  
- 国内若源站/用户都在大陆，还需考虑备案与网络质量；Tunnel 域名走 Cloudflare 线路，**不保证**大陆访问体验  

---

## 路线 3：Cloudflare Pages（直接托管静态 / 前端站）

### 适合

- 纯静态站（HTML/CSS/JS）  
- Vite / React / Vue / 部分框架的前端构建产物  
- 希望：连 GitHub → push 自动构建发布  

### 不适合

- **原样部署 Streamlit**（需要常驻 Python，Pages 不提供）  
- 强依赖服务器会话、本地文件上传后长期存在于单机磁盘等场景（需另想后端）  

### 步骤概要

1. 代码推到 GitHub（或直接上传静态文件）  
2. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Pages**  
3. 选择 **Connect to Git**，授权仓库  
4. 配置构建：
   - 静态纯 HTML：构建命令可留空，输出目录为仓库根或 `public`  
   - Vite 示例：Build command `npm run build`，Output directory `dist`  
5. 保存后自动部署；之后每次 push 指定分支会自动更新  
6. 可绑定自己的域名（域名需在 Cloudflare 托管 DNS）  

### 要点

- 这是 Cloudflare 上最接近「官网式托管」的路径  
- 免费档通常够用个人站 / 文档站 / 前端 Demo  
- 和 Tunnel 不同：**文件由 Cloudflare 托管**，你的电脑不用一直开着  

---

## 路线 4：域名接入 Cloudflare（源站在别处，如腾讯云）

### 适合

- 网站已经在腾讯云 / 其他 VPS 上跑着  
- 只想用 Cloudflare 做 DNS、HTTPS、CDN、防护  

### 步骤概要

1. 域名 NS 切到 Cloudflare  
2. DNS 里加 `A` / `CNAME` 指向腾讯云公网 IP 或负载均衡  
3. 打开代理状态（橙色云）则走 Cloudflare CDN；灰色云则仅 DNS  
4. SSL/TLS 模式按源站证书情况选择（常见 Full / Full strict）  
5. 源站（腾讯云）继续跑 Nginx + Streamlit 等  

### 与路线 2 的区别

| | 路线 4 DNS/CDN | 路线 2 Named Tunnel |
|--|----------------|---------------------|
| 源站是否需公网端口 | 通常要（80/443） | 可不对公网开站端口 |
| 流量路径 | 用户 → CF → 你的公网 IP | 用户 → CF → 隧道 → 本机服务 |
| 典型用法 | 正规云主机站 | 内网/家宽/不想暴露端口 |

---

## Streamlit 专项：在 Cloudflare 体系里怎么走

```text
Streamlit 看板
│
├─ 临时分享本机画面
│     → 路线 1：本机 streamlit + Quick Tunnel
│
├─ 长期固定域名，自己有常开机器（电脑或腾讯云）
│     → 机器上跑 streamlit（建议前面还可加 Nginx）
│     → 路线 2：Named Tunnel 指到 8501 或 Nginx
│
├─ 想让 Cloudflare「托管整个看板程序」
│     → ❌ Pages 做不到
│     → 改用 Streamlit Community Cloud，或腾讯云跑进程
│        （可选再套路线 4 做域名与防护）
│
└─ 只有前端外壳是静态的、数据另有 API
      → 前端可走路线 3 Pages；API 仍要单独部署
```

---

## 国内访问怎么选（务实）

| 方案 | 国内不翻墙体验 |
|------|----------------|
| Quick Tunnel（`trycloudflare.com`） | 经常差 / 打不开 |
| Named Tunnel + 域名（CF 代理） | 看线路，**不保证**稳定 |
| Pages 站点 | 同样不保证大陆访问质量 |
| 腾讯云大陆 + 备案域名（可不用 CF，或仅 DNS） | 通常最稳 |

结论：给**国内用户长期用**，优先腾讯云正式部署；Cloudflare 更适合临时演示、海外访问、静态站全球分发、或给已有源站加一层防护。

---

## 和「GitHub 自动部署」怎么拼

| 你的站类型 | Cloudflare 侧 | GitHub 侧 |
|------------|----------------|-----------|
| 静态 / 前端 | 路线 3 Pages | Connect 仓库，push 自动构建 |
| Streamlit 在腾讯云 | 可选路线 4 | Actions SSH 部署到服务器（见 `DEPLOYMENT.md`） |
| Streamlit 在家用电脑 | 路线 2 Tunnel | 一般只 `git pull`；全自动较麻烦（机器要在线） |
| 临时 Demo | 路线 1 | 可不涉及 GitHub |

---

## 推荐决策清单（直接勾）

1. 是不是静态站 / 纯前端？  
   - 是 → **路线 3 Pages**  
   - 否 → 看 2  
2. 只是临时给人看？  
   - 是 → **路线 1 Quick Tunnel**  
   - 否 → 看 3  
3. 有没有一台会长期开机的机器跑程序？  
   - 有 → **路线 2 Named Tunnel**（或腾讯云 + 路线 4）  
   - 没有 → **不要用 Tunnel 硬撑**；改用 Streamlit Cloud / 买云主机  
4. 用户主要在中国大陆？  
   - 是 → 优先 **腾讯云 + 备案**；Cloudflare 当辅助而非唯一方案  

---

## 相关文档

- 本仓库总览（本地分享 vs GitHub/腾讯云）：见 [`DEPLOYMENT.md`](./DEPLOYMENT.md)  
- Cloudflare 官方文档入口：  
  - Tunnel：https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/  
  - Pages：https://developers.cloudflare.com/pages/  
  - 域名与 DNS：https://developers.cloudflare.com/dns/  
