from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException
from orcanium.app.core.db import ChannelConfig, get_db
from orcanium.app.domains.channel.manager import channel_runner
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/")
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(ChannelConfig).all()
    res = []
    for chan in channels:
        res.append(
            {
                "id": chan.id,
                "platform": chan.platform,
                "enabled": chan.enabled,
                "config": chan.get_config(),
            }
        )
    return res


@router.post("/register")
def register_channel(
    channel_id: str,
    platform: str,
    config: Dict[str, Any],
    enabled: bool = False,
    db: Session = Depends(get_db),
):
    try:
        channel = (
            db.query(ChannelConfig).filter(ChannelConfig.id == channel_id).first()
        )
        if not channel:
            channel = ChannelConfig(id=channel_id, platform=platform, enabled=enabled)
            channel.set_config(config)
            db.add(channel)
        else:
            channel.platform = platform
            channel.enabled = enabled
            channel.set_config(config)

        db.commit()
        db.refresh(channel)

        # Hot-reload in channel runner
        channel_runner.reload_channel(channel_id, platform, config, enabled)
        return {
            "status": "success",
            "channel": {"id": channel.id, "enabled": channel.enabled},
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{channel_id}/toggle")
def toggle_channel(channel_id: str, enabled: bool, db: Session = Depends(get_db)):
    channel = db.query(ChannelConfig).filter(ChannelConfig.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.enabled = enabled
    db.commit()

    # Reload bot state
    channel_runner.reload_channel(
        channel_id, channel.platform, channel.get_config(), enabled
    )
    return {"status": "success", "channel_id": channel_id, "enabled": channel.enabled}


@router.delete("/{channel_id}")
def delete_channel(channel_id: str, db: Session = Depends(get_db)):
    channel = db.query(ChannelConfig).filter(ChannelConfig.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Stop bot execution if running
    channel_runner.stop_channel(channel_id)

    db.delete(channel)
    db.commit()
    return {"status": "success", "detail": f"Channel {channel_id} deleted"}
