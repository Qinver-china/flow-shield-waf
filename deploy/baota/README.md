# 流盾 WAF · 宝塔 (BaoTa / aaPanel) 部署指南

流盾 WAF（Flow Shield WAF）通过 Docker Compose 一键部署，可直接在宝塔面板中使用。

## 一、前置条件

1. 宝塔面板已安装 **Docker 管理器**（软件商店搜索 Docker 安装）。
2. 服务器已放行端口：`80`、`443`（WAF 对外）、`9000`（管理面板，可自定义）。

## 二、端口协调（重要）

流盾 WAF 引擎需要占用 `80` / `443` 对外提供防护。若宝塔自带 Nginx 已占用这两个端口，二选一：

- 方案 A（推荐）：让宝塔 Nginx 改监听高位端口（如 `8080`/`8443`），源站改由流盾 WAF 回源；对外只暴露流盾 WAF。
- 方案 B：仅用流盾 WAF 保护部分站点，把这些站点的源站指向宝塔 Nginx 的高位端口。

站点的「源站地址」在面板「站点管理」中填写。推荐 `host.docker.internal`（生成 Nginx 配置时原样保留，由 Docker 内置 DNS 解析为宿主机网关）；也可直接填 `172.17.0.1` 等宿主机 IP。HTTP 端口填宝塔监听端口，例如 `8088`。

## 三、首次部署

```bash
# 1. 克隆项目到服务器（私有仓库需先配置 GitHub 访问：HTTPS Token 或 SSH 密钥）
cd /www/wwwroot
git clone https://github.com/Qinver-china/flow-shield-waf.git
cd flow-shield-waf

# 若已上传压缩包解压到该目录，可跳过 clone，直接进入目录后执行后续步骤

# 2. 生成配置并修改密码/密钥
cp .env.example .env
vi .env   # 必改：REDIS 密码、JWT_SECRET、WAF_CHALLENGE_SECRET、WAF_ADMIN_PASSWORD

# 3. 一键启动
bash deploy/baota/install.sh
```

或直接：

```bash
docker compose up -d --build
```

将启动 **3 个容器**：`redis`、`clickhouse`、`app`（后端 + Worker + 引擎 + 面板；业务数据位于 `app_data` 卷 `/data`）。

## 四、访问

- 管理面板：`http://<服务器IP>:9000`，用 `.env` 中 `WAF_ADMIN_USER` / `WAF_ADMIN_PASSWORD` 登录。
- 添加站点后，把域名解析到本服务器，流量即经流盾 WAF 防护后回源。

## 五、版本更新

在已部署环境中升级新版本：

```bash
cd /www/wwwroot/flow-shield-waf   # 按实际路径

# 推荐：使用更新脚本（含备份 .env、拉代码、重建）
bash deploy/baota/upgrade.sh
```

或手动执行：

```bash
# 1. 备份配置
cp .env .env.bak.$(date +%Y%m%d)

# 2. 拉取代码（默认分支 main）
git pull origin main

# 3. 检查 .env 是否有新增变量（对照 .env.example）
diff .env.example .env || true

# 4. 重建并启动（数据卷保留，不会丢站点/规则/日志）
docker compose up -d --build

# 5. 验证
docker compose ps
curl -fsS http://127.0.0.1:9000/health
curl -fsS http://127.0.0.1/waf-health
```

**注意：**

- 更新过程会短暂重建 `app` 容器，代理可能有 10–30 秒抖动
- 不要在生产环境随意修改 `JWT_SECRET`、`WAF_CHALLENGE_SECRET`
- 数据库结构变更由程序自动 patch，无需手工 SQL

详细说明见 [`docs/upgrade.md`](../../docs/upgrade.md)。

## 六、常用运维

```bash
docker compose ps                 # 查看状态
docker compose logs -f app        # 应用日志（含后端/引擎/面板）
docker compose restart app        # 重启应用容器
docker compose down               # 停止（勿加 -v，否则会删数据卷）
```

## 七、数据与备份

| 数据卷 | 内容 |
|--------|------|
| `flowshield-waf_app_data` | 业务数据：`/data/waf.db`、引擎 conf/certs |
| `flowshield-waf_redis_data` | Redis 持久化（可空卷重建） |
| `flowshield-waf_clickhouse_data` | 防护日志与流水事件（可空卷重建） |

从旧六卷布局升级时，先执行：`bash scripts/migrate-app-volume.sh`。

备份示例：

```bash
# SQLite 配置库
docker compose exec -T app cp /data/waf.db /tmp/waf_backup_$(date +%Y%m%d).db
docker cp flowshield-waf-app:/tmp/waf_backup_$(date +%Y%m%d).db ./

# 业务数据卷打包
docker run --rm -v flowshield-waf_app_data:/data -v $PWD:/backup alpine \
  tar czf /backup/app_data_$(date +%Y%m%d).tgz /data
```
