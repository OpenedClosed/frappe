"""
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List

import asyncclick as aclick
from backend.fastapi_web.chats.db.mongo.schemas import ChatSession
import click
from loguru import logger

from db.mongo.db_init import mongo_db
from chats.integrations.constructor_chat.handlers import push_to_constructor

# python -m chats.utils.cli_commands export-chats-to-constructor --company "Автошкола" --year 2025 --month 7



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
    required=True,
    help="Название компании (поле ChatSession.company_name)",
)
@aclick.option(
    "--year",
    "-y",
    type=int,
    default=datetime.now().year,
    show_default=True,
    help="Год, за который выгружаем чаты",
)
@aclick.option(
    "--month",
    "-m",
    type=int,
    default=datetime.now().month,
    show_default=True,
    help="Месяц (1–12), за который выгружаем чаты",
)
async def export_chats_to_constructor_cli(company: str, year: int, month: int):
    """
    Выгружает ВСЕ чаты указанной компании за выбранный месяц в Constructor.chat.
    """
    # --- диапазон дат ---
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(
        day=1
    )  # первый день след. месяца

    query = {
        "company_name": company,
        "created_at": {"$gte": month_start, "$lt": month_end},
    }

    cursor = mongo_db["chats"].find(query)
    total, exported = 0, 0

    async for doc in cursor:
        total += 1
        try:
            session = ChatSession(**doc)

            # Push ВСЮ историю чата (универсальный энд-поинт создаст чат, если нужно)
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
