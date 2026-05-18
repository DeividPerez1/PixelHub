
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import ProfileRepository,Profile,Session,engine


def show_profile_main_menu():
    session=Session(bind=engine)
    profile_Rep=ProfileRepository(session)
    
    
    table=Table(caption="Main Menu Profile")

    table.add_column("Option")
    table.add_column("Profile Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        profile=Profile()
        option=Prompt.ask("Choose an option")
        if option=="1":
            id_user=Prompt.ask("[bold green]ID User: ")
            first_name=Prompt.ask("[bold green]First Name:[bold green] ")
            last_name=Prompt.ask("[bold green]Last Name:[bold green] ")
            bio=Prompt.ask("[bold green]Biography:[bold green] ")
            phone=Prompt.ask("[bold green]Phone Number:[bold green] ")
            loc=Prompt.ask("[bold green]Location:[bold green] ")
            birth=Prompt.ask("[bold green]Birth Date:[bold green] ")
            profile.user_id=id_user
            profile.first_name=first_name
            profile.last_name=last_name
            profile.bio=bio
            profile.phone_number=phone
            profile.location=loc
            profile.birth_date=birth
            profile_Rep.save(profile)
        elif option=="2":
            id=Prompt.ask("[bold red]ID profile:[bold red] ")
            profile_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID profile:[bold yellow] ")
            profileobj=profile_Rep.get(id)
            ask=Prompt.ask("What attribute? (user id, first name, last name, bio, phone, location, birth date): ")
            if ask.lower()== "user id":
                user=Prompt.ask("[bold yellow]New ID:[bold yellow] ")
                profileobj.user_id=user
            elif ask.lower()=="first name":
                name=Prompt.ask("[bold yellow]New First Name:[bold yellow] ")
                profileobj.first_name=name
            elif ask.lower()=="last name":
                last=Prompt.ask("[bold yellow]New Last Name:[bold yellow] ")
                profileobj.last_name=last
            elif ask.lower() == "bio":
                abio=Prompt.ask("[bold yellow]New Bio:[bold yellow] ")
                profileobj.bio=abio
            elif ask.lower()=="phone":
                aphone=Prompt.ask("[bold yellow]New Phone:[bold yellow] ")
                profileobj.phone_number=aphone
            elif ask.lower()=="location":
                aloc=Prompt.ask("[bold yellow]New Location:[bold yellow] ")
                profileobj.location=aloc
            elif ask.lower()=="birth date":
                abirth=Prompt.ask("[bold yellow]New Birth Date:[bold yellow] ")
                profileobj.birth_date=abirth
            else:
                print("no correct input")
            profile_Rep.update          
        
        elif option=="4":
            result=profile_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")      
        else:
            session.commit()
            return
        
        