from persistence import work_unit
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import RoleRepository,Role,Session,engine

def show_role_main_menu():
    session=Session(bind=engine)
    role_Rep=RoleRepository(session)
    
    
    table=Table(caption="Main Menu Role")

    table.add_column("Option")
    table.add_column("Role Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        role=Role()
        option=Prompt.ask("Choose an option")
        if option=="1":
            name=Prompt.ask("[bold green]Name: ")
            description=Prompt.ask("[bold green]Description of the Role:[bold green] ")
            role.name=name
            role.description=description
            role_Rep.save(role)
        elif option=="2":
            id=Prompt.ask("[bold red]ID role:[bold red] ")
            role_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID role:[bold yellow] ")
            roleobj=role_Rep.get(id)
            ask=Prompt.ask("What attribute? (name, description): ")
            if ask.lower()=="name":
                aname=Prompt.ask("[bold yellow]New Name:[bold yellow] ")
                roleobj.name=aname
            elif ask.lower()=="description":
                adesc=Prompt.ask("[bold yellow]New Description:[bold yellow] ")
                roleobj.description=adesc
            else:
                print("Incorrect Input")
            role_Rep.update(roleobj)
        elif option=="4":
            result=role_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")      
        else:
            session.commit()
            return
        
        