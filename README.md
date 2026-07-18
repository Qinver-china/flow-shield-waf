# 流盾 WAF（Flow Shield WAF）

> **流盾 WAF，守住每一次真实访问。**

流盾 WAF 是一款面向网站、业务接口和 Web 应用的**智能流量防护系统**，专注于 CC 攻击防护、恶意访问识别、自动化攻击拦截和网站安全加固。基于 **OpenResty 反向代理**构建：添加站点后，流量先进入流盾引擎再转发到源站；以「域名 + IP + 请求特征」为维度对每个请求做规则匹配与防护，并提供可视化管理面板。支持 Docker Compose 一键部署，兼容宝塔面板。

核心理念不是「挡住所有流量」，而是 **识别 → 拦截 → 清洗 → 守护**：

| 阶段 | 说明 |
|------|------|
| **识别** | 看清每一次访问背后的风险（IP、UA、URL、Body、Geo 等） |
| **拦截** | 阻断 CC、爬虫、扫描器、SQL 注入、恶意请求 |
| **清洗** | 过滤异常流量，保留真实用户 |
| **守护** | 持续保护网站稳定运行，支持观察模式与渐进上线 |

---

## 产品特点

### 反向代理型 WAF

- 流量路径：`客户端 → 流盾引擎 (:80/:443) → 源站`
- 在面板中添加站点、配置回源地址与证书后，域名解析到本机即可生效
- 规则与限速策略通过 Redis **热同步**，改配置无需重启引擎（仅站点拓扑变更才触发 Nginx reload）

### 统一规则引擎

- 黑白名单、防护例外、速率防护、自定义规则共用同一套**匹配字段目录**与 condition DSL
- 支持 AND/OR 条件组、IP 组引用、流量基线对比（`traffic.global`）等高级匹配
- 自定义规则按优先级排序执行；内置 SQL 注入、PHP 攻击、反 PCDN、CC 防护等策略模板（首次安装以**观察模式**种子，可自行切换为拦截）

### 五种防护模式

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
| 配置与计数 | MySQL 8 + Redis 7（默认 Unix Socket） |
| 日志存储 | ClickHouse 24 |
| 前端面板 | Vue 3 + Vite + TypeScript + Ant Design Vue |
| 部署 | Docker Compose（4 服务） |

---

## 目录结构

```
flow-shield-waf/
├── docker-compose.yml      # mysql + redis + clickhouse + app
├── .env.example            # 环境变量模板（部署前必改）
├── engine/                 # OpenResty WAF 引擎（Lua）
├── backend/                # FastAPI 管理后端 + Worker
├── frontend/               # Vue 3 管理面板
├── slide_captcha/          # 滑动验证素材（可自定义）
├── deploy/
│   ├── app/                # 应用镜像（后端 + Worker + 引擎 + 面板）
│   ├── clickhouse/         # ClickHouse 初始化 SQL
│   ├── baota/              # 宝塔一键部署
│   └── smoke_test.sh       # 集成回归脚本
├── scripts/
│   └── fresh-start.sh      # 清空数据卷并重建（开发/测试用）
└── docs/                   # 架构 / 规则 DSL / API 文档
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
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | 数据库密码 |
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

### 第二步：构建并启动

```bash
docker compose up -d --build
```

等待所有容器健康（首次启动约 1–2 分钟）：

```bash
docker compose ps
```

编排为 **4 个容器**：

| 容器 | 说明 |
|------|------|
| `mysql` | MySQL 8，持久化业务配置 |
| `redis` | Redis 7，规则缓存 / 限速计数 / 日志 Stream |
| `clickhouse` | ClickHouse 24，防护日志存储与聚合 |
| `app` | 合一镜像：后端 + Worker + WAF 引擎 + 管理面板（supervisord 管理） |

`app` 容器内进程：

| 进程 | 端口 | 职责 |
|------|------|------|
| backend | 127.0.0.1:8000 | FastAPI API |
| worker | — | 日志消费、预警调度、留存清理 |
| engine | :80 / :443 | OpenResty WAF 拦截与回源 |
| panel | :9000 | 管理面板静态资源 + API 反代 |

### 第三步：登录面板并添加站点

1. 打开管理面板：`http://<服务器IP>:9000`
2. 使用 `.env` 中的 `WAF_ADMIN_USER` / `WAF_ADMIN_PASSWORD` 登录
3. **站点管理** → 新增站点：填写域名、回源地址、监听端口（HTTP/HTTPS）
4. 若启用 HTTPS，先在**证书管理**上传证书，再在站点中选择
5. 将域名 DNS 解析到本服务器，流量即经 WAF 防护后回源

### 第四步：验证（可选）

```bash
# 检查面板与引擎健康
curl -fsS http://localhost:9000/health
curl -fsS http://localhost/waf-health

# 完整集成回归（需先登录凭据与 httpbin 可达）
bash deploy/smoke_test.sh
```

### 端口与宝塔共存

流盾 WAF 引擎需占用 `80` / `443` 对外服务。若宝塔 Nginx 已占用这两个端口：

- **推荐**：宝塔 Nginx 改听高位端口（如 `8080`/`8443`），站点的源站填 `http://127.0.0.1:8080`
- 对外仅由流盾 WAF 承接 80/443

详见 [`deploy/baota/README.md`](deploy/baota/README.md)。

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
                    ├─ FastAPI :8000（写 MySQL、发布 Redis 配置）
                    ├─ Worker（消费日志 → ClickHouse、预警）
                    ├─ Panel :9000（Vue 管理界面）
                    └─ MySQL（站点、规则、用户等）
                         ClickHouse（防护日志）
```

**配置热更新**：规则/限速/黑白名单变更 → 写入 Redis 并递增版本号 → 引擎 worker 轮询加载，无需 reload。

**站点拓扑变更**（增删域名、改监听端口）→ 重新生成 Nginx server 配置 → 引擎 reload。

---

## 管理面板功能一览

| 模块 | 功能 |
|------|------|
| 总览 | 请求量、拦截统计、配置版本、站点概览 |
| 站点管理 | 域名、回源、HTTP/HTTPS、证书、自定义拦截页 |
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
| `flowshield-waf_mysql_data` | 业务数据库 |
| `flowshield-waf_redis_data` | Redis 持久化 |
| `flowshield-waf_clickhouse_data` | 防护日志 |
| `flowshield-waf_engine_conf` | 引擎 per-site Nginx 配置 |
| `flowshield-waf_engine_certs` | SSL 证书文件 |

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

- 仅需重建 `app` 镜像；MySQL / Redis / ClickHouse 数据卷自动保留
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
```

数据库采用模型驱动建表（`create_all` + 轻量 schema patch），全新环境可用 `./scripts/fresh-start.sh` 重建；已有数据环境升级时 backend 启动会自动应用列补丁。

---

## 文档

| 文档 | 说明 |
|------|------|
| [`docs/architecture.md`](docs/architecture.md) | 架构、请求流程、配置下发、日志链路 |
| [`docs/rule-dsl.md`](docs/rule-dsl.md) | 条件 DSL、操作符、字段目录 |
| [`docs/api.md`](docs/api.md) | REST API 说明 |
| [`docs/review-after-fix.md`](docs/review-after-fix.md) | 安全加固与审查记录 |
| [`docs/upgrade.md`](docs/upgrade.md) | **版本更新**、回滚与检查清单 |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本更新日志 |
| [`deploy/baota/README.md`](deploy/baota/README.md) | 宝塔部署指南 |

---

## 许可

本项目采用 **[PolyForm Noncommercial License 1.0.0](LICENSE)**（非商业许可），**禁止商业使用**。

| 允许 | 禁止 |
|------|------|
| 个人学习、研究、测试 | 向客户收费部署或提供有偿 WAF 服务 |
| 业余项目、非营利组织内部使用 | 作为商业产品/服务销售或 SaaS 运营 |
| 在遵守许可前提下修改与再分发 | 未经授权的企业商业化使用 |

如需商业授权，请联系项目著作权人。完整条款见根目录 [`LICENSE`](LICENSE) 文件。
