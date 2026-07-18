# 流盾WAF · API 说明

- Base 前缀：`/api/v1`
- 认证：除登录外均需 `Authorization: Bearer <access_token>`
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
