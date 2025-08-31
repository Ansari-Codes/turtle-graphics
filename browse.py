import asyncio
from nicegui import ui, app
from db import get_db_conn

async def search_projects(query: str, limit: int = 30) -> list[dict]:
    conn = await get_db_conn()
    try:
        result = await conn.fetch('''
            SELECT id, title, username, pivot_count
            FROM projects
            WHERE title ILIKE $1 AND status = 'published'
            ORDER BY pivot_count DESC
            LIMIT $2
        ''', query, limit)
        return [dict(row) for row in result]
    finally:
        await conn.close()

async def return_placeholder() -> list[dict]:
    conn = await get_db_conn()
    try:
        result = await conn.fetch('''
            SELECT id, title, username, pivot_count
            FROM projects
            WHERE status = 'published'
            ORDER BY pivot_count DESC
            LIMIT 30
        ''')
        return [dict(row) for row in result]
    finally:
        await conn.close()

async def update_content(query: str, container):
    container.clear()
    with container:
        if query:
            projects = await search_projects(query)
            if projects:
                container.clear()
                for proj in projects:
                    ui.label(proj['title'])
            else:
                container.clear()
                ui.label('🔍 No results matched your search.')
        else:
            projects = await return_placeholder()
            container.clear()
            for proj in projects:
                ui.label(proj['title'])

async def create_browse(theme, btn, props):
    ui.colors(**theme)
    async def handle_search(e):
        await update_content(e.value, result_container)
    with ui.row().classes('w-full justify-center'):
        with ui.row().classes('w-full md:w-[40vw] items-center gap-2'):
            query_input = ui.input(
                placeholder='Search...',
                on_change=handle_search
            ).props('dense outlined').classes('flex-grow')
            ui.button(icon='search', on_click=lambda: handle_search(query_input))\
                .props(props)
    result_container = ui.column()
    await update_content('', result_container)
