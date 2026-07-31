# 流盾WAF · 规则 DSL（条件结构参考）

黑白名单、防护例外、限速、自定义规则全部复用同一套 condition 结构与字段目录。字段目录的权威来源是 `backend/app/fields/catalog.py`，前端通过 `GET /api/v1/meta/fields` 动态获取，引擎通过 `engine/lua/waf/fields_catalog.json`（由后端导出）获取。

## 1. Condition 结构

统一的嵌套 JSON，支持 AND/OR 任意层级组合：

```jsonc
{
  "logic": "and",              // "and" | "or"（组节点）
  "conditions": [
    {
      "field": "ip.src",       // 字段 key，见字段目录
      "op": "in_cidr",         // 操作符，取决于字段 value_type
      "value": "10.0.0.0/8"    // 比较值（类型随 op 而定）
    },
    {
      "field": "http.header",  // requires_arg=true 的字段
      "arg": "X-Api-Key",      // 具体键名（header/cookie/query/json 字段名等）
      "op": "is_empty"
    },
    {
      "logic": "or",           // 嵌套组
      "conditions": [
        { "field": "http.uri.path", "op": "starts_with", "value": "/admin" },
        { "field": "http.ua", "op": "regex", "value": "(sqlmap|nikto)" }
      ]
    }
  ]
}
```

- **组节点**：含 `logic` + `conditions`。
- **叶子节点**：含 `field` + `op`（+ 可选 `arg` + 可选 `value`）。
- `requires_arg=true` 的字段（如 `http.header`、`http.cookie`、`http.query`、`http.body.json`）必须提供 `arg` 指定键名。
- `is_empty` / `exists` / `key_exists` / `key_absent` 等操作符不需要 `value`。

## 2. 操作符

按字段 `value_type` 分组（源自 `OPERATORS_BY_TYPE`）：

| value_type | 可用操作符 |
| --- | --- |
| `string` | equals, not_equals, contains, not_contains, starts_with, ends_with, regex, in_list, not_in, is_empty, exists, len_gt, len_lt |
| `number` | eq, neq, gt, gte, lt, lte, between |
| `ip` | eq, in_cidr, in_list, geo_in, exists |
| `enum` | eq, neq, in_list |
| `bool` | eq |
| `traffic` | compare |
| `system` | compare |

`requires_arg=true` 的字段额外支持 `key_exists` / `key_absent`（判断键本身是否存在）。

操作符中文标签：

| op | 标签 | op | 标签 |
| --- | --- | --- | --- |
| equals | 等于 | eq | 等于 |
| not_equals | 不等于 | neq | 不等于 |
| contains | 包含 | gt | 大于 |
| not_contains | 不包含 | gte | 大于等于 |
| starts_with | 以…开头 | lt | 小于 |
| ends_with | 以…结尾 | lte | 小于等于 |
| regex | 正则匹配 | between | 介于 |
| in_list | 包含 | in_cidr | 在网段中 |
| not_in | 不包含 | geo_in | 属于地区 |
| is_empty | 为空 | key_exists | 键存在 |
| exists | 存在 | key_absent | 键不存在 |
| len_gt | 长度大于 | len_lt | 长度小于 |
| compare | 窗口比较（流量 / 系统 CPU） | | |

- `in_list` / `not_in` 的 `value` 为数组或换行/逗号分隔字符串。
- `between` 的 `value` 为 `[min, max]`。
- `compare` 用于 `traffic.*` / `system.cpu`：`value` 为对象（见下文）。

## 3. 字段目录

> 权威来源为 `catalog.py`；下表为快照。带 `arg` 标记的字段需要在条件中提供 `arg`。

### 客户端与网络

| key | 说明 | 类型 |
| --- | --- | --- |
| ip.src | 客户端 IP | ip |
| ip.src.is_private | IP 是否内网 | bool |
| net.src_port | 客户端端口 | number |
| net.dst_port | 服务端口 | number |
| net.scheme | 协议 | enum |
| http.version | HTTP 版本 | enum |

### 地理位置与情报（需启用 GeoIP2，见 architecture.md）

| key | 说明 | 类型 |
| --- | --- | --- |
| geo.country | IP 国家/地区 | string |
| geo.region | IP 省/州 | string |
| geo.city | IP 城市 | string |
| geo.asn | IP ASN | number |
| geo.isp | 运营商 ISP | string |

### 请求行

| key | 说明 | 类型 |
| --- | --- | --- |
| http.method | 请求方法 | enum |
| http.host | 请求域名 | string |
| http.url | 完整 URL | string |
| http.request_uri | 原始请求行 | string |

### URL 与路径

| key | 说明 | 类型 | arg |
| --- | --- | --- | --- |
| http.uri.path | 请求路径 | string | |
| http.uri.segment | 路径段 | string | ✓ |
| http.uri.ext | 文件后缀 | string | |
| http.uri.depth | 路径深度 | number | |
| http.uri.query | 原始查询串 | string | |

### 查询参数

| key | 说明 | 类型 | arg |
| --- | --- | --- | --- |
| http.query | 查询参数 | string | ✓ |
| http.query.count | 查询参数个数 | number | |

### 请求头

| key | 说明 | 类型 | arg |
| --- | --- | --- | --- |
| http.header | 请求头 | string | ✓ |
| http.header.count | 请求头数量 | number | |
| http.ua | User-Agent | string | |
| http.referer | Referer | string | |
| http.content_type | Content-Type | string | |
| http.content_length | Content-Length | number | |
| http.accept | Accept | string | |
| http.accept_language | Accept-Language | string | |
| http.accept_encoding | Accept-Encoding | string | |
| http.origin | Origin | string | |
| http.xff | X-Forwarded-For | string | |
| http.range | Range | string | |
| http.has_auth | 是否带 Authorization | bool | |

### Cookie

| key | 说明 | 类型 | arg |
| --- | --- | --- | --- |
| http.cookie | Cookie 参数 | string | ✓ |
| http.cookie_raw | 原始 Cookie | string | |
| http.cookie.count | Cookie 个数 | number | |

### 请求体

| key | 说明 | 类型 | arg |
| --- | --- | --- | --- |
| http.body.raw | 原始请求体 | string | |
| http.body.size | 请求体大小 | number | |
| http.body.form | 表单参数 | string | ✓ |
| http.body.json | JSON 字段 | string | ✓ |
| http.upload.filename | 上传文件名 | string | |
| http.upload.ext | 上传文件后缀 | string | |

### TLS 与指纹

| key | 说明 | 类型 |
| --- | --- | --- |
| tls.version | TLS 版本 | string |
| tls.cipher | TLS 加密套件 | string |
| tls.sni | SNI | string |
| tls.ja3 | JA3 指纹（需外部模块） | string |

### 派生维度

| key | 说明 | 类型 |
| --- | --- | --- |
| derived.args_count | 参数总数 | number |
| derived.time.hour | 当前小时 | number |
| derived.time.weekday | 星期几 | number |
| derived.fingerprint | 请求指纹 | string |

### 时间与流量 / 系统 CPU

| key | 说明 | 类型 |
| --- | --- | --- |
| traffic.global | 全站请求量（窗口比较） | traffic |
| traffic.site | 当前站点请求量（窗口比较） | traffic |
| traffic.origin_global | 全站回源请求量（窗口比较） | traffic |
| traffic.origin_site | 当前站点回源请求量（窗口比较） | traffic |
| system.cpu | 系统 CPU（窗口均值比较） | system |

`system.cpu` 示例（后台每 5 秒采样，写入 Redis `waf:system:metrics`，提供 1/5/30 分钟窗口均值）：

```json
{
  "field": "system.cpu",
  "op": "compare",
  "value": {
    "window_sec": 300,
    "compare": "container_cpu_gt",
    "threshold": 80
  }
}
```

`compare` 可选：`container_cpu_gt/lt`、`host_cpu_gt/lt`。  
`window_sec` 仅支持 `60` / `300` / `1800`。容器 CPU% 来自 cgroup，宿主机 CPU% 来自 `/proc/stat`。

## 4. 防护动作（自定义规则 mode）

| mode | 行为 |
| --- | --- |
| observe | 观察模式：仅记录日志，放行 |
| block | 拦截模式：返回 403 拦截页 |
| captcha | 人机验证：算术验证码，通过后签发 HMAC 通行 Cookie |
| js | JavaScript 挑战：浏览器执行 JS 计算后签发通行 Cookie |
