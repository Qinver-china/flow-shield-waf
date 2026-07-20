# 流盾 WAF · 版本更新指南

本文说明在**已部署环境**上升级流盾 WAF 的标准流程。适用于 Docker Compose 部署（含宝塔）。

---

## 更新会影响什么

| 变更类型 | 是否需要重建镜像 | 是否丢数据 | 业务影响 |
|----------|------------------|------------|----------|
| 应用代码（backend / frontend / engine） | 是（`app` 镜像） | 否 | 重建 `app` 时约 10–30 秒代理短暂抖动 |
| `.env` 环境变量 | 通常需重启 `app` | 否 | 改密钥会导致已登录会话失效 |
| 数据库表结构（schema patch） | 否 | 否 | 后端启动时自动执行，无需手工迁移 |
| 规则 / 限速 / 黑白名单 | 否 | 否 | Redis 热同步，无需 reload |
| 站点域名 / 监听端口 / 证书路径 | 否 | 否 | 自动 Nginx reload，秒级生效 |

**数据卷在常规更新中不会删除**，站点、规则、日志均保留。

---

## 标准更新流程（推荐）

在服务器项目根目录执行：

### 1. 备份（生产强烈建议）

```bash
cd /path/to/flow-shield-waf

# 备份 .env
cp .env .env.bak.$(date +%Y%m%d)

# 备份 SQLite 配置库
docker compose exec -T app cp /data/waf.db /tmp/waf_backup_$(date +%Y%m%d).db
docker cp flowshield-waf-app:/tmp/waf_backup_$(date +%Y%m%d).db ./

# 或打包数据卷（可选）
docker run --rm \
  -v flowshield-waf_waf_sqlite:/data \
  -v "$(pwd)":/backup alpine \
  tar czf /backup/waf_sqlite_$(date +%Y%m%d).tgz /data
```

### 2. 拉取新版本代码

```bash
git fetch origin
git pull origin main   # 或切换到指定版本：git checkout <tag/branch> && git pull origin <tag/branch>
```

若通过压缩包更新，解压覆盖代码目录，**保留原有 `.env` 文件**，不要直接覆盖。

### 3. 核对新增环境变量

对比 `.env` 与 `.env.example`，将新版本新增的变量补进 `.env`：

```bash
diff .env.example .env || true
```

常见新增项示例（以当前版本为准）：

| 变量 | 说明 |
|------|------|
| `WAF_ALLOW_INSECURE_DEFAULTS` | 是否允许默认密钥（生产保持 `false`） |
| `CORS_ORIGINS` | 面板跨域来源 |
| `CLICKHOUSE_*` | 日志库连接（Compose 内通常用默认值即可） |

> **不要**在更新时随意修改 `JWT_SECRET`、`WAF_CHALLENGE_SECRET`，否则已签发 Token 与挑战 Cookie 会失效。

### 4. 重建并启动

```bash
docker compose up -d --build
```

仅重建应用容器、不动数据库时也可：

```bash
docker compose build app
docker compose up -d app
```

### 5. 验证

```bash
# 容器健康
docker compose ps

# 面板与引擎
curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1/waf-health

# 查看启动日志（关注 schema patch、config publish）
docker compose logs --tail=80 app
```

可选：运行集成回归脚本

```bash
bash deploy/smoke_test.sh http://127.0.0.1:9000 http://127.0.0.1
```

### 6. 登录面板确认

1. 打开管理面板，确认可正常登录
2. **总览** 页查看配置版本号是否递增
3. 抽查站点访问与一条测试规则是否生效

---

## 数据库与结构变更

项目**不使用 Alembic**，采用：

1. 首次启动：`create_all()` 自动建表
2. 后续升级：`backend/app/services/schema_patches.py` 在 backend 启动时自动补列

更新后若 backend 日志出现 `schema patch applied: ...` 属正常现象。无需手工执行 SQL。

---

## 仅更新部分组件

| 场景 | 命令 |
|------|------|
| 只改了 Lua 引擎 | `docker compose up -d --build app` |
| 只改了后端/前端 | `docker compose up -d --build app` |
| 修改了 `docker-compose.yml` 或基础镜像 | `docker compose up -d --build` |
| 仅重启应用进程 | `docker compose restart app` |
| 更新 ClickHouse 初始化 SQL | 需自行评估；已有数据卷不会自动重放 init |

---

## 回滚

若新版本异常，可回退代码后重建：

```bash
git checkout <previous-tag-or-commit>
docker compose up -d --build app
```

若已执行不可逆 schema patch，回滚代码后一般仍可运行（新增列通常向后兼容）；严重问题可从备份恢复 MySQL 数据卷。

---

## 全量重置（⚠️ 会清空所有数据）

**仅用于开发/测试**，生产勿用：

```bash
./scripts/fresh-start.sh
```

将删除所有 Docker 数据卷并从头部署。

---

## 宝塔环境更新

与标准流程相同，在项目根目录执行：

```bash
cd /www/wwwroot/flow-shield-waf   # 按实际路径
git pull origin main
docker compose up -d --build
```

也可使用快捷脚本（若已提供）：

```bash
bash deploy/baota/upgrade.sh
```

---

## 更新后检查清单

- [ ] `docker compose ps` 四个服务均为 `healthy`（或 `running`）
- [ ] `/health` 与 `/waf-health` 返回正常
- [ ] 面板可登录，总览配置版本正常
- [ ] 至少一个受保护站点可访问源站
- [ ] 防护日志有新数据写入（若有机流量）
- [ ] `.env` 中无意外改动的生产密钥
