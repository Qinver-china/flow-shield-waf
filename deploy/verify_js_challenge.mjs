#!/usr/bin/env node
/**
 * End-to-end JS challenge verifier: simulates browser PoW + POST verify.
 */
import crypto from "node:crypto";

const BASE = process.env.WAF_ENGINE || "http://127.0.0.1";
const HOST = process.env.WAF_HOST || "127.0.0.1";

function leadingZeros(hash, n) {
  for (let i = 0; i < n; i++) {
    if (hash[i] !== "0") return false;
  }
  return true;
}

function sha256hex(msg) {
  return crypto.createHash("sha256").update(msg).digest("hex");
}

async function solvePow(cid, seed, difficulty) {
  for (let nonce = 0; nonce < 5_000_000; nonce++) {
    const hash = sha256hex(`${cid}:${seed}:${nonce}`);
    if (leadingZeros(hash, difficulty)) return nonce;
  }
  return null;
}

function extractVar(html, name) {
  const re = new RegExp(`var ${name}=([^;\\n]+)`);
  const m = html.match(re);
  if (!m) throw new Error(`missing ${name}`);
  return JSON.parse(m[1]);
}

async function main() {
  const headers = {
    Host: HOST,
    "User-Agent":
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    Accept: "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
  };

  console.log("[1] Fetch challenge page...");
  const r1 = await fetch(`${BASE}/`, { headers, redirect: "manual" });
  const html = await r1.text();
  console.log(`    status=${r1.status} len=${html.length}`);
  if (r1.status !== 503) {
    throw new Error(`expected 503, got ${r1.status}`);
  }
  if (!html.includes("solvePow")) {
    throw new Error("challenge page missing PoW script");
  }

  const token = extractVar(html, "token");
  const cid = extractVar(html, "cid");
  const seed = extractVar(html, "seed");
  const baseDifficulty = extractVar(html, "baseDifficulty");
  const fp = 0;
  const difficulty = Math.min(7, Math.max(baseDifficulty, baseDifficulty + Math.floor(fp / 25)));
  console.log(`[2] PoW params cid=${cid.slice(0, 8)}... difficulty=${difficulty}`);

  const t0 = Date.now();
  const nonce = await solvePow(cid, seed, difficulty);
  const ms = Date.now() - t0;
  if (nonce === null) throw new Error("PoW solve failed");
  console.log(`[3] PoW solved nonce=${nonce} in ${ms}ms`);

  const body = new URLSearchParams({
    t: token,
    r: "/",
    nonce: String(nonce),
    fp: String(fp),
  });
  console.log("[4] POST /.waf/js-verify ...");
  const r2 = await fetch(`${BASE}/.waf/js-verify`, {
    method: "POST",
    headers: {
      ...headers,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
    redirect: "manual",
  });
  console.log(`    status=${r2.status} location=${r2.headers.get("location") || "(none)"}`);
  if (r2.status !== 302) {
    const err = await r2.text();
    throw new Error(`verify failed: ${r2.status} ${err.slice(0, 200)}`);
  }

  console.log("[5] Second request (should bypass challenge)...");
  const r3 = await fetch(`${BASE}/`, { headers, redirect: "manual" });
  console.log(`    status=${r3.status}`);
  if (r3.status === 503) {
    throw new Error("clearance not granted — still challenged");
  }
  console.log("PASS: JS challenge flow complete");
}

main().catch((e) => {
  console.error("FAIL:", e.message);
  process.exit(1);
});
