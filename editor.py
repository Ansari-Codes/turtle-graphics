import cmath, math, random, statistics, numpy
import decimal, fractions, itertools, functools, collections, colorsys
import time
from nicegui import ui, app
import contextlib, io, asyncio, html
from js import (add_canvas_interactivity, 
                draw_image, 
                js_cs, copy_js,
                setup_zoom_pan, 
                toggle_visibility)
from web_turtle import Turtle
from datetime import datetime
from db import get_db_conn
import uuid
import base64
from PIL import Image, ImageColor
SAFE_MODULES = {
    'math': math,
    'cmath': cmath,
    'random': random,
    'statistics': statistics,
    'numpy': numpy,
    'asyncio': asyncio,
    'decimal': decimal,
    'fractions': fractions,
    'itertools': itertools,
    'functools': functools,
    'collections': collections,
    'colorsys':colorsys,
    'time':time
}

def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    allowed = SAFE_MODULES
    if name in allowed:
        return allowed[name]
    raise ImportError(f"Import of module '{name}' is not allowed.")

def input_stub(*args, **kwargs):
    pass

class Pond:
    def __init__(self):
        self.turtles = []
    
    def add_turtle(self, turtle):
        self.turtles.append(turtle)
        return turtle
    
    def get_turtles(self):
        return self.turtles

itsglobal = {
    '__builtins__': {
        'print': print,
        'input': input_stub,
        'range': range,
        'enumerate': enumerate,
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'list': list,
        'tuple': tuple,
        'dict': dict,
        'set': set,
        'len': len,
        'sum': sum,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'zip': zip,
        'map': map,
        'filter': filter,
        'all': all,
        'any': any,
        'sorted': sorted,
        'reversed': reversed,
        'isinstance': isinstance,
        'type': type,
        '__import__': safe_import,
        'chr': chr,              
        'ord': ord,              
        'bin': bin,              
        'oct': oct,              
        'hex': hex,              
        'id': id,                
        'format': format,        
        'slice': slice,
        'dir': dir,
        'True': True,
        'False': False,
        'None': None,
        'type': type,
        'id': id,
        'repr': repr,
        'Exception': Exception,
        'ValueError': ValueError,
        'TypeError': TypeError,
        'ZeroDivisionError': ZeroDivisionError,
        'now': time.time,
        'time_sec': time.perf_counter,
        'strftime': time.strftime,
        'Turtle': Turtle,
        'Pond': Pond
    },
    'divmod': divmod,
    'pow': pow,
    'complex': complex
}

class Logs(ui.markdown):
    def __init__(self, content: str = '') -> None:
        super().__init__(content)
        self.line_list = []
        self.maxlines = 50
        self.classes('log-box w-full h-full')
        self.style("""
            overflow-y: auto;
            scroll-behavior: smooth;
        """)
        self.classes('log-box')
    
    def push(self, lines: str):
        for line in lines.splitlines():
            self.line_list.append(line)
        if len(self.line_list) > self.maxlines:
            self.line_list = self.line_list[-self.maxlines:]
        self.content = '\n'.join(self.line_list)
        ui.run_javascript('''
            const box = document.querySelector(".log-box");
            if (box) box.scrollTop = box.scrollHeight;
        ''')
    
    def clear(self):
        self.line_list.clear()
        self.content = ''

def _execute_code(code: str, globals_dict: dict, stdout: io.StringIO, stderr: io.StringIO):
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exec(code, globals_dict)

async def execute_with_timeout(code: str, globals_dict: dict, timeout: float = 10):
    stdout = io.StringIO()
    stderr = io.StringIO()
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(
                None,
                _execute_code, code, globals_dict, stdout, stderr
            ),
            timeout=timeout
        )
        return stdout.getvalue(), stderr.getvalue(), None
    except asyncio.TimeoutError:
        return stdout.getvalue(), stderr.getvalue(), "Execution timed out"
    except Exception as e:
        return stdout.getvalue(), stderr.getvalue(), str(e)

def clear_screen(canvas):
    ui.run_javascript(js_cs)

def clear_logs(log):
    log.clear()

def get_VB(x, y):
    return f'-{x} -{y} {x*2} {y*2}'

def setup_buttons(code_editor, logs, canvas):
    code_editor.set_value("""t1 = Turtle()
for i in range(100):
    t1.fd(i)
    t1.lt(85)
""")
    
    def stop_running():
        client = ui.context.client
        client.running = False
        task = getattr(client, 'task', None)
        if task and not task.done():
            task.cancel()
        logs.push('\n'+f"<b>[{datetime.now().strftime('%H:%M:%S')}] Stopped</b><br>"+'\n')
        run_btn.enable()
        stop_btn.disable()
        
    async def run_code():
        client = ui.context.client
        if getattr(client, 'running', False):
            logs.push('\n'+"Already Running!"+'\n')
            return
        client.running = True
        client.task = asyncio.current_task()
        stop_btn.enable()
        run_btn.disable()
        clear_btn.disable()
        try:
            safe_globals = {}
            safe_globals.update(itsglobal)
            safe_globals['Turtle'] = Turtle
            logs.push(f"""<b>[{datetime.now().strftime('%H:%M:%S')}] RUNNING...</b><br>Executing...""")
            stdout, stderr, error = await execute_with_timeout(code_editor.value, safe_globals)
            logs.push(f"\nExecuted!<br>Drawing...\n")
            if stderr:
                logs.push('\n'+stderr+'\n')
            if error:
                logs.push('\n'+f"Error: {error}"+'\n')
                return
            logs.push('\n'+stdout+'\n')
            turtles = [value for name, value in safe_globals.items()
                    if isinstance(value, Turtle)]
            img_data_list = []
            if turtles:
                for turtle in turtles:
                    img_data_list.append(turtle._get_image_data())
            else:
                return
            screen = safe_globals.get("SCREEN", {})
            geom: tuple = screen.get('geometry', (600, 600))
            bg = screen.get('bg', 'white')
            if not len(geom) == 2:
                logs.push("\n`GEOMETRY` in `SCREEN` must be a tuple of two elements ('width', 'height')!\n")
                return
            width, height = geom[0], geom[1]
            if (width > 6000 or width < 100) or (
                height > 6000 or height < 100
            ):
                logs.push('Width or Height specified in `SCREEN` must be greater than 100 but less than or equal to 6000.')
                return
            canvas.set_content(f'''
                <div id="canvas-container" class="flex justify-center items-center w-full h-full overflow-auto bg-gray-100 p-4">
                    <div id="canvas-wrapper" data-width="{width}" data-height="{height}">
                        <canvas id="turtle-canvas" width="{width}" height="{height}" style="background: transparent;" class="rounded-lg shadow-lg border-2 border-gray-300"></canvas>
                    </div>
                </div>
            ''')
            canvas.props('id=canvas1')
            try:
                bg_ = ImageColor.getcolor
            except ValueError:
                bg_ = (255, 255, 255, 255)
            try:
                if img_data_list:
                    try:
                        combined_img = Image.new('RGBA', (width, height), bg)
                        for img_data in img_data_list:
                            if img_data.startswith('data:image/png;base64,'):
                                img_data = img_data.split(',')[1]
                            img_bytes = base64.b64decode(img_data)
                            img = Image.open(io.BytesIO(img_bytes))
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            temp_canvas = Image.new('RGBA', (width, height), bg)
                            x_offset = (width - img.width) // 2
                            y_offset = (height - img.height) // 2
                            temp_canvas.paste(img, (x_offset, y_offset), img)
                            combined_img = Image.alpha_composite(combined_img, temp_canvas)
                        buffer = io.BytesIO()
                        combined_img.save(buffer, format='PNG')
                        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        combined_data = f"data:image/png;base64,{img_str}"
                    except Exception as e:
                        logs.push(f"\nError combining images: {str(e)}\n")
                        blank_img = Image.new('RGBA', (width, height), bg)
                        buffer = io.BytesIO()
                        blank_img.save(buffer, format='PNG')
                        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        combined_data = f"data:image/png;base64,{img_str}"
                else:
                    # No images, create a blank one
                    blank_img = Image.new('RGBA', (width, height), bg)
                    buffer = io.BytesIO()
                    blank_img.save(buffer, format='PNG')
                    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    combined_data = f"data:image/png;base64,{img_str}"
            except Exception as e:
                combined_data = f"data:image/png;base64,"
            ui.run_javascript(draw_image(combined_data))
            return
        finally:
            client.running = False
            client.task = None
            run_btn.enable()
            stop_btn.disable()
            clear_btn.enable()
            logs.push(f"""\n<b>[{datetime.now().strftime('%H:%M:%S')}] RAN!</b><br>""")    
    with ui.row():
        with ui.row().classes('w-full flex-wrap'):
            run_btn = ui.button().props('push icon=play_arrow color=positive') \
                .classes('w-full sm:flex-1 sm:w-1/3')
            
            stop_btn = ui.button().props('push icon=stop color=negative') \
                .classes('w-full sm:flex-1 sm:w-1/3')
            clear_btn = ui.button(
                on_click=lambda: clear_screen(canvas)
            ).props('push icon=layers_clear color=warning') \
                .classes('w-full sm:flex-1 sm:w-1/3')
    run_btn.on('click', run_code)
    stop_btn.on('click', stop_running)
    stop_btn.disable()

async def get_projects(limit=5):
    username = app.storage.user.get('username')
    if not username:
        return []
    
    db = await get_db_conn()
    try:
        rows = await db.fetch("""
        SELECT 
            title, 
            code_data AS code, 
            svg_data AS svg, 
            created_at
        FROM projects
        WHERE username = $1
        ORDER BY created_at DESC
        LIMIT $2
        """, username, limit)
        
        projects = [dict(row) for row in rows]
        return projects
    finally:
        await db.close()

async def create_dialogs(user, codearea):
    theme_dark = app.storage.user.get('theme_dark', False)
    theme_class = f'bg-secondary_{theme_dark.__str__().lower()}'
    with ui.dialog().classes('w-fit h-fit') as dialog, ui.card().classes(f'w-[98%] h-[410px] {theme_class} flex-col overflow-x-hidden'):
        with ui.row().classes('w-full h-[60px] items-center px-4 bg-dark'):
            ui.label('Open Project').classes('text-lg font-bold')
            ui.space()
            ui.button(on_click=dialog.close).classes('bg-negative').props('icon=close push dense')
        with ui.tabs().classes('w-full') as tabs:
            ui.tab('gallery', 'My Gallery')
            ui.tab('upload', 'Upload from Local')
        with ui.tab_panels(tabs, value='gallery').classes('w-full flex-grow'):
            with ui.tab_panel('gallery').classes('p-4 h-full'):
                with ui.column().classes('w-full h-full gap-4'):
                    ui.label('Your Projects').classes('text-lg font-semibold')
                    projects_container = ui.row().classes('w-full h-full overflow-y-auto gap-4 flex-wrap')
                    with ui.row().classes('w-full h-full items-center justify-center') as loading_indicator:
                        ui.spinner()
                        ui.label('Loading projects...').classes('ml-2')
                    async def load_projects():
                        try:
                            projects = await get_projects()
                            loading_indicator.clear()
                            projects_container.clear()
                            if not projects:
                                with projects_container:
                                    with ui.column().classes('w-full h-full items-center justify-center'):
                                        ui.icon('folder_open').classes('text-4xl text-gray-400')
                                        ui.label('No projects found').classes('text-gray-500')
                                return
                            with projects_container:
                                for p in projects:
                                    with ui.card().classes('w-48 h-56 p-3 flex flex-col gap-2'):
                                        ui.label(p['title']).classes('font-bold text-center truncate')
                                        if p.get('svg'):
                                            ui.image(p['svg']).classes('w-full h-32 object-contain bg-gray-100 rounded')
                                        else:
                                            with ui.element('div').classes('w-full h-32 bg-gray-100 rounded flex items-center justify-center'):
                                                ui.icon('image_not_supported').classes('text-gray-400 text-3xl')
                                        if p.get('created_at'):
                                            created = p['created_at']
                                            if isinstance(created, str):
                                                ui.label(f"Created: {created[:10]}").classes('text-xs text-gray-500')
                                            else:
                                                ui.label(f"Created: {created.strftime('%Y-%m-%d')}").classes('text-xs text-gray-500')
                                        ui.button('Open', on_click=lambda e,proj=p: [
                                            codearea().set_value(proj['code']),
                                            dialog.close()
                                        ]).props('color=primary size=sm')
                        except Exception as e:
                            loading_indicator.clear()
                            with projects_container:
                                with ui.column().classes('w-full h-full items-center justify-center'):
                                    ui.icon('error').classes('text-4xl text-negative')
                                    ui.label('Error loading projects').classes('text-negative font-medium')
                                    ui.label(str(e)).classes('text-gray-500 text-sm')
                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancel', on_click=dialog.close).props('outline color=negative')
            
            with ui.tab_panel('upload').classes('p-4 h-full'):
                ui.label('Upload Project File').classes('text-lg font-semibold')
                with ui.column().classes('w-full h-full gap-4 items-center'):
                    ui.upload(
                        max_file_size=51200,
                        on_upload=lambda e: [codearea().set_value(e.content.read().decode()), dialog.close()]
                    ).props('push')
    dialog.props('persistent')
    dialog.on('show', load_projects)
    return dialog

async def validate_title(title):
    conn = await get_db_conn()
    try:
        result = await conn.fetchrow(
            'SELECT * FROM projects WHERE title=$1',
            title
        )
    finally:
        await conn.close()
        await asyncio.sleep(0.1)
    exists = result is not None
    return exists

async def export_canvas():
    notifcation = ui.notification('Preparing and downloading...',
                                    timeout=3600,
                                    spinner=True)
    try:
        await ui.run_javascript('''
            const canvas = document.getElementById('turtle-canvas');
            if (canvas) {
                canvas.toBlob(function(blob) {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'turtle-canvas-' + Date.now() + '.png';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(function() {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    }, 100);
                }, 'image/png');
            } else {
                alert('No canvas found to export');
            }
        ''')
        notifcation.dismiss()
    except Exception as e:
        ui.notify(f'Error: {e}', type='negative')
        notifcation.dismiss()

async def _save(code, pid):
    username = app.storage.user.get('username')
    if not username:
        ui.notify('Please log in to save projects', type='warning')
        return
    code_data = code.value
    spinner = ui.notification('Saving...', spinner=True, timeout=3600)
    title = ui.context.client.pname
    id_ = pid
    try:
        spinner._text = 'Collecting canvas...'
        spinner.update()
        
        img_src = await ui.run_javascript('''
            const canvas = document.getElementById('turtle-canvas');
            if (canvas) {
                return canvas.toDataURL('image/png');
            }
            return null;
        ''', timeout=3600)
        if not img_src:
            spinner.dismiss()
            await asyncio.sleep(0.02)
            ui.notify('No image found on canvas. Please run your code first to generate the drawing.', type='warning')
            return
        svg_data = img_src
    except Exception as e:
        spinner.dismiss()
        await asyncio.sleep(0.02)
        ui.notify(f'Failed to get image content: {str(e)}', type='negative')
        return
    
    spinner._text = 'Validating everything...'
    spinner.update()
    if not title:
        spinner.dismiss()
        await asyncio.sleep(0.02)
        ui.notify('Project title cannot be empty', type='warning')
        return
    if not code_data:
        spinner.dismiss()
        await asyncio.sleep(0.02)
        ui.notify('Project code not found...', type='warning')
        return
    spinner._text = 'Saving...'
    spinner.update()
    conn = await get_db_conn()
    try:
        await conn.execute(
            '''
            UPDATE projects
            SET username = $1,
                title = $2,
                code_data = $3,
                svg_data = $4,
                status = 'draft'
            WHERE id = $5
            ''',
            username, title, code_data, svg_data, pid
        )
        ui.notify('Project Saved Successfully!', type='positive')
    except Exception as e:
        ui.notify(f'Failed to save project: {str(e)}', type='negative')
    finally:
        await conn.close()
        spinner.dismiss()

async def get_id(title):
    con = await get_db_conn()
    try:
        result = await con.fetchrow(
            'SELECT id FROM projects WHERE title=$1',
            title
        )
        return result['id'] if result else None
    finally:
        await con.close()

def save(code, labels):
    client = ui.context.client
    prev_title = uuid.uuid1().hex[:8] if not hasattr(client, 'pname') else client.pname
    async def change_title():
        new_title = tinp.value.strip()
        if not new_title:
            ui.notify('Project title cannot be empty', type='warning')
            return
        if new_title != prev_title:
            exists = await validate_title(new_title)
            if exists:
                ui.notify(f'Project with title "{new_title}" already exists', type='warning')
                return
        client.pname = new_title
        try:
            img_src = await ui.run_javascript('''
                const canvas = document.getElementById('turtle-canvas');
                if (canvas) {
                    return canvas.toDataURL('image/png');
                }
                return null;
            ''', timeout=3600)
        except:
            img_src = ''
        conn = await get_db_conn()
        try:
            result = await conn.fetchrow(
                '''
                INSERT INTO projects (username, title, code_data, svg_data, status)
                VALUES ($1, $2, $3, $4, 'draft')
                RETURNING id
                ''',
                client.username, new_title, code().value, img_src
            )
            
            client.pid = result['id']
            for l in labels():
                l.set_text(new_title)
            ui.notify('Project Created Successfully!', type='positive')
        except Exception as e:
            ui.notify(f'Failed to create project: {str(e)}', type='negative')
        finally:
            await conn.close()
        dg.close()
    with ui.dialog() as dg, ui.card().classes('w-fit h-fit'):
        with ui.column().classes('p-4'):
            ui.label('Project Name').classes('text-lg font-bold mb-2')
            tinp = ui.input(placeholder='Enter project name...', value=prev_title).props('dense')            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel').on_click(dg.close).props('outline color=negative')
                ui.button('Save').on_click(change_title).props('color=positive')
    return dg

async def create_new(theme, style, props):
    ui.colors(**theme)
    dark = ui.dark_mode(app.storage.user.get('theme_dark', False))
    async def run_horizon():
        try:
            horizontal = await ui.run_javascript('window.innerWidth < 640', timeout=10)
        except Exception:
            horizontal = False
        return horizontal
    with ui.column()\
        .classes('w-full h-[95vh] items-'+\
        'center justify-center') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.html('Loading <span class="text-primary bold">Editor</span>...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    await ui.context.client.connected(100)
    await asyncio.sleep(1)
    print("Connected!")
    horizontal = await run_horizon()
    primary = theme['primary']
    def toggle():
        dark.toggle()
        codearea1.theme = 'githubDark' if dark.value else 'githubLight'
    plabels = []
    async def init():
        theme_dark = app.storage.user.get("theme_dark")
        user = app.storage.user.get('username')
        codearea1.theme = 'githubDark' if theme_dark else 'githubLight'
        canvas1.classes('bg-white')
        client = ui.context.client
        client.username = user
        if not hasattr(client, 'pname'):
            client.pname = uuid.uuid1().hex[:8]
        
        setup_zoom_pan()
        add_canvas_interactivity()
    
    async def handle_save():
        if hasattr(client, 'pid'):
            print(client.pname, client.pid)
            return await _save(codearea1, client.pid)
        save_dialog.open()
    open_dialog = await create_dialogs(user = app.storage.user.get('username'),
                                codearea=lambda: codearea1)
    save_dialog = save(lambda: codearea1, lambda: plabels)
    ee.delete()
    with ui.header().classes('shadow-md').style(f'background: {primary}; color: white;'):
        with ui.row().classes('items-center justify-start w-full px-4 py-2 gap-4'):
            buttons = [
                {"Settings": [
                    ('Editor', 'edit', 'editor'),
                    ('Theme', 'palette', 'toggle_theme'),
                ]},
                {"File": [
                    ('Load', 'photo_library', 'load'),
                    ('Save', 'save', 'save'),
                    ('Export Code', 'code', 'export_code'),
                    ('Export Canvas', 'image', 'export_canvas'),
                    ('Export Logs', 'list_alt', 'export_logs'),
                    ('Publish', 'upload', 'publish'),
                ]},
                {"Edit": [
                    ('Copy Canvas', 'photo_library', 'copy_canvas'),
                    ('Copy Logs', 'assignment', 'copy_logs'),
                    ('Clear Canvas', 'layers_clear', 'clear_canvas'),
                    ('Clear Logs', 'delete_sweep', 'clear_logs'),
                ]},
                {"Help": [
                    ('Docs', 'menu_book', 'docs'),
                    ('Learn', 'school', 'learn'),
                ]}
            ]
            def add_btn(label, icon, action_id, is_mobile=False):
                btn = ui.button().classes(
                    'w-full mb-1 justify-between' if not is_mobile else 'w-[100%]'
                )
                with btn:
                    ui.label(label).classes('text-left')
                    ui.space()
                    ui.icon(icon)
                if action_id == 'toggle_theme':
                    btn.on('click', toggle)
                elif action_id in ('editor', 'load', 'save', 'export_code', 'export_canvas', 'export_logs', 'publish', 'docs', 'learn'):
                    if action_id == 'load':
                        btn.on_click(open_dialog.open)
                    elif action_id == 'save':
                        btn.on_click(handle_save)
                    elif action_id == 'export_code':
                        btn.on_click(lambda: ui.download.content(codearea1.value, f'turtle-code-{uuid.uuid1().hex[:8]}.py'))
                    elif action_id == 'export_canvas':
                        btn.on_click(export_canvas)
                    elif action_id == 'export_logs':
                        btn.on_click(lambda: ui.download.content(logs1.content, f'turtle-logs-{uuid.uuid1().hex[:8]}.log'))
                    else:
                        btn.on('click', lambda e, a=action_id: print(f"Action: {a}"))
                elif action_id == 'clear_canvas':
                    btn.on('click', lambda e: clear_screen(canvas1))
                elif action_id == 'clear_logs':
                    btn.on('click', lambda e: clear_logs(logs1))
            with ui.row().classes('desktop-toolbar w-full items-center').style('gap: 1rem') as desktop:
                ui.image('data/create.png').classes('w-[150px]').style('user-select: none;')
                for group in buttons:
                    group_name, options = list(group.items())[0]
                    with ui.button(group_name).props(f'{props} icon-right=arrow_drop_down').style(style):
                        with ui.menu().props('push auto-close').classes('p-4 rounded-xl shadow-xl w-[200px]'):
                            for label, icon, action_id in options:
                                if action_id == 'copy_canvas':
                                    with ui.button().classes('w-full mb-1 justify-between') as btn:
                                        ui.label(label).classes('text-left')
                                        ui.space()
                                        ui.icon(icon)
                                    btn.on('click', js_handler=copy_js)
                                elif action_id == 'copy_logs':
                                    with ui.button().classes('w-full mb-1 justify-between') as btn:
                                        ui.label(label).classes('text-left')
                                        ui.space()
                                        ui.icon(icon)
                                    btn.on('click', js_handler='''
                                        () => {
                                            const logs = document.getElementById("logs1");
                                            navigator.clipboard.writeText(logs ? logs.innerText : '');
                                        }
                                    ''')
                                else:
                                    add_btn(label, icon, action_id)
                ui.space()
                loggedin = app.storage.user.get('auth', False)
                loggeduser = app.storage.user.get('username', None)
                if not loggedin:
                    ui.button('Sign Up', on_click=lambda: ui.navigate.to('/signup')).props(props).style(style)
                    ui.button('Sign In', on_click=lambda: ui.navigate.to('/login')).props(props).style(style)
                else:
                    client = ui.context.client
                    project_name = client.pname if hasattr(client, 'pname') else 'Untitled'
                    plabel = ui.label(f'Project: {project_name}').classes('text-white font-medium')
                    plabels.append(plabel)
                    ui.button(str(loggeduser), on_click=lambda: ui.navigate.to(f'/{loggeduser}/dashboard'))
            with ui.row().classes('mobile-toolbar w-full items-center') as mobile:
                ui.image('data/create.png').classes('w-[80px]').style('user-select: none;')
                ui.space()
                with ui.button(icon='menu').props(props):
                    with ui.menu().classes('w-[200px] p-4 rounded-xl shadow-xl').props('push'):
                        with ui.column().classes('flex flex-col gap-2'):
                            for group in buttons:
                                group_name, options = list(group.items())[0]
                                with ui.button().classes('w-[100%]').props(f'{props}').style(style):
                                    ui.icon('arrow_left')
                                    ui.label(group_name).classes('text-left')
                                    with ui.menu().props('push self=top_middle auto-close').classes('p-4 rounded-xl shadow-xl w-[45vw]'):
                                        for label, icon, action_id in options:
                                            if action_id == 'copy_canvas':
                                                with ui.button().classes('w-full mb-1 justify-between') as btn:
                                                    ui.label(label).classes('text-left')
                                                    ui.space()
                                                    ui.icon(icon)
                                                btn.on('click', js_handler=copy_js)
                                            elif action_id == 'copy_logs':
                                                with ui.button().classes('w-full mb-1 justify-between') as btn:
                                                    ui.label(label).classes('text-left')
                                                    ui.space()
                                                    ui.icon(icon)
                                                btn.on('click', js_handler='''
                                                    () => {
                                                        const logs = document.getElementById("logs1");
                                                        navigator.clipboard.writeText(logs ? logs.innerText : '');
                                                    }
                                                ''')
                                            else:
                                                add_btn(label, icon, action_id, is_mobile=True)
                                    ui.separator()
                            if not loggedin:
                                btn = ui.button().classes('w-[100%]' )
                                with btn:
                                    ui.label('Signup').classes('text-left')
                                    ui.space()
                                    ui.icon('add')
                                btn.on_click(lambda: ui.navigate.to('/signup')).props(props).style(style)
                                btn2 = ui.button().classes('w-[100%]' )
                                with btn2:
                                    ui.label('SignIn').classes('text-left')
                                    ui.space()
                                    ui.icon('add')
                                btn2.on_click(lambda: ui.navigate.to('/login')).props(props).style(style)
                            else:
                                client = ui.context.client
                                project_name = client.pname if hasattr(client, 'pname') else 'Untitled'
                                plabel = ui.label(f'Project: {project_name}').classes('text-white font-medium')
                                plabels.append(plabel)
                                btn = ui.button().classes('w-[100%]' )
                                with btn:
                                    ui.label(str(loggeduser)).classes('text-center w-full')
                                    ui.space()
                                btn.on_click(lambda: ui.navigate.to(f'/{loggeduser}/dashboard')).props(props).style(style)
    ui.on('clipboard_read', lambda e: codearea1.set_value(e.args if e.args else ''))
    with ui.splitter(horizontal=horizontal, value=50, limits=(0, 100) if not horizontal else (20, 80)) \
            .classes('splitter-tg-lg w-full h-[86vh] mt-1').style('overflow: hidden;') as splitter:
        with splitter.before:
            with ui.splitter(horizontal=True, value=50) \
                    .classes('w-full h-full') \
                    .style('overflow: hidden;') as splitter_child:
                with splitter_child.before:
                    theme_dark = app.storage.user.get('theme_dark')
                    codearea1 = ui.codemirror('', language='Python').classes('h-full').props('id=codearea1')
                with splitter_child.after:
                    logs1 = Logs().classes('h-full bg-primary').props('id=logs1')
                with splitter_child.separator:
                    ui.icon('arrow_range').classes('text-gray-400 w-[10px]')
        with splitter.after:
            with ui.card().classes('w-full h-full rounded shadow flex-col-reverse'):
                canvas1 = ui.html().props('id=canvas1')
                canvas1.classes('w-full h-full').style('overflow-y:auto;')
                setup_buttons(codearea1, logs1, canvas1)
    await init()
    toggle_visibility()