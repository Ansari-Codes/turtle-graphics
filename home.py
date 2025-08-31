import asyncio
from nicegui import ui, app
from db import get_db_conn

async def search_projects(query: str):
    conn = await get_db_conn()
    try:
        rows = await conn.fetch('''
            SELECT id, title, username FROM projects
            WHERE LOWER(title) LIKE LOWER($1) AND status='published'
            LIMIT 15
        ''', f'%{query}%')  # Add wildcards for LIKE
        return [dict(row) for row in rows]
    finally:
        await conn.close()

async def fetch_project_sections():
    conn = await get_db_conn()
    try:
        most_liked = await conn.fetch('''
            SELECT id, title FROM projects
            WHERE status = 'published'
            ORDER BY likes DESC LIMIT 15
        ''')
        most_pivoted = await conn.fetch('''
            SELECT id, title FROM projects 
            WHERE status = 'published'
            ORDER BY pivot_count DESC LIMIT 15
        ''')
        most_remixed = await conn.fetch('''
            SELECT id, title FROM projects 
            WHERE status = 'published'
            ORDER BY remix_count DESC LIMIT 15
        ''')
        random_projects = await conn.fetch('''
            SELECT id, title FROM projects 
            WHERE status = 'published'
            ORDER BY RANDOM() LIMIT 15
        ''')
        return {
            "Most Liked": [dict(row) for row in most_liked],
            "Most Pivoted": [dict(row) for row in most_pivoted],
            "Most Remixed": [dict(row) for row in most_remixed],
            "Some other...": [dict(row) for row in random_projects],
        }
    finally:
        await conn.close()

def create_search(id='search-bar', container=ui.column()):
    async def handle_search(e=None):
        container.clear()
        if not e:
            sections = await fetch_project_sections()
            container.clear()
            with container:
                for section, projects in sections.items():
                        ui.label(section).classes('font-bold')
                        with ui.row().classes('flex-wrap gap-2'):
                            for proj in projects:
                                with ui.card().classes('p-2'):
                                    ui.label(proj['title'])
        else:
            data = await search_projects(e.value)
            if data:
                container.clear()
                with container:
                    with ui.grid().classes('grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4'):
                        for proj in data:
                            with ui.card().classes('transition hover:shadow-lg hover:scale-[1.01]'):
                                with ui.column().classes('p-4'):
                                    ui.label(proj['title']).classes('text-lg font-semibold')
                                    ui.label(f"👤 {proj['username']}").classes('text-sm text-gray-600')
            else:
                container.clear()
                with container:
                    ui.label('🔍 No results found.')

    with ui.row().classes(f'{id} items-center mt-4 justify-center'):
        with ui.row().classes('w-full sm:w-[60vw] items-center gap-2'):
            search_input = ui.input(
                placeholder='Search...',
                on_change=lambda e: handle_search(e)
            ).props('dense outlined').classes('flex-grow')

            ui.button(icon='search', on_click=lambda: handle_search(search_input))\
                .props('push color=primary')

    return handle_search

def toggle_visibility():
    ui.run_javascript('''
        function updateButtonVisibility() {
            const isMobile = window.innerWidth < 640;
            document.querySelectorAll('.desktop-buttons').forEach(el => {
                el.style.display = isMobile ? 'none' : 'flex';
            });
        }
        window.addEventListener('resize', updateButtonVisibility);
        updateButtonVisibility();
    ''')

async def navigate():
    async def nav():
        ui.navigate.to(f"/{app.storage.user.get('username')}/dashboard/new")
    async def nav2():
        ui.navigate.to("/login")
    if app.storage.user.get('auth'):
        await nav()
    else:
        await nav2()

def header(theme, style, props):
    toggle_visibility()
    secondary = theme['primary']
    secondary_false = theme['accent']
    loggedin = app.storage.user.get('auth', False)
    username = app.storage.user.get('username')
    with ui.header(fixed=True, elevated=True).style(f'''
        background: linear-gradient(to right, {secondary}, {secondary_false});
    '''):
        with ui.row().classes('items-center w-full no-wrap').style('padding: 10px'):
            ui.image('data/banner.png').classes('w-[50%] lg:w-[20%]').style('user-select:none;')
            ui.space()
            dark = ui.dark_mode(app.storage.user.get('theme_dark'))
            def toggle():
                if dark.value == None:
                    dark.value = True
                dark.toggle()
                app.storage.user['theme_dark'] = dark.value
            options = [
                ('Home', 'home', lambda: ui.navigate.to('/')),
                ('Browse', 'folder', lambda: ui.navigate.to('/browse')),
                ('Create', 'add', navigate),
                ('About', 'info', lambda: ui.navigate.to('/docs/aboutus')),
                ('Docs', 'description', lambda: ui.navigate.to('/docs')),
                ('Help', 'help_outline', lambda: ui.navigate.to('/docs/help')),
                ('Theme', 'palette', toggle),
            ]

            with ui.row().classes('desktop-buttons gap-2 items-center'):
                for label, icon, command in options:
                    ui.button(label).props(f'{props} icon={icon}').style(style).on('click', command)
                if not loggedin:
                    ui.button('Join', on_click=lambda : ui.navigate.to('/signup')).props(f'{props} icon=add').style(style)
                    ui.button('Login', on_click=lambda : ui.navigate.to('/login')).props(f'{props} icon=add').style(style)
                else:
                    ui.button('Dashboard', on_click=lambda : ui.navigate.to(f'/{username}/dashboard')).props(f'{props} icon=person').style(style)

            with ui.button(icon='menu').classes('md:hidden').props(props):
                with ui.menu().classes('w-[45vw] p-4 rounded-xl shadow-xl').props('push'):
                    with ui.column().classes('flex flex-col gap-2'):
                        for label, icon, command in options:
                            ui.button(label).props(f'{props} icon={icon}').on('click', command).classes('w-full')
                        if not loggedin:
                            ui.button('Join', on_click=lambda : ui.navigate.to('/signup')).props(f'{props} icon=add').style(style).classes('w-full')
                            ui.button('Login', on_click=lambda : ui.navigate.to('/login')).props(f'{props} icon=add').style(style).classes('w-full')
                        else:
                            ui.button('Dashboard', on_click=lambda : ui.navigate.to(f'/{username}/dashboard')).props(f'{props} icon=person').style(style)

async def create_home(theme, btn, props):
    ui.colors(**theme)
    loggeduser = app.storage.user.get('username', None)
    loggedin = app.storage.user.get('auth', False)
    with ui.column()\
        .classes('w-full h-[95vh] items-'+\
        'center justify-center') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.html('Loading <span class="text-primary bold">TurtleGraphics</span>...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    await ui.context.client.connected(100)
    await asyncio.sleep(1)
    ee.delete()
    with ui.card().classes('w-full bg-[{light}] dark:bg-[{dark}]'.format(
    light=theme['secondary_false'],
    dark=theme['secondary_true']
)):
        with ui.row().classes('w-full'):
            ui.image('data/turtle2.png').style('width:25%; user-select:none;')
            with ui.column():
                if not loggedin:
                    ui.markdown('''
                        ## Hi, I'm Tortoise!
                        I am your turtle graphic teacher! Join me!
                        The journey of art is full of fun!
                    ''').style('user-select:none;')
                else:
                    ui.markdown(f'''
                        ## Hi <span style='color:black'>{str(loggeduser).title()}</span>, I'm Tortoise!\n
                        #### -> I am your turtle graphic teacher!\n
                        #### -> Let us start creating something or explore!\n
                        #### -> The journey of art is full of fun!\n
                    ''').style('user-select:none;')
                with ui.row():
                    ui.button('Start Creating').props('push icon=arrow_right')
                    ui.button('About').props('push icon=info')
            ui.space()
            ui.image('data/board.png').style('width:25%; user-select:none;')

    with ui.column().classes('search-desktop flex-col-reverse items-center w-full'):
        ui.button('See more', on_click=lambda:ui.navigate.to('/browse')).props(props).style(btn).classes('w-[50%]')
        row = ui.column()
        await create_search('search-bar-desktop', row)()
