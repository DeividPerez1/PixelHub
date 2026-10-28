from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from view.user_view import show_user_main_menu
from view.role_view import show_role_main_menu
from view.profile_view import show_profile_main_menu
from view.post_view import show_post_main_menu
from view.category_view import show_category_main_menu
from view.tag_view import show_tag_main_menu

console = Console()

def show_logo():
    path = Path("Logo.txt")
    if path.exists():
        print(path.read_text())
    else:
        console.print("[bold cyan] PixelHub back-office")

def run_back_office():
    show_logo()
    while True:
        option = select_menu()
        if option == "1":
            show_user_main_menu()
        elif option == "2":
            show_role_main_menu()
        elif option == "3":
            show_profile_main_menu()
        elif option == "4":
            show_post_main_menu()
        elif option == "5":
            show_category_main_menu()
        elif option == "6":
            show_tag_main_menu()
        elif option == "0":
            return
        else:
            console.print("[bold red]Invalid option.[/bold red]")
            
def select_menu():
    table = Table(caption="Main Menu")
    table.add_column("Option")
    table.add_column("Menu")
    table.add_row("1", "User")
    table.add_row("2", "Role")
    table.add_row("3", "Profile")
    table.add_row("4", "Post")
    table.add_row("5", "Category")
    table.add_row("6", "Tag")
    table.add_row("0", "exit")
    console.print(table)

    return Prompt.ask("choose an option")

if __name__ == "__main__":
    run_back_office()