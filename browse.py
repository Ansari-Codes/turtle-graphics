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
        ''', f'%{query}%', limit)
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
    if query:
        projects = await search_projects(query)
        container.clear()
        if projects:
            for proj in projects:
                with container:
                    with ui.card():
                        ui.label(proj['title'])
        else:
            with container:
                ui.label('🔍 No results matched your search.')
    else:
        projects = await return_placeholder()
        container.clear()
        for proj in projects:
            with container:
                with ui.card():
                    ui.label(proj['title'])

async def create_browse(theme, btn, props):
    ui.colors(**theme)
    with ui.column()\
        .classes('w-full h-[95vh] items-'+\
        'center justify-center') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.html('Loading <span class="text-primary bold">Browser</span>...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    await ui.context.client.connected(100)
    ee.delete()
    with ui.page_sticky('top').classes('w-full bg-primary px-4 py-3 items-center z-50'):
        ui.label('/Browse')\
            .classes('text-2xl font-bold text-white')
    with ui.column().classes('items-center w-full mt-16'):
        with ui.row().classes(
            'search-bar-container items-center gap-2 px-4 py-2 rounded-full bg-white dark:bg-gray-800 flex-grow'
        ).style('border: 1px solid #ccc;').classes(
            'w-[full] sm: w-[60%]'
        ):
            query_input = ui.input(placeholder='Search...')\
                .props('borderless dense input-style="color:black"')\
                .classes('flex-grow text-black')\
                .style('background: transparent; outline: none; min-width: 0;')
            query_input.on('change', lambda _: update_content(query_input.value, result_row))
            ui.button(icon='arrow_forward')\
                .props('flat round dense')\
                .classes('bg-primary text-white')\
                .on('click', lambda: update_content(query_input.value, result_row))
        result_row = ui.row().classes('w-full flex-wrap justify-center mt-4')
        await update_content('', result_row)
