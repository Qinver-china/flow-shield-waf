# 修复后审查清单

本文档对应《流盾 WAF 全面修复计划》第五轮审查闭环，用于验证修复是否到位。

## 第一轮：自动化

- [ ] `cd backend && pytest -q`
- [ ] `cd frontend && npm run build`
- [ ] `bash deploy/smoke_test.sh`

## 第二轮：安全专项

| 检查项 | 通过标准 |
|--------|----------|
| 默认凭据 | `.env` / 面板登录后尽快改为自有密钥与管理员密码 |
| Challenge 密钥 | 引擎无 `waf_default_secret` 回退 |
| 登录限速 | 连续错误登录触发 429 |
| Refresh 禁用用户 | 返回 401 |
| AI confirm 注入 | 篡改 payload 被拒绝 |

## 第三轮：业务链路 E2E

- [ ] 规则/站点/黑白名单/例外/限速/IP 组变更后引擎行为一致
- [ ] Dashboard feed 返回 15 条
- [ ] AlertPolicies 分页正常
- [ ] Access token 静默 refresh
- [ ] `auto_by_traffic` 空闲期 block 事件仍可查询

## 已知限制（本次未处理）

- 算术 **captcha 模式**加固（按计划跳过）
- IPv6 CIDR 完整支持
- 多用户注册与细粒度权限

## 残余风险

- 单 consumer 日志水平扩展需手动分片
- 高 QPS 下 ClickHouse keyword 查询仍需结合时间范围控制
