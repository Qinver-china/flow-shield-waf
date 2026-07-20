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

/** 美国州/特区 ISO 3166-2 代码（去掉 US- 前缀，与 MaxMind subdivisions iso_code 一致） */
export const GEO_US_REGION_LABELS: Record<string, string> = {
  AL: "阿拉巴马",
  AK: "阿拉斯加",
  AZ: "亚利桑那",
  AR: "阿肯色",
  CA: "加利福尼亚",
  CO: "科罗拉多",
  CT: "康涅狄格",
  DE: "特拉华",
  FL: "佛罗里达",
  GA: "佐治亚",
  HI: "夏威夷",
  ID: "爱达荷",
  IL: "伊利诺伊",
  IN: "印第安纳",
  IA: "艾奥瓦",
  KS: "堪萨斯",
  KY: "肯塔基",
  LA: "路易斯安那",
  ME: "缅因",
  MD: "马里兰",
  MA: "马萨诸塞",
  MI: "密歇根",
  MN: "明尼苏达",
  MS: "密西西比",
  MO: "密苏里",
  MT: "蒙大拿",
  NE: "内布拉斯加",
  NV: "内华达",
  NH: "新罕布什尔",
  NJ: "新泽西",
  NM: "新墨西哥",
  NY: "纽约",
  NC: "北卡罗来纳",
  ND: "北达科他",
  OH: "俄亥俄",
  OK: "俄克拉何马",
  OR: "俄勒冈",
  PA: "宾夕法尼亚",
  RI: "罗得岛",
  SC: "南卡罗来纳",
  SD: "南达科他",
  TN: "田纳西",
  TX: "得克萨斯",
  UT: "犹他",
  VT: "佛蒙特",
  VA: "弗吉尼亚",
  WA: "华盛顿",
  WV: "西弗吉尼亚",
  WI: "威斯康星",
  WY: "怀俄明",
  DC: "哥伦比亚特区",
};

/** 省/州英文全名（小写）→ 中文；兼容非 iso_code 入库场景 */
export const GEO_REGION_NAME_LABELS: Record<string, string> = {
  beijing: "北京",
  tianjin: "天津",
  hebei: "河北",
  shanxi: "山西",
  "inner mongolia": "内蒙古",
  "nei mongol": "内蒙古",
  liaoning: "辽宁",
  jilin: "吉林",
  heilongjiang: "黑龙江",
  shanghai: "上海",
  jiangsu: "江苏",
  zhejiang: "浙江",
  anhui: "安徽",
  fujian: "福建",
  jiangxi: "江西",
  shandong: "山东",
  henan: "河南",
  hubei: "湖北",
  hunan: "湖南",
  guangdong: "广东",
  guangxi: "广西",
  hainan: "海南",
  chongqing: "重庆",
  sichuan: "四川",
  guizhou: "贵州",
  yunnan: "云南",
  tibet: "西藏",
  "xizang": "西藏",
  shaanxi: "陕西",
  gansu: "甘肃",
  qinghai: "青海",
  ningxia: "宁夏",
  xinjiang: "新疆",
  california: "加利福尼亚",
  "new york": "纽约",
  texas: "得克萨斯",
  florida: "佛罗里达",
  washington: "华盛顿",
  virginia: "弗吉尼亚",
  illinois: "伊利诺伊",
  pennsylvania: "宾夕法尼亚",
  ohio: "俄亥俄",
  georgia: "佐治亚",
  "north carolina": "北卡罗来纳",
  michigan: "密歇根",
  "new jersey": "新泽西",
  arizona: "亚利桑那",
  massachusetts: "马萨诸塞",
  tennessee: "田纳西",
  indiana: "印第安纳",
  missouri: "密苏里",
  maryland: "马里兰",
  wisconsin: "威斯康星",
  colorado: "科罗拉多",
  minnesota: "明尼苏达",
  "south carolina": "南卡罗来纳",
  alabama: "阿拉巴马",
  louisiana: "路易斯安那",
  kentucky: "肯塔基",
  oregon: "俄勒冈",
  oklahoma: "俄克拉何马",
  connecticut: "康涅狄格",
  utah: "犹他",
  iowa: "艾奥瓦",
  nevada: "内华达",
  arkansas: "阿肯色",
  mississippi: "密西西比",
  kansas: "堪萨斯",
  "new mexico": "新墨西哥",
  nebraska: "内布拉斯加",
  "west virginia": "西弗吉尼亚",
  idaho: "爱达荷",
  hawaii: "夏威夷",
  "new hampshire": "新罕布什尔",
  maine: "缅因",
  montana: "蒙大拿",
  "rhode island": "罗得岛",
  delaware: "特拉华",
  "south dakota": "南达科他",
  "north dakota": "北达科他",
  alaska: "阿拉斯加",
  vermont: "佛蒙特",
  wyoming: "怀俄明",
  "district of columbia": "哥伦比亚特区",
  england: "英格兰",
  scotland: "苏格兰",
  wales: "威尔士",
  "northern ireland": "北爱尔兰",
  ontario: "安大略",
  quebec: "魁北克",
  "british columbia": "不列颠哥伦比亚",
  tokyo: "东京都",
  osaka: "大阪府",
  "seoul-teukbyeolsi": "首尔",
  "taipei city": "台北市",
  "new taipei city": "新北市",
  "hong kong": "香港",
};

/**
 * 常见城市英文名（小写，与 MaxMind city names en 一致）→ 中文。
 * 仅展示用；筛选/匹配仍用原文。
 */
export const GEO_CITY_LABELS: Record<string, string> = {
  // 中国大陆
  beijing: "北京",
  shanghai: "上海",
  guangzhou: "广州",
  shenzhen: "深圳",
  hangzhou: "杭州",
  chengdu: "成都",
  chongqing: "重庆",
  wuhan: "武汉",
  "xi'an": "西安",
  xian: "西安",
  nanjing: "南京",
  tianjin: "天津",
  suzhou: "苏州",
  zhengzhou: "郑州",
  changsha: "长沙",
  dongguan: "东莞",
  foshan: "佛山",
  ningbo: "宁波",
  qingdao: "青岛",
  dalian: "大连",
  xiamen: "厦门",
  kunming: "昆明",
  hefei: "合肥",
  fuzhou: "福州",
  shenyang: "沈阳",
  harbin: "哈尔滨",
  jinan: "济南",
  wuxi: "无锡",
  wenzhou: "温州",
  nanchang: "南昌",
  changchun: "长春",
  guiyang: "贵阳",
  nanning: "南宁",
  haikou: "海口",
  sanya: "三亚",
  lanzhou: "兰州",
  urumqi: "乌鲁木齐",
  hohhot: "呼和浩特",
  lhasa: "拉萨",
  taiyuan: "太原",
  shijiazhuang: "石家庄",
  zhuhai: "珠海",
  zhongshan: "中山",
  huizhou: "惠州",
  jiangmen: "江门",
  quanzhou: "泉州",
  putian: "莆田",
  yantai: "烟台",
  weifang: "潍坊",
  baoding: "保定",
  tangshan: "唐山",
  luoyang: "洛阳",
  changzhou: "常州",
  nantong: "南通",
  xuzhou: "徐州",
  yangzhou: "扬州",
  jiaxing: "嘉兴",
  shaoxing: "绍兴",
  jinhua: "金华",
  taizhou: "台州",
  // 港澳台与亚太
  "hong kong": "香港",
  macau: "澳门",
  macao: "澳门",
  taipei: "台北",
  "new taipei": "新北",
  kaohsiung: "高雄",
  taichung: "台中",
  tainan: "台南",
  singapore: "新加坡",
  tokyo: "东京",
  osaka: "大阪",
  yokohama: "横滨",
  nagoya: "名古屋",
  seoul: "首尔",
  busan: "釜山",
  bangkok: "曼谷",
  "ho chi minh city": "胡志明市",
  hanoi: "河内",
  jakarta: "雅加达",
  "kuala lumpur": "吉隆坡",
  manila: "马尼拉",
  mumbai: "孟买",
  delhi: "德里",
  "new delhi": "新德里",
  bangalore: "班加罗尔",
  bengaluru: "班加罗尔",
  chennai: "金奈",
  hyderabad: "海得拉巴",
  // 欧美澳
  london: "伦敦",
  manchester: "曼彻斯特",
  birmingham: "伯明翰",
  paris: "巴黎",
  frankfurt: "法兰克福",
  berlin: "柏林",
  munich: "慕尼黑",
  amsterdam: "阿姆斯特丹",
  rotterdam: "鹿特丹",
  brussels: "布鲁塞尔",
  zurich: "苏黎世",
  geneva: "日内瓦",
  madrid: "马德里",
  barcelona: "巴塞罗那",
  rome: "罗马",
  milan: "米兰",
  stockholm: "斯德哥尔摩",
  dublin: "都柏林",
  moscow: "莫斯科",
  "saint petersburg": "圣彼得堡",
  istanbul: "伊斯坦布尔",
  dubai: "迪拜",
  "abu dhabi": "阿布扎比",
  "new york": "纽约",
  "los angeles": "洛杉矶",
  "san francisco": "旧金山",
  "san jose": "圣何塞",
  seattle: "西雅图",
  chicago: "芝加哥",
  dallas: "达拉斯",
  houston: "休斯顿",
  miami: "迈阿密",
  atlanta: "亚特兰大",
  boston: "波士顿",
  washington: "华盛顿",
  denver: "丹佛",
  phoenix: "凤凰城",
  philadelphia: "费城",
  "las vegas": "拉斯维加斯",
  toronto: "多伦多",
  montreal: "蒙特利尔",
  vancouver: "温哥华",
  sydney: "悉尼",
  melbourne: "墨尔本",
  brisbane: "布里斯班",
  auckland: "奥克兰",
  "sao paulo": "圣保罗",
  "são paulo": "圣保罗",
  "rio de janeiro": "里约热内卢",
  "mexico city": "墨西哥城",
};

function normalizeCode(code: string | null | undefined): string {
  return String(code || "").trim().toUpperCase();
}

function lookupRegionName(raw: string): string | undefined {
  const key = raw.trim().toLowerCase();
  if (!key) return undefined;
  return GEO_REGION_NAME_LABELS[key];
}

function resolveRegionLabel(
  code: string,
  country?: string | null,
): string | undefined {
  const cc = normalizeCode(country);
  if (cc === "CN") return GEO_CN_REGION_LABELS[code];
  if (cc === "US") return GEO_US_REGION_LABELS[code];
  // 无国家上下文：优先中国（产品语境），再美国；重叠码（HI/NM/SC/SD）按中国语义
  return GEO_CN_REGION_LABELS[code] || GEO_US_REGION_LABELS[code];
}

/** 中国 (CN) / 未知码原样 / 空则空串 */
export function formatGeoCountry(code: string | null | undefined): string {
  const c = normalizeCode(code);
  if (!c) return "";
  const name = GEO_COUNTRY_LABELS[c];
  return name ? `${name} (${c})` : c;
}

/** 广东 (GD) / 弗吉尼亚 (VA)；未知则原样 */
export function formatGeoRegion(
  region: string | null | undefined,
  country?: string | null,
): string {
  const raw = String(region || "").trim();
  if (!raw) return "";
  const code = normalizeCode(raw);
  const byCode = resolveRegionLabel(code, country);
  if (byCode) return `${byCode} (${code})`;
  const byName = lookupRegionName(raw);
  if (byName) return `${byName} (${raw})`;
  return raw;
}

/** 北京 (Beijing)；未知英文名则原样 */
export function formatGeoCity(city: string | null | undefined): string {
  const raw = String(city || "").trim();
  if (!raw) return "";
  const name = GEO_CITY_LABELS[raw.toLowerCase()];
  return name ? `${name} (${raw})` : raw;
}

/**
 * 常见 ASN 号 → 中文/语义化组织名（展示用；筛选仍用数字）。
 * 覆盖国内三大运营商、主流云与 CDN。
 */
export const GEO_ASN_LABELS: Record<number, string> = {
  // 中国运营商 / 教育科研
  4134: "中国电信",
  4809: "中国电信 CN2",
  4812: "中国电信上海",
  4837: "中国联通",
  9929: "中国联通精品网",
  9808: "中国移动",
  56040: "中国移动",
  56046: "中国移动",
  56048: "中国移动",
  24400: "中国移动",
  4538: "教育网 CERNET",
  7497: "中科院 CSTNET",
  23910: "教育网 CERNET2",
  // 国内云 / 互联网
  37963: "阿里云",
  45102: "阿里云",
  45090: "腾讯云",
  132203: "腾讯云",
  136958: "华为云",
  55967: "百度",
  38365: "北京百度",
  137753: "北京北龙超级云",
  137718: "北京火山引擎",
  59019: "北京金山云",
  135377: "优刻得 UCloud",
  58466: "中国广电",
  // 港澳台
  9304: "香港电讯 HKT",
  9269: "香港宽频",
  10103: "香港宽频",
  9381: "HKBN",
  3462: "中华电信",
  9924: "台湾固网",
  24158: "台湾大哥大",
  // 海外云 / CDN
  13335: "Cloudflare",
  20940: "Akamai",
  16625: "Akamai",
  54113: "Fastly",
  16509: "亚马逊 AWS",
  14618: "亚马逊 AWS",
  15169: "谷歌",
  396982: "谷歌云",
  8075: "微软",
  8068: "微软",
  14061: "DigitalOcean",
  63949: "Linode / Akamai",
  20473: "Vultr",
  16276: "OVH",
  24940: "Hetzner",
  31898: "甲骨文云",
  36351: "SoftLayer / IBM",
  32934: "Meta",
  714: "Apple",
  36459: "GitHub",
  60068: "CDN77",
  133752: "Leaseweb",
  9009: "M247",
  174: "Cogent",
  3356: "Lumen / Level3",
  1299: "Arelion / Telia",
  2914: "NTT",
  6939: "Hurricane Electric",
};

/** Cloudflare (13335)；未知则原样数字 */
export function formatGeoAsn(asn: number | string | null | undefined): string {
  if (asn == null || asn === "") return "";
  const n = typeof asn === "number" ? asn : Number(String(asn).trim());
  if (!Number.isFinite(n) || n <= 0) {
    return String(asn).trim();
  }
  const name = GEO_ASN_LABELS[n];
  return name ? `${name} (${n})` : String(n);
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
  const city = formatGeoCity(parts.city);
  if (city) bits.push(city);
  const isp = formatGeoIsp(parts.isp);
  if (isp) bits.push(isp);
  const asn = formatGeoAsn(parts.asn);
  if (asn) bits.push(asn);
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
