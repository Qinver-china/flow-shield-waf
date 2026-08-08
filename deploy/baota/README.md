# 流盾 WAF · 宝塔 (BaoTa / aaPanel) 部署指南

流盾 WAF（Flow Shield WAF）通过 Docker Compose 一键部署，可直接在宝塔面板中使用。

## 一、前置条件

1. 宝塔面板已安装 **Docker 管理器**（软件商店搜索 Docker 安装）。
2. 服务器已放行端口：`80`、`443`（WAF 对外）、`9000`（管理面板，可自定义）。

## 二、首次部署

### 1. 获取代码并配置环境变量

```bash
# 克隆项目到服务器（私有仓库需先配置 GitHub 访问：HTTPS Token 或 SSH 密钥）
cd /www/wwwroot
git clone https://github.com/Qinver-china/flow-shield-waf.git
cd flow-shield-waf

# 若已上传压缩包解压到该目录，可跳过 clone，直接进入目录后执行后续步骤

cp .env.example .env
vi .env   # 必改：REDIS 密码、JWT_SECRET、WAF_CHALLENGE_SECRET、WAF_ADMIN_PASSWORD
```

### 2. 检查端口

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

#### (a) 方案 1：本机已安装 Nginx（含宝塔 Nginx）

宝塔默认会用 Nginx 托管网站，通常已占用 80 / 443。需要把 **Nginx / 宝塔下所有网站** 的监听端口都改成其他端口（例如 `8080` / `8443`），把 80 / 443 留给流盾。

常见改法（宝塔面板）：

1. 打开宝塔 → **网站**，逐个站点进入设置
2. 把 HTTP / HTTPS 监听端口改为高位端口（如 `8080` / `8443`）
3. 保存后确认 Nginx 已重载

或在服务器上直接改 Nginx 配置（常见路径如 `/www/server/panel/vhost/nginx/`），把各站点里的 `listen 80;`、`listen 443 ssl;` 等改成新端口，然后：

```bash
nginx -t && nginx -s reload
```

改完后，流盾面板里配置站点回源时：

- 地址：推荐 `host.docker.internal`（生成 Nginx 配置时原样保留，由 Docker 内置 DNS 解析为宿主机网关）；也可直接填 `172.17.0.1` 等宿主机 IP
- HTTP 端口：填宝塔 / Nginx 的新端口（例如 `8088`），而不是 80 / 443

> - **推荐**：对外只让流盾接 80 / 443，宝塔网站全部改到高位端口，流盾再回源到这些端口  
> - **只保护部分站**：仅把被保护站点的源站指向宝塔 Nginx 的对应高位端口

### 3. 构建并启动

```bash
bash deploy/baota/install.sh
```

或直接：

```bash
docker compose up -d --build
```

将启动 **3 个容器**：`redis`、`clickhouse`、`app`（后端 + Worker + 引擎 + 面板；业务数据位于 `app_data` 卷 `/data`）。

## 三、访问

- 管理面板：`http://<服务器IP>:9000`，用 `.env` 中 `WAF_ADMIN_USER` / `WAF_ADMIN_PASSWORD` 登录。
- 添加站点后，把域名解析到本服务器，流量即经流盾 WAF 防护后回源。

## 四、版本更新

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

## 五、常用运维

```bash
docker compose ps                 # 查看状态
docker compose logs -f app        # 应用日志（含后端/引擎/面板）
docker compose restart app        # 重启应用容器
docker compose down               # 停止（勿加 -v，否则会删数据卷）
```

**构建失败（容器内 `apk add` / `npm ci` 报 temporary error）**：多为 Docker 桥接网络出网问题，与项目代码无关。Linux 宿主机可在 `docker-compose.yml` 的 `app.build` 下取消注释 `network: host` 后重新 `docker compose build app`；或在本机构建镜像后 `docker save` 传到服务器 `docker load`。

## 六、数据与备份

| 数据卷 | 内容 |
|--------|------|
| `flowshield-waf_app_data` | 业务数据：`/data/waf.db`、引擎 conf/certs |
| `flowshield-waf_redis_data` | Redis 持久化（可空卷重建） |
| `flowshield-waf_clickhouse_data` | 防护日志与流水事件（可空卷重建） |

备份示例：

```bash
# SQLite 配置库
docker compose exec -T app cp /data/waf.db /tmp/waf_backup_$(date +%Y%m%d).db
docker cp flowshield-waf-app:/tmp/waf_backup_$(date +%Y%m%d).db ./

# 业务数据卷打包
docker run --rm -v flowshield-waf_app_data:/data -v $PWD:/backup alpine \
  tar czf /backup/app_data_$(date +%Y%m%d).tgz /data
```
