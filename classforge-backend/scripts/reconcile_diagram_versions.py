# -*- coding: utf-8 -*-
"""
Script opcional de reconciliación de versiones históricas (C7).

Antes de la corrección C7, el backend guardaba el snapshot con el grafo previo
(versión N) y luego incrementaba la versión del diagrama a N+1.
Este script opcional permite alinear diagramas existentes asegurando que
cada diagrama tenga un snapshot de su estado actual con su versión actual (diagram.version)
en la colección 'diagram_versions'.

Uso:
    python scripts/reconcile_diagram_versions.py [--apply] [--dry-run]
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Añadir ruta para importar configuración
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import settings


async def reconcile_versions(apply: bool = False):
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print(f"[*] Conectado a MongoDB: {settings.DATABASE_NAME}")
    cursor = db["diagrams"].find({"is_deleted": False})
    diagrams = await cursor.to_list(length=None)

    reconciled = 0
    already_synced = 0

    for diagram in diagrams:
        diagram_id = diagram["_id"]
        current_version = diagram.get("version", 1)
        current_graph = diagram.get("graph_data", {"nodes": [], "edges": []})

        # Buscar si existe un snapshot para la versión actual
        snapshot = await db["diagram_versions"].find_one({
            "diagram_id": diagram_id,
            "version": current_version,
        })

        if snapshot is None:
            reconciled += 1
            print(f"[!] Diagrama {diagram_id} ('{diagram.get('name')}') versión {current_version} no tiene snapshot actual.")
            if apply:
                await db["diagram_versions"].insert_one({
                    "diagram_id": diagram_id,
                    "version": current_version,
                    "graph_data": current_graph,
                    "saved_by": diagram.get("created_by"),
                    "comment": "Reconciliación de snapshot de estado actual (C7)",
                    "created_at": diagram.get("updated_at") or datetime.now(timezone.utc),
                })
                print(f"    -> Creado snapshot para versión {current_version}.")
        else:
            already_synced += 1

    mode = "APLICADO" if apply else "SIMULACIÓN (dry-run)"
    print(f"\n[*] Modo: {mode}")
    print(f"[*] Total diagramas analizados: {len(diagrams)}")
    print(f"[*] Diagramas que requerían reconciliación: {reconciled}")
    print(f"[*] Diagramas ya sincronizados: {already_synced}")

    client.close()


def main():
    parser = argparse.ArgumentParser(description="Reconciliación opcional de versiones de diagramas (C7)")
    parser.add_argument("--apply", action="store_true", help="Aplica los cambios en la base de datos")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Solo muestra qué se modificaría")
    args = parser.parse_args()

    apply = args.apply
    asyncio.run(reconcile_versions(apply=apply))


if __name__ == "__main__":
    main()
