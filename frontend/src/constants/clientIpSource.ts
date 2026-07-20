export interface ClientIpSourceOption {
  value: string;
  label: string;
  desc: string;
}

/** Keep in sync with backend app/constants/client_ip.py */
export const CLIENT_IP_SOURCE_OPTIONS: ClientIpSourceOption[] = [
  {
    value: "remote_addr",
    label: "直连 IP（TCP 连接地址）",
    desc: "默认。源站直连 WAF、无 CDN 时使用。",
  },
  {
    value: "xff_first",
    label: "X-Forwarded-For（第一个 IP）",
    desc: "取 X-Forwarded-For 链最左侧 IP，常见于多层代理。",
  },
  {
    value: "xff_last",
    label: "X-Forwarded-For（最后一个 IP）",
    desc: "取 X-Forwarded-For 链最右侧 IP。",
  },
  {
    value: "x_real_ip",
    label: "X-Real-IP",
    desc: "读取 X-Real-IP 请求头。",
  },
  {
    value: "cf_connecting_ip",
    label: "CF-Connecting-IP（Cloudflare）",
    desc: "站点接入 Cloudflare 时选用。",
  },
  {
    value: "true_client_ip",
    label: "True-Client-IP（Akamai 等）",
    desc: "Akamai、部分企业 CDN 使用的真实客户端头。",
  },
  {
    value: "x_client_ip",
    label: "X-Client-IP",
    desc: "部分 CDN / 负载均衡使用的客户端 IP 头。",
  },
];

export function clientIpSourceLabel(value: string | null | undefined): string {
  const item = CLIENT_IP_SOURCE_OPTIONS.find((o) => o.value === value);
  return item?.label ?? value ?? "-";
}
