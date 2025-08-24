import asyncio
from datetime import datetime
from nicegui import ui, app
from db import get_db_conn
import plotly.graph_objects as go

def view_project(project_data, dialog):
    dialog.clear()
    title = project_data.get('title', 'Untitled Project')
    code = project_data.get('code', '')
    img = project_data.get('svg', '')
    created_at = project_data.get('created_at', '')
    status = project_data.get('status', 'draft')
    if created_at:
        if isinstance(created_at, str):
            created_str = created_at[:10]
        else:
            created_str = created_at.strftime('%Y-%m-%d')
    else:
        created_str = 'Unknown'
    with dialog.classes('w-full h-full flex-col'), ui.card().classes('w-full h-full flex flex-col rounded-xl shadow-2xl'):
        with ui.carousel(animated=True).classes('w-full h-full') as c:
            with ui.carousel_slide('Graphics').classes('w-full h-full'):
                with ui.row().classes('rounded-lg p-2 m-0 bg-primary w-full'):
                    ui.label(title.__str__().capitalize()).classes('text-xl')
                    ui.badge(status, color='positive' if status=='published' else 'gray')
                    ui.space()
                    ui.button(icon='close')\
                        .on_click(dialog.close).\
                            props('push color=negative')
                with ui.element('div').classes('flex-grow w-full bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center'):
                    if img:
                        ui.image(img).classes('max-w-full max-h-full object-contain')
                    else:
                        with ui.column().classes('items-center justify-center text-gray-400'):
                            ui.icon('image_not_supported').classes('text-4xl')
                            ui.label('No preview available')
                with ui.row():
                    ui.button('Code', icon='navigate_next').\
                        on_click(c.next).\
                            props('push')
            with ui.carousel_slide('Code').classes('max-w-full max-h-full').\
                props('control-color=primary'):
                with ui.row().classes('rounded-lg p-2 m-0 bg-primary w-full'):
                    ui.label(title.__str__()).classes('text-xl')
                    ui.badge(status, color='positive' if status=='published' else 'gray')
                    ui.space()
                    ui.button(icon='close')\
                        .on_click(dialog.close).\
                            props('push color=negative')
                ui.code(code).classes('w-full overflow-auto')
                with ui.row().classes('justify-between mt-2 text-sm text-gray-500'):
                    ui.label(f"Lines: {len(code.splitlines())}")
                    ui.label(f"Characters: {len(code)}")
                with ui.row():
                    ui.button('Output', icon='navigate_before').\
                        on_click(c.previous).\
                            props('push')
    dialog.open()

async def get_projects(limit=5, order_by="created_at"):
    username = app.storage.user.get('username')
    db = await get_db_conn()
    query = f"""
        SELECT 
            title, 
            code_data AS code, 
            svg_data AS svg, 
            pivot_count, 
            remix_count, 
            created_at, 
            likes,
            description,
            status
        FROM projects
        WHERE username = $1
        ORDER BY {order_by} DESC
        LIMIT $2
    """
    rows = await db.fetch(query, username, limit)
    await db.close()
    return [dict(row) for row in rows]

async def projector():
    order_map = {
        "Latest": ("created_at", True),
        "Oldest": ("created_at", False),
        "Most Likes": ("likes", True),
        "Most Remixed": ("remix_count", True),
        "Most Pivots": ("pivot_count", True)
    }
    
    with ui.row().classes('w-full flex-wrap gap-4 items-center'):
        ui.label('Projects').classes('text-2xl')
        ui.space()
        selected_order = ui.select(
            list(order_map.keys()), 
            value="Latest", 
            label="Sort by"
        ).props('dense bordered')
        limit_input = ui.number(
            label="Limit", 
            value=5, 
            min=1,
            max=20,
            step=1
        ).props('dense bordered')
    
    project_container = ui.scroll_area().classes("w-full h-[60vh] gap-4")
    
    async def refresh_projects():
        order_by, desc = order_map[str(selected_order.value)]
        projects = await get_projects(limit_input.value, order_by)
        if not desc:
            projects = list(reversed(projects))
        
        project_container.clear()
        with project_container:
            for p in projects:
                with ui.card().classes(
                    'w-full p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-2'
                ):
                    with ui.column():
                        ui.label(p['title']).classes('text-lg font-semibold')
                        ui.label(f"Created: {p['created_at'][:10] if isinstance(p['created_at'], str) else p['created_at'].strftime('%Y-%m-%d')}").classes('text-sm text-gray-500')
                    with ui.row().classes('gap-4 items-center'):
                        ui.badge(p['status']).props('color=primary')
                        ui.label(f"❤️ {p['likes']}")
                        ui.label(f"⬆️ {p['pivot_count']}")
    
    selected_order.on('change', lambda _: refresh_projects())
    limit_input.on('change', lambda _: refresh_projects())
    await refresh_projects()
    return project_container

async def main():
    projects_data = await get_projects(limit=1000)  # Get all projects for stats
    with ui.column().classes('w-full gap-6'):
        with ui.row().classes('flex flex-col md:flex-row w-full gap-6'):
            with ui.column().classes('w-full md:w-[40vw]'):
                with ui.row().classes('flex flex-wrap gap-4 w-full'):
                    with ui.card().classes('flex-1 min-w-[140px] p-4'):
                        ui.label('Total Projects').classes('text-sm text-gray-500')
                        ui.label(len(projects_data)).classes('text-2xl font-bold')# pyright: ignore[reportArgumentType]
                    with ui.card().classes('flex-1 min-w-[140px] p-4'):
                        ui.label('Total Likes').classes('text-sm text-gray-500')
                        ui.label(sum(p['likes'] for p in projects_data)).classes('text-2xl font-bold')# pyright: ignore[reportArgumentType]
                    with ui.card().classes('flex-1 min-w-[140px] p-4'):
                        ui.label('Total Remixes').classes('text-sm text-gray-500')
                        ui.label(sum(p['remix_count'] for p in projects_data)).classes('text-2xl font-bold')# pyright: ignore[reportArgumentType]
                    with ui.card().classes('flex-1 min-w-[140px] p-4'):
                        ui.label('Total Pivots').classes('text-sm text-gray-500')
                        ui.label(sum(p['pivot_count'] for p in projects_data)).classes('text-2xl font-bold') # pyright: ignore[reportArgumentType]
                await projector()
            
            with ui.column().classes('w-full md:w-[40vw]'):
                with ui.row().classes('flex flex-col gap-6 w-full'):
                    # Responsive container for charts
                    with ui.element('div').classes('w-full max-w-full sm:max-w-[400px] md:max-w-none mx-auto'):
                        pie_fig = go.Figure(
                            data=[go.Pie(
                                labels=['Draft', 'Published'],
                                values=[
                                    sum(1 for p in projects_data if p['status'] == 'draft'),
                                    sum(1 for p in projects_data if p['status'] == 'published'),
                                ],
                            )]
                        )
                        pie_fig.update_layout(title='Project Status', margin=dict(l=20, r=20, t=40, b=20))
                        ui.plotly(pie_fig).classes('w-full h-[300px] sm:h-[350px] md:h-[400px]')

                    with ui.element('div').classes('w-full max-w-full sm:max-w-[400px] md:max-w-none mx-auto'):
                        bar_fig = go.Figure(
                            data=[go.Bar(
                                x=[p['title'][:15] + '...' if len(p['title']) > 15 else p['title'] for p in projects_data[:10]],
                                y=[p['likes'] for p in projects_data[:10]],
                            )]
                        )
                        bar_fig.update_layout(title='Likes per Project (Top 10)', margin=dict(l=20, r=20, t=40, b=20))
                        ui.plotly(bar_fig).classes('w-full h-[300px] sm:h-[350px] md:h-[400px]')

async def projects_page(dialog, max_proj=30):
    all_projects = await get_projects(limit=1000)
    total_projects = len(all_projects)
    total_pages = max(1, (total_projects + max_proj - 1) // max_proj)
    search_input = ui.input(placeholder='Search projects...',
        on_change=lambda e: show_content(1, e.value)).classes('w-full mb-4')
    cont = ui.row().classes('w-full justify-start flex-wrap gap-4 mt-4')
    pagination_container = ui.row().classes('w-full justify-center mt-4')
    def show_content(page, search_text=''):
        cont.clear()
        pagination_container.clear()
        filtered = [p for p in all_projects if search_text.lower() in p['title'].lower()]
        filtered_total = len(filtered)
        filtered_pages = max(1, (filtered_total + max_proj - 1) // max_proj)
        start = (page-1) * max_proj
        end = min(page * max_proj, filtered_total)
        with cont:
            for row in filtered[start:end]:
                created = row['created_at']
                if isinstance(created, datetime):
                    created_str = created.strftime("%b %d, %Y")
                else:
                    created_str = str(created)
                with ui.card().classes('w-full sm:w-[300px] h-fit p-4 shadow-md hover:shadow-lg transition'):
                    ui.label(row['title']).classes('font-bold text-lg mb-2')
                    if row['svg']:
                        ui.image(row['svg']).classes('w-full h-[150px] overflow-hidden mb-3 bg-gray-100 rounded object-contain')
                    else:
                        ui.label('No preview').classes('text-gray-500 italic mb-3')
                    with ui.row().classes('justify-between w-full mb-2'):
                        ui.label(f"❤️ {row['likes']}").classes('text-red-500')
                        ui.label(f"🔄 {row['pivot_count']} pivots")
                    ui.label(f"📅 {created_str} --- {row['status']}").classes('text-gray-500 text-sm mb-2')
                    ui.button('View Project', on_click=lambda r=row: view_project(r, dialog)) \
                        .props('color=secondary outline rounded')
        with pagination_container:
            ui.pagination(value=page, 
                        min=1, 
                        max=filtered_pages, 
                        direction_links=True,
                        on_change=lambda e: show_content(e.value, search_input.value)).classes('w-full')
    show_content(1)
    return cont

async def create_dashboard(theme, style, props, user):
    ui.colors(**theme)
    if not app.storage.user.get('auth', False):
        ui.label(f'Un-authorized access!')
        ui.navigate.to('/login')
        return
    
    dark = ui.dark_mode(app.storage.user.get('theme_dark', False))
    
    # Loading screen
    with ui.column().classes('w-full h-[95vh] items-center justify-center') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.html('Loading <span class="text-primary bold">Dashboard</span>...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    
    await ui.context.client.connected(100)
    await asyncio.sleep(1)
    ee.delete()
    
    ui.add_css('''
    .q-btn-toggle .q-btn {
        border-radius: 10px !important;
        margin-bottom: 8px;
    }
    .q-btn-toggle .q-btn:not(:last-child) {
        border-right: none !important;
    }
    ''')
    
    dialog = ui.dialog()
    
    with ui.left_drawer(fixed=False, value=True, elevated=False).classes('bg-primary') as drawer:
        with ui.column().classes('w-[95%] h-full m-1'):
            ui.image('data/banner.png').style('user-select:none;')
            options = [
                'Dashboard',
                'Projects',
                'Analytics',
                'Profile',
                'Settings'
            ]
            ui.toggle(options, value='Dashboard',
                on_change=lambda e: switch_panel(e.value)).classes('flex-col shadow-none bg-none text-sm w-full') \
                .props('push color=secondary toggle-color=dark text-color=accent',
                )
    with ui.column().classes('w-full m-0 p-0'):
        with ui.row().classes('w-full h-[60px] rounded-t-2xl bg-primary items-center px-3 justify-between m-0 p-0 flex-nowrap'):
            ui.button(on_click=drawer.toggle, icon='sym_s_side_navigation').props('push rounded size=sm')
            panel_label = ui.label('Dashboard').classes('text-white text-lg font-bold sm:text-xl truncate')
            ui.label('@' + app.storage.user.get('username','')).classes('text-white text-base font-bold sm:text-xl truncate')
        content_container = ui.column().classes('w-full m-0 p-0')
        async def switch_panel(panel_name):
            panel_label.set_text(panel_name)
            content_container.clear()
            with content_container:
                if panel_name == 'Dashboard':
                    await main()
                elif panel_name == 'Projects':
                    await projects_page(dialog)
        await switch_panel('Dashboard')