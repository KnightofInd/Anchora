"""
Anchora – Seed Script
Inserts default roles and an admin user into the database.
Run once after migration: python seed.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.config.settings import settings
from app.models.role import Role
from app.models.user import User
from app.models.policy import Policy
from app.core.security import hash_password

RULES_PATH = os.path.join(os.path.dirname(__file__), "app", "rules", "default_rules.json")


engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"ssl": "require"},
)
Session = async_sessionmaker(bind=engine, expire_on_commit=False)


DEFAULT_ROLES = [
    {
        "name": "admin",
        "permissions": {
            "decisions": ["create", "read", "update", "delete"],
            "workflows": ["create", "read", "update"],
            "documents": ["create", "read", "delete"],
            "audit":     ["read"],
            "policies":  ["create", "read", "update", "delete"],
            "users":     ["create", "read", "update", "delete"],
        },
    },
    {
        "name": "analyst",
        "permissions": {
            "decisions": ["create", "read"],
            "workflows": ["read"],
            "documents": ["create", "read"],
            "audit":     [],
            "policies":  ["read"],
            "users":     [],
        },
    },
    {
        "name": "auditor",
        "permissions": {
            "decisions": ["read"],
            "workflows": ["read"],
            "documents": ["read"],
            "audit":     ["read"],
            "policies":  ["read"],
            "users":     [],
        },
    },
    {
        "name": "viewer",
        "permissions": {
            "decisions": ["read"],
            "workflows": ["read"],
            "documents": ["read"],
            "audit":     [],
            "policies":  [],
            "users":     [],
        },
    },
]


async def seed():
    async with Session() as db:
        # ── Seed roles ──────────────────────────────────────────────────────
        role_map = {}
        for role_data in DEFAULT_ROLES:
            existing = await db.execute(select(Role).where(Role.name == role_data["name"]))
            role = existing.scalar_one_or_none()
            if not role:
                role = Role(name=role_data["name"], permissions=role_data["permissions"])
                db.add(role)
                await db.flush()
                print(f"  [+] Role created: {role_data['name']}")
            else:
                print(f"  [=] Role exists:  {role_data['name']}")
            role_map[role_data["name"]] = role

        await db.commit()

        # Re-fetch after commit
        for role_data in DEFAULT_ROLES:
            result = await db.execute(select(Role).where(Role.name == role_data["name"]))
            role_map[role_data["name"]] = result.scalar_one()

        # ── Seed admin user ──────────────────────────────────────────────────
        admin_email = "admin@anchora.dev"
        existing_user = await db.execute(select(User).where(User.email == admin_email))
        if not existing_user.scalar_one_or_none():
            admin = User(
                email=admin_email,
                full_name="Anchora Admin",
                password_hash=hash_password("Admin@1234"),
                role_id=role_map["admin"].id,
            )
            db.add(admin)
            await db.commit()
            print(f"  [+] Admin user created: {admin_email} / Admin@1234")
        else:
            print(f"  [=] Admin user exists: {admin_email}")

        # ── Seed policies from default_rules.json ───────────────────────────
        with open(RULES_PATH, "r") as f:
            rules = json.load(f)

        for rule in rules:
            existing_policy = await db.execute(select(Policy).where(Policy.name == rule["name"]))
            if not existing_policy.scalar_one_or_none():
                policy = Policy(
                    name=rule["name"],
                    description=rule.get("description", ""),
                    rule_definition=rule["rule_definition"],
                    is_active=True,
                )
                db.add(policy)
                print(f"  [+] Policy created: {rule['name']}")
            else:
                print(f"  [=] Policy exists:  {rule['name']}")

        await db.commit()
        print("\nSeed complete.")

    await engine.dispose()


if __name__ == "__main__":
    print("Seeding Anchora database...")
    asyncio.run(seed())
