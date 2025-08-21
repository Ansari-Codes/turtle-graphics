import math
import asyncio
from PIL import Image, ImageDraw
import io
import base64
from nicegui import ui
from contextlib import contextmanager
import html

class Turtle:
    def __init__(self, width =5000, height=5000):
        self.width = width
        self.height = height
        
        self.image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.x, self.y = 0, 0
        self.heading = 0
        self.pen_down = True
        self.pen_color = "black"
        self.pen_size = 1
        self.show_head = True
        
        # Aliases
        self.fd = self.forward
        self.bk = self.backward
        self.lt = self.left
        self.rt = self.right
        self.pc = self.pencolor
        self.pd = self.pendown
        self.pu = self.penup
        self.pz = self.pensize
        self.sp = self.setpos
        self.sh = self.setheading
        self.hm = self.home
        self.ht = self.hide
        self.st = self.show
        self.cs = self.clearscreen
        self.goto = self.sp
        
        # Fill handling
        self._fill_stack = []
        self._fill_color = self.pen_color
        self._stop_flag = False
        
    def _to_physical(self, x, y):
        """Convert logical coordinates to physical coordinates"""
        # Convert from logical (center origin, y up) to physical (top-left origin, y down)
        phys_x = (self.width / 2) + x
        phys_y = (self.height / 2) - y  # Flip y-axis
        return phys_x, phys_y
        
    def forward(self, dist):
        theta = math.radians(self.heading)
        new_x = self.x + dist * math.cos(theta)
        new_y = self.y + dist * math.sin(theta)  # Note: y increases in the direction of movement
        
        if self.pen_down:
            # Convert to physical coordinates
            start_x, start_y = self._to_physical(self.x, self.y)
            end_x, end_y = self._to_physical(new_x, new_y)
            
            # Calculate pen width with scaling
            pen_width = max(1, int(self.pen_size))
            
            self.draw.line(
                [(start_x, start_y), (end_x, end_y)],
                fill=self.pen_color,
                width=pen_width
            )
        
        self.x, self.y = new_x, new_y
        
        if self._fill_stack:
            self._fill_stack[-1]['path'].append((self.x, self.y))
            
    def backward(self, dist):
        self.forward(-dist)
        
    def left(self, angle):
        if angle: self.heading += angle
        return self.heading
        
    def right(self, angle):
        if angle: self.heading -= angle
        return self.heading
        
    def penup(self):
        self.pen_down = False
        
    def pendown(self):
        self.pen_down = True
        
    def isdown(self):
        return self.pen_down
        
    def pencolor(self, clr=None):
        if clr is not None:
            self.pen_color = clr
        return self.pen_color
        
    def fillcolor(self, clr=None):
        if clr is not None:
            self._fill_color = clr
        return self._fill_color
        
    def pensize(self, sz=None):
        if sz is not None and sz >= 0:
            self.pen_size = sz
        return self.pen_size
        
    def clearscreen(self):
        # Create image with transparent background
        self.image = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.x, self.y = 0, 0  # Fixed: initialized as tuple with 3 values
        self.heading = 0
        
    def setpos(self, x, y):
        self.x, self.y = x, y  # Logical coordinates
        
    def setheading(self, angle):
        self.heading = angle
        
    def home(self):
        self.setpos(0, 0)
        self.setheading(0)
        
    def circle(self, radius):
        if not radius:
            raise ValueError("circle(radius) requires a non-zero radius")
        center_x, center_y = self._to_physical(self.x, self.y)
        
        # Calculate radius with scaling
        phys_radius = radius
        
        bbox = [
            center_x - phys_radius, center_y - phys_radius,
            center_x + phys_radius, center_y + phys_radius
        ]
        
        # Calculate pen width with scaling
        pen_width = max(1, int(self.pen_size))
        
        self.draw.ellipse(
            bbox,
            outline=self.pen_color,
            width=pen_width
        )
        
    def dot(self, size=5):
        phys_x, phys_y = self._to_physical(self.x, self.y)
        phys_size = size
        self.draw.ellipse(
            [phys_x - phys_size, phys_y - phys_size, phys_x + phys_size, phys_y + phys_size],
            fill=self.pen_color
        )
        
    def show(self):
        self.show_head = True
        
    def hide(self):
        self.show_head = False
    
    def begin_fill(self, layer=None):
        if layer is None:
            layer = len(self._fill_stack)
        self._fill_stack.append({
            'color': self._fill_color,
            'path': [(self.x, self.y)],
            'layer': layer
        })
    
    def end_fill(self):
        if self._fill_stack:
            fill = self._fill_stack.pop()
            if len(fill['path']) > 2:
                # Convert all points to physical coordinates
                phys_points = [self._to_physical(x, y) for x, y in fill['path']]
                # Draw filled polygon on PIL image
                self.draw.polygon(phys_points, fill=fill['color'])
    
    @contextmanager
    def filling(self, color=None, layer=None):
        if color:
            self.fillcolor(color)
        self.begin_fill(layer)
        try:
            yield
        finally:
            self.end_fill()
    
    def stop(self):
        self._stop_flag = True
        
    def _get_image_data(self):
        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
        
    def write(self, text='', **kwargs):
        phys_x, phys_y = self._to_physical(self.x, self.y)
        text = str(text)
        attributes = {
            'xy': (phys_x, phys_y),
            'text': text,
            'fill': self.pen_color,
        }
        if 'font' in kwargs:
            try:
                from PIL import ImageFont
                font_size = int(kwargs.get('font_size', 12))
                attributes['font'] = ImageFont.truetype(kwargs['font'], font_size)
            except:
                pass
        if 'text_anchor' in kwargs:
            anchor_map = {
                'start': 'lt',
                'middle': 'mt',
                'end': 'rt'
            }
            attributes['anchor'] = anchor_map.get(kwargs['text_anchor'], 'lt')
        self.draw.text(**attributes)
