# 更新日志

## [Unreleased]

### 部署

- Docker 命名卷收敛为 3 个：`app_data`（SQLite + 引擎 conf/certs）、`redis_data`、`clickhouse_data`
- Compose 中 Redis 默认走 TCP；镜像不再声明 engine 子路径 `VOLUME`，避免匿名卷盖住 `app_data`

### 流量基线

- 取消内置基线突增自动告警（不再写 `traffic_alerts`、打 TRAFFIC_ALERT 日志）；改由预警/AI 策略的「流量高于/低于基线」条件自行配置
- 移除 AI 防护触发类型 `traffic_intel.anomaly`；总览卡片改称「流量与基线」，不再标红异常状态
- 实时请求量：秒桶/分钟环同步 Redis，面板与告警判断只读 Redis；SQLite 仅存稀疏分钟环轻量备份（约 30s，不含 10s）；全站/分站点含 24 小时窗口

## [0.3.7] - 2026-07-20

### 站点卡片

- 站点列表改为卡片指标布局：第一行展示 24 小时总请求、拦截数、独立 IP，并附带「较昨日」对比；点击跳转对应防护日志统计页
- 第二行展示 5 / 30 / 60 分钟实时流量（请求数 + QPS）及基线偏差，样式对齐总览流量异常检测；实时流量卡片不可点击
- 底部操作改为「查看 / 编辑 / 日志 / 统计 / 更多」（更多靠右）；日志与统计默认近 24 小时；「更多」中移除重复的日志入口
- 源站、证书、客户端 IP 等元信息单行显示，超出省略

### 总览大屏

- 「安全总览」标题区改为透明背景：左侧圆角图标 + 同行副标题，下方展示 MySQL / Redis / ClickHouse 服务状态
- 右侧两行：更新时间精确到时分秒；「自动刷新」改为文案 + 开关（自顶栏移入）
- 「最新动态」改为时间线展示，并补充站点 / 规则元信息

### AI 防护

- 防御分析支持多轮工具调用：首轮仅提供近 30 分钟、最多 200 条放行日志，AI 可继续查询日志后再提交结论
- 分析结束需调用 `submit_analysis`；可选择不创建规则（事件状态 `analyzed`）
- 防护策略支持自定义提示词，触发分析时一并传给 AI
- AI 配置新增「显示悬浮 AI 助手」开关，可按需隐藏悬浮入口

### 地理字段

- 移除无数据的 `geo.ip_type` / `geo_ip_type`（引擎、字段目录、ClickHouse、规则 DSL、前端统计维度）

### 界面与其他

- 总览大屏流量异常检测与站点卡片基线展示对齐
- 日志筛选条件字段选择器优化；地理标签展示增强
- 表格分页在移动端改为小号无边框样式

## [0.3.6] - 2026-07-20

### 地理字段语义化

- 日志统计与详情：城市、省/州、ASN 常见值展示中文语义（如 `北京 (Beijing)`、`广东 (GD)`、`亚马逊 AWS (16509)`）
- 补充中国省市、美国州、常见城市与主流 ASN 映射；未知值仍显示原文

### 规则条件编辑器

- `geo.region` / `geo.city` / `geo.asn` 提供常见可视化选项
- 国家/地理等带选项字段支持「下拉选择 + 手动输入代码」
- 多选操作改为可搜索 tags，可点选也可回车添加自定义值

### 界面微调

- 条件编辑器与侧栏选中态样式微调

## [0.3.5] - 2026-07-20

### Bot 库

- 修复 Bot 库页 Tab 切换后内容空白（对齐 `fs-tabs-animated` 外置内容渲染）
- 取消内置/自定义类型限制：Bot 与分类均可编辑、删除；仅预留分类 `other` 不可删除
- 移除 Bot 启用/关闭开关，库内条目一律参与识别
- 本地 Bot 表格增加 UA 匹配模式列（Tag 展示）
- Bot 支持多分类：同一 Bot 可同时属于多个分类，规则按任一分类即可命中

### 地理与条件字段

- `geo.country` 升级为枚举字段，条件编辑器提供国家选项
- `geo.isp` 等地理字段补充选项提示与中文标签映射

### AI 防护

- 增强 AI 助手上下文、工具与提示词，改进待确认动作卡片与对话面板交互

## [0.3.4] - 2026-07-20

### 修复

- 修复日志国家/地区/运营商为空：OpenResty 镜像缺少 GeoIP2 动态模块导致 entrypoint 静默跳过 `.mmdb` 配置
- 构建阶段编译并安装 `ngx_http_geoip2_module.so`，启动时启用 GeoLite2 Country/City/ASN
- 修复 GeoIP2 构建：正确解析 `openresty/x.y.z` 版本（此前误用 `nginx/` 导致下载失败）；模块源码改为 vendored，避免依赖 GitHub clone
- GeoIP 查询源改为站点解析后的真实客户端 IP（`waf_geoip_client`），避免 CDN 场景下误查边缘节点
- 若检测到 `.mmdb` 但模块缺失，启动日志输出明确 WARN，不再静默失败

## [0.3.3] - 2026-07-20

### 界面与交互

- 顶栏控件统一为图标按钮：自动刷新、主题切换、用户菜单视觉风格一致
- 主题切换改为太阳/月亮图标，匹配日间/夜间模式认知
- 侧栏折叠触发器改为底部图标按钮，且侧栏固定在视口高度，长页面下始终可见
- Bot 库页面布局优化：远程库与本地库信息层级更清晰

### 邮件通知

- 统一引入流盾品牌化 HTML 邮件模板（含标题区、内容区、页脚）
- AI 防护触发、分析中、分析结果邮件全部支持 HTML 展示
- 预警策略通知与通知通道测试邮件改为纯文本 + HTML 双格式发送
- SMTP 发送逻辑升级为标准 multipart/alternative，提升主流邮箱客户端渲染兼容性

## [0.3.2] - 2026-07-20

### 地理维度（GeoIP）

- 新增引擎模块 `geo_lookup.lua`：规则提取与日志写入共用同一套 Geo 字段解析
- **日志懒补全**：凡写入日志的请求均补全 `geo_country` / `geo_region` / `geo_city` / `geo_asn` / `geo_isp`；规则已 trace 的字段直接复用，未 trace 的仅在日志路径批量读取 `ngx.var`（不影响未写日志的请求与未引用 `geo.*` 的规则匹配）
- **内网 IP 跳过 Geo**：规则匹配与日志补全前均判断 `util.is_private_ip`（10/8、172.16/12、192.168/16、127/8），内网地址不进行任何地理查询
- 部署支持自动启用 GeoIP2：将 MaxMind `.mmdb` 放入 `deploy/geoip/` 后容器启动自动生成 `geoip2` 配置；未配置时国家可回退 `CF-IPCountry`
- **仓库已附带** GeoLite2-Country / City / ASN 三库（`deploy/geoip/`），开箱即用；需更新时自行下载覆盖同名文件后重启 `app`
- 大屏「来源国家」统计改为仅统计**已拦截**请求（`blocked = 1`）

### 站点与 CDN

- 站点新增 **客户端 IP 获取方式**：支持直连 IP、`X-Forwarded-For`（首/末跳）、`X-Real-IP`、`CF-Connecting-IP`、`True-Client-IP`、`X-Client-IP`；影响规则 `ip.src`、限速、挑战、日志与 GeoIP
- 单值 CDN 头模式自动生成 Nginx `real_ip` 配置，使 GeoIP2 与真实客户端 IP 对齐

### Bot 识别

- CrawlerDetect 改为 **vendored 规则**：从上游 [JayBizzle/Crawler-Detect](https://github.com/JayBizzle/Crawler-Detect) 拉取 JSON，本地编译后下发引擎；移除运行时 `crawlerdetect` Python 依赖
- Bot 管理页展示 vendored 版本信息，支持「立即更新 vendored」；系统每 30 天自动同步上游
- 引擎日志入库时直接写入 `bot_name` / `bot_category` / `ua_family`；识别顺序仍为 **自建 Bot 库 → vendored 爬虫规则 → UA 启发式**
- Python 日志 enrich 优先信任引擎已写入的 bot 维度，减少重复判断
- 修复引擎 `sync.lua` 未加载 `bots` / `crawler_detect` 导致规则与日志侧 Bot 识别失效的问题
- 引擎 `bot.lua` 合并 `resolve_dimensions` 并缓存 vendored 正则匹配结果，避免日志 enrich 重复跑大正则
- `bot.name` / `bot.category` 规则求值前先确认 `ua.family` 为 bot，浏览器流量直接短路，避免重复 Bot 名称/分类判断

### URL 维度对齐

- 新增引擎共享模块 `uri_parse.lua`，规则提取与日志写入共用同一套路径/后缀/深度/查询串解析逻辑
- 修复日志 `uri_depth` 与规则 `http.uri.depth` 算法不一致的问题（统一为路径段数量）
- 统一 `uri_ext` 与 `http.uri.ext` 的后缀正则（支持字母、数字与连字符）
- 日志列 `uri` 重命名为 `request_uri`（对应 `http.request_uri`）；新增 `uri_query`（`http.uri.query`）、`referer`（`http.referer`）
- 引擎入库时直接写入 `query_count`，与 `http.query.count` 对齐
- 日志统计/筛选 UI 标注与规则字段的对应关系（如 `http.uri.path`、`http.host`）

### 字段目录 UI 对齐

- 规则条件字段选择器与日志统计/筛选维度采用统一分类（`网络与地理` / `URL 与路径` / `HTTP 请求` / `客户端识别` / `时间与流量`；日志另含 `防护命中`）
- 日志统计/筛选支持 `request_uri`（原始请求行）、`uri_query`（原始查询串）维度，与规则字段 `http.request_uri` / `http.uri.query` 对齐

## [0.3.1] - 2026-07-20

### 清理

- 移除 MySQL → SQLite 一次性迁移脚本与相关依赖（`migrate-to-sqlite.sh`、`migrate_mysql_to_sqlite.py`、`aiomysql` / `pymysql`）
- 移除 `.env` 中 MySQL 迁移专用变量与健康检查 `mysql` 兼容字段
- 总览跳转防护日志时默认时间范围改为近 24 小时（与总览数据一致）

## [0.3.0] - 2026-07-20

> **重大架构升级**：自本版本起，Docker Compose 由四容器（含 MySQL）精简为三容器；业务配置迁入嵌入式 SQLite，流水类数据统一写入 ClickHouse。从 0.2.x（MySQL 版）升级请务必阅读下方「迁移指引」。

### 存储架构（核心）

- 业务配置库由 MySQL 改为嵌入式 **SQLite**（`DB_PATH`，默认 `/data/waf.db`），Docker Compose **移除 `mysql` 服务**
- 流水数据迁移至 **ClickHouse** 三张表：`ai_guard_incidents`、`alert_notification_logs`、`traffic_alerts`
- AI 对话历史（`ai_guard_chat_*`）仍保存在 SQLite
- 废弃遗留 `rule_suggestion` 表与 `/rule-suggestions` API
- 新增 `scripts/migrate_mysql_to_sqlite.py` 与 `scripts/migrate-to-sqlite.sh` 一键迁移（可选导入历史流水至 ClickHouse）
- 仪表盘健康检查展示 SQLite 状态（保留 `mysql` 字段名兼容旧前端）

### 分析与流水层

- 新增 `backend/app/services/analytics/`：`incident_store`、`alert_log_store`、`traffic_alert_store`
- AI 防护流水线、预警评估、流量异常、仪表盘动态等改为读写 ClickHouse 流水表
- 修复 ClickHouse 24 下 `argMax` 嵌套聚合报错（incident 列表查询）
- 修复 `LogSampler` 对 `named_results()` 生成器误用 `len()` 的问题

### AI 防护增强

- AI 分析完成后发送 HTML 邮件通知，含建议规则摘要与「应用规则」「忽略」操作链接
- 新增 JWT 鉴权公开接口（10 分钟有效）：`/api/v1/ai-guard/incidents/actions/apply|dismiss`
- 面板外网地址改为 **系统设置 → 显示设置** 配置（`panel_public_url`），首次访问自动从请求推断（含端口）
- 分析记录页状态文案中文化（pending / analyzing / suggested / applied / failed / dismissed）

### 规则与筛选

- 站点筛选改为仅匹配**明确绑定站点**的规则（不含全局规则），与列表语义一致
- 迁移遗留 `site_ids='null'` 文本由 schema patch 自动清理

### 运维与部署

- `docker-compose.yml` 调整为 redis + clickhouse + app 三服务
- 面板 Nginx 反代补充 `Host $http_host` 与 `X-Forwarded-Port`，修复自动推断面板地址丢端口
- `.env.example`、`docs/architecture.md`、`docs/upgrade.md`、`deploy/baota/README.md` 同步更新

### 迁移指引（0.2.x MySQL → 0.3.0）

在**已运行旧版四容器**的服务器上：

```bash
git pull origin main
bash scripts/migrate-to-sqlite.sh    # 备份 MySQL → 迁移 SQLite/ClickHouse → 重建三容器栈
```

全新部署直接 `docker compose up -d --build`，无需迁移脚本。完整步骤见 `scripts/migrate-to-sqlite.sh` 头部注释与 `README.md`。

## [0.2.14] - 2026-07-20

### AI 智能助手

- 完整页 `/ai-guard` 离开再进入时自动恢复最近会话，与悬浮窗共用会话记忆
- 悬浮按钮支持拖动并记忆位置；在 AI 智能助手完整页隐藏悬浮入口
- 小屏下完整页侧栏可折叠收起，主区域全宽显示对话
- 欢迎区快捷提示宽屏横排、间距优化；会话列表去除外框留白，选中项浅底高亮
- 悬浮窗使用 `v-show` 保持状态，关闭后再次打开不丢失对话进度

## [0.2.13] - 2026-07-20

### AI 智能助手

- 悬浮窗关闭后重新打开时自动恢复上次会话，不再每次重置为新对话
- 输入框上方快捷提示仅在无消息的新会话中显示
- 修复历史消息加载时 `steps` 未定义导致助手回复无法渲染的问题

## [0.2.12] - 2026-07-19

### AI 智能助手

- 新增全局悬浮窗入口，支持侧栏会话列表、新对话与一键清空全部会话
- 聊天改为 SSE 真流式输出，展示思考过程、工具调用与最终回复；支持 Markdown 渲染
- AI 可自主按条件查询 ClickHouse 拦截日志与统计
- 修复历史会话仅显示用户消息、流式超时后页面空白等问题；放宽 Nginx SSE 代理超时并增加保活
- 悬浮窗 compact 模式字号优化

### 防护资源

- 规则、限速、黑白名单支持自定义拦截页（状态码与 HTML 模板）
- 资源管理支持 JSON 批量导入

### 运维

- Docker 各服务日志轮转（单文件 50MB、保留 3 份）；补充 ClickHouse 相关环境变量说明
- ClickHouse 默认关闭 query_log，降低磁盘占用

## [0.2.11] - 2026-07-19

### 流量基线

- 基线学习支持冷启动与稳定两档样本门槛：先显示初步基线，样本充足后再参与异常告警
- 历史不足时自动放宽时间槽（同星期同时段 → 同小时 → 仅小时）以加快首次出数
- 基线重算间隔由 1 小时缩短为 15 分钟；修复 ClickHouse 查询时区边界
- 总览异常检测卡片在基线未稳定时显示「学习中」

### Bot 识别

- 引擎集成 CrawlerDetect 规则库，与日志 enrich 对齐，识别常见爬虫 UA
- 规则同步下发 `crawler_detect` 配置；`bot_name` 优先 Bot 库命中，其次爬虫签名

## [0.2.10] - 2026-07-19

### 规则匹配

- 新增 `ua.family`（UA 类型）、`ua.os`（操作系统）条件维度，与日志统计一致
- 「包含字符串 / 排除字符串」支持多值输入（回车添加）
- 字段选择改为自定义弹层：分类小标题 + 三列按钮网格，支持搜索

### 总览

- 流量异常检测仅展示基线窗口（1 分钟～60 分钟），实时流量保留 10 秒 / 30 秒计数
- 优化流量与异常检测卡片布局与字号

## [0.2.8] - 2026-07-18

### 性能

- **ClickHouse 日志写入**：collector 批次默认 2000、支持积压连续 drain；ingest 线程复用连接并默认开启 `async_insert`；默认 detach 小时聚合物化视图以降低写入 CPU（可通过 `CLICKHOUSE_HOURLY_MV_ENABLED=true` 恢复）
- **Worker enrich**：批量共享 bot 目录快照，减少每条日志重复加载
- **引擎日志路径**：`capture_baseline` 单次采集；多条 observe 命中仅保留最后一条日志；全匹配 catch-all observe 规则自动置底；traffic 窗口聚合仅在 worker 0 执行

### 日志

- 明细列表域名、IP、方法、URL 等列支持与统计页一致的快捷筛选与资源下钻

### 界面

- 资源管理列表移动端卡片间距优化

## [0.2.7] - 2026-07-18

### 日志

- 修复统计/明细页「查看当前规则」等资源详情因缺少 GET 接口返回 405 的问题

### Bot 库

- 顶部分类筛选支持多选，并修复选项加载后下拉为空的问题
- 表格增加备注列，移除 UA 模式与生效站点列；新增/编辑表单不再配置站点
- 分类管理表格增加备注列

## [0.2.6] - 2026-07-18

### 日志

- 统计页与明细页共用统一筛选栏：扩展时间维度，支持多条件组合（等于/包含/不等于/不包含/模糊匹配）
- 统计表格与明细「命中规则」等维度支持点击菜单：添加到筛选、查看资源管理、下钻日志明细
- 修复「已拦截」筛选导致统计接口 500 的 ClickHouse 列名冲突问题
- 修复 URL `dimension` 参数在统计页未自动选中的问题
- 窄屏下时间维度改为下拉选择；统计卡片移至结果列上方

## [0.2.5] - 2026-07-18

### 仪表盘

- 修复自动刷新时顶部时间范围不同步的问题；时间显示精确到秒
- 自动刷新轮询间隔由 5 秒调整为 8 秒

## [0.2.4] - 2026-07-18

### 仪表盘

- 顶部时间范围与图表轴时间按系统时区正确显示；刷新前先更新时间再发起请求
- 自动刷新默认开启；改为请求完成后延时 5 秒再轮询，避免网络阻塞时并发重复请求
- 实时刷新时图表与安全动态列表静默更新，不再反复出现加载动画

### 界面

- 侧边栏触发器与 Logo 区域背景样式微调

## [0.2.3] - 2026-07-18

### 流量异常检测

- 基线计算改用系统时区、15 分钟时间槽、28 天回看、中位数 + 95 分位异常值剔除
- 支持全站与各启用站点分别计算基线；引擎快照新增 `sites` 维度
- 告警规则条件扩展 `traffic.global` / `traffic.site`，支持多时间窗口与 QPS、基线百分比比较
- 修复 `options_for_field()` 未包含 `TRAFFIC` 类型导致时间窗口下拉选项不全的问题
- 修复 Alpine 容器缺少 `tzdata` 时流量智能接口 502 的问题

### 仪表盘

- 实时流量与流量异常检测卡片支持按站点筛选
- 顶栏新增「实时刷新」开关（默认关闭，5 秒轮询，偏好写入 localStorage）
- 实时刷新时图表静默更新数据，避免重复销毁重建与加载动画闪烁

### 列表与日志

- 资源列表支持站点筛选、名称悬停快捷操作、规则名称解析展示
- 日志详情与统计页增强；列表筛选栏与条件编辑器小幅优化

### 构建

- Docker 镜像补充 `tzdata`；宝塔部署文档更新

## [0.2.2] - 2026-07-18

### 修复

- 移除 `logging` 包 `__init__` 中的预加载导入，避免导入 `crawler_detect` 时触发 enrich 循环依赖

## [0.2.1] - 2026-07-18

### 修复

- 修复 `bot_identify` ↔ `crawler_detect` 循环导入导致后端/worker 无法启动、管理面板 API 全部 502 的问题

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
