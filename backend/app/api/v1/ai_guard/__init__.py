from fastapi import APIRouter

from app.api.v1.ai_guard import chat, incidents, knowledge, policies, settings

router = APIRouter()
router.include_router(settings.router, prefix="/settings", tags=["ai-guard-settings"])
router.include_router(chat.router, prefix="/chat", tags=["ai-guard-chat"])
router.include_router(policies.router, prefix="/policies", tags=["ai-guard-policies"])
router.include_router(incidents.router, prefix="/incidents", tags=["ai-guard-incidents"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["ai-guard-knowledge"])
