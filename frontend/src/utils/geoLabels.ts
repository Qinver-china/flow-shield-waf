/** ISO 3166-1 alpha-2 → 中文名（规则下拉 / 日志展示共用） */
export const GEO_COUNTRY_LABELS: Record<string, string> = {
  CN: "中国",
  US: "美国",
  HK: "中国香港",
  TW: "中国台湾",
  MO: "中国澳门",
  JP: "日本",
  KR: "韩国",
  SG: "新加坡",
  GB: "英国",
  DE: "德国",
  FR: "法国",
  RU: "俄罗斯",
  IN: "印度",
  AU: "澳大利亚",
  CA: "加拿大",
  NL: "荷兰",
  VN: "越南",
  TH: "泰国",
  MY: "马来西亚",
  ID: "印度尼西亚",
  PH: "菲律宾",
  BR: "巴西",
  IT: "意大利",
  ES: "西班牙",
  SE: "瑞典",
  CH: "瑞士",
  AE: "阿联酋",
  TR: "土耳其",
  PL: "波兰",
  UA: "乌克兰",
  MX: "墨西哥",
  AR: "阿根廷",
  ZA: "南非",
  NZ: "新西兰",
  IE: "爱尔兰",
  BE: "比利时",
  AT: "奥地利",
  PT: "葡萄牙",
  FI: "芬兰",
  NO: "挪威",
  DK: "丹麦",
  CZ: "捷克",
  RO: "罗马尼亚",
  HU: "匈牙利",
  IL: "以色列",
  SA: "沙特阿拉伯",
  PK: "巴基斯坦",
  BD: "孟加拉国",
  NG: "尼日利亚",
  EG: "埃及",
  KZ: "哈萨克斯坦",
  UZ: "乌兹别克斯坦",
  MM: "缅甸",
  KH: "柬埔寨",
  LA: "老挝",
  NP: "尼泊尔",
  LK: "斯里兰卡",
  IQ: "伊拉克",
  IR: "伊朗",
  UNKNOWN: "未知",
  XX: "未知",
};

/** 中国大陆省/直辖市/自治区 ISO 3166-2 代码（去掉 CN- 前缀后的部分，与 MaxMind subdivisions iso_code 一致） */
export const GEO_CN_REGION_LABELS: Record<string, string> = {
  BJ: "北京",
  TJ: "天津",
  HE: "河北",
  SX: "山西",
  NM: "内蒙古",
  LN: "辽宁",
  JL: "吉林",
  HL: "黑龙江",
  SH: "上海",
  JS: "江苏",
  ZJ: "浙江",
  AH: "安徽",
  FJ: "福建",
  JX: "江西",
  SD: "山东",
  HA: "河南",
  HB: "湖北",
  HN: "湖南",
  GD: "广东",
  GX: "广西",
  HI: "海南",
  CQ: "重庆",
  SC: "四川",
  GZ: "贵州",
  YN: "云南",
  XZ: "西藏",
  SN: "陕西",
  GS: "甘肃",
  QH: "青海",
  NX: "宁夏",
  XJ: "新疆",
};

function normalizeCode(code: string | null | undefined): string {
  return String(code || "").trim().toUpperCase();
}

/** 中国 (CN) / 未知码原样 / 空则空串 */
export function formatGeoCountry(code: string | null | undefined): string {
  const c = normalizeCode(code);
  if (!c) return "";
  const name = GEO_COUNTRY_LABELS[c];
  return name ? `${name} (${c})` : c;
}

/** 广东 (GD)；非中国或未知码则原样 */
export function formatGeoRegion(
  region: string | null | undefined,
  country?: string | null,
): string {
  const r = normalizeCode(region);
  if (!r) return "";
  const cc = normalizeCode(country);
  if (cc === "CN" || !cc) {
    const name = GEO_CN_REGION_LABELS[r];
    if (name) return `${name} (${r})`;
  }
  return r;
}

/**
 * 常见 ASN 组织名关键词 → 中文标注（按优先级从前到后匹配，忽略大小写）。
 * 匹配仍使用 MaxMind 原始组织名；此处仅用于展示。
 */
export const GEO_ISP_LABELS: { match: string; label: string }[] = [
  { match: "china mobile international", label: "中国移动国际" },
  { match: "chinanet", label: "中国电信" },
  { match: "china telecom", label: "中国电信" },
  { match: "china-telecom", label: "中国电信" },
  { match: "china unicom", label: "中国联通" },
  { match: "chinaunicom", label: "中国联通" },
  { match: "china-unicom", label: "中国联通" },
  { match: "china mobile", label: "中国移动" },
  { match: "chinamobile", label: "中国移动" },
  { match: "cmnet", label: "中国移动" },
  { match: "cmcc", label: "中国移动" },
  { match: "cernet", label: "教育网 CERNET" },
  { match: "cstnet", label: "中科院 CSTNET" },
  { match: "drpeng", label: "鹏博士" },
  { match: "wasu", label: "华数" },
  { match: "gehua", label: "歌华有线" },
  { match: "alibaba", label: "阿里云" },
  { match: "aliyun", label: "阿里云" },
  { match: "taobao", label: "阿里云" },
  { match: "tencent", label: "腾讯云" },
  { match: "huawei", label: "华为云" },
  { match: "baidu", label: "百度云" },
  { match: "bytedance", label: "字节跳动" },
  { match: "byteplus", label: "火山引擎" },
  { match: "volcengine", label: "火山引擎" },
  { match: "jd.com", label: "京东云" },
  { match: "jingdong", label: "京东云" },
  { match: "kingsoft", label: "金山云" },
  { match: "ucloud", label: "UCloud" },
  { match: "qingcloud", label: "青云" },
  { match: "hkt", label: "香港电讯" },
  { match: "pccw", label: "电讯盈科" },
  { match: "chunghwa", label: "中华电信" },
  { match: "far eastone", label: "远传电信" },
  { match: "taiwan mobile", label: "台湾大哥大" },
  { match: "amazon", label: "亚马逊 AWS" },
  { match: "google", label: "谷歌云" },
  { match: "microsoft", label: "微软 Azure" },
  { match: "azure", label: "微软 Azure" },
  { match: "cloudflare", label: "Cloudflare" },
  { match: "akamai", label: "Akamai" },
  { match: "fastly", label: "Fastly" },
  { match: "digitalocean", label: "DigitalOcean" },
  { match: "linode", label: "Linode" },
  { match: "vultr", label: "Vultr" },
  { match: "ovh", label: "OVH" },
  { match: "hetzner", label: "Hetzner" },
  { match: "oracle", label: "甲骨文云" },
  { match: "softlayer", label: "IBM SoftLayer" },
  { match: "ibm", label: "IBM 云" },
  { match: "leaseweb", label: "Leaseweb" },
  { match: "contabo", label: "Contabo" },
  { match: "m247", label: "M247" },
  { match: "cogent", label: "Cogent" },
  { match: "lumen", label: "Lumen" },
  { match: "level 3", label: "Level3" },
  { match: "level3", label: "Level3" },
  { match: "meta platforms", label: "Meta" },
  { match: "facebook", label: "Meta" },
  { match: "apple", label: "Apple" },
  { match: "github", label: "GitHub" },
];

/** 筛选/规则提示：value 尽量贴近常见 MaxMind 组织名片段（精确匹配仍以日志原文为准） */
export const GEO_ISP_SELECT_HINTS: { value: string; label: string }[] = [
  { value: "China Telecom", label: "中国电信 (China Telecom)" },
  { value: "China Unicom", label: "中国联通 (China Unicom)" },
  { value: "China Mobile", label: "中国移动 (China Mobile)" },
  { value: "CERNET", label: "教育网 (CERNET)" },
  { value: "Alibaba", label: "阿里云 (Alibaba)" },
  { value: "Tencent", label: "腾讯云 (Tencent)" },
  { value: "Huawei", label: "华为云 (Huawei)" },
  { value: "Amazon.com, Inc.", label: "亚马逊 AWS (Amazon.com, Inc.)" },
  { value: "GOOGLE", label: "谷歌云 (GOOGLE)" },
  { value: "MICROSOFT-CORP-MSN-AS-BLOCK", label: "微软 Azure (Microsoft)" },
  { value: "CLOUDFLARENET", label: "Cloudflare (CLOUDFLARENET)" },
  { value: "AKAMAI", label: "Akamai" },
  { value: "DIGITALOCEAN", label: "DigitalOcean" },
  { value: "Hetzner Online GmbH", label: "Hetzner" },
  { value: "OVH SAS", label: "OVH" },
];

export function formatGeoIsp(isp: string | null | undefined): string {
  const raw = String(isp || "").trim();
  if (!raw) return "";
  const lower = raw.toLowerCase();
  for (const item of GEO_ISP_LABELS) {
    if (lower.includes(item.match)) {
      return `${item.label} (${raw})`;
    }
  }
  return raw;
}

export function formatGeoLocation(parts: {
  country?: string | null;
  region?: string | null;
  city?: string | null;
  isp?: string | null;
  asn?: number | string | null;
}): string {
  const bits: string[] = [];
  const country = formatGeoCountry(parts.country);
  if (country) bits.push(country);
  const region = formatGeoRegion(parts.region, parts.country);
  if (region) bits.push(region);
  if (parts.city) bits.push(String(parts.city));
  const isp = formatGeoIsp(parts.isp);
  if (isp) bits.push(isp);
  if (parts.asn != null && parts.asn !== "") bits.push(`AS${parts.asn}`);
  return bits.length ? bits.join(" · ") : "";
}

export function geoCountrySelectOptions(): { value: string; label: string }[] {
  return Object.entries(GEO_COUNTRY_LABELS)
    .filter(([code]) => code !== "UNKNOWN" && code !== "XX")
    .map(([code, name]) => ({ value: code, label: `${name} (${code})` }))
    .sort((a, b) => a.label.localeCompare(b.label, "zh-CN"));
}

export function geoCnRegionSelectOptions(): { value: string; label: string }[] {
  return Object.entries(GEO_CN_REGION_LABELS)
    .map(([code, name]) => ({ value: code, label: `${name} (${code})` }))
    .sort((a, b) => a.label.localeCompare(b.label, "zh-CN"));
}
