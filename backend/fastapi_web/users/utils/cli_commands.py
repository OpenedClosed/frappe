"""Быстраые команды приложения."""
import asyncclick as aclick
import click

from db.mongo.db_init import mongo_db
from users.db.mongo.schemas import User


@aclick.group()
def cli():
    pass


@cli.command("create-admin")
async def create_admin_cli():
    """
    Создаёт суперпользователя (админа).
    Данные запрашиваются интерактивно через консоль.
    """
    username = click.prompt("Enter username", type=str)
    password = click.prompt(
        "Enter password",
        type=str,
        hide_input=True,
        confirmation_prompt=True)
    is_superuser = click.confirm("Is superuser?", default=False)

    existing = await mongo_db["users"].find_one({"username": username})
    if existing:
        click.echo(f"User '{username}' already exists.")
        return

    user = User(
        username=username,
        password=password,
        is_superuser=is_superuser,
    )
    user.set_password()
    await mongo_db["users"].insert_one(user.model_dump())
    click.echo(f"Admin user was successfully created!")

if __name__ == "__main__":
    cli()
