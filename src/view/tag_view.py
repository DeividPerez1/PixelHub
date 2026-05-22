
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import TagRepository,Tag,Session,engine


def show_tag_main_menu():
    session=Session(bind=engine)
    tag_Rep=TagRepository(session)
    
    
    table=Table(caption="Main Menu Tag")

    table.add_column("Option")
    table.add_column("Tag Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("5","Get")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        tag=Tag()
        option=Prompt.ask("Choose an option")
        if option=="1":
            name=Prompt.ask("[bold green]Name:[bold green] ")
            tag.name=name
            tag_Rep.save(tag)
        elif option=="2":
            id=Prompt.ask("[bold red]ID Tag:[bold red] ")
            tag_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID Tag:[bold yellow] ")
            tagobj=tag_Rep.get(id)
            ask=Prompt.ask("[bold cyan]New name:[bold cyan] ")
            tagobj.name=ask
            tag_Rep.update(tag)
        elif option=="4":
            result=tag_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")  
        elif option=="5":
            id=Prompt.ask("[bold yellow]ID:[bold yellow] ")
            result=tag_Rep.get(id)
            console.print(result)    
        else:
            return
        session.commit()
        
        
        