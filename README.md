# 流盾 WAF（Flow Shield WAF）

> **流盾 WAF，守住每一次真实访问。**

**官网及详细文档：** [https://fswaf.top](https://fswaf.top)

流盾 WAF 是一款面向网站、业务接口和 Web 应用的**智能流量防护系统**，专注于 CC 攻击防护、恶意访问识别、自动化攻击拦截和网站安全加固。基于 **OpenResty 反向代理**构建：添加站点后，流量先进入流盾引擎再转发到源站；以「域名 + IP + 请求特征」为维度对每个请求做规则匹配与防护，并提供可视化管理面板。支持 Docker Compose 一键部署，兼容宝塔面板。

核心理念不是「挡住所有流量」，而是 **识别 → 拦截 → 清洗 → 守护**：

| 阶段 | 说明 |
|------|------|
| **识别** | 看清每一次访问背后的风险（IP、UA、URL、Body、Geo 等） |
| **拦截** | 阻断 CC、爬虫、扫描器、SQL 注入、恶意请求 |
| **清洗** | 过滤异常流量，保留真实用户 |
| **守护** | 持续保护网站稳定运行，支持观察模式与渐进上线 |

---

## 为什么做流盾？

我是 **[子比主题](https://www.zibll.com/)作者老唐**，在网站与建站领域深耕十多年。

这些年，为了给自己的站扛住 CC、刷量与恶意扫描，我几乎把市面上常见的 Web 防护都试过一遍——腾讯 EdgeOne、阿里云边缘 CDN、雷池、宝塔 WAF……用下来的感受很直接：要么关键能力不够用，要么价格让人犹豫很久。

靠多年运营经验，我越来越确信一件事：**CC 与 Web 防护的核心，并不是堆砌黑盒，而是找到攻击的共同特征与规律，再写成可执行的防御规则。** 道理其实很朴素；真正卡住站长的，往往是「规则匹配不够细、日志不够好查、策略不好打磨」。

于是我花了一段时间，把这套想法做成了**流盾 WAF**：希望它不只服务 [子比主题](https://www.zibll.com/) 的用户，也能帮到所有需要守护 Web 流量的朋友——让防护更懂站长、更好上手、也更敢用来打仗。

---

## 流盾核心优势

### 1. 极快

引擎基于 **Lua** 构建，配合 **Redis** 做规则与计数：单个请求跑完全部防护流程，通常 **不到 1 毫秒**。防护要挡得住，也要尽量不拖慢真实用户。

### 2. 超级丰富的规则策略

不止常见的 URL、IP、请求头、地域……还覆盖 Cookie、Bot 管理等 **30+ 匹配项**，支持包含 / 排除 / 等于 / 不等于 / 正则等多种条件。把攻击特征拆得更细，策略才能既精准、又好用。

### 3. 丰富的日志筛选

这一点深受腾讯 EdgeOne 启发：**从日志里找攻击共性，才是防御最关键的一步。** 当攻击手法不断变化，流盾提供多维度排行与分析，帮你更快锁定「这批请求长什么样」，再反哺成更完善的规则。

### 4. 功能完善

黑名单、白名单、防护例外、速率防护、自定义规则之外，还有总览统计、站点管理、证书管理、**Bot 库**、IP 组，以及 AI 能力——把日常防护真正需要的能力收进同一块面板，而不是东拼西凑。

### 5. AI 驱动自行防护

遇到棘手攻击时，可调用 AI 辅助生成更精准的策略；也支持 **AI 自动防护**：条件触发后，后台自动分析近期日志、提炼攻击特征并创建规则，尽量做到无人值守持续防守。

---

## 产品特点

### 反向代理型 WAF

- 流量路径：`客户端 → 流盾引擎 (:80/:443) → 源站`
- 在面板中添加站点、配置回源地址与证书后，域名解析到本机即可生效
- 规则与限速策略通过 Redis **热同步**，改配置无需重启引擎（仅站点拓扑变更才触发 Nginx reload）

### 统一规则引擎

- 黑白名单、防护例外、速率防护、自定义规则共用同一套**匹配字段目录**与 condition DSL
- 支持 AND/OR 条件组、IP 组引用、流量基线对比（`traffic.global`）等高级匹配
- 自定义规则按优先级排序执行；首次安装会种子化内置 IP 组、黑白名单、例外、限速、自定义规则与 Bot 库（可自行启停或改动作）

### 五种防护方式

| 模式 | 说明 |
|------|------|
| **观察** | 仅记录日志，不阻断请求，适合上线前验证规则 |
| **拦截** | 返回自定义拦截页并终止请求 |
| **算术验证** | 弹出简单算术 CAPTCHA（开发/测试可用，生产建议优先滑动或 JS 挑战） |
| **JS 挑战** | 浏览器端 PoW 挑战，抵御自动化脚本 |
| **滑动验证** | 滑块人机验证，适合表单/API 限速场景 |

### CC 与访问控制

- 多维度速率防护：按 IP、URI、Cookie 等组合键限速
- 全局黑白名单、防护例外（可跳过全部/仅规则/仅限速）
- IP 组管理，支持 `in_ip_group` / `not_in_ip_group` 条件
- 限速计数器异常时默认 **fail-open 放行**（可在系统设置中关闭，生产建议保持开启）

### 日志与可观测性

- 引擎异步写入 Redis Stream → Worker 消费 → **ClickHouse** 持久化
- 防护日志支持多维度查询、统计聚合、详情追溯
- 可配置日志采样、突发流量自动降采样、保留天数 TTL
- 调试模式可在响应头附带规则命中信息（仅建议测试环境开启）

### 预警与 AI 防护

- **预警通知**：按条件触发，支持邮件/Webhook 等通道，带冷却时间
- **AI 防护**：对话式辅助分析日志、生成/优化规则（需配置 LLM）

### 生产级安全基线

- 启动时校验 JWT、挑战密钥、管理员密码，拒绝不安全默认值
- 登录接口 Redis 限速，Refresh Token 查库校验用户状态
- 黑名单、全站例外、非观察限速**禁止空条件**，避免误拦整站
- 引擎启动与后端解耦：后端暂时不可用时不阻断 WAF 代理服务
- 健康检查同时探测管理面板与 WAF 引擎

---

## 技术栈

| 层 | 技术 |
|----|------|
| 拦截引擎 | OpenResty（Nginx + Lua） |
| 管理后端 | Python FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 配置与计数 | SQLite + Redis 7（Compose 默认 TCP） |
| 日志存储 | ClickHouse 24 |
| 前端面板 | Vue 3 + Vite + TypeScript + Ant Design Vue |
| 部署 | Docker Compose（3 服务 + SQLite 内嵌于 app） |

---

## 目录结构

```
flow-shield-waf/
├── docker-compose.yml      # redis + clickhouse + app（SQLite 在 app 卷内）
├── .env.example            # 环境变量模板（部署前必改）
├── engine/                 # OpenResty WAF 引擎（Lua）
├── backend/                # FastAPI 管理后端 + Worker
├── frontend/               # Vue 3 管理面板
├── slide_captcha/          # 滑动验证素材（可自定义）
├── deploy/
│   ├── app/                # 应用镜像（后端 + Worker + 引擎 + 面板）
│   ├── clickhouse/         # ClickHouse 初始化 SQL
│   ├── geoip/              # MaxMind .mmdb（已附带，见 deploy/geoip/README.md）
│   ├── baota/              # 宝塔一键部署
│   └── smoke_test.sh       # 集成回归脚本
├── scripts/
│   ├── fresh-start.sh      # 清空数据卷并重建（开发/测试用）
│   └── stress_test.py      # 防护分阶段 QPS 压测
└── docs/                   # 架构 / 规则 DSL / API / 压测文档
```

---

## 安装部署

### 环境要求

- Docker 20.10+ 与 Docker Compose v2
- 服务器放行端口：`80`、`443`（WAF 对外）、`9000`（管理面板，可改）
- 建议内存 ≥ 2 GB（含 ClickHouse）

### 第一步：获取代码并配置环境变量

```bash
# 克隆仓库（私有仓库需先在服务器配置 GitHub 访问：HTTPS Token 或 SSH 密钥）
git clone https://github.com/Qinver-china/flow-shield-waf.git
cd flow-shield-waf

cp .env.example .env
```

编辑 `.env`，**务必修改**以下项：

| 变量 | 说明 |
|------|------|
| `DB_PATH` | SQLite 配置库路径（Docker 默认 `/data/waf.db`） |
| `REDIS_PASSWORD` | Redis 密码 |
| `JWT_SECRET` | JWT 签名密钥（≥ 16 位随机串） |
| `WAF_CHALLENGE_SECRET` | 挑战 Cookie HMAC 密钥（≥ 16 位随机串） |
| `WAF_ADMIN_USER` / `WAF_ADMIN_PASSWORD` | 初始管理员（首次启动自动创建） |

生产环境建议同时设置：

```bash
WAF_ALLOW_INSECURE_DEFAULTS=false   # 拒绝默认密钥（默认已是 false）
ENABLE_DOCS=false                   # 关闭 OpenAPI 文档
CORS_ORIGINS=https://your-panel.example.com  # 限制面板跨域来源
```

> 若使用示例中的默认密钥且未设置 `WAF_ALLOW_INSECURE_DEFAULTS=true`，后端将拒绝启动。本地调试可临时设 `WAF_ALLOW_INSECURE_DEFAULTS=true`。

### 第二步：检查端口

流盾对外提供网站访问时，需要占用服务器的 **80**（HTTP）和 **443**（HTTPS）端口。启动前先确认这两个端口空闲，否则容器起不来或无法对外服务。

在服务器上执行下面任一命令，看谁占用了端口：

```bash
# 推荐：ss
ss -tlnp | grep -E ':80 |:443 '

# 或
lsof -iTCP:80 -sTCP:LISTEN
lsof -iTCP:443 -sTCP:LISTEN

# 或（部分系统需先安装 net-tools）
netstat -tlnp | grep -E ':80 |:443 '
```

如果命令没有输出，一般表示端口空闲，可以进入下一步。

如果端口已被占用，按下面列表排查处理：

#### (a) 方案 1：本机已安装 Nginx

若服务器上已经装了 Nginx，并由它托管多个网站，通常会占用 80 / 443。需要把 **Nginx 下所有网站** 的监听端口都改成其他端口（例如 `8080` / `8443`），把 80 / 443 留给流盾。

常见改法：

1. 找到 Nginx 站点配置（常见路径如 `/etc/nginx/sites-enabled/`、`/etc/nginx/conf.d/`）
2. 把各站点里的 `listen 80;`、`listen 443 ssl;` 等改成新端口
3. 检查配置并重载：

```bash
nginx -t && systemctl reload nginx
```

改完后，流盾面板里配置站点回源时，源站端口要填 Nginx 的新端口，而不是 80 / 443。

> 用宝塔面板时，端口协调方式见下方 [端口与宝塔共存](#端口与宝塔共存) 及 [`deploy/baota/README.md`](deploy/baota/README.md)。

### 第三步：构建并启动

```bash
docker compose up -d --build
```

等待所有容器健康（首次启动约 1–2 分钟）：

```bash
docker compose ps
```

编排为 **3 个容器**（业务数据挂载在 `app` 的 `app_data` 卷 `/data`）：

| 容器 | 说明 |
|------|------|
| `redis` | Redis 7，规则缓存 / 限速计数 / 日志 Stream |
| `clickhouse` | ClickHouse 24，防护日志、AI/预警/流量异常流水 |
| `app` | 合一镜像：后端 + Worker + WAF 引擎 + 管理面板 + SQLite |

`app` 容器内进程：

| 进程 | 端口 | 职责 |
|------|------|------|
| backend | 127.0.0.1:8000 | FastAPI API |
| worker | — | 日志消费、预警调度、留存清理 |
| engine | :80 / :443 | OpenResty WAF 拦截与回源 |
| panel | :9000 | 管理面板静态资源 + API 反代 |

### 第四步：登录面板并添加站点

1. 打开管理面板：`http://<服务器IP>:9000`
2. 使用 `.env` 中的 `WAF_ADMIN_USER` / `WAF_ADMIN_PASSWORD` 登录
3. **站点管理** → 新增站点：填写域名、回源地址、监听端口（HTTP/HTTPS）
4. 若启用 HTTPS，先在**证书管理**上传证书，再在站点中选择
5. 将域名 DNS 解析到本服务器，流量即经 WAF 防护后回源

### 第五步：验证（可选）

```bash
# 检查面板与引擎健康
curl -fsS http://localhost:9000/health
curl -fsS http://localhost/waf-health

# 完整集成回归（需先登录凭据与 httpbin 可达）
bash deploy/smoke_test.sh

# 防护压测（默认 20/50/100 QPS × 各 2 分钟；详见 docs/stress-test.md）
python3 scripts/stress_test.py --url http://127.0.0.1 --host your.site.com
```

### 端口与宝塔共存

流盾 WAF 引擎需占用 `80` / `443` 对外服务。若宝塔 Nginx 已占用这两个端口：

- **推荐**：宝塔 Nginx 改听高位端口（如 `8080`/`8443`），站点的源站填 `http://127.0.0.1:8080`
- 对外仅由流盾 WAF 承接 80/443

详见 [`deploy/baota/README.md`](deploy/baota/README.md)。

---

## 地理位置（GeoIP）

流盾 WAF 支持基于 MaxMind GeoIP2 的地理维度匹配与日志补全，用于按国家/地区/运营商编写规则，并在防护日志中记录来源地理信息。

### 内网 IP 自动跳过（性能优先）

在进行**任何**地理位置相关操作之前，引擎会先判断客户端 IP 是否为内网地址。内网 IP **不会**触发 GeoIP2 查询，也不会读取 `CF-IPCountry` 等兜底头，以避免无意义的性能开销。

内网判定标准由引擎统一维护（`engine/lua/waf/util.lua` → `is_private_ip`），当前包含以下 IPv4 网段：

| 网段 | 说明 |
|------|------|
| `10.0.0.0/8` | RFC 1918 A 类私网 |
| `172.16.0.0/12` | RFC 1918 B 类私网 |
| `192.168.0.0/16` | RFC 1918 C 类私网 |
| `127.0.0.0/8` | 回环地址 |

适用场景：

- **规则匹配**：`geo.country`、`geo.region` 等字段对内网 IP 直接返回空，不查库
- **日志写入**：内网请求不写地理字段（`geo_country` 等保持为空），`ip_is_private` 记为 `true`

> 客户端 IP 取自 TCP 连接地址（`remote_addr`），与限速、挑战一致，防止伪造 `X-Forwarded-For`。若需扩展内网网段定义，请修改 `util.is_private_ip` 后重建 `app` 镜像。

### 启用 MaxMind GeoIP2

项目 `deploy/geoip/` 目录**已附带** GeoLite2 三库（Country / City / ASN），默认直接可用，无需下载。

```bash
docker compose up -d --build   # 或已部署时：docker compose restart app
```

`docker-compose.yml` 将该目录挂载到容器内 `/etc/nginx/geoip`；entrypoint 检测到 `.mmdb` 后**自动生成** GeoIP2 配置。

**需要更新库时**：自行从 [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) 下载最新文件，覆盖 `deploy/geoip/` 中同名文件后重启 `app` 即可。详见 [`deploy/geoip/README.md`](deploy/geoip/README.md)。

### 规则与日志行为

| 路径 | 行为 |
|------|------|
| 规则引用 `geo.*` | 仅在该字段被求值时查询；内网 IP 直接跳过 |
| 日志写入 | 凡落库的请求均尝试补全地理字段 |
| 规则已 trace 地理字段 | 写日志时复用 trace，不重复查询 |
| 规则未查地理 | 仅在日志路径懒加载批量读取 `ngx.var` |
| 未配置 GeoIP2 | 公网 IP 的国家可回退 `CF-IPCountry`（Cloudflare） |

可在自定义规则中使用 `geo.country`、`geo.region`、`geo.city`、`geo.asn`、`geo.isp` 及 `geo_in` 操作符。总览大屏「拦截来源国家」仅统计已拦截（`blocked = 1`）请求。

### 接入 CDN 时的客户端 IP

若域名前置了 CDN 或反向代理，请在 **站点管理 → 回源配置 → 客户端 IP 获取方式** 选择与上游一致的头字段：

| 选项 | 适用场景 |
|------|----------|
| 直连 IP（默认） | 客户端直连 WAF，无 CDN |
| CF-Connecting-IP | Cloudflare |
| True-Client-IP | Akamai 等 |
| X-Real-IP / X-Client-IP | 通用反向代理 |
| X-Forwarded-For（第一个/最后一个） | 多层代理链 |

该设置影响规则中的 `ip.src`、限速键、挑战校验、防护日志与 GeoIP。对于 `X-Real-IP`、`CF-Connecting-IP` 等单值头，引擎还会在站点 Nginx 配置中启用 `real_ip` 模块，使 GeoIP2 与 `$remote_addr` 同步为真实客户端地址。

> 请确保流量**仅**从可信 CDN / 代理进入 WAF，避免客户端伪造 IP 头。直连公网暴露时请保持「直连 IP」。

更多细节见 [`deploy/geoip/README.md`](deploy/geoip/README.md) 与 [`docs/rule-dsl.md`](docs/rule-dsl.md)。

---

## 架构示意

```
客户端
  │
  ▼
流盾 WAF 引擎 (OpenResty :80/:443)
  │  access.lua：白名单 → 黑名单 → 例外 → 限速 → 规则
  │  命中放行 → proxy_pass 源站
  │
  ├─ 读/写 ──► Redis（规则版本、限速计数、日志 Stream）
  │
  └─ 配置来源 ◄── app 容器
                    ├─ FastAPI :8000（写 SQLite、发布 Redis 配置）
                    ├─ Worker（消费日志 → ClickHouse、预警）
                    ├─ Panel :9000（Vue 管理界面）
                    └─ SQLite（站点、规则、用户、AI 对话）
                         ClickHouse（防护日志与流水事件）
```

**配置热更新**：规则/限速/黑白名单变更 → 写入 Redis 并递增版本号 → 引擎 worker 轮询加载，无需 reload。

**站点拓扑变更**（增删域名、改监听端口）→ 重新生成 Nginx server 配置 → 引擎 reload。

---

## 管理面板功能一览

| 模块 | 功能 |
|------|------|
| 总览 | 请求量、拦截统计、配置版本、站点概览 |
| 站点管理 | 域名、回源、HTTP/HTTPS、证书、客户端 IP 获取方式（CDN）、自定义拦截页 |
| 证书管理 | SSL 证书上传与管理 |
| 自定义规则 | SQL 注入、扫描器等防护规则，支持优先级与五种模式 |
| 黑名单 / 白名单 | 全局访问控制（黑名单必须配置匹配条件） |
| IP 组 | IP/CIDR 集合，供规则引用 |
| 防护例外 | 按条件跳过全部/规则/限速检测 |
| 速率防护 | CC 防护，多维度键 + 时间窗口 + 阈值 |
| 防护日志 | 查询、统计、详情追溯 |
| 预警通知 | 条件触发 + 通知通道 |
| AI 防护 | 对话式规则辅助 |
| 系统设置 | 挑战 TTL、日志策略、拦截页、时区、调试模式、限速 fail-open |

---

## 常用运维命令

```bash
docker compose ps                    # 查看容器状态
docker compose logs -f app           # 应用日志（后端/引擎/面板）
docker compose restart app           # 重启应用容器
docker compose down                  # 停止所有服务
```

版本更新请参见下方 **[版本更新](#版本更新)** 章节，勿直接 `down -v`（会删除数据卷）。

### 数据卷

| 卷名 | 内容 |
|------|------|
| `flowshield-waf_app_data` | 业务数据：`/data/waf.db`、引擎 conf/certs |
| `flowshield-waf_redis_data` | Redis 持久化（可空卷重建） |
| `flowshield-waf_clickhouse_data` | 防护日志（可空卷重建） |

---

## 版本更新

已部署环境升级时，**保留 `.env` 与数据卷**，按以下步骤操作：

```bash
cd flow-shield-waf

# 1. 备份（生产建议）
cp .env .env.bak.$(date +%Y%m%d)

# 2. 拉取新代码（默认分支 main）
git pull origin main

# 3. 对比 .env.example，将新增环境变量补入 .env
diff .env.example .env || true

# 4. 重建应用镜像并启动（数据不丢）
docker compose up -d --build

# 5. 验证
docker compose ps
curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1/waf-health
```

**说明：**

- 仅需重建 `app` 镜像；Redis / ClickHouse / SQLite 数据卷自动保留
- 数据库表结构变更由 backend 启动时的 schema patch **自动完成**，无需手工迁移
- 规则与限速策略通过 Redis 热同步，更新期间代理可能短暂抖动约 10–30 秒
- 更新后不要在生产环境修改 `JWT_SECRET`、`WAF_CHALLENGE_SECRET`，否则会导致登录与挑战失效

宝塔环境可使用：

```bash
bash deploy/baota/upgrade.sh
```

完整说明、回滚与检查清单见 [`docs/upgrade.md`](docs/upgrade.md)。

### 全量重置（仅开发/测试）

```bash
./scripts/fresh-start.sh   # ⚠️ 会删除所有数据卷
```

---

## 开发

```bash
# 后端
cd backend && pip install -e ".[dev]"
uvicorn app.main:app --reload

# 前端
cd frontend && npm install && npm run dev

# 引擎：修改 engine/lua/waf/*.lua 后
docker compose up -d --build app

# 字段目录：修改 backend/app/fields/catalog.py 后
cd backend && python -m app.fields.export

# 单元测试
cd backend && pytest

# 防护压测（对已配置站点；完整说明见 docs/stress-test.md）
python3 scripts/stress_test.py --url https://你的站点.com
python3 scripts/stress_test.py --url http://127.0.0.1 --host your.site.com --mix-attack --report report.json
```

数据库采用模型驱动建表（`create_all` + 轻量 schema patch），全新环境可用 `./scripts/fresh-start.sh` 重建；已有数据环境升级时 backend 启动会自动应用列补丁。

---

## 文档

### 详细文档及教程请查看[https://fswaf.top](https://fswaf.top)

| 文档 | 说明 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | 架构、请求流程、配置下发、日志链路 |
| [`docs/rule-dsl.md`](docs/rule-dsl.md) | 条件 DSL、操作符、字段目录 |
| [`docs/api.md`](docs/api.md) | REST API 说明 |
| [`docs/stress-test.md`](docs/stress-test.md) | **防护压测**脚本用法与参数 |
| [`docs/review-after-fix.md`](docs/review-after-fix.md) | 安全加固与审查记录 |
| [`docs/upgrade.md`](docs/upgrade.md) | **版本更新**、回滚与检查清单 |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本更新日志 |
| [`deploy/baota/README.md`](deploy/baota/README.md) | 宝塔部署指南 |

---

## 其他项目

- **[子比主题](https://www.zibll.com/)** — 更优雅的全能型 WordPress 主题，集成文章资讯、会员系统、商城系统、社区论坛等能力，助力快速搭建内容、社区与商业化兼具的专业网站。

---

## 许可

本项目采用 **[PolyForm Noncommercial License 1.0.0](LICENSE)**（非商业许可），**禁止商业使用**。

| 允许 | 禁止 |
|------|------|
| 个人学习、研究、测试 | 向客户收费部署或提供有偿 WAF 服务 |
| 业余项目、非营利组织内部使用 | 作为商业产品/服务销售或 SaaS 运营 |
| 在遵守许可前提下修改与再分发 | 未经授权的企业商业化使用 |

如需商业授权，请联系项目著作权人。完整条款见根目录 [`LICENSE`](LICENSE) 文件。
