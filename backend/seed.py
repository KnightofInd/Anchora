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

DEFAULT_USERS_BY_ROLE = [
    {
        "email": "admin@anchora.dev",
        "full_name": "Anchora Admin",
        "password": "Admin@1234",
        "role": "admin",
    },
    {
        "email": "analyst@anchora.dev",
        "full_name": "Anchora Analyst",
        "password": "Analyst@1234",
        "role": "analyst",
    },
    {
        "email": "auditor@anchora.dev",
        "full_name": "Anchora Auditor",
        "password": "Auditor@1234",
        "role": "auditor",
    },
    {
        "email": "viewer@anchora.dev",
        "full_name": "Anchora Viewer",
        "password": "Viewer@1234",
        "role": "viewer",
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

        # ── Seed one default user per role ───────────────────────────────────
        for user_data in DEFAULT_USERS_BY_ROLE:
            existing_user = await db.execute(select(User).where(User.email == user_data["email"]))
            if not existing_user.scalar_one_or_none():
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    password_hash=hash_password(user_data["password"]),
                    role_id=role_map[user_data["role"]].id,
                )
                db.add(user)
                await db.flush()
                print(f"  [+] User created: {user_data['email']} / {user_data['password']}")
            else:
                print(f"  [=] User exists:  {user_data['email']}")

        await db.commit()

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
