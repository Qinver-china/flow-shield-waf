#!/usr/bin/env python3
"""流盾 WAF 防护压测脚本（仅依赖 Python 3 标准库）。

按阶段以固定 QPS 向目标站点发起随机 URL 访问。采用开环调度：
按 1/QPS 间隔发出请求，不等待上一响应完成，优先保证实际发出速率达标。

示例:
  python3 scripts/stress_test.py --url https://example.com
  python3 scripts/stress_test.py --url http://127.0.0.1 --host site.example.com
  python3 scripts/stress_test.py --url https://example.com --phases 20:120,50:120,100:120
  python3 scripts/stress_test.py --url https://example.com --mix-attack --report report.json

快速冒烟（各阶段 5 秒）:
  python3 scripts/stress_test.py --url https://httpbin.org --phases 5:5,10:5 --cooldown 1
"""

from __future__ import annotations

import argparse
import http.client
import json
import math
import random
import ssl
import string
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urljoin, urlparse


# ---------------------------------------------------------------------------
# URL / 请求模拟
# ---------------------------------------------------------------------------

PATH_TEMPLATES = [
    "/",
    "/index.html",
    "/home",
    "/about",
    "/products",
    "/products/{id}",
    "/products/{slug}",
    "/category/{slug}",
    "/blog",
    "/blog/{id}",
    "/blog/{slug}",
    "/news/{id}",
    "/api/v1/health",
    "/api/v1/items",
    "/api/v1/items/{id}",
    "/api/v1/search",
    "/api/v1/users/{id}",
    "/api/v1/orders/{id}",
    "/search",
    "/user/profile",
    "/user/settings",
    "/cart",
    "/checkout",
    "/static/css/app.css",
    "/static/js/main.js",
    "/static/img/{slug}.png",
    "/assets/{slug}.js",
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/page/{id}",
    "/p/{slug}",
    "/tag/{slug}",
    "/docs/{slug}",
]

QUERY_KEYS = [
    "page", "q", "id", "sort", "limit", "offset", "lang", "ref", "utm_source",
    "utm_medium", "category", "filter", "from", "to",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

ATTACK_PATHS = [
    "/admin/login.php",
    "/wp-admin/",
    "/wp-login.php",
    "/.env",
    "/.git/config",
    "/phpmyadmin/",
    "/actuator/env",
    "/console/",
    "/api/v1/items?id=1'%20OR%20'1'='1",
    "/search?q=%3Cscript%3Ealert(1)%3C/script%3E",
    "/page?id=1%20UNION%20SELECT%20null,null--",
    "/../../etc/passwd",
    "/cgi-bin/test.cgi",
]


def _rand_slug(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _rand_id() -> str:
    return str(random.randint(1, 99999))


def build_random_url(base: str, mix_attack: bool = False, attack_ratio: float = 0.08) -> str:
    """基于站点根地址生成随机 URL。"""
    if mix_attack and random.random() < attack_ratio:
        path = random.choice(ATTACK_PATHS)
        return urljoin(base.rstrip("/") + "/", path.lstrip("/"))

    tmpl = random.choice(PATH_TEMPLATES)
    path = tmpl.format(id=_rand_id(), slug=_rand_slug())

    query: dict[str, str] = {}
    if random.random() < 0.55 and "?" not in path:
        for _ in range(random.randint(1, 3)):
            key = random.choice(QUERY_KEYS)
            if key in ("page", "limit", "offset", "id"):
                query[key] = _rand_id()
            else:
                query[key] = _rand_slug(6)

    url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    if query:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urlencode(query)}"
    return url


# ---------------------------------------------------------------------------
# HTTP（线程安全连接复用）
# ---------------------------------------------------------------------------

class HttpPool:
    """按线程本地复用 http.client 连接，降低建连开销以便打满 QPS。"""

    def __init__(
        self,
        scheme: str,
        netloc: str,
        host_header: str | None,
        timeout: float,
        insecure: bool,
        follow_redirects: bool,
    ) -> None:
        self.scheme = scheme
        self.netloc = netloc
        self.host_header = host_header
        self.timeout = timeout
        self.insecure = insecure
        self.follow_redirects = follow_redirects
        self._local = threading.local()

    def _connect(self) -> http.client.HTTPConnection:
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            if self.insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            return http.client.HTTPSConnection(self.netloc, timeout=self.timeout, context=ctx)
        return http.client.HTTPConnection(self.netloc, timeout=self.timeout)

    def _conn(self) -> http.client.HTTPConnection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _reset(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            self._local.conn = None

    def request(
        self,
        method: str,
        url: str,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, float]:
        """返回 (status_code, latency_ms)。失败抛异常。"""
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        if self.host_header:
            headers["Host"] = self.host_header
        if extra_headers:
            headers.update(extra_headers)

        t0 = time.perf_counter()
        redirects = 0
        while True:
            try:
                conn = self._conn()
                conn.request(method, path, headers=headers)
                resp = conn.getresponse()
                status = resp.status
                # 读完 body，保持连接可复用
                resp.read()
            except Exception:
                self._reset()
                raise

            latency = (time.perf_counter() - t0) * 1000
            if (
                self.follow_redirects
                and status in (301, 302, 303, 307, 308)
                and redirects < 5
            ):
                loc = resp.getheader("Location")
                if not loc:
                    return status, latency
                next_url = urljoin(url, loc)
                next_parsed = urlparse(next_url)
                if next_parsed.netloc and next_parsed.netloc != self.netloc:
                    # 跨域重定向：不继续跟，直接返回当前状态
                    return status, latency
                path = next_parsed.path or "/"
                if next_parsed.query:
                    path = f"{path}?{next_parsed.query}"
                method = "GET" if status in (303,) else method
                redirects += 1
                continue
            return status, latency


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

@dataclass
class PhaseStats:
    name: str
    target_qps: float
    duration_s: float
    planned: int
    launched: int = 0
    completed: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    status_counts: Counter = field(default_factory=Counter)
    error_counts: Counter = field(default_factory=Counter)
    wall_start: float = 0.0
    launch_end: float = 0.0  # 最后一次发出请求的时刻（用于计算发出 QPS）
    wall_end: float = 0.0    # 全部完成（含等待在途）的时刻
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def actual_launch_qps(self) -> float:
        # 只按「发出窗口」计 QPS，不含等待慢响应收尾的时间
        elapsed = max(self.launch_end - self.wall_start, 1e-9)
        return self.launched / elapsed

    @property
    def actual_complete_qps(self) -> float:
        elapsed = max(self.wall_end - self.wall_start, 1e-9)
        return self.completed / elapsed

    def record_ok(self, status: int, latency_ms: float) -> None:
        with self._lock:
            self.latencies_ms.append(latency_ms)
            self.status_counts[status] += 1
            self.completed += 1

    def record_err(self, err_name: str, latency_ms: float) -> None:
        with self._lock:
            self.latencies_ms.append(latency_ms)
            self.status_counts["error"] += 1
            self.error_counts[err_name] += 1
            self.completed += 1

    def percentile(self, p: float) -> float | None:
        if not self.latencies_ms:
            return None
        xs = sorted(self.latencies_ms)
        if len(xs) == 1:
            return xs[0]
        k = (len(xs) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return xs[int(k)]
        return xs[f] * (c - k) + xs[c] * (k - f)

    def summary(self) -> dict[str, Any]:
        lats = self.latencies_ms
        success = sum(
            n for s, n in self.status_counts.items()
            if isinstance(s, int) and 200 <= s < 400
        )
        return {
            "name": self.name,
            "target_qps": self.target_qps,
            "duration_s": round(self.duration_s, 2),
            "planned_requests": self.planned,
            "launched": self.launched,
            "completed": self.completed,
            "actual_launch_qps": round(self.actual_launch_qps, 2),
            "actual_complete_qps": round(self.actual_complete_qps, 2),
            "qps_achieved": self.actual_launch_qps >= self.target_qps * 0.95,
            "success_2xx_3xx": success,
            "success_rate": round(success / self.completed, 4) if self.completed else 0.0,
            "latency_ms": {
                "min": round(min(lats), 2) if lats else None,
                "avg": round(statistics.fmean(lats), 2) if lats else None,
                "p50": round(self.percentile(50) or 0, 2) if lats else None,
                "p90": round(self.percentile(90) or 0, 2) if lats else None,
                "p95": round(self.percentile(95) or 0, 2) if lats else None,
                "p99": round(self.percentile(99) or 0, 2) if lats else None,
                "max": round(max(lats), 2) if lats else None,
            },
            "status_counts": {
                str(k): v for k, v in sorted(self.status_counts.items(), key=lambda x: str(x[0]))
            },
            "error_counts": dict(self.error_counts),
        }


# ---------------------------------------------------------------------------
# 压测执行
# ---------------------------------------------------------------------------

def phase_id(phase_idx: int, target_qps: float, duration_s: float) -> str:
    """阶段 ASCII 标识，便于 URL / Header 检索。"""
    return f"phase{phase_idx}-{int(target_qps)}qps-{int(duration_s)}s"


def send_phase_marker(
    pool: HttpPool,
    base_url: str,
    phase_name: str,
    phase_idx: int,
    target_qps: float,
    duration_s: float,
    event: str,
) -> None:
    """阶段起止标记请求：URL 与 Header 均体现阶段名 + start/end。

    Header 中的中文阶段名做 percent-encoding，避免 http.client Latin-1 限制。
    """
    assert event in ("start", "end")
    pid = phase_id(phase_idx, target_qps, duration_s)
    path = f"/__flowshield_stress__/{pid}/{event}"
    qs = urlencode(
        {
            "phase": phase_name,
            "phase_id": pid,
            "event": event,
            "qps": int(target_qps),
            "duration_s": int(duration_s),
        },
        encoding="utf-8",
    )
    url = f"{urljoin(base_url.rstrip('/') + '/', path.lstrip('/'))}?{qs}"
    # Header 值须为 Latin-1 可编码：中文名用 percent-encoding
    headers = {
        "X-Stress-Phase": pid,
        "X-Stress-Phase-Name": quote(phase_name, safe=""),
        "X-Stress-Event": event,
        "X-Stress-Phase-Index": str(phase_idx),
        "X-Stress-Target-QPS": str(int(target_qps)),
        "X-Stress-Duration-S": str(int(duration_s)),
    }
    try:
        status, latency = pool.request("GET", url, extra_headers=headers)
        print(
            f"  [{event.upper()}] 标记请求 HTTP {status}  {latency:.1f}ms  "
            f"phase={phase_name!r}  {url[:100]}",
            flush=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"  [{event.upper()}] 标记请求失败: {type(exc).__name__}: {exc}  "
            f"phase={phase_name!r}",
            flush=True,
        )


def _do_one(pool: HttpPool, url: str, stats: PhaseStats) -> None:
    t0 = time.perf_counter()
    try:
        status, latency = pool.request("GET", url)
        stats.record_ok(status, latency)
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - t0) * 1000
        stats.record_err(type(exc).__name__, latency)


def run_phase(
    pool: HttpPool,
    base_url: str,
    target_qps: float,
    duration_s: float,
    concurrency: int,
    mix_attack: bool,
    phase_idx: int,
) -> PhaseStats:
    name = f"阶段{phase_idx}: {int(target_qps)} QPS × {int(duration_s)}s"
    planned = max(1, int(round(target_qps * duration_s)))
    stats = PhaseStats(name=name, target_qps=target_qps, duration_s=duration_s, planned=planned)
    interval = 1.0 / target_qps

    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"  计划请求数: {planned}  |  间隔: {interval * 1000:.2f} ms  |  并发上限: {concurrency}")
    print(f"{'=' * 60}")

    # 阶段开始标记（不计入本阶段 QPS 统计）
    send_phase_marker(
        pool, base_url, name, phase_idx, target_qps, duration_s, event="start",
    )

    stats.wall_start = time.perf_counter()
    progress_every = max(1, planned // 20)
    pending = set()

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        for i in range(planned):
            target_at = stats.wall_start + i * interval
            now = time.perf_counter()
            delay = target_at - now
            if delay > 0:
                time.sleep(delay)

            # 仅在严重积压时限流，阈值偏高以优先保住发出 QPS
            if len(pending) >= concurrency * 2:
                _, pending = wait(pending, return_when=FIRST_COMPLETED)
                pending = set(pending)

            url = build_random_url(base_url, mix_attack=mix_attack)
            fut = ex.submit(_do_one, pool, url, stats)
            pending.add(fut)
            stats.launched += 1

            if stats.launched % progress_every == 0 or stats.launched == planned:
                elapsed = time.perf_counter() - stats.wall_start
                live_qps = stats.launched / max(elapsed, 1e-9)
                print(
                    f"  [{stats.launched:>6}/{planned}] "
                    f"已发出 QPS≈{live_qps:.1f}  已完成={stats.completed}  "
                    f"在途={len(pending)}  耗时={elapsed:.1f}s",
                    flush=True,
                )

        stats.launch_end = time.perf_counter()
        if pending:
            wait(pending)

    stats.wall_end = time.perf_counter()

    # 阶段结束标记（等在途请求收完后再发）
    send_phase_marker(
        pool, base_url, name, phase_idx, target_qps, duration_s, event="end",
    )
    return stats


def print_phase_report(stats: PhaseStats) -> None:
    s = stats.summary()
    lat = s["latency_ms"]
    mark = "✓" if s["qps_achieved"] else "✗"
    print(f"\n--- {s['name']} 结果 ---")
    print(f"  目标 QPS:        {s['target_qps']}")
    print(f"  实际发出 QPS:    {s['actual_launch_qps']}  [{mark} 达到目标≥95%]")
    print(f"  实际完成 QPS:    {s['actual_complete_qps']}")
    print(f"  请求: 计划={s['planned_requests']} 发出={s['launched']} 完成={s['completed']}")
    print(f"  成功(2xx/3xx):   {s['success_2xx_3xx']}  ({s['success_rate'] * 100:.1f}%)")
    if lat["avg"] is not None:
        print(
            f"  延迟(ms): min={lat['min']} avg={lat['avg']} "
            f"p50={lat['p50']} p90={lat['p90']} p95={lat['p95']} "
            f"p99={lat['p99']} max={lat['max']}"
        )
    print(f"  状态码分布:      {s['status_counts']}")
    if s["error_counts"]:
        print(f"  异常分布:        {s['error_counts']}")


def parse_phases(spec: str) -> list[tuple[float, float]]:
    """解析 '20:120,50:120,100:120' → [(qps, duration_s), ...]"""
    phases: list[tuple[float, float]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise argparse.ArgumentTypeError(f"阶段格式错误: {part!r}，应为 QPS:秒数")
        qps_s, dur_s = part.split(":", 1)
        qps, dur = float(qps_s), float(dur_s)
        if qps <= 0 or dur <= 0:
            raise argparse.ArgumentTypeError(f"QPS 与时长须为正数: {part!r}")
        phases.append((qps, dur))
    if not phases:
        raise argparse.ArgumentTypeError("至少需要一个阶段")
    return phases


def main() -> None:
    parser = argparse.ArgumentParser(
        description="流盾 WAF 防护压测：按阶段固定 QPS 随机访问目标站点",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url", required=True, help="目标站点根 URL，如 https://example.com")
    parser.add_argument(
        "--host",
        default=None,
        help="可选 Host 头（经 IP 访问引擎、按域名匹配站点时使用）",
    )
    parser.add_argument(
        "--phases",
        type=parse_phases,
        default="20:120,50:120,100:120",
        help="阶段列表，格式 QPS:秒[,QPS:秒...]；默认三阶段各 2 分钟",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=0,
        help="在途请求并发上限；0 表示按 max(QPS)*5 自动估算",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="单请求超时（秒）")
    parser.add_argument("--cooldown", type=float, default=5.0, help="阶段之间冷却秒数")
    parser.add_argument(
        "--mix-attack",
        action="store_true",
        help="混入少量攻击/扫描特征 URL（用于触发防护规则）",
    )
    parser.add_argument("--insecure", action="store_true", help="跳过 TLS 证书校验")
    parser.add_argument(
        "--follow-redirects",
        action="store_true",
        help="跟随重定向（默认不跟随，便于观察 WAF 挑战/拦截状态码）",
    )
    parser.add_argument("--report", default=None, help="将汇总结果写入 JSON 文件路径")
    args = parser.parse_args()

    if isinstance(args.phases, str):
        args.phases = parse_phases(args.phases)

    base = args.url.rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"无效 URL: {args.url}", file=sys.stderr)
        sys.exit(2)

    max_qps = max(q for q, _ in args.phases)
    # 默认并发偏高：在途请求多一点，开环发出节奏不易被慢响应拖垮
    concurrency = args.concurrency or max(100, int(max_qps * 5))

    print("流盾 WAF 防护压测")
    print(f"  目标:     {base}")
    if args.host:
        print(f"  Host:     {args.host}")
    print(f"  阶段:     {', '.join(f'{int(q)}QPS×{int(d)}s' for q, d in args.phases)}")
    print(f"  并发上限: {concurrency}")
    print(f"  超时:     {args.timeout}s")
    print(f"  混合攻击: {'开' if args.mix_attack else '关'}")
    print(f"  开始时间: {datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}")

    pool = HttpPool(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        host_header=args.host,
        timeout=args.timeout,
        insecure=args.insecure,
        follow_redirects=args.follow_redirects,
    )

    # 预热
    warm_url = build_random_url(base, mix_attack=False)
    try:
        status, latency = pool.request("GET", warm_url)
        print(f"  预热请求: HTTP {status}  {latency:.1f}ms  {warm_url[:80]}")
    except Exception as exc:  # noqa: BLE001
        print(f"  预热失败（仍继续压测）: {type(exc).__name__}: {exc}")

    all_summaries: list[dict[str, Any]] = []
    try:
        for idx, (qps, duration) in enumerate(args.phases, start=1):
            stats = run_phase(
                pool=pool,
                base_url=base,
                target_qps=qps,
                duration_s=duration,
                concurrency=concurrency,
                mix_attack=args.mix_attack,
                phase_idx=idx,
            )
            print_phase_report(stats)
            all_summaries.append(stats.summary())
            if idx < len(args.phases) and args.cooldown > 0:
                print(f"\n  … 阶段间冷却 {args.cooldown}s …")
                time.sleep(args.cooldown)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        sys.exit(130)

    report = {
        "target": base,
        "host": args.host,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "phases": all_summaries,
        "all_qps_achieved": all(p["qps_achieved"] for p in all_summaries),
    }

    print(f"\n{'=' * 60}")
    print("汇总")
    print(f"{'=' * 60}")
    for p in all_summaries:
        mark = "✓" if p["qps_achieved"] else "✗"
        print(
            f"  {mark} {p['name']}: 发出QPS={p['actual_launch_qps']} "
            f"(目标 {p['target_qps']})  "
            f"p95={p['latency_ms']['p95']}ms  "
            f"成功={p['success_rate'] * 100:.1f}%"
        )
    overall = "全部达标" if report["all_qps_achieved"] else "存在未达标阶段"
    print(f"\nQPS 达标情况: {overall}")

    if args.report:
        path = Path(args.report)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入: {path.resolve()}")

    sys.exit(0 if report["all_qps_achieved"] else 1)


if __name__ == "__main__":
    main()
