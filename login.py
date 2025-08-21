from nicegui import ui, app
from db import get_db_conn
from contextlib import asynccontextmanager
import bcrypt
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def disable(button: ui.button):
    button.set_enabled(False)
    await asyncio.sleep(0.05)
    try:
        yield
    finally:
        button.set_enabled(True)

async def get_username_from_credentials(identifier: str, password: str) -> str | None:
    conn = await get_db_conn()
    query = """
        SELECT username, pswd
        FROM accounts
        WHERE username = $1 OR mail = $1
        LIMIT 1
    """
    row = await conn.fetchrow(query, identifier)
    if row:
        hashed = row['pswd'].encode('utf-8')  # stored hashed password
        if bcrypt.checkpw(password.encode('utf-8'), hashed):
            return row['username']
    return None

def create_login(theme, btn, props, propsinp, style_inp):
    ui.colors(**theme)
    dark = app.storage.user.get('theme_dark')
    ui.dark_mode(dark)
    with ui.column().classes('w-full h-[95vh] items-center'):
        ui.element('div').style('height: 1vh')
        ui.image('data/banner.png').classes('w-[300px]').style('user-select: none;')
        with ui.card().classes('w-full lg:w-[440px] rounded-xl shadow p-4'):
            ui.label("Welcome Back 👋").classes('text-2xl font-bold')
            ui.label("Please Login to your account").classes('text-gray-500 mb-4')
            username_or_mail = ui.input('Username/Email').props(propsinp).classes('w-full').classes(style_inp)
            password = ui.input('Password', password=True, password_toggle_button=True).props(propsinp).classes('w-full').classes(style_inp)
            login_btn = ui.button('Login').props(props).style(btn).classes('w-full mt-4')
            async def _(e):
                async with disable(login_btn):
                    user = username_or_mail.value.strip()
                    pswd = password.value
                    if not user or not pswd:
                        ui.notify('Please enter both fields ❗', type='negative')
                        return
                    name = await get_username_from_credentials(user, pswd)
                    if name:
                        ui.notify('Welcome back!', type='positive')
                        app.storage.user.update({
                            'auth': True,
                            'username': name,
                        })
                        ui.navigate.to(f'/{name}/dashboard')
                    else:
                        ui.notify('Invalid username/email or password.', type='negative')
            login_btn.on_click(_)
            with ui.row().classes('justify-between w-full mt-2'):
                ui.link('Forgot Password?', '/forgot-password').classes('text-sm text-blue-600 underline')

