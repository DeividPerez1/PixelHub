from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from network_client import send_request
from view.helpers import display_response


console = Console()


def show_tag_main_menu():
    table = Table(caption="Main Menu Tag")
    table.add_column("Option")
    table.add_column("Tag Menu")
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
            display_response(send_request("add_tag", {"name": Prompt.ask("Tag name")}))
        elif option == "2":
            display_response(send_request("delete_tag", {"id": Prompt.ask("Tag ID")}))
        elif option == "3":
            tag_id = Prompt.ask("Tag ID")
            display_response(
                send_request(
                    "update_tag",
                    {
                        "id": tag_id,
                        "attribute": "name",
                        "new_value": Prompt.ask("New tag name"),
                    },
                )
            )
        elif option == "4":
            display_response(send_request("get_all_tags"))
        elif option == "5":
            display_response(send_request("get_tag", {"id": Prompt.ask("Tag ID")}))
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
