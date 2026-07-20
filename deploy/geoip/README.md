# MaxMind GeoIP2 数据库

本目录已附带 GeoLite2 数据库，**开箱即用**，无需自行下载：

| 文件名 | 用途 |
|--------|------|
| `GeoLite2-Country.mmdb` | 国家代码（`geo.country` / `geo_country`） |
| `GeoLite2-City.mmdb` | 省/州、城市（`geo.region` / `geo.city`） |
| `GeoLite2-ASN.mmdb` | ASN、运营商（`geo.asn` / `geo.isp`） |

`docker-compose.yml` 已将 `./deploy/geoip` 挂载到容器内 `/etc/nginx/geoip`。启动或重启 `app` 容器后，entrypoint 会自动检测上述文件并启用 GeoIP2，**无需修改 Nginx 配置**。

```bash
docker compose restart app
```

## 是否需要更新？

- **不需要更新**：直接使用本目录现有文件即可，不用做任何操作。
- **需要更新**：自行前往 [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) 注册并下载最新 `.mmdb`，**覆盖**本目录中同名文件后，重启 `app` 容器。

MaxMind 建议定期更新库以保持地理信息准确；是否更新由你自行决定，本项目不内置自动拉取。

## 其他说明

- 站点接入 CDN 时，请在面板 **站点管理 → 客户端 IP 获取方式** 选择与 CDN 一致的头字段，以便 GeoIP 解析到真实客户端 IP（详见根目录 `README.md`）。
- **内网 IP**（`10/8`、`172.16/12`、`192.168/16`、`127/8`）不进行任何地理查询。
- **规则匹配**：仅当规则引用 `geo.*` 字段时才读取 GeoIP。
- **日志写入**：写入日志时懒补全地理字段；规则已 trace 的字段直接复用。
- 未启用 GeoIP2 时，公网 IP 的国家可回退 `CF-IPCountry`（Cloudflare）。
