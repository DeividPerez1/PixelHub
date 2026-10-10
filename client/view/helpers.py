from rich.console import Console
from rich.table import Table


console = Console()


def display_response(response):
    message = response.get("message", "The server returned no message.")
    if response.get("status") != "ok":
        console.print(f"[bold red]{message}[/bold red]")
        return

    console.print(f"[bold cyan]{message}[/bold cyan]")
    data = response.get("data")
    if isinstance(data, list):
        if not data:
            console.print("No records found.")
            return
        table = Table()
        for key in data[0]:
            table.add_column(key)
        for item in data:
            table.add_row(*(str(item.get(key, "")) for key in data[0]))
        console.print(table)
    elif data is not None:
        console.print(data)
