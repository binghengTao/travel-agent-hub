"""
旅行助手 源码组件。


"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import current_user, sessions
from app.core.response import success
from app.services.auth_service import AuthenticatedUser
from app.services.session_store import SessionStore

router = APIRouter()


class PreferenceProfile(BaseModel):
    """PreferenceProfile"""
    budget_level: str = Field(default="", description="low / medium / high")
    travel_style: str = ""
    favorite_themes: list[str] = Field(default_factory=list)
    disliked_themes: list[str] = Field(default_factory=list)
    pace: str = ""
    food_preference: str = ""
    hotel_preference: str = ""
    notes: str = ""


class PreferenceMergeRequest(BaseModel):
    """PreferenceMergeRequest"""
    profiles: list[PreferenceProfile] = Field(default_factory=list)
    user_ids: list[str] = Field(default_factory=list)
    target_user_id: str | None = None


@router.get("/me")
async def get_preferences(
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：get_preferences 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    return success({"user_id": user.user_id, "profile": await store.get_profile(user.user_id)})


@router.put("/me")
async def update_preferences(
    profile: PreferenceProfile,
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：update_preferences 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    data = {key: value for key, value in profile.model_dump().items() if value not in ("", [], None)}
    saved = await store.save_profile(user.user_id, data)
    return success({"user_id": user.user_id, "profile": saved})


@router.delete("/me")
async def delete_preferences(
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：delete_preferences 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    await store.delete_profile(user.user_id)
    return success({"user_id": user.user_id, "deleted": True})


@router.post("/merge")
async def merge_preferences(
    payload: PreferenceMergeRequest,
    store: SessionStore = Depends(sessions),
    user: AuthenticatedUser = Depends(current_user),
) -> dict:
    """说明：merge_preferences 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    profiles = [profile.model_dump() for profile in payload.profiles]
    current_profile = await store.get_profile(user.user_id)
    if current_profile:
        profiles.append(current_profile)

    # User IDs are accepted for backward compatibility, but cannot cross user boundaries.
    for requested_user_id in payload.user_ids:
        if requested_user_id in (user.user_id, "me", "current"):
            stored = await store.get_profile(user.user_id)
            if stored:
                profiles.append(stored)
        else:
            raise HTTPException(status_code=403, detail="Cannot merge another user's preferences.")

    target_user_id = payload.target_user_id or user.user_id
    if target_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Cannot merge another user's preferences.")
    merged: dict = {
        "budget_level": _mode([item.get("budget_level", "") for item in profiles]),
        "travel_style": _mode([item.get("travel_style", "") for item in profiles]),
        "pace": _mode([item.get("pace", "") for item in profiles]),
        "favorite_themes": _unique_sum(item.get("favorite_themes", []) for item in profiles),
        "disliked_themes": _unique_sum(item.get("disliked_themes", []) for item in profiles),
        "food_preference": "；".join(item.get("food_preference", "") for item in profiles if item.get("food_preference")),
        "hotel_preference": "；".join(item.get("hotel_preference", "") for item in profiles if item.get("hotel_preference")),
        "notes": "；".join(item.get("notes", "") for item in profiles if item.get("notes")),
    }
    merged = {key: value for key, value in merged.items() if value not in ("", [], None)}
    merged = await store.save_profile(target_user_id, merged)
    return success({"user_id": target_user_id, "profile": merged, "source_count": len(profiles)})


def _mode(values: list[str]) -> str:
    """说明：_mode 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return max(counts, key=counts.get) if counts else ""


def _unique_sum(groups) -> list[str]:
    """说明：_unique_sum 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。"""
    result: list[str] = []
    for group in groups:
        for item in group or []:
            if item and item not in result:
                result.append(item)
    return result
