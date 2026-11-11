from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from network_client import send_request_sync as send_request
from view.helpers import display_response


console = Console()
POST_ATTRIBUTES = {
    "1": ("category_id", "Category ID"),
    "2": ("user_id", "User ID"),
    "3": ("title", "Title"),
    "4": ("content", "Content"),
    "5": ("img", "Image URL"),
}


def show_post_main_menu():
    table = Table(caption="Main Menu Post")
    table.add_column("Option")
    table.add_column("Post Menu")
    table.add_row("1", "Add")
    table.add_row("2", "Delete")
    table.add_row("3", "Update")
    table.add_row("4", "Show all")
    table.add_row("5", "Get by ID")
    table.add_row("6", "Get by category")
    table.add_row("7", "Get by user")
    table.add_row("8", "Get latest")
    table.add_row("0", "Exit")
    console.print(table)

    while True:
        option = Prompt.ask("Choose an option")
        if option == "1":
            data = {
                "category_id": Prompt.ask("Category ID"),
                "user_id": Prompt.ask("User ID"),
                "title": Prompt.ask("Title"),
                "content": Prompt.ask("Content"),
                "img": Prompt.ask("Image URL (leave blank if none)", default=""),
            }
            display_response(send_request("add_post", data))
        elif option == "2":
            display_response(send_request("delete_post", {"id": Prompt.ask("Post ID")}))
        elif option == "3":
            post_id = Prompt.ask("Post ID")
            console.print("Post field to update:")
            for key, (_, label) in POST_ATTRIBUTES.items():
                console.print(f"{key}. {label}")
            selected = Prompt.ask("Choose a field", choices=list(POST_ATTRIBUTES))
            attribute, label = POST_ATTRIBUTES[selected]
            display_response(
                send_request(
                    "update_post",
                    {
                        "id": post_id,
                        "attribute": attribute,
                        "new_value": Prompt.ask(f"New {label}"),
                    },
                )
            )
        elif option == "4":
            display_response(send_request("get_all_posts"))
        elif option == "5":
            display_response(send_request("get_post", {"id": Prompt.ask("Post ID")}))
        elif option == "6":
            display_response(
                send_request(
                    "get_posts_by_category",
                    {"category_id": Prompt.ask("Category ID")},
                )
            )
        elif option == "7":
            display_response(send_request("get_posts_by_user", {"user_id": Prompt.ask("User ID")}))
        elif option == "8":
            display_response(send_request("get_last_posts"))
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
