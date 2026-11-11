from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from network_client import send_request_sync as send_request
from view.helpers import display_response


console = Console()
PROFILE_ATTRIBUTES = {
    "1": ("user_id", "User ID"),
    "2": ("first_name", "First name"),
    "3": ("last_name", "Last name"),
    "4": ("bio", "Biography"),
    "5": ("phone_number", "Phone number"),
    "6": ("location", "Location"),
    "7": ("birth_date", "Birth date (YYYY-MM-DD)"),
    "8": ("avatar_url", "Avatar URL"),
}


def show_profile_main_menu():
    table = Table(caption="Main Menu Profile")
    table.add_column("Option")
    table.add_column("Profile Menu")
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
                "user_id": Prompt.ask("User ID"),
                "first_name": Prompt.ask("First name"),
                "last_name": Prompt.ask("Last name"),
                "bio": Prompt.ask("Biography"),
                "phone_number": Prompt.ask("Phone number"),
                "location": Prompt.ask("Location"),
                "birth_date": Prompt.ask("Birth date (YYYY-MM-DD)"),
            }
            display_response(send_request("add_profile", data))
        elif option == "2":
            display_response(send_request("delete_profile", {"id": Prompt.ask("Profile ID")}))
        elif option == "3":
            profile_id = Prompt.ask("Profile ID")
            console.print("Profile field to update:")
            for key, (_, label) in PROFILE_ATTRIBUTES.items():
                console.print(f"{key}. {label}")
            selected = Prompt.ask("Choose a field", choices=list(PROFILE_ATTRIBUTES))
            attribute, label = PROFILE_ATTRIBUTES[selected]
            display_response(
                send_request(
                    "update_profile",
                    {
                        "id": profile_id,
                        "attribute": attribute,
                        "new_value": Prompt.ask(f"New {label}"),
                    },
                )
            )
        elif option == "4":
            display_response(send_request("get_all_profiles"))
        elif option == "5":
            display_response(send_request("get_profile", {"id": Prompt.ask("Profile ID")}))
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
