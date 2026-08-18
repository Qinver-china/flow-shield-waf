# 流盾WAF · API 说明

- Base 前缀：`/api/v1`
- 认证：除登录、初始账号设置外均需 `Authorization: Bearer <access_token>`
- 交互式文档（`ENABLE_DOCS=true` 时）：`/docs`（Swagger）、`/redoc`

## 统一响应结构

```json
{ "code": 0, "message": "ok", "data": { } }
```

`code=0` 表示成功；分页数据形如 `{ "items": [...], "total": 123, "page": 1, "page_size": 20 }`。

## 认证 `/auth`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/login` | 用户名密码登录，返回 access/refresh token |
| POST | `/auth/refresh` | 用 refresh token 换取新 access token |
| GET | `/auth/me` | 当前登录用户信息 |
| GET | `/auth/setup-status` | 公开接口：库中是否已有管理员（`needs_setup`） |
| POST | `/auth/initial-setup` | 公开接口：无管理员时创建首个账号并返回 token |

## 元数据 `/meta`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/meta/fields` | 字段目录（分组）+ 操作符，供前端条件编辑器 |
| GET | `/meta/enums` | 枚举值（防护方式、名单类型等） |

## 站点 `/sites`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/sites` | 列表（分页） |
| POST | `/sites` | 新建站点，触发规则下发 + Nginx 配置生成/reload |
| GET | `/sites/{id}` | 详情 |
| PUT | `/sites/{id}` | 更新，触发重新下发 |
| DELETE | `/sites/{id}` | 删除，移除对应 Nginx 配置 |

## 自定义规则 `/rules`

标准 CRUD。请求体含 `conditions`（见 `rule-dsl.md`）与 `mode`（observe/block/captcha/js）、`priority`、`enabled`。写操作触发向 Redis 下发。

## 黑白名单 `/blacklist`、`/whitelist`

两者共用 CRUD 结构（内部由 `_iplist.py` 工厂生成）。请求体含 `conditions`，`list_type` 由端点自动决定。

## 防护例外 `/exceptions`

标准 CRUD，命中 `conditions` 的请求跳过后续规则匹配。

## 限速 `/ratelimit`

标准 CRUD。请求体含匹配 `conditions`、限速 `keys`（按哪些字段聚合计数）、阈值与时间窗口、动作。

## 日志 `/logs`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/logs` | 按时间段、站点、IP、动作、命中规则等过滤 + 分页 |
| GET | `/logs/stats` | 聚合统计（按动作/规则/时间等） |

## 仪表盘 `/dashboard`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/dashboard/overview` | 概览卡片数据 |
| GET | `/dashboard/stats` | 趋势/分布图表数据 |

## 面板账号 `/panel-connections`

外部宝塔 / 1Panel 账号。列表不回显完整 API 密钥；备份「系统设置」分区会包含该表（含密钥明文）。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/panel-connections` | 账号列表 |
| POST | `/panel-connections` | 新建 |
| POST | `/panel-connections/test` | 未保存账号测连 |
| GET/PUT/DELETE | `/panel-connections/{id}` | 详情 / 更新 / 删除；更新时密钥留空表示不改 |
| POST | `/panel-connections/{id}/test` | 已保存账号测连 |
| GET | `/panel-connections/{id}/sites` | 预览可导入站点（不含私钥） |
| POST | `/panel-connections/{id}/sites/import` | 按 key 批量导入站点与已部署证书 |
| GET | `/panel-connections/{id}/certificates` | 预览可导入证书（不含私钥） |
| POST | `/panel-connections/{id}/certificates/import` | 按 key 批量导入证书 |

`provider` 为 `baota` 或 `onepanel`。同服务器账号导入时回源默认 `host.docker.internal`，80/443 纠正为 8080/4343。`GET /panel-connections/{id}/sites?purpose=sync` 用于证书续期推送选站：不把「域名已在流盾」标成不可选。

## 证书 `/certificates`

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/certificates` | 列表（分页） |
| POST | `/certificates` | 粘贴 PEM 新建 |
| POST | `/certificates/upload` | 上传证书/私钥文件 |
| GET | `/certificates/{id}` | 详情（含 PEM） |
| PUT | `/certificates/{id}` | 更新 |
| DELETE | `/certificates/{id}` | 删除（被站点引用时拒绝） |
| POST | `/certificates/acme/issue` | 申请免费证书 |
| POST | `/certificates/acme/issue/stream` | 同上，SSE 进度 |
| POST | `/certificates/{id}/sync-to-panels` | 将当前 PEM 推送到已配置的宝塔 / 1Panel 站点 |

自动续期可附带 `panel_push_enabled` 与 `panel_push_targets`（`[{ "connection_id": 1, "site_keys": ["..."] }]`）。续期成功后后台会按该配置推送，并把同步结果写进同一封续期通知（未开启推送时通知内容不变）。`sync-to-panels` 的 body 可带 `targets` 覆盖已存配置以便测试。申请接口未提交这两个字段时，覆盖已有证书会保留原推送配置。推送到宝塔后会调用 `CloseToHttps` 关闭面板默认打开的强制 HTTPS；1Panel 使用 `HTTPAlso`，不会打开 `HTTPToHTTPS`。
