import asyncio
from nicegui import ui, app
from db import get_db_conn

async def fetch_project(id):
    db = await get_db_conn()
    try:
        project = await db.fetch_row('''
                    SELECT * FROM projects
                    WHERE id=$1
                    LIMIT 1
                    ''', id)
        return dict(project)
    except Exception as e:
        return dict()

async def create_show(id, theme):
    ui.colors(**theme)
    if not app.storage.user.get('auth', False):
        ui.label(f'Un-authorized access!')
        ui.navigate.to('/login')
        return
    ui.dark_mode(app.storage.user.get('theme_dark', False))
    with ui.column().classes('w-full h-[95vh] items-center justify-center') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.html('Loading <span class="text-primary bold">Dashboard</span>...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    await ui.context.client.connected(100)
    project = await fetch_project(id)
    await asyncio.sleep(1)
    ee.delete()
    title = project.get('title', '')
    username = project.get('username', '')
    code = project.get('code_data', '')
    svg = project.get('svg_data', '')
    likes = project.get('likes', 0)
    pivots = project.get('pivot_count', 0)
    created_at = project.get('created_at', '')
    description = project.get('description','')






