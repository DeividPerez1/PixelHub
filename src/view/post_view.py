
from rich.table import Table
from rich.console import Console
console= Console()
from rich.prompt import Prompt
from domain import PostRepository,Post,Session,engine


def show_post_main_menu():
    session=Session(bind=engine)
    post_Rep=PostRepository(session)
    
    
    table=Table(caption="Main Menu Post")

    table.add_column("Option")
    table.add_column("Post Menu")
    table.add_row("1","add")
    table.add_row("2","Delete")
    table.add_row("3","update")
    table.add_row("4","Show Them")
    table.add_row("0","exit")
    console.print(table)
    
    while True:
        post=Post()
        option=Prompt.ask("Choose an option")
        if option=="1":
            id_category=Prompt.ask("[bold green]ID Category: ")
            user_id=Prompt.ask("[bold green]ID User:[bold green] ")
            title=Prompt.ask("[bold green]Title :[bold green] ")
            content=Prompt.ask("[bold green]Content:[bold green] ")
            post.user_id=user_id
            post.category_id=id_category
            post.title=title
            post.content=content
            post_Rep.save(post)
        elif option=="2":
            id=Prompt.ask("[bold red]ID Post:[bold red] ")
            post_Rep.delete(id)
        elif option=="3":
            id=Prompt.ask("[bold yellow]ID Post:[bold yellow] ")
            postobj=post_Rep.get(id)
            ask=Prompt.ask("What attribute? (category id, user id, title, content): ")
            if ask.lower()=="category id":
                acat=Prompt.ask("[bold yellow]New Category Id:[bold yellow] ")
                postobj.category_id=acat
            elif ask.lower()=="user id":
                auser=Prompt.ask("[bold yellow]New User Id:[bold yellow] ")
                postobj.user_id=auser
            elif ask.lower()=="title":
                atitle=Prompt.ask("[bold yellow]New Title:[bold yellow] ")
                postobj.title=atitle
            elif ask.lower()=="content":
                acontent=Prompt.ask("[bold yellow]New Content:[bold yellow] ")
                postobj.content=acontent
            else:
                print("Incorrect Input")
            post_Rep.update(postobj)

        elif option=="4":
            result=post_Rep.get_all()
            for i in result:
                console.print(f"\t{i}")      
        else:
            session.commit()
            return
        
        