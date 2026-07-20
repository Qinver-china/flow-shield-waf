"""Human-readable Chinese labels for log statistics dimension values."""
from __future__ import annotations

SOURCE_LABELS: dict[str, str] = {
    "ratelimit": "速率防护",
    "rule": "自定义规则",
    "blacklist": "黑名单",
    "whitelist": "白名单",
    "bot": "Bot 库",
}

_BOT_CATEGORY_LABELS: dict[str, str] = {}


def set_bot_category_labels(labels: dict[str, str]) -> None:
    global _BOT_CATEGORY_LABELS
    _BOT_CATEGORY_LABELS = dict(labels)

MODE_LABELS: dict[str, str] = {
    "observe": "观察",
    "block": "拦截",
    "captcha": "数学计算验证",
    "js_challenge": "JS 挑战",
    "slide_captcha": "滑动验证",
    "unknown": "未知",
}

LOG_TYPE_LABELS: dict[str, str] = {
    "protection": "防护命中",
    "access-control": "访问控制",
    "audit": "审计",
}

# Common ISO 3166-1 alpha-2 codes (fallback to raw code)
GEO_COUNTRY_LABELS: dict[str, str] = {
    "CN": "中国",
    "US": "美国",
    "HK": "中国香港",
    "TW": "中国台湾",
    "MO": "中国澳门",
    "JP": "日本",
    "KR": "韩国",
    "SG": "新加坡",
    "GB": "英国",
    "DE": "德国",
    "FR": "法国",
    "RU": "俄罗斯",
    "IN": "印度",
    "AU": "澳大利亚",
    "CA": "加拿大",
    "NL": "荷兰",
    "VN": "越南",
    "TH": "泰国",
    "MY": "马来西亚",
    "ID": "印度尼西亚",
    "PH": "菲律宾",
    "BR": "巴西",
    "IT": "意大利",
    "ES": "西班牙",
    "SE": "瑞典",
    "CH": "瑞士",
    "AE": "阿联酋",
    "TR": "土耳其",
    "PL": "波兰",
    "UA": "乌克兰",
    "MX": "墨西哥",
    "AR": "阿根廷",
    "ZA": "南非",
    "NZ": "新西兰",
    "IE": "爱尔兰",
    "BE": "比利时",
    "AT": "奥地利",
    "PT": "葡萄牙",
    "FI": "芬兰",
    "NO": "挪威",
    "DK": "丹麦",
    "CZ": "捷克",
    "RO": "罗马尼亚",
    "HU": "匈牙利",
    "IL": "以色列",
    "SA": "沙特阿拉伯",
    "PK": "巴基斯坦",
    "BD": "孟加拉国",
    "NG": "尼日利亚",
    "EG": "埃及",
    "KZ": "哈萨克斯坦",
    "UZ": "乌兹别克斯坦",
    "MM": "缅甸",
    "KH": "柬埔寨",
    "LA": "老挝",
    "NP": "尼泊尔",
    "LK": "斯里兰卡",
    "IQ": "伊拉克",
    "IR": "伊朗",
    "UNKNOWN": "未知",
    "XX": "未知",
}

GEO_CN_REGION_LABELS: dict[str, str] = {
    "BJ": "北京",
    "TJ": "天津",
    "HE": "河北",
    "SX": "山西",
    "NM": "内蒙古",
    "LN": "辽宁",
    "JL": "吉林",
    "HL": "黑龙江",
    "SH": "上海",
    "JS": "江苏",
    "ZJ": "浙江",
    "AH": "安徽",
    "FJ": "福建",
    "JX": "江西",
    "SD": "山东",
    "HA": "河南",
    "HB": "湖北",
    "HN": "湖南",
    "GD": "广东",
    "GX": "广西",
    "HI": "海南",
    "CQ": "重庆",
    "SC": "四川",
    "GZ": "贵州",
    "YN": "云南",
    "XZ": "西藏",
    "SN": "陕西",
    "GS": "甘肃",
    "QH": "青海",
    "NX": "宁夏",
    "XJ": "新疆",
}

GEO_US_REGION_LABELS: dict[str, str] = {
    "AL": "阿拉巴马",
    "AK": "阿拉斯加",
    "AZ": "亚利桑那",
    "AR": "阿肯色",
    "CA": "加利福尼亚",
    "CO": "科罗拉多",
    "CT": "康涅狄格",
    "DE": "特拉华",
    "FL": "佛罗里达",
    "GA": "佐治亚",
    "HI": "夏威夷",
    "ID": "爱达荷",
    "IL": "伊利诺伊",
    "IN": "印第安纳",
    "IA": "艾奥瓦",
    "KS": "堪萨斯",
    "KY": "肯塔基",
    "LA": "路易斯安那",
    "ME": "缅因",
    "MD": "马里兰",
    "MA": "马萨诸塞",
    "MI": "密歇根",
    "MN": "明尼苏达",
    "MS": "密西西比",
    "MO": "密苏里",
    "MT": "蒙大拿",
    "NE": "内布拉斯加",
    "NV": "内华达",
    "NH": "新罕布什尔",
    "NJ": "新泽西",
    "NM": "新墨西哥",
    "NY": "纽约",
    "NC": "北卡罗来纳",
    "ND": "北达科他",
    "OH": "俄亥俄",
    "OK": "俄克拉何马",
    "OR": "俄勒冈",
    "PA": "宾夕法尼亚",
    "RI": "罗得岛",
    "SC": "南卡罗来纳",
    "SD": "南达科他",
    "TN": "田纳西",
    "TX": "得克萨斯",
    "UT": "犹他",
    "VT": "佛蒙特",
    "VA": "弗吉尼亚",
    "WA": "华盛顿",
    "WV": "西弗吉尼亚",
    "WI": "威斯康星",
    "WY": "怀俄明",
    "DC": "哥伦比亚特区",
}

GEO_REGION_NAME_LABELS: dict[str, str] = {
    "beijing": "北京",
    "tianjin": "天津",
    "hebei": "河北",
    "shanxi": "山西",
    "inner mongolia": "内蒙古",
    "nei mongol": "内蒙古",
    "liaoning": "辽宁",
    "jilin": "吉林",
    "heilongjiang": "黑龙江",
    "shanghai": "上海",
    "jiangsu": "江苏",
    "zhejiang": "浙江",
    "anhui": "安徽",
    "fujian": "福建",
    "jiangxi": "江西",
    "shandong": "山东",
    "henan": "河南",
    "hubei": "湖北",
    "hunan": "湖南",
    "guangdong": "广东",
    "guangxi": "广西",
    "hainan": "海南",
    "chongqing": "重庆",
    "sichuan": "四川",
    "guizhou": "贵州",
    "yunnan": "云南",
    "tibet": "西藏",
    "xizang": "西藏",
    "shaanxi": "陕西",
    "gansu": "甘肃",
    "qinghai": "青海",
    "ningxia": "宁夏",
    "xinjiang": "新疆",
    "california": "加利福尼亚",
    "new york": "纽约",
    "texas": "得克萨斯",
    "florida": "佛罗里达",
    "washington": "华盛顿",
    "virginia": "弗吉尼亚",
    "illinois": "伊利诺伊",
    "pennsylvania": "宾夕法尼亚",
    "ohio": "俄亥俄",
    "georgia": "佐治亚",
    "north carolina": "北卡罗来纳",
    "michigan": "密歇根",
    "new jersey": "新泽西",
    "arizona": "亚利桑那",
    "massachusetts": "马萨诸塞",
    "tennessee": "田纳西",
    "indiana": "印第安纳",
    "missouri": "密苏里",
    "maryland": "马里兰",
    "wisconsin": "威斯康星",
    "colorado": "科罗拉多",
    "minnesota": "明尼苏达",
    "south carolina": "南卡罗来纳",
    "alabama": "阿拉巴马",
    "louisiana": "路易斯安那",
    "kentucky": "肯塔基",
    "oregon": "俄勒冈",
    "oklahoma": "俄克拉何马",
    "connecticut": "康涅狄格",
    "utah": "犹他",
    "iowa": "艾奥瓦",
    "nevada": "内华达",
    "arkansas": "阿肯色",
    "mississippi": "密西西比",
    "kansas": "堪萨斯",
    "new mexico": "新墨西哥",
    "nebraska": "内布拉斯加",
    "west virginia": "西弗吉尼亚",
    "idaho": "爱达荷",
    "hawaii": "夏威夷",
    "new hampshire": "新罕布什尔",
    "maine": "缅因",
    "montana": "蒙大拿",
    "rhode island": "罗得岛",
    "delaware": "特拉华",
    "south dakota": "南达科他",
    "north dakota": "北达科他",
    "alaska": "阿拉斯加",
    "vermont": "佛蒙特",
    "wyoming": "怀俄明",
    "district of columbia": "哥伦比亚特区",
    "england": "英格兰",
    "scotland": "苏格兰",
    "wales": "威尔士",
    "northern ireland": "北爱尔兰",
    "ontario": "安大略",
    "quebec": "魁北克",
    "british columbia": "不列颠哥伦比亚",
    "tokyo": "东京都",
    "osaka": "大阪府",
    "hong kong": "香港",
}

GEO_CITY_LABELS: dict[str, str] = {
    "beijing": "北京",
    "shanghai": "上海",
    "guangzhou": "广州",
    "shenzhen": "深圳",
    "hangzhou": "杭州",
    "chengdu": "成都",
    "chongqing": "重庆",
    "wuhan": "武汉",
    "xi'an": "西安",
    "xian": "西安",
    "nanjing": "南京",
    "tianjin": "天津",
    "suzhou": "苏州",
    "zhengzhou": "郑州",
    "changsha": "长沙",
    "dongguan": "东莞",
    "foshan": "佛山",
    "ningbo": "宁波",
    "qingdao": "青岛",
    "dalian": "大连",
    "xiamen": "厦门",
    "kunming": "昆明",
    "hefei": "合肥",
    "fuzhou": "福州",
    "shenyang": "沈阳",
    "harbin": "哈尔滨",
    "jinan": "济南",
    "wuxi": "无锡",
    "wenzhou": "温州",
    "nanchang": "南昌",
    "changchun": "长春",
    "guiyang": "贵阳",
    "nanning": "南宁",
    "haikou": "海口",
    "sanya": "三亚",
    "lanzhou": "兰州",
    "urumqi": "乌鲁木齐",
    "hohhot": "呼和浩特",
    "lhasa": "拉萨",
    "taiyuan": "太原",
    "shijiazhuang": "石家庄",
    "zhuhai": "珠海",
    "zhongshan": "中山",
    "huizhou": "惠州",
    "jiangmen": "江门",
    "quanzhou": "泉州",
    "putian": "莆田",
    "yantai": "烟台",
    "weifang": "潍坊",
    "baoding": "保定",
    "tangshan": "唐山",
    "luoyang": "洛阳",
    "changzhou": "常州",
    "nantong": "南通",
    "xuzhou": "徐州",
    "yangzhou": "扬州",
    "jiaxing": "嘉兴",
    "shaoxing": "绍兴",
    "jinhua": "金华",
    "taizhou": "台州",
    "hong kong": "香港",
    "macau": "澳门",
    "macao": "澳门",
    "taipei": "台北",
    "new taipei": "新北",
    "kaohsiung": "高雄",
    "taichung": "台中",
    "tainan": "台南",
    "singapore": "新加坡",
    "tokyo": "东京",
    "osaka": "大阪",
    "yokohama": "横滨",
    "nagoya": "名古屋",
    "seoul": "首尔",
    "busan": "釜山",
    "bangkok": "曼谷",
    "ho chi minh city": "胡志明市",
    "hanoi": "河内",
    "jakarta": "雅加达",
    "kuala lumpur": "吉隆坡",
    "manila": "马尼拉",
    "mumbai": "孟买",
    "delhi": "德里",
    "new delhi": "新德里",
    "bangalore": "班加罗尔",
    "bengaluru": "班加罗尔",
    "chennai": "金奈",
    "hyderabad": "海得拉巴",
    "london": "伦敦",
    "manchester": "曼彻斯特",
    "birmingham": "伯明翰",
    "paris": "巴黎",
    "frankfurt": "法兰克福",
    "berlin": "柏林",
    "munich": "慕尼黑",
    "amsterdam": "阿姆斯特丹",
    "rotterdam": "鹿特丹",
    "brussels": "布鲁塞尔",
    "zurich": "苏黎世",
    "geneva": "日内瓦",
    "madrid": "马德里",
    "barcelona": "巴塞罗那",
    "rome": "罗马",
    "milan": "米兰",
    "stockholm": "斯德哥尔摩",
    "dublin": "都柏林",
    "moscow": "莫斯科",
    "saint petersburg": "圣彼得堡",
    "istanbul": "伊斯坦布尔",
    "dubai": "迪拜",
    "abu dhabi": "阿布扎比",
    "new york": "纽约",
    "los angeles": "洛杉矶",
    "san francisco": "旧金山",
    "san jose": "圣何塞",
    "seattle": "西雅图",
    "chicago": "芝加哥",
    "dallas": "达拉斯",
    "houston": "休斯顿",
    "miami": "迈阿密",
    "atlanta": "亚特兰大",
    "boston": "波士顿",
    "washington": "华盛顿",
    "denver": "丹佛",
    "phoenix": "凤凰城",
    "philadelphia": "费城",
    "las vegas": "拉斯维加斯",
    "toronto": "多伦多",
    "montreal": "蒙特利尔",
    "vancouver": "温哥华",
    "sydney": "悉尼",
    "melbourne": "墨尔本",
    "brisbane": "布里斯班",
    "auckland": "奥克兰",
    "sao paulo": "圣保罗",
    "são paulo": "圣保罗",
    "rio de janeiro": "里约热内卢",
    "mexico city": "墨西哥城",
}

GEO_ASN_LABELS: dict[int, str] = {
    # 中国运营商 / 教育科研
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
    # 国内云 / 互联网
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
    # 港澳台
    9304: "香港电讯 HKT",
    9269: "香港宽频",
    10103: "香港宽频",
    9381: "HKBN",
    3462: "中华电信",
    9924: "台湾固网",
    24158: "台湾大哥大",
    # 海外云 / CDN
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
}


def format_geo_country(code: str | None) -> str:
    c = (code or "").strip().upper()
    if not c:
        return ""
    name = GEO_COUNTRY_LABELS.get(c)
    return f"{name} ({c})" if name else c


def _resolve_region_label(code: str, country: str | None = None) -> str | None:
    cc = (country or "").strip().upper()
    if cc == "CN":
        return GEO_CN_REGION_LABELS.get(code)
    if cc == "US":
        return GEO_US_REGION_LABELS.get(code)
    return GEO_CN_REGION_LABELS.get(code) or GEO_US_REGION_LABELS.get(code)


def format_geo_region(region: str | None, country: str | None = None) -> str:
    raw = (region or "").strip()
    if not raw:
        return ""
    code = raw.upper()
    by_code = _resolve_region_label(code, country)
    if by_code:
        return f"{by_code} ({code})"
    by_name = GEO_REGION_NAME_LABELS.get(raw.lower())
    if by_name:
        return f"{by_name} ({raw})"
    return raw


def format_geo_city(city: str | None) -> str:
    raw = (city or "").strip()
    if not raw:
        return ""
    name = GEO_CITY_LABELS.get(raw.lower())
    return f"{name} ({raw})" if name else raw


def format_geo_asn(asn: int | str | None) -> str:
    if asn is None or asn == "":
        return ""
    try:
        n = int(str(asn).strip())
    except (TypeError, ValueError):
        return str(asn).strip()
    if n <= 0:
        return ""
    name = GEO_ASN_LABELS.get(n)
    return f"{name} ({n})" if name else str(n)


# Common MaxMind ASN org-name keywords → Chinese labels (case-insensitive substring).
# Matching still uses the raw organization string; this is display-only.
GEO_ISP_LABELS: list[tuple[str, str]] = [
    ("china mobile international", "中国移动国际"),
    ("chinanet", "中国电信"),
    ("china telecom", "中国电信"),
    ("china-telecom", "中国电信"),
    ("china unicom", "中国联通"),
    ("chinaunicom", "中国联通"),
    ("china-unicom", "中国联通"),
    ("china mobile", "中国移动"),
    ("chinamobile", "中国移动"),
    ("cmnet", "中国移动"),
    ("cmcc", "中国移动"),
    ("cernet", "教育网 CERNET"),
    ("cstnet", "中科院 CSTNET"),
    ("drpeng", "鹏博士"),
    ("wasu", "华数"),
    ("gehua", "歌华有线"),
    ("alibaba", "阿里云"),
    ("aliyun", "阿里云"),
    ("taobao", "阿里云"),
    ("tencent", "腾讯云"),
    ("huawei", "华为云"),
    ("baidu", "百度云"),
    ("bytedance", "字节跳动"),
    ("byteplus", "火山引擎"),
    ("volcengine", "火山引擎"),
    ("jd.com", "京东云"),
    ("jingdong", "京东云"),
    ("kingsoft", "金山云"),
    ("ucloud", "UCloud"),
    ("qingcloud", "青云"),
    ("hkt", "香港电讯"),
    ("pccw", "电讯盈科"),
    ("chunghwa", "中华电信"),
    ("far eastone", "远传电信"),
    ("taiwan mobile", "台湾大哥大"),
    ("amazon", "亚马逊 AWS"),
    ("google", "谷歌云"),
    ("microsoft", "微软 Azure"),
    ("azure", "微软 Azure"),
    ("cloudflare", "Cloudflare"),
    ("akamai", "Akamai"),
    ("fastly", "Fastly"),
    ("digitalocean", "DigitalOcean"),
    ("linode", "Linode"),
    ("vultr", "Vultr"),
    ("ovh", "OVH"),
    ("hetzner", "Hetzner"),
    ("oracle", "甲骨文云"),
    ("softlayer", "IBM SoftLayer"),
    ("ibm", "IBM 云"),
    ("leaseweb", "Leaseweb"),
    ("contabo", "Contabo"),
    ("m247", "M247"),
    ("cogent", "Cogent"),
    ("lumen", "Lumen"),
    ("level 3", "Level3"),
    ("level3", "Level3"),
    ("meta platforms", "Meta"),
    ("facebook", "Meta"),
    ("apple", "Apple"),
    ("github", "GitHub"),
]

# Filter / rule hints: value ≈ common MaxMind organization fragments
GEO_ISP_SELECT_HINTS: list[dict[str, str]] = [
    {"value": "China Telecom", "label": "中国电信 (China Telecom)"},
    {"value": "China Unicom", "label": "中国联通 (China Unicom)"},
    {"value": "China Mobile", "label": "中国移动 (China Mobile)"},
    {"value": "CERNET", "label": "教育网 (CERNET)"},
    {"value": "Alibaba", "label": "阿里云 (Alibaba)"},
    {"value": "Tencent", "label": "腾讯云 (Tencent)"},
    {"value": "Huawei", "label": "华为云 (Huawei)"},
    {"value": "Amazon.com, Inc.", "label": "亚马逊 AWS (Amazon.com, Inc.)"},
    {"value": "GOOGLE", "label": "谷歌云 (GOOGLE)"},
    {"value": "MICROSOFT-CORP-MSN-AS-BLOCK", "label": "微软 Azure (Microsoft)"},
    {"value": "CLOUDFLARENET", "label": "Cloudflare (CLOUDFLARENET)"},
    {"value": "AKAMAI", "label": "Akamai"},
    {"value": "DIGITALOCEAN", "label": "DigitalOcean"},
    {"value": "Hetzner Online GmbH", "label": "Hetzner"},
    {"value": "OVH SAS", "label": "OVH"},
]


def format_geo_isp(isp: str | None) -> str:
    raw = (isp or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    for match, label in GEO_ISP_LABELS:
        if match in lower:
            return f"{label} ({raw})"
    return raw


def geo_country_field_options() -> list[dict[str, str]]:
    items = [
        {"value": code, "label": f"{name} ({code})"}
        for code, name in GEO_COUNTRY_LABELS.items()
        if code not in ("UNKNOWN", "XX")
    ]
    items.sort(key=lambda x: x["label"])
    return items


def geo_cn_region_field_options() -> list[dict[str, str]]:
    items = [
        {"value": code, "label": f"{name} ({code})"}
        for code, name in GEO_CN_REGION_LABELS.items()
    ]
    items.sort(key=lambda x: x["label"])
    return items


# CN/US 重叠的省州码（无国家上下文时优先中国语义，选项里只保留中国侧）
_GEO_REGION_CODE_OVERLAP = frozenset({"HI", "NM", "SC", "SD"})

# MaxMind city names en 特例（不能简单 .title()）
_GEO_CITY_CANONICAL: dict[str, str] = {
    "xi'an": "Xi'an",
    "são paulo": "São Paulo",
    "sao paulo": "Sao Paulo",
    "ho chi minh city": "Ho Chi Minh City",
    "kuala lumpur": "Kuala Lumpur",
    "new york": "New York",
    "los angeles": "Los Angeles",
    "san francisco": "San Francisco",
    "san jose": "San Jose",
    "las vegas": "Las Vegas",
    "new delhi": "New Delhi",
    "abu dhabi": "Abu Dhabi",
    "saint petersburg": "Saint Petersburg",
    "rio de janeiro": "Rio de Janeiro",
    "mexico city": "Mexico City",
    "hong kong": "Hong Kong",
    "new taipei": "New Taipei",
}


def _city_canonical_en(en_lower: str) -> str:
    special = _GEO_CITY_CANONICAL.get(en_lower)
    if special:
        return special
    return " ".join(part.capitalize() for part in en_lower.split())


def geo_region_field_options() -> list[dict[str, str]]:
    """省/州下拉：中国大陆 + 不与中国码冲突的美国州。"""
    items = [
        {"value": code, "label": f"{name} ({code})"}
        for code, name in GEO_CN_REGION_LABELS.items()
    ]
    for code, name in GEO_US_REGION_LABELS.items():
        if code in GEO_CN_REGION_LABELS or code in _GEO_REGION_CODE_OVERLAP:
            continue
        items.append({"value": code, "label": f"{name} ({code})"})
    items.sort(key=lambda x: x["label"])
    return items


def geo_city_field_options() -> list[dict[str, str]]:
    """城市下拉：常见英文名（与 MaxMind city names en 对齐）+ 中文标签。"""
    items = [
        {
            "value": _city_canonical_en(en_lower),
            "label": f"{zh} ({_city_canonical_en(en_lower)})",
        }
        for en_lower, zh in GEO_CITY_LABELS.items()
    ]
    # 去重（xian / xi'an 等）
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for item in items:
        if item["value"] in seen:
            continue
        seen.add(item["value"])
        uniq.append(item)
    uniq.sort(key=lambda x: x["label"])
    return uniq


def geo_asn_field_options() -> list[dict[str, str]]:
    """ASN 下拉：常见 ASN 号 + 语义化组织名。"""
    items = [
        {"value": str(asn), "label": f"{name} ({asn})"}
        for asn, name in GEO_ASN_LABELS.items()
    ]
    items.sort(key=lambda x: x["label"])
    return items


def geo_isp_field_options() -> list[dict[str, str]]:
    return list(GEO_ISP_SELECT_HINTS)


def _lookup(mapping: dict[str, str], value: str | None) -> str | None:
    if value is None:
        return None
    return mapping.get(str(value).strip()) or mapping.get(str(value).strip().lower())


def format_rule_stats_label(
    *,
    rule_id: int | str,
    rule_name: str | None,
    source: str | None = None,
) -> str:
    """Format a grouped hit-rule row, prefixing localized source in brackets."""
    rid = str(rule_id)
    name = (rule_name or "").strip() or f"规则 #{rid}"
    body = f"{name} (#{rid})"
    if not source:
        return body
    src = _lookup(SOURCE_LABELS, source) or source
    return f"[{src}]{body}"


def format_dimension_label(
    dimension: str,
    key: str,
    raw_label: str,
    *,
    site_name: str | None = None,
    site_domain: str | None = None,
) -> str:
    """Convert a grouped stats row label to Chinese where applicable."""
    if key == "none" or raw_label == "（空）":
        return "（空）"

    if dimension == "source":
        return _lookup(SOURCE_LABELS, key) or _lookup(SOURCE_LABELS, raw_label) or raw_label
    if dimension in ("mode", "action"):
        return _lookup(MODE_LABELS, key) or _lookup(MODE_LABELS, raw_label) or raw_label
    if dimension == "log_type":
        return _lookup(LOG_TYPE_LABELS, key) or _lookup(LOG_TYPE_LABELS, raw_label) or raw_label
    if dimension == "blocked":
        return "已拦截" if key == "true" else "已放行"
    if dimension == "geo_country":
        code = (key or raw_label or "").upper()
        return format_geo_country(code) or raw_label or code
    if dimension == "geo_region":
        return format_geo_region(key or raw_label) or raw_label or key
    if dimension == "geo_city":
        return format_geo_city(key or raw_label) or raw_label or key
    if dimension == "geo_asn":
        return format_geo_asn(key or raw_label) or raw_label or key
    if dimension == "geo_isp":
        return format_geo_isp(key or raw_label) or raw_label or key
    if dimension == "ua":
        return raw_label or key
    if dimension == "full_url":
        return raw_label or key
    if dimension in ("request_uri", "uri_query"):
        return raw_label or key
    if dimension == "bot_category":
        return _BOT_CATEGORY_LABELS.get(key, raw_label or key)
    if dimension == "site_id":
        if site_name and site_domain:
            return f"{site_name} ({site_domain})"
        if site_name:
            return f"{site_name} (#{key})"
        if site_domain:
            return f"{site_domain} (#{key})"
        return f"站点 #{key}" if key != "none" else "（空）"

    return raw_label
