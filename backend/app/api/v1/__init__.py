from fastapi import APIRouter

from app.api.v1 import (
    ai_guard,
    alert_policies,
    auth,
    backup,
    blacklist,
    bot_categories,
    bots,
    certificates,
    dashboard,
    exceptions,
    ip_groups,
    logs,
    meta,
    notification_channels,
    ratelimit,
    rules,
    settings,
    sites,
    traffic,
    traffic_intel,
    whitelist,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(
    notification_channels.router,
    prefix="/notification-channels",
    tags=["notification-channels"],
)
api_router.include_router(alert_policies.router, prefix="/alert-policies", tags=["alert-policies"])
api_router.include_router(ai_guard.router, prefix="/ai-guard", tags=["ai-guard"])
api_router.include_router(certificates.router, prefix="/certificates", tags=["certificates"])
api_router.include_router(sites.router, prefix="/sites", tags=["sites"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(blacklist.router, prefix="/blacklist", tags=["blacklist"])
api_router.include_router(bots.router, prefix="/bots", tags=["bots"])
api_router.include_router(
    bot_categories.router, prefix="/bot-categories", tags=["bot-categories"]
)
api_router.include_router(whitelist.router, prefix="/whitelist", tags=["whitelist"])
api_router.include_router(exceptions.router, prefix="/exceptions", tags=["exceptions"])
api_router.include_router(ip_groups.router, prefix="/ip-groups", tags=["ip-groups"])
api_router.include_router(ratelimit.router, prefix="/ratelimit", tags=["ratelimit"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(traffic.router, prefix="/traffic", tags=["traffic"])
api_router.include_router(
    traffic_intel.router, prefix="/traffic/intel", tags=["traffic-intel"]
)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
