import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_db
from app.core.security import get_password_hash
from app.modules.users.repository import UserRepository

async def seed():
    await connect_to_mongo()
    db = get_db()
    repo = UserRepository(db)

    # Admin user
    admin = await repo.get_by_email("admin@classforge.com")
    if not admin:
        admin_id = await repo.create({
            "email": "admin@classforge.com",
            "password_hash": get_password_hash("Admin123!"),
            "name": "Administrador",
            "role": "admin",
            "avatar_url": None,
            "team_ids": []
        })
        print(f"Usuario Admin creado: admin@classforge.com (ID: {admin_id})")
    else:
        print("Usuario Admin ya existe.")

    # Dev user
    dev = await repo.get_by_email("dev@classforge.com")
    if not dev:
        dev_id = await repo.create({
            "email": "dev@classforge.com",
            "password_hash": get_password_hash("Dev123!"),
            "name": "Desarrollador",
            "role": "dev",
            "avatar_url": None,
            "team_ids": []
        })
        print(f"Usuario Dev creado: dev@classforge.com (ID: {dev_id})")
    else:
        print("Usuario Dev ya existe.")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed())
