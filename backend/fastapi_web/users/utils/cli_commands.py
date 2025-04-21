"""Быстраые команды приложения."""
import asyncclick as aclick
import click
from db.mongo.db_init import mongo_db
from users.db.mongo.enums import RoleEnum
from users.db.mongo.schemas import User


@aclick.group()
def cli():
    pass


@cli.command("create-admin")
async def create_admin_cli():
    """
    Создаёт суперадмина.
    Данные запрашиваются интерактивно через консоль.
    """
    username = click.prompt("Enter username", type=str)
    password = click.prompt(
        "Enter password",
        type=str,
        hide_input=True,
        confirmation_prompt=True
    )

    existing = await mongo_db["users"].find_one({"username": username})
    if existing:
        click.echo(f"User '{username}' already exists.")
        return

    user = User(
        username=username,
        password=password,
        role=RoleEnum.SUPERADMIN
    )
    user.set_password()
    await mongo_db["users"].insert_one(user.model_dump(mode="python"))
    click.echo("Superadmin user was successfully created!")

if __name__ == "__main__":
    cli()
