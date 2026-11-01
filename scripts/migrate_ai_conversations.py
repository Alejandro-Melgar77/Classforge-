"""
Migration Script: migrate_ai_conversations.py
Migrates legacy ai_conversations.messages[] array into the scalable ai_messages collection.

Guarantees:
- Idempotent: checks for existing messages by id/client_id before inserting.
- Safe: never deletes or modifies the legacy ai_conversations collection.
- Supports --dry-run mode for previewing operations without altering data.
- Provides a detailed summary report of conversations and message counts.
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_ai_conversations")


async def run_migration(
    mongodb_url: str = "mongodb://localhost:27017",
    database_name: str = "classforge",
    dry_run: bool = False,
    project_id_filter: Optional[str] = None,
    client: Optional[Any] = None,
    db: Optional[Any] = None,
) -> Dict[str, int]:
    """Executes the migration from ai_conversations to ai_messages and ai_project_state."""
    close_client = False
    if db is None:
        if client is None:
            client = AsyncIOMotorClient(mongodb_url)
            close_client = True
        db = client[database_name]

    logger.info(f"Connected to database '{database_name}'")
    if dry_run:
        logger.info("=== RUNNING IN DRY-RUN MODE (No writes will be committed) ===")

    stats = {
        "conversations_scanned": 0,
        "messages_scanned": 0,
        "messages_migrated": 0,
        "messages_skipped": 0,
        "project_states_created": 0,
        "errors": 0,
    }

    try:
        query: Dict[str, Any] = {}
        if project_id_filter:
            from bson import ObjectId
            if ObjectId.is_valid(project_id_filter):
                query["project_id"] = {"$in": [project_id_filter, ObjectId(project_id_filter)]}
            else:
                query["project_id"] = project_id_filter

        cursor = db["ai_conversations"].find(query)
        conversations = await cursor.to_list(length=None)
        stats["conversations_scanned"] = len(conversations)

        for conv in conversations:
            p_id = str(conv.get("project_id", ""))
            if not p_id:
                logger.warning(f"Skipping conversation without project_id: {conv.get('_id')}")
                continue

            messages: List[Dict[str, Any]] = conv.get("messages", [])
            active_roles: List[str] = conv.get("active_ai_roles", [])

            # 1. Initialize ai_project_state if missing
            existing_state = await db["ai_project_state"].find_one({"project_id": p_id})
            if not existing_state:
                from app.ai_team.domain.roles import ROLES_REGISTRY
                active_set = set(active_roles)
                initial_roles = [
                    {
                        "role_id": r_id,
                        "enabled": (r_id in active_set) if active_set else True,
                        "autonomy": "suggest",
                    }
                    for r_id in ROLES_REGISTRY.keys()
                ]
                now_utc = datetime.now(timezone.utc)
                state_doc = {
                    "project_id": p_id,
                    "participative": {
                        "enabled": len(active_roles) > 1,
                        "updated_by": "migration_script",
                        "updated_at": now_utc,
                    },
                    "roles": initial_roles,
                    "digest": {
                        "text": "",
                        "tokens": 0,
                        "covers_until": None,
                        "updated_at": None,
                    },
                    "updated_at": now_utc,
                }
                stats["project_states_created"] += 1
                if not dry_run:
                    try:
                        await db["ai_project_state"].insert_one(state_doc)
                    except Exception as e:
                        logger.warning(f"Could not create initial project state for {p_id}: {e}")

            # 2. Migrate messages
            last_user_owner: Optional[str] = None

            for msg in messages:
                stats["messages_scanned"] += 1
                msg_id = str(msg.get("id") or msg.get("_id") or "")
                if not msg_id:
                    stats["errors"] += 1
                    continue

                # Idempotency check: check if already migrated
                existing_msg = await db["ai_messages"].find_one({
                    "$or": [
                        {"_id": msg_id},
                        {"client_id": msg_id},
                    ]
                })

                if existing_msg:
                    stats["messages_skipped"] += 1
                    # Keep track of owner if user message
                    if existing_msg.get("author_type") == "user" and existing_msg.get("owner_id"):
                        last_user_owner = existing_msg.get("owner_id")
                    continue

                author_type = msg.get("author_type", "user")
                author_id = str(msg.get("author_id")) if msg.get("author_id") else None

                # Thread and owner logic
                if author_type == "user":
                    thread = "personal"
                    owner_id = author_id
                    last_user_owner = owner_id
                else:
                    # AI message: belongs to the personal thread of preceding user if known
                    if last_user_owner:
                        thread = "personal"
                        owner_id = last_user_owner
                    else:
                        thread = "project"
                        owner_id = None

                created_at = msg.get("timestamp") or msg.get("created_at") or datetime.now(timezone.utc)
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except Exception:
                        created_at = datetime.now(timezone.utc)

                doc_to_insert = {
                    "_id": msg_id,
                    "id": msg_id,
                    "project_id": p_id,
                    "thread": thread,
                    "owner_id": owner_id,
                    "author_type": author_type,
                    "author_id": author_id,
                    "author_name": msg.get("author_name", "Usuario"),
                    "author_role_label": msg.get("author_role_label", "dev"),
                    "ai_role": msg.get("ai_role"),
                    "content": msg.get("content", ""),
                    "content_format": "markdown",
                    "proposals": msg.get("proposals", []) or [],
                    "proposal_state": {},
                    "mentions": [],
                    "reply_to": None,
                    "client_id": msg_id,
                    "trigger": "migration",
                    "status": "ok",
                    "error_code": None,
                    "model": None,
                    "created_at": created_at,
                    "updated_at": msg.get("updated_at"),
                }

                if not dry_run:
                    try:
                        await db["ai_messages"].insert_one(doc_to_insert)
                        stats["messages_migrated"] += 1
                    except Exception as e:
                        logger.error(f"Error inserting message {msg_id}: {e}")
                        stats["errors"] += 1
                else:
                    stats["messages_migrated"] += 1

    except Exception as e:
        logger.error(f"Migration error: {e}")
        stats["errors"] += 1
    finally:
        if close_client and client:
            client.close()

    return stats


def print_report(stats: Dict[str, int], dry_run: bool) -> None:
    mode_str = "DRY-RUN (Simulación)" if dry_run else "REAL (Aplicado a BD)"
    print("\n" + "=" * 60)
    print(f" INFORME DE MIGRACIÓN: ai_conversations -> ai_messages [{mode_str}]")
    print("=" * 60)
    print(f" Conversaciones procesadas      : {stats['conversations_scanned']}")
    print(f" Estados de proyecto creados    : {stats['project_states_created']}")
    print(f" Total mensajes examinados      : {stats['messages_scanned']}")
    print(f" Mensajes migrados / a migrar   : {stats['messages_migrated']}")
    print(f" Mensajes omitidos (ya existían): {stats['messages_skipped']}")
    print(f" Errores encontrados           : {stats['errors']}")
    print("=" * 60)
    print(" Colección 'ai_conversations' PRESERVADA intacta (cero borrados).")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Migra mensajes desde ai_conversations hacia la colección ai_messages."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la migración sin insertar datos reales.",
    )
    parser.add_argument(
        "--mongodb-url",
        default="mongodb://localhost:27017",
        help="URL de conexión a MongoDB.",
    )
    parser.add_argument(
        "--database",
        default="classforge",
        help="Nombre de la base de datos de ClassForge.",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="ID de proyecto específico para migrar (opcional).",
    )

    args = parser.parse_args()

    stats = asyncio.run(
        run_migration(
            mongodb_url=args.mongodb_url,
            database_name=args.database,
            dry_run=args.dry_run,
            project_id_filter=args.project_id,
        )
    )
    print_report(stats, args.dry_run)
    if stats["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
