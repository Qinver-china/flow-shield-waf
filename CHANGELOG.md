# 更新日志

## [0.2.0] - 2026-07-18

### Bot 识别库

- Bot 管理改为**纯识别库**：维护 UA 模式与分类，不再内置拦截动作；拦截请用黑白名单 / 自定义规则 / 限速，配合 `bot.name`、`bot.category`、`bot.is_known` 条件
- 新增**可管理 Bot 分类**（`/api/v1/bot-categories`），内置 `other` 为系统预留兜底分类
- 未命中 Bot 库但判定为爬虫时，日志 `bot_category` 统一写入 `other`（含 CrawlerDetect 兜底）

### 日志与 UA 解析

- 入库时统一解析 `ua_os`、`ua_browser`、`bot_name`、`bot_category` 等维度
- UA 库升级为 `ua-parser` + `crawlerdetect`，替代停更的 `user-agents`

### 构建

- Docker 依赖分层安装（`requirements-base` / `requirements-extra`），仅增量包触发重装
- 默认使用清华 PyPI 镜像，构建过程输出分步提示

### 迁移提示

- 原 Bot 条目上的 `action` 已移除，请改为自定义规则 + `bot.*` 字段实现放行或拦截
