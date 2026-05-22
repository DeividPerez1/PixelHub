
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import CategoryRepository,Category,Session,engine


def show_category_main_menu():
    session=Session(bind=engine)
    cat_Rep=CategoryRepository(session)
    
    
    table=Table(caption="Main Menu Category")

    table.add_column("Option")
    table.add_column("Category Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("5","Get by id")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        cat=Category()
        option=Prompt.ask("Choose an option")
        if option=="1":
            name=Prompt.ask("[bold green]Name: ")
            cat.name=name
            cat_Rep.save(cat)
        elif option=="2":
            id=Prompt.ask("[bold red]ID Post:[bold red] ")
            cat_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID Post:[bold yellow] ")
            catobj=cat_Rep.get(id)
            ask=Prompt.ask("[bold yellow]New Name:[bold yellow] ")
            catobj.name=ask
            cat_Rep.update(catobj)
        elif option=="4":
            result=cat_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")
        elif option=="5":
            id=Prompt.ask("[bold yellow]ID:[bold yellow] ")
            result=cat_Rep.get(id)
            console.print(result)
        else:
            return
        session.commit()
        
        