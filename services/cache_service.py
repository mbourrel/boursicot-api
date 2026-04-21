"""
Helpers génériques de cache PostgreSQL (table macro_cache).
Extraits de routers/macro.py pour être réutilisables par tous les services.
"""
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
import models


def get_cached(db: Session, key: str, max_age_hours: int = 24):
    """Retourne les données du cache si elles existent et ne sont pas périmées."""
    record = db.query(models.MacroCache).filter(models.MacroCache.cache_key == key).first()
    if not record:
        return None
    if datetime.utcnow() - record.updated_at > timedelta(hours=max_age_hours):
        return None
    return json.loads(record.data_json)


def get_stale(db: Session, key: str):
    """Retourne le cache même périmé — fallback si la source externe est indisponible."""
    record = db.query(models.MacroCache).filter(models.MacroCache.cache_key == key).first()
    if not record:
        return None
    return json.loads(record.data_json)


def set_cached(db: Session, key: str, data: dict):
    """Écrit ou met à jour une entrée de cache."""
    record = db.query(models.MacroCache).filter(models.MacroCache.cache_key == key).first()
    if record:
        record.data_json  = json.dumps(data, ensure_ascii=False)
        record.updated_at = datetime.utcnow()
    else:
        record = models.MacroCache(
            cache_key=key,
            data_json=json.dumps(data, ensure_ascii=False),
        )
        db.add(record)
    db.commit()
