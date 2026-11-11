from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from network_client import send_request_sync as send_request
from view.helpers import display_response


console = Console()


def show_user_main_menu():
    table = Table(caption="Main Menu User")
    table.add_column("Option")
    table.add_column("User Menu")
    table.add_row("1", "Add")
    table.add_row("2", "Delete")
    table.add_row("3", "Update")
    table.add_row("4", "Show all")
    table.add_row("5", "Get by ID")
    table.add_row("6", "Get by username")
    table.add_row("7", "Get by email")
    table.add_row("0", "Exit")
    console.print(table)

    while True:
        option = Prompt.ask("Choose an option")
        if option == "1":
            data = {
                "username": Prompt.ask("Username"),
                "email": Prompt.ask("Email"),
                "password": Prompt.ask("Password", password=True),
                "role_id": Prompt.ask("Role ID"),
            }
            display_response(send_request("add_user", data))
        elif option == "2":
            display_response(send_request("delete_user", {"id": Prompt.ask("User ID")}))
        elif option == "3":
            user_id = Prompt.ask("User ID")
            attribute = Prompt.ask(
                "Attribute to update",
                choices=["username", "email", "password", "role_id"],
            )
            display_response(
                send_request(
                    "update_user",
                    {
                        "id": user_id,
                        "attribute": attribute,
                        "new_value": Prompt.ask(f"New {attribute}"),
                    },
                )
            )
        elif option == "4":
            display_response(send_request("get_all_users"))
        elif option == "5":
            display_response(send_request("get_user", {"id": Prompt.ask("User ID")}))
        elif option == "6":
            display_response(
                send_request(
                    "get_user_by_username",
                    {"username": Prompt.ask("Username")},
                )
            )
        elif option == "7":
            display_response(
                send_request("get_user_by_email", {"email": Prompt.ask("Email")})
            )
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
