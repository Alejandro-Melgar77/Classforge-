import asyncio
from datetime import datetime
from bson import ObjectId
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.security import get_password_hash

async def seed():
    await connect_to_mongo()
    db = get_db()
    users_coll = db["users"]
    teams_coll = db["teams"]

    password_hash = get_password_hash("1234")
    now = datetime.utcnow()

    # 1. Definición de usuarios requeridos
    accounts_to_create = [
        {"name": "Admin", "email": "admin@classforge.com", "role": "admin"},
        {"name": "Alejandro", "email": "alejandro@classforge.com", "role": "scrum_master"},
        {"name": "Fernando", "email": "fernando@classforge.com", "role": "dev"},
        {"name": "Nicol", "email": "nicol@classforge.com", "role": "dev"},
        {"name": "Nathaly", "email": "nathaly@classforge.com", "role": "dev"},
        {"name": "Michael", "email": "michael@classforge.com", "role": "dev"},
    ]

    user_ids = {}

    print("=== 1. CREANDO O ACTUALIZANDO USUARIOS ===")
    for acc in accounts_to_create:
        existing = await users_coll.find_one({"email": acc["email"]})
        if existing:
            await users_coll.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "name": acc["name"],
                    "role": acc["role"],
                    "password_hash": password_hash,
                    "is_active": True,
                    "is_deleted": False,
                    "updated_at": now
                }}
            )
            user_ids[acc["email"]] = existing["_id"]
            print(f"[OK] Usuario actualizado: {acc['name']} ({acc['email']}) [Rol: {acc['role']}]")
        else:
            doc = {
                "name": acc["name"],
                "email": acc["email"],
                "password_hash": password_hash,
                "role": acc["role"],
                "avatar_url": None,
                "team_ids": [],
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "is_deleted": False,
                "deleted_at": None,
                "last_activity": now
            }
            res = await users_coll.insert_one(doc)
            user_ids[acc["email"]] = res.inserted_id
            print(f"[OK] Usuario creado: {acc['name']} ({acc['email']}) [Rol: {acc['role']}]")

    # 2. Creación del Equipo
    print("\n=== 2. CONFIGURANDO EQUIPO DE TRABAJO ===")
    sm_id = user_ids["alejandro@classforge.com"]
    admin_id = user_ids["admin@classforge.com"]
    dev_ids = [
        user_ids["fernando@classforge.com"],
        user_ids["nicol@classforge.com"],
        user_ids["nathaly@classforge.com"],
        user_ids["michael@classforge.com"]
    ]
    all_members = [sm_id] + dev_ids

    team_name = "Equipo Alejandro"
    existing_team = await teams_coll.find_one({"name": team_name, "is_deleted": False})

    if existing_team:
        team_id = existing_team["_id"]
        await teams_coll.update_one(
            {"_id": team_id},
            {"$set": {
                "scrum_master_id": sm_id,
                "member_ids": all_members,
                "description": "Equipo de desarrollo liderado por Alejandro",
                "updated_at": now
            }}
        )
        print(f"[OK] Equipo actualizado: '{team_name}' con {len(all_members)} miembros.")
    else:
        team_doc = {
            "name": team_name,
            "description": "Equipo de desarrollo liderado por Alejandro",
            "scrum_master_id": sm_id,
            "member_ids": all_members,
            "avatar_color": "#2563eb",
            "is_active": True,
            "is_deleted": False,
            "deleted_at": None,
            "created_by": admin_id,
            "created_at": now,
            "updated_at": now
        }
        res = await teams_coll.insert_one(team_doc)
        team_id = res.inserted_id
        print(f"[OK] Equipo creado: '{team_name}' con ID {team_id}")

    # 3. Vincular team_id a los miembros
    await users_coll.update_many(
        {"_id": {"$in": all_members}},
        {"$addToSet": {"team_ids": str(team_id)}}
    )
    print("[OK] Miembros vinculados al equipo correctamente.")

    print("\n=== RESUMEN DE CUENTAS CREADAS ===")
    print("Contraseña para todas las cuentas: 1234\n")
    for acc in accounts_to_create:
        print(f"- {acc['name']}: {acc['email']} | Rol: {acc['role']}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed())
