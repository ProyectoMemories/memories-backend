"""La migración 0001 sube, baja y vuelve a subir sin dejar restos."""

import psycopg
from alembic import command
from alembic.config import Config

TABLES = {
    "app_user", "privacy_consent", "user_session",
    "album", "album_member", "album_invitation", "tag", "album_tag",
    "photo", "description",
    "memory", "memory_item", "memory_page",
    "memory_access", "memory_invitation", "memory_link",
}  # fmt: skip
ENUMS = {
    "account_status", "member_role", "base_category", "memory_output",
    "memory_status", "memory_item_kind", "client_platform",
}  # fmt: skip


def _schema(url: str) -> tuple[set[str], set[str], set[str]]:
    with psycopg.connect(url) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            )
        } - {"alembic_version"}
        enums = {
            row[0]
            for row in conn.execute(
                "SELECT t.typname FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'public' AND t.typtype = 'e'"
            )
        }
        functions = {
            row[0]
            for row in conn.execute(
                "SELECT p.proname FROM pg_proc p "
                "JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'public'"
            )
        }
    return tables, enums, functions


def test_upgrade_downgrade_upgrade(migrated_db: str, alembic_config: Config) -> None:
    assert _schema(migrated_db) == (TABLES, ENUMS, {"set_updated_at"})

    command.downgrade(alembic_config, "base")
    assert _schema(migrated_db) == (set(), set(), set())

    command.upgrade(alembic_config, "head")
    assert _schema(migrated_db) == (TABLES, ENUMS, {"set_updated_at"})
