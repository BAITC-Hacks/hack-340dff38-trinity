from sqlalchemy import select
from ..models import ModerationItem
from .ai.moderation import moderate


def record_moderation(db, entity_type, entity_id, text):
    result = moderate(text)
    item = db.scalar(
        select(ModerationItem).where(
            ModerationItem.entity_type == entity_type,
            ModerationItem.entity_id == str(entity_id),
        )
    )
    if not item:
        item = ModerationItem(entity_type=entity_type, entity_id=str(entity_id))
        db.add(item)
    item.status = result.status
    item.reasons = result.reasons
    item.excerpt = text[:1000]
    item.ai_source = result.source
