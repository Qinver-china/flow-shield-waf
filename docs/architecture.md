# 流盾WAF · 架构说明

## 总览

流盾WAF（Flow Shield WAF）是一款面向网站、业务接口和 Web 应用的智能流量防护系统，基于 OpenResty（Nginx + Lua）构建的反向代理型 WAF，核心理念为「识别 → 拦截 → 清洗 → 守护」。

部署采用 **3 个 Docker 容器**（SQLite 配置库内嵌于 `app` 卷）：

| 容器 | 技术栈 | 职责 |
| --- | --- | --- |
| `redis` | Redis 7 官方镜像 | 规则缓存、限速计数、日志 Stream |
| `clickhouse` | ClickHouse 24 | 访问/防护日志、AI 分析/预警/流量异常流水 |
| `app` | 自构建镜像（supervisord） | 后端 API、Worker、WAF 引擎、管理面板、SQLite |

`app` 容器内由 supervisord 管理四个进程：

| 进程 | 说明 |
| --- | --- |
| backend | FastAPI，127.0.0.1:8000 |
| worker | 日志消费 / 留存清理 |
| engine | OpenResty WAF，:80 / :443 |
| panel | Nginx 静态面板 + API 反代，:9000 |

## 请求处理流程（engine）

```
client ──> OpenResty access 阶段 (waf/access.lua)
             1. 解析真实客户端 IP
             2. 白名单命中 → 直接放行
             3. 黑名单命中 → 拦截/挑战
             4. 防护例外命中 → 跳过后续规则
             5. 限速命中 → 限流动作
             6. 自定义规则按优先级匹配 → 观察/拦截/人机验证/JS 挑战
             7. 记录结构化日志到 Redis Stream
           ──> 命中放行则 proxy_pass 到源站
```

匹配逻辑统一由 `waf/matcher.lua` 递归执行 condition 树，字段取值由 `waf/extractor.lua` 惰性提取，操作符由 `waf/operators.lua` 实现。字段定义与后端 `app/fields/catalog.py` 保持一致（见下文单一真源）。

## 配置下发与热更新

1. 管理员在后台增删改配置 → backend 写入 SQLite。
2. backend `services/rule_sync.py` 将全量配置序列化为 JSON 写入 Redis，并递增版本号。
3. engine 每个 worker 周期性对比版本号（`waf/sync.lua`），变化时重新加载并索引到 worker 本地内存。
4. 站点级 Nginx server 配置由 backend `services/nginx_conf.py` 生成到共享卷，并通过 Redis key 通知 engine 执行 `openresty -s reload`（`waf/reloader.lua`）。

## 字段目录：单一真源

`backend/app/fields/catalog.py` 是所有「判断维度」的唯一权威来源，被三方消费：

1. 后端条件校验（`app/fields/validator.py`）
2. 前端条件编辑器（通过 `GET /api/v1/meta/fields`）
3. 引擎字段目录 JSON（`python -m app.fields.export` 导出到 `engine/lua/waf/fields_catalog.json`），engine 在 worker 初始化时加载并用于校验规则字段是否已知。

修改字段时：更新 `catalog.py` → 同步 `extractor.lua` 的取值分支 → 重新执行 `python -m app.fields.export` 生成 JSON。

## 防护方式说明

系统支持观察、拦截、算术 captcha、JS 挑战、滑动验证等模式。其中 **算术 captcha 模式本次未做专项加固**，生产环境建议优先使用滑动验证或 JS 挑战。

## 日志模块

日志链路：`engine` 异步写入 Redis Stream → `collector.py` 消费 → ClickHouse `waf_logs` 表。

- **通用索引字段**（时间、站点、IP、动作、命中规则等）+ 类型化 `payload` JSON。
- `clickhouse_store.py` 负责批量入库；`query_clickhouse.py` 提供列表、详情与 28 维度聚合查询。
- `workers/retention.py` 按后台「日志保留天数」设置 ClickHouse TTL（默认 30 天）自动清理。

## 数据库初始化与升级

运行时 backend 启动会执行 `Base.metadata.create_all()`，根据 SQLAlchemy 模型自动建表，全新部署无需额外迁移步骤。

**版本升级**时，`services/schema_patches.py` 会在 backend 启动阶段自动补列，无需手工执行 SQL。完整更新流程见 [版本更新指南](./upgrade.md)。

开发环境全量重置：

```bash
./scripts/fresh-start.sh
```
