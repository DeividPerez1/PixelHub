from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from network_client import send_request
from view.helpers import display_response


console = Console()


def show_role_main_menu():
    table = Table(caption="Main Menu Role")
    table.add_column("Option")
    table.add_column("Role Menu")
    table.add_row("1", "Add")
    table.add_row("2", "Delete")
    table.add_row("3", "Update")
    table.add_row("4", "Show all")
    table.add_row("5", "Get by ID")
    table.add_row("0", "Exit")
    console.print(table)

    while True:
        option = Prompt.ask("Choose an option")
        if option == "1":
            data = {
                "name": Prompt.ask("Name"),
                "description": Prompt.ask("Description"),
            }
            display_response(send_request("add_role", data))
        elif option == "2":
            display_response(send_request("delete_role", {"id": Prompt.ask("Role ID")}))
        elif option == "3":
            role_id = Prompt.ask("Role ID")
            attribute = Prompt.ask("Attribute to update", choices=["name", "description"])
            display_response(
                send_request(
                    "update_role",
                    {
                        "id": role_id,
                        "attribute": attribute,
                        "new_value": Prompt.ask(f"New {attribute}"),
                    },
                )
            )
        elif option == "4":
            display_response(send_request("get_all_roles"))
        elif option == "5":
            display_response(send_request("get_role", {"id": Prompt.ask("Role ID")}))
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
