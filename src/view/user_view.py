from persistence import work_unit
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import UserRepository,User,Session,engine

def show_user_main_menu():
    session=Session(bind=engine)
    user_Rep=UserRepository(session)
    
    
    table=Table(caption="Main Menu user")

    table.add_column("Option")
    table.add_column("user Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("5","Get")
    table.add_row("6","Get by Username")
    table.add_row("7","Get by Email")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        user=User()
        option=Prompt.ask("Choose an option")
        if option=="1":
            name=Prompt.ask("[bold green]User Name: ")
            email=Prompt.ask("[bold green]Email of the user:[bold green] ")
            password=Prompt.ask("[bold yellow]Password of the user:[bold yellow] ")
            role=Prompt.ask("[bold yellow]What Role put id:[bold yellow] ")
            user.username=name
            user.email=email
            user.password=password
            user.role_id=role
            user_Rep.save(user)
        elif option=="2":
            id=Prompt.ask("[bold red]ID user:[bold red] ")
            user_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID user:[bold yellow] ")
            userobj=user_Rep.get(id)
            ask=Prompt.ask("What attribute? (name, email, password, role,): ")
            if ask.lower()=="name":
                aname=Prompt.ask("[bold yellow]New Name:[bold yellow] ")
                userobj.username=aname
            elif ask.lower()=="email":
                aemail=Prompt.ask("[bold yellow]New Email:[bold yellow] ")
                userobj.email=aemail
            elif ask.lower()=="password":
                apass=Prompt.ask("[bold yellow]New Password:[bold yellow] ")
                userobj.password=apass
            elif ask.lower()=="role":
                arole=Prompt.ask("[bold yellow]New Role:[bold yellow] ")
                userobj.role_id=arole
            else:
                print("Incorrect Input")
            user_Rep.update(userobj)
        elif option=="4":
            result=user_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")
        elif option=="5":
            id=Prompt.ask("[bold yellow]ID:[bold yellow] ")
            result=user_Rep.get(id)
            console.print(result)
        elif option=="6":
            name=Prompt.ask("[bold yellow]Username:[bold yellow] ")
            resul=user_Rep.get_by_username(name)
            console.print(result)
        elif option=="7":
            email=Prompt.ask("[bold yellow]Email:[bold yellow] ")
            result=user_Rep.get_by_email(email)
            console.print(result)
        
        else:
            return
        session.commit()