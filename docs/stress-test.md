# 防护压测

脚本路径：[`scripts/stress_test.py`](../scripts/stress_test.py)

仅依赖 **Python 3 标准库**，无需额外安装包。按阶段以固定 QPS 向目标站点发起随机 URL 访问；采用开环调度（按 `1/QPS` 间隔发出，不等待上一响应），优先保证实际发出速率达标。

## 默认流程

| 阶段 | QPS | 时长 |
|------|-----|------|
| 1 | 20 | 2 分钟 |
| 2 | 50 | 2 分钟 |
| 3 | 100 | 2 分钟 |

每个阶段开始前 / 结束后各发 **1 条标记请求**（不计入该阶段 QPS 统计），在 URL 与 Header 中标明阶段名与 `start` / `end`，便于在防护日志中对齐时间窗。

## 常用命令

在仓库根目录执行：

```bash
# 完整压测（默认三阶段：20 → 50 → 100 QPS，各 2 分钟）
python3 scripts/stress_test.py --url https://你的站点.com

# 经引擎 IP 访问、按域名匹配站点（设置 Host）
python3 scripts/stress_test.py --url http://127.0.0.1 --host your.site.com

# 混入少量攻击/扫描特征 URL（约 8%，用于触发防护规则）
python3 scripts/stress_test.py --url https://你的站点.com --mix-attack

# 导出 JSON 汇总报告
python3 scripts/stress_test.py --url https://你的站点.com --report report.json

# 自签证书 / 跳过 TLS 校验
python3 scripts/stress_test.py --url https://你的站点.com --insecure

# 短时冒烟（各阶段 10 秒，阶段间冷却 2 秒）
python3 scripts/stress_test.py --url https://你的站点.com \
  --phases 20:10,50:10,100:10 --cooldown 2

# 自定义阶段：格式为 QPS:秒[,QPS:秒...]
python3 scripts/stress_test.py --url https://你的站点.com \
  --phases 20:120,50:120,100:120
```

查看全部参数：

```bash
python3 scripts/stress_test.py --help
```

## 参数说明

| 参数 | 说明 | 默认 |
|------|------|------|
| `--url` | 目标站点根 URL（必填） | — |
| `--host` | 覆盖 `Host` 头（经 IP 打引擎时用） | 无 |
| `--phases` | 阶段列表 `QPS:秒,...` | `20:120,50:120,100:120` |
| `--concurrency` | 在途请求并发上限；`0` 为按 `max(QPS)×5` 估算 | `0` |
| `--timeout` | 单请求超时（秒） | `10` |
| `--cooldown` | 阶段之间冷却（秒） | `5` |
| `--mix-attack` | 混入攻击/扫描特征 URL | 关 |
| `--insecure` | 跳过 TLS 证书校验 | 关 |
| `--follow-redirects` | 跟随重定向（默认不跟，便于观察挑战/拦截状态码） | 关 |
| `--report` | 将汇总写入 JSON 文件 | 无 |

## 阶段标记请求

便于在 ClickHouse / 防护日志中按阶段切分：

- **URL**：`/__flowshield_stress__/phase{N}-{qps}qps-{dur}s/{start|end}?phase=...&event=start|end&...`
- **Header**（节选）：
  - `X-Stress-Phase`：ASCII 阶段 ID（如 `phase1-20qps-120s`）
  - `X-Stress-Phase-Name`：阶段名（percent-encoding，规避 HTTP Latin-1 限制）
  - `X-Stress-Event`：`start` 或 `end`
  - `X-Stress-Phase-Index` / `X-Stress-Target-QPS` / `X-Stress-Duration-S`

开始标记在压测发出前发送；结束标记在本阶段在途请求收完后发送。

## 输出指标

每个阶段结束会打印：

- 目标 QPS / **实际发出 QPS**（按发出窗口计，不含等待慢响应收尾）
- 实际完成 QPS、成功数（2xx/3xx）与成功率
- 延迟：min / avg / p50 / p90 / p95 / p99 / max（毫秒）
- 状态码分布、异常分布

全部阶段「发出 QPS ≥ 目标 × 95%」时进程退出码为 `0`，否则为 `1`。

## 注意

- 压测对象应为 **WAF 防护的业务站点**（经引擎 `:80`/`:443`），不要直接打管理面板 `:9000`
- 生产环境请控制时长与 QPS，避免影响正常业务
- 随机路径可能返回 404，属预期；关注发出 QPS、延迟与防护日志中的拦截/挑战记录即可
