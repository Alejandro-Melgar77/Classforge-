# -*- coding: utf-8 -*-
"""
Script de migración idempotente para desacoplar el historial embebido de diagramas
hacia la colección dedicada `diagram_versions`.

Mide y reporta el tamaño BSON antes y después de la migración.
Soporta banderas:
  --rollback : Reconstruye el array embebido 'history' desde 'diagram_versions'.
  --verify   : Comprueba la consistencia de los datos migrados.
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
import bson
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings


async def ensure_version_indexes(db):
    """Crea los índices necesarios en la colección diagram_versions."""
    await db["diagram_versions"].create_index([("diagram_id", 1), ("version", -1)], unique=True)
    await db["diagram_versions"].create_index([("diagram_id", 1), ("created_at", -1)])
    await db["diagram_versions"].create_index([("created_at", -1)])
    print("[*] Índices en 'diagram_versions' verificados exitosamente.")


async def migrate_diagram_versions(db) -> dict:
    """Migra el historial embebido hacia diagram_versions de manera idempotente."""
    await ensure_version_indexes(db)

    cursor = db["diagrams"].find({"history": {"$exists": True, "$ne": []}})
    diagrams = await cursor.to_list(length=None)

    total_diagrams = len(diagrams)
    total_versions_migrated = 0
    total_bytes_before = 0
    total_bytes_after = 0

    print(f"[*] Encontrados {total_diagrams} diagramas con historial embebido para migrar.")

    for doc in diagrams:
        doc_id = doc["_id"]
        history = doc.get("history", [])
        if not history:
            continue

        raw_bson_before = bson.BSON.encode(doc)
        size_before = len(raw_bson_before)
        total_bytes_before += size_before

        for item in history:
            version_num = item.get("version")
            if version_num is None:
                continue

            created_at = item.get("saved_at") or item.get("created_at") or datetime.now(timezone.utc)
            version_doc = {
                "diagram_id": doc_id,
                "version": version_num,
                "graph_data": item.get("graph_data", {}),
                "saved_by": item.get("saved_by"),
                "saved_at": created_at,
                "created_at": created_at,
                "comment": item.get("comment"),
            }

            # Upsert idempotente
            await db["diagram_versions"].update_one(
                {"diagram_id": doc_id, "version": version_num},
                {"$set": version_doc},
                upsert=True
            )
            total_versions_migrated += 1

        # Remover array embebido 'history' del documento
        await db["diagrams"].update_one(
            {"_id": doc_id},
            {"$unset": {"history": ""}}
        )

        after_doc = await db["diagrams"].find_one({"_id": doc_id})
        size_after = len(bson.BSON.encode(after_doc))
        total_bytes_after += size_after

        savings = ((size_before - size_after) / size_before) * 100 if size_before else 0
        print(f"  [+] Diagrama {doc_id} ('{doc.get('name', 'Sin nombre')}'): {size_before:,} bytes -> {size_after:,} bytes (-{savings:.1f}%) | {len(history)} versiones migradas.")

    overall_savings = (
        ((total_bytes_before - total_bytes_after) / total_bytes_before) * 100
        if total_bytes_before else 0
    )

    summary = {
        "total_diagrams": total_diagrams,
        "total_versions_migrated": total_versions_migrated,
        "bytes_before": total_bytes_before,
        "bytes_after": total_bytes_after,
        "saved_bytes": total_bytes_before - total_bytes_after,
        "savings_percentage": overall_savings
    }

    print("\n" + "=" * 60)
    print("RESUMEN DE MIGRACIÓN DE VERSIONES")
    print("=" * 60)
    print(f"Diagramas procesados:        {total_diagrams}")
    print(f"Versiones migradas:          {total_versions_migrated}")
    print(f"Tamaño total antes:          {total_bytes_before:,} bytes ({total_bytes_before / 1024:.2f} KB)")
    print(f"Tamaño total después:        {total_bytes_after:,} bytes ({total_bytes_after / 1024:.2f} KB)")
    print(f"Reducción lograda:           {summary['saved_bytes']:,} bytes ({summary['saved_bytes'] / 1024:.2f} KB) -> -{overall_savings:.2f}%")
    print("=" * 60 + "\n")

    return summary


async def rollback_diagram_versions(db) -> None:
    """Restaura el historial embebido leyendo las últimas 20 versiones de cada diagrama."""
    print("[*] Iniciando ROLLBACK: reincrustando versiones en documentos de diagramas...")
    cursor = db["diagram_versions"].aggregate([
        {"$group": {"_id": "$diagram_id", "count": {"$sum": 1}}}
    ])
    diagram_ids = [item["_id"] async for item in cursor]

    restored = 0
    for d_id in diagram_ids:
        versions_cursor = db["diagram_versions"].find({"diagram_id": d_id}).sort("version", -1).limit(20)
        versions_list = await versions_cursor.to_list(length=20)
        versions_list.reverse() # chronological order

        history_array = []
        for v in versions_list:
            history_array.append({
                "version": v["version"],
                "graph_data": v.get("graph_data", {}),
                "saved_by": v.get("saved_by"),
                "saved_at": v.get("saved_at", v.get("created_at")),
                "comment": v.get("comment"),
            })

        await db["diagrams"].update_one(
            {"_id": d_id},
            {"$set": {"history": history_array}}
        )
        restored += 1
        print(f"  [+] Diagrama {d_id}: restauradas {len(history_array)} versiones en 'history'.")

    print(f"[OK] Rollback completado para {restored} diagramas.")


async def verify_versions(db) -> bool:
    """Verifica que no queden documentos con history embebido y que las versiones existan en diagram_versions."""
    unmigrated = await db["diagrams"].count_documents({"history": {"$exists": True, "$ne": []}})
    total_versions = await db["diagram_versions"].count_documents({})

    print("\n--- ESTADO DE VERIFICACIÓN ---")
    print(f"Diagramas con historial embebido remanente: {unmigrated}")
    print(f"Total de registros en 'diagram_versions':   {total_versions}")

    if unmigrated == 0:
        print("[SUCCESS] Verificación exitosa: 0 documentos con historial embebido.")
        return True
    else:
        print(f"[WARN] Existen {unmigrated} documentos pendientes de migración.")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Migración de historial de diagramas a diagram_versions")
    parser.add_argument("--rollback", action="store_true", help="Revertir migración reincrustando history")
    parser.add_argument("--verify", action="store_true", help="Verificar estado de migración")
    args = parser.parse_args()

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    try:
        if args.rollback:
            await rollback_diagram_versions(db)
        elif args.verify:
            await verify_versions(db)
        else:
            await migrate_diagram_versions(db)
            await verify_versions(db)
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
