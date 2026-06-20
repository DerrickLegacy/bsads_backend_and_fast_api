import httpx
import logging
from typing import List
from sqlalchemy.orm import Session

from api.models import PushNotificationDevice, Alert, Hive, User, AdvisoryAction, AdvisoryTemplate, InferenceResult

logger = logging.getLogger(__name__)


EXPO_PUSH_API_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notification(token: str, title: str, body: str, data: dict = None):
    """Send a push notification using Expo's Push API."""
    message = {
        "to": token,
        "title": title,
        "body": body,
        "data": data or {},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                EXPO_PUSH_API_URL,
                json=message,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            if result.get("errors"):
                logger.error(f"Expo Push API error: {result['errors']}")
            return result
    except Exception as e:
        logger.exception(f"Failed to send push notification: {e}")
        return None


async def send_alert_notifications(alert: Alert, db: Session):
    """Send push notifications to all active devices of the alert's hive owner."""
    # Get hive owner
    hive = db.query(Hive).filter(Hive.hive_id == alert.hive_id).first()
    if not hive:
        logger.warning(f"No hive found for alert {alert.alert_id}")
        return

    user = db.query(User).filter(User.user_id == hive.owner_id).first()
    if not user:
        logger.warning(f"No user found for hive {hive.hive_id}")
        return

    # Get active devices
    devices = db.query(PushNotificationDevice).filter(
        PushNotificationDevice.user_id == user.user_id,
        PushNotificationDevice.is_active == True,
    ).all()

    if not devices:
        logger.info(f"No active devices for user {user.user_id}")
        return

    # Prepare notification content
    title = "Hive Alert!"
    # Get hive state from inference or template
    hive_state = "Unknown State"
    if alert.inference_id:
        inference = db.query(InferenceResult).filter(
            InferenceResult.inference_id == alert.inference_id
        ).first()
        if inference:
            action = db.query(AdvisoryAction).filter(
                AdvisoryAction.inference_id == alert.inference_id
            ).first()
            if action:
                template = db.query(AdvisoryTemplate).filter(
                    AdvisoryTemplate.template_id == action.template_id
                ).first()
                if template:
                    hive_state = template.hive_state.replace("_", " ").title()
                else:
                    hive_state = inference.hive_state.replace("_", " ").title()

    body = f"{hive.hive_name or 'Your hive'} - {hive_state}: {alert.recommended_action or 'Check your hive for details.'}"
    data = {
        "alert_id": str(alert.alert_id),
        "hive_id": str(hive.hive_id),
        "type": "alert",
    }

    # Send to all devices
    for device in devices:
        await send_push_notification(device.token, title, body, data)
