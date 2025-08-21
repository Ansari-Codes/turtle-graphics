from nicegui import ui

js_cs = '''
    const canvas = document.getElementById('turtle-canvas');
    const wrapper = document.getElementById('canvas-wrapper');
    if (canvas) {
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Reset zoom and pan
        canvas.style.transform = 'translate(0px, 0px) scale(1)';
        canvas.style.transformOrigin = 'top left';
        
        // Reset wrapper size if needed
        if (wrapper) {
            wrapper.style.width = canvas.width + 'px';
            wrapper.style.height = canvas.height + 'px';
        }
    }
'''
def draw_image(combined_data):
    return f'''
        setupZoomPan();
        const canvas = document.getElementById('turtle-canvas');
        const wrapper = document.getElementById('canvas-wrapper');
        const container = document.getElementById('canvas-container');
        const ctx = canvas.getContext('2d', {{ willReadFrequently: true }});
        const img = new Image();
        img.onload = function() {{
            // Get the intended dimensions from the wrapper's data attributes
            const intendedWidth = parseInt(wrapper.dataset.width || img.width);
            const intendedHeight = parseInt(wrapper.dataset.height || img.height);
            
            // Set canvas dimensions to match the intended geometry
            canvas.width = intendedWidth;
            canvas.height = intendedHeight;
            
            // Keep wrapper dimensions as set by Python (don't change them)
            // wrapper.style.width = `${{intendedWidth}}px`;  // Remove this line
            // wrapper.style.height = `${{intendedHeight}}px`; // Remove this line
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Create a temporary canvas to hold the image
            const tempCanvas = document.createElement('canvas');
            const tempCtx = tempCanvas.getContext('2d');
            tempCanvas.width = img.width;
            tempCanvas.height = img.height;
            tempCtx.drawImage(img, 0, 0);
            
            // Scale the image to fit the canvas while maintaining aspect ratio
            const scale = Math.min(intendedWidth / img.width, intendedHeight / img.height);
            const x = (intendedWidth - img.width * scale) / 2;
            const y = (intendedHeight - img.height * scale) / 2;
            
            // Draw the scaled image
            ctx.drawImage(tempCanvas, x, y, img.width * scale, img.height * scale);
            
            // Store the image data for later use
            window.turtleImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        }};
        img.src = '{combined_data}';
    '''

def toggle_visibility():
    ui.run_javascript('''
        const updateToolbar = () => {
            const isMobile = window.innerWidth < 640;
            document.querySelectorAll('.desktop-toolbar').forEach(el => {
                el.style.display = isMobile ? 'none' : 'flex';
            });
            document.querySelectorAll('.mobile-toolbar').forEach(el => {
                el.style.display = isMobile ? 'flex' : 'none';
            });
        };
        window.addEventListener('resize', updateToolbar);
        updateToolbar();
    ''')

def setup_zoom_pan():
    ui.run_javascript('''
        window.setupZoomPan = function() {
            const canvas = document.getElementById('turtle-canvas');
            const wrapper = document.getElementById('canvas-wrapper');
            const container = document.getElementById('canvas-container');
            if (!canvas || !wrapper || !container) return;
            
            // Get the intended dimensions from data attributes
            const intendedWidth = parseInt(wrapper.dataset.width || canvas.width);
            const intendedHeight = parseInt(wrapper.dataset.height || canvas.height);
            
            // Set wrapper dimensions to the intended geometry
            wrapper.style.width = `${intendedWidth}px`;
            wrapper.style.height = `${intendedHeight}px`;
            
            // Current state
            let scale = 1;
            let translateX = 0;
            let translateY = 0;
            let isDragging = false;
            let startX, startY;
            
            // Apply transformations to canvas
            function applyTransform() {
                requestAnimationFrame(() => {
                    // Combine scale and translation in a single transform
                    canvas.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
                    canvas.style.transformOrigin = 'top left';
                });
            }
            
            // Handle wheel events with passive: false to allow preventDefault
            const wheelHandler = function(e) {
                e.preventDefault();
                
                // Get the current mouse position relative to the wrapper
                const rect = wrapper.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                // Calculate the relative position (0 to 1)
                const relX = mouseX / rect.width;
                const relY = mouseY / rect.height;
                
                // Calculate the delta and new scale with limits
                const delta = e.deltaY > 0 ? 0.9 : 1.1;
                const newScale = Math.max(0.1, Math.min(3, scale * delta)); // Limit max zoom
                
                // Calculate the change in scale
                const scaleChange = newScale - scale;
                
                // Adjust translation to zoom towards the mouse position
                translateX -= (rect.width * scaleChange * relX);
                translateY -= (rect.height * scaleChange * relY);
                
                // Update scale
                scale = newScale;
                
                // Apply the transformations
                applyTransform();
            };
            
            // Add event listener with passive: false
            container.addEventListener('wheel', wheelHandler, { passive: false });
            
            // Pan with left mouse button
            canvas.addEventListener('mousedown', function(e) {
                if (e.button === 0) { // Left mouse button
                    e.preventDefault();
                    isDragging = true;
                    startX = e.clientX - translateX;
                    startY = e.clientY - translateY;
                    canvas.style.cursor = 'grabbing';
                }
            });
            
            document.addEventListener('mousemove', function(e) {
                if (isDragging) {
                    translateX = e.clientX - startX;
                    translateY = e.clientY - startY;
                    applyTransform();
                }
            });
            
            document.addEventListener('mouseup', function(e) {
                if (e.button === 0) {
                    isDragging = false;
                    canvas.style.cursor = 'default';
                }
            });
            
            // Set initial cursor
            canvas.style.cursor = 'default';
            
            // Initialize with proper dimensions
            applyTransform();
        };
    ''')

def add_canvas_interactivity():
    ui.run_javascript('''
        window.addCanvasInteractivity = function() {
            const canvas = document.getElementById('turtle-canvas');
            if (canvas) {
                canvas.addEventListener('contextmenu', function(event) {
                    event.preventDefault(); // Prevent the default context menu
                    
                    // Get the current transform
                    const style = window.getComputedStyle(canvas);
                    const transform = style.transform;
                    
                    // Default values if no transform
                    let scaleX = 1, scaleY = 1, translateX = 0, translateY = 0;
                    
                    if (transform && transform !== 'none') {
                        const matrix = transform.match(/matrix.*\\((.+)\\)/)[1].split(', ');
                        scaleX = parseFloat(matrix[0]);
                        scaleY = parseFloat(matrix[3]);
                        translateX = parseFloat(matrix[4]);
                        translateY = parseFloat(matrix[5]);
                    }
                    
                    // Calculate the position relative to the canvas without transform
                    const rect = canvas.getBoundingClientRect();
                    const x = (event.clientX - rect.left - translateX) / scaleX;
                    const y = (event.clientY - rect.top - translateY) / scaleY;
                    
                    // Get pixel data at click position
                    const ctx = canvas.getContext('2d', { willReadFrequently: true });
                    const pixel = ctx.getImageData(Math.floor(x), Math.floor(y), 1, 1).data;
                    
                    // Create a popup with pixel information
                    const popup = document.createElement('div');
                    popup.style.position = 'fixed';
                    popup.style.left = `${event.clientX}px`;
                    popup.style.top = `${event.clientY}px`;
                    popup.style.backgroundColor = 'rgba(0, 1, 0, 0.3)';
                    popup.style.border = '1px solid black';
                    popup.style.padding = '10px';
                    popup.style.zIndex = '1000';
                    popup.innerHTML = `
                        Position: (${Math.round(x)}, ${Math.round(y)})<br>
                        Color: RGB(${pixel[0]}, ${pixel[1]}, ${pixel[2]})<br>
                        Alpha: ${pixel[3]/255}
                    `;
                    document.body.appendChild(popup);
                    
                    // Remove popup after 2 seconds
                    setTimeout(() => {
                        document.body.removeChild(popup);
                    }, 2000);
                });
            }
        };
    ''')

copy_js = '''
    () => {
        const canvas = document.getElementById("turtle-canvas");
        if (canvas) {
            canvas.toBlob(function(blob) {
                const item = new ClipboardItem({ 'image/png': blob });
                navigator.clipboard.write([item]);
            });
        }
    }
'''
async def dummy():
    pass
async def show_loading(extra=dummy):
    with ui.element('div')\
        .classes('fixed inset-0 flex flex-col items-center justify-center bg-white z-50') as ee:
        ui.spinner(size='3em', type='grid').classes('text-primary')
        ui.label('Loading WebTurtle...').classes('text-2xl mt-4 text-gray-700')
        ui.label('Please wait a moment').classes('text-gray-500')
    await ui.context.client.connected(100)
    output = await extra()
    ee.delete()
    return output