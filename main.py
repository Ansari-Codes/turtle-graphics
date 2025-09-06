from nicegui import ui, app
from home import create_home as ch, header as h
from signup import create_signup as cs
from browse import create_browse as cb
from login import create_login as cl
from editor import create_new as cn
from dashboard import create_dashboard as cd
import asyncpg, asyncio

DB_CONFIG = {
    'user': 'postgres',
    'password': 'postgres@app',
    'database': 'users',
    'host': 'localhost',
    'port': 7864,
}

@app.on_startup
async def clear_db_on_start():
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            await conn.execute('TRUNCATE accounts, projects RESTART IDENTITY CASCADE')
            print("🧹 Database table cleared on startup.")
        finally:
            await conn.close()
    except Exception as e:
        print(f"❌ Database startup error: {e}")
theme = {
    "primary": "#2B9644",
    "secondary": "#aaffaa",
    "secondary_true": "#095700",
    "secondary_false": "#aaffaa",
    "secondary_none": "#aaffaa",
    "accent": "#73AB6D",
    "dark": "#022400",
    "dark_page": "#0b1200",
    "positive": "#0db534",
    "negative": "#ff001e",
    "info": "#8ab000",
    "warning": "#e3c100",
    "btn-bg":"#26642A"
}
style = f'''
        font-family: Arial;
        font-size: 15px;
        border-radius:20px;
    '''
props = 'push color=btn-bg'
propsinp = 'outlined dense'
classes_inp = 'w-full rounded text-sm'
classes = classes_inp + ' bg-transparent'
@ui.page('/')
async def create_home():
    print("Loading Home...")
    h(theme, style, props)
    await ch(theme, style, props)
    print("Loaded!")

@ui.page('/browse')
async def create_browse():
    print("Loading Home...")
    h(theme, style, props)
    print("Loaded heade!\nLoading Browse...")
    await cb(theme, style, props)
    print("Loaded!")

@ui.page('/{user}/dashboard/new/{proj_name}')
async def create_new(user: str, proj_name: str):
    print(f"Loading dashboard/{user}/new")
    await cn(theme, style, props, proj_name)
    print(f"Loaded dashboard/{user}/new")

@ui.page('/{user}/dashboard/')
async def create_dash(user: str):
    print(f"Loading dashboard/{user}")
    await cd(theme, style, props, user)
    print(f"Loading dashboard/{user}")

@ui.page('/signup')
def create_signup():
    print(f"Loading Signup...")
    cs(theme, style, props, propsinp, classes)
    print(f"Loaded Signup")

@ui.page('/login')
def create_login():
    print(f"Loading Login...")
    cl(theme, style, props, propsinp, '')
    print(f"Loaded Login")

secret = '123-asdf-2134-sadf-234-sadf-324-sadf-324-sdf-435-sfda-4'
import os
ui.run(
    storage_secret=secret,
    title='Turtle Graphics',
    reload=False,
    host='0.0.0.0',
    port=int(os.environ.get("PORT", 8080))
)
