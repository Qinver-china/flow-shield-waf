# 流盾 WAF · 宝塔 (BaoTa / aaPanel) 部署指南

流盾 WAF（Flow Shield WAF）通过 Docker Compose 一键部署，可直接在宝塔面板中使用。

## 一、前置条件

1. 宝塔面板已安装 **Docker 管理器**（软件商店搜索 Docker 安装）。
2. 服务器已放行端口：`80`、`443`（WAF 对外）、`9000`（管理面板，可自定义）。

## 二、端口协调（重要）

流盾 WAF 引擎需要占用 `80` / `443` 对外提供防护。若宝塔自带 Nginx 已占用这两个端口，二选一：

- 方案 A（推荐）：让宝塔 Nginx 改监听高位端口（如 `8080`/`8443`），源站改由流盾 WAF 回源；对外只暴露流盾 WAF。
- 方案 B：仅用流盾 WAF 保护部分站点，把这些站点的源站指向宝塔 Nginx 的高位端口。

站点的「源站地址」在面板「站点管理」中填写，例如 `http://127.0.0.1:8080`。

## 三、首次部署

```bash
# 1. 上传/克隆项目到服务器，例如 /www/wwwroot/flow-shield-waf
cd /www/wwwroot/flow-shield-waf

# 2. 生成配置并修改密码/密钥
cp .env.example .env
vi .env   # 必改：MYSQL/REDIS 密码、JWT_SECRET、WAF_CHALLENGE_SECRET、WAF_ADMIN_PASSWORD

# 3. 一键启动
bash deploy/baota/install.sh
```

或直接：

```bash
docker compose up -d --build
```

将启动 **4 个容器**：`mysql`、`redis`、`clickhouse`、`app`（后端 + Worker + 引擎 + 面板）。

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

# 2. 拉取代码
git pull

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
| `flowshield-waf_mysql_data` | 业务配置（站点、规则、用户） |
| `flowshield-waf_redis_data` | Redis 持久化 |
| `flowshield-waf_clickhouse_data` | 防护日志 |
| `flowshield-waf_engine_conf` | 引擎 per-site Nginx 配置 |
| `flowshield-waf_engine_certs` | SSL 证书（容器内路径 `/data/engine/certs/`） |

备份示例：

```bash
# MySQL 逻辑备份
docker compose exec -T mysql mysqldump -uwaf -p<密码> waf > backup_$(date +%Y%m%d).sql

# 数据卷打包
docker run --rm -v flowshield-waf_mysql_data:/data -v $PWD:/backup alpine \
  tar czf /backup/mysql_data_$(date +%Y%m%d).tgz /data
```
