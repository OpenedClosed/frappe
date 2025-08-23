"""
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from venv import logger

import asyncclick as aclick
from chats.db.mongo.schemas import ChatSession
import click
import logging 

from db.mongo.db_init import mongo_db
from chats.integrations.constructor_chat.handlers import push_to_constructor

# python -m chats.utils.cli_commands export-chats-to-constructor --company "Автошкола" --year 2025 --month 7

logger = logging.getLogger()

# ------------------------------------------------------------------------------
# Группа CLI
# ------------------------------------------------------------------------------

@aclick.group()
def cli():
    """Корневая группа CLI-команд чатов."""
    pass


@cli.command("export-chats-to-constructor")
@aclick.option(
    "--company",
    "-c",
    required=False,
    default=None,
    help="Название компании (поле ChatSession.company_name)",
)
@aclick.option(
    "--year",
    "-y",
    type=int,
    required=False,
    default=None,
    show_default=False,
    help="Год (если не задан, по времени не фильтруем)",
)
@aclick.option(
    "--month",
    "-m",
    type=aclick.IntRange(1, 12),
    required=False,
    default=None,
    show_default=False,
    help="Месяц (1–12). Работает только вместе с --year",
)
async def export_chats_to_constructor_cli(company: str | None, year: int | None, month: int | None):
    """
    Выгружает чаты в Constructor.chat.
    """
    query = {}

    if company:
        query["company_name"] = company

    if year is not None:
        if month is not None:
            month_start = datetime(year, month, 1, tzinfo=timezone.utc)
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        else:
            month_start = datetime(year, 1, 1, tzinfo=timezone.utc)
            month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

        query["created_at"] = {"$gte": month_start, "$lt": month_end}

    cursor = mongo_db.chats.find(query)
    print(query)
    total, exported = 0, 0

    async for doc in cursor:
        total += 1
        try:
            session = ChatSession(**doc)
            await push_to_constructor(session, session.messages)  # type: ignore[arg-type]
            exported += 1
            click.echo(f"✔ Exported chat {session.chat_id}")
        except Exception as exc:
            logger.exception("❌ Failed to export chat %s: %s", doc.get("chat_id"), exc)

    click.echo(f"\nГотово. Успешно выгружено {exported}/{total} чатов.")


# ------------------------------------------------------------------------------
# Entry-point для asyncclick
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(cli())
