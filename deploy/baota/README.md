# 流盾 WAF · 宝塔 (BaoTa / aaPanel) 部署指南

流盾 WAF（Flow Shield WAF）通过 Docker Compose 部署，可直接在宝塔面板中使用。

**推荐优先使用一键脚本**（安装与更新同一命令）：

```bash
# 在 /www/wwwroot 等目标目录执行
# 推荐
curl -fsSL https://fswaf.top/install.sh | bash
# 备用
curl -fsSL https://raw.githubusercontent.com/Qinver-china/flow-shield-waf/main/install.sh | bash
```

官网文档：[快速开始](https://fswaf.top/guide/quick-start) · [宝塔手动步骤](https://fswaf.top/guide/baota)

安装与更新统一使用仓库根目录的 `install.sh`（或上方一键命令）。

## 一、前置条件

1. 宝塔面板已安装 **Docker 管理器**（软件商店搜索 Docker 安装），或由一键脚本自动安装 Docker。
2. 服务器已放行端口：`80`、`443`（WAF 对外）、`9000`（管理面板，可自定义）。

## 二、手动首次部署

### 1. 获取代码并配置环境变量

```bash
cd /www/wwwroot
git clone https://github.com/Qinver-china/flow-shield-waf.git
cd flow-shield-waf

cp .env.example .env #仅首次安装拷贝
vi .env   # 推荐修改：REDIS 密码、JWT_SECRET、WAF_CHALLENGE_SECRET、WAF_ADMIN_PASSWORD
```

### 2. 检查端口

确认 `80` / `443` 空闲。宝塔 Nginx 占用时，把各网站 listen 改为高位端口（如 `8080` / `4343`），把 `80` / `443` 留给流盾，然后：

```bash
nginx -t && nginx -s reload
```

面板里配置站点回源时填写新端口。一键脚本可自动改写 Nginx 的 `listen` 行（会先备份）。

### 3. 构建并启动

```bash
bash install.sh
# 或
docker compose up -d --build
```

将启动 **3 个容器**：`redis`、`clickhouse`、`app`。

## 三、访问

- 管理面板：`http://<服务器IP>:9000`，用 `.env` 中账号登录。
- 添加站点后，把域名解析到本服务器即可。

## 四、版本更新

```bash
cd /www/wwwroot/flow-shield-waf
bash install.sh
```

或再次执行官网一键命令。手动步骤见 [`docs/upgrade.md`](../../docs/upgrade.md)。

## 五、常用运维

```bash
docker compose ps
docker compose logs -f app
docker compose restart app
docker compose down               # 停止（勿加 -v）
```

**构建失败（容器内 apk/npm 出网问题）**：可在 `docker-compose.yml` 的 `app.build` 下取消注释 `network: host` 后重新 `docker compose build app`。
