import math
import asyncio
from PIL import Image, ImageDraw, ImageFilter
import io
import base64
from nicegui import ui
from contextlib import contextmanager
import html

class Turtle:
    def __init__(self, width=5000, height=5000, supersample=2):
        self.supersample = supersample
        self.width = width
        self.height = height
        self.image = Image.new('RGBA', (self.width * self.supersample, self.height * self.supersample), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.x, self.y = 0, 0
        self.heading = 0
        self.pen_down = True
        self.pen_color = "black"
        self.pen_size = 1
        self.show_head = True
        
        # Track the bounding box of all drawn points
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        
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
        
    def _update_bounding_box(self, x, y):
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y)
    
    def _to_physical(self, x, y):
        phys_x = ((self.width / 2) + x) * self.supersample
        phys_y = ((self.height / 2) - y) * self.supersample
        return phys_x, phys_y
    
    def forward(self, dist):
        theta = math.radians(self.heading)
        new_x = self.x + dist * math.cos(theta)
        new_y = self.y + dist * math.sin(theta)
        if self.pen_down:
            start_x, start_y = self._to_physical(self.x, self.y)
            end_x, end_y = self._to_physical(new_x, new_y)
            pen_width = max(1, int(self.pen_size * self.supersample))
            self.draw.line(
                [(start_x, start_y), (end_x, end_y)],
                fill=self.pen_color,
                width=pen_width
            )
            # Update bounding box with both start and end points
            self._update_bounding_box(self.x, self.y)
            self._update_bounding_box(new_x, new_y)
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
        self.image = Image.new('RGBA', (self.width * self.supersample, self.height * self.supersample), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.x, self.y = 0, 0
        self.heading = 0
        # Reset bounding box
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
    
    def setpos(self, x, y):
        self.x, self.y = x, y
        self._update_bounding_box(x, y)
    
    def setheading(self, angle):
        self.heading = angle
    
    def home(self):
        self.setpos(0, 0)
        self.setheading(0)
    
    def circle(self, radius):
        if not radius:
            raise ValueError("circle(radius) requires a non-zero radius")
        center_x, center_y = self._to_physical(self.x, self.y)
        phys_radius = radius * self.supersample
        bbox = [
            center_x - phys_radius, center_y - phys_radius,
            center_x + phys_radius, center_y + phys_radius
        ]
        pen_width = max(1, int(self.pen_size * self.supersample))
        self.draw.ellipse(
            bbox,
            outline=self.pen_color,
            width=pen_width
        )
        # Update bounding box with the circle's extents
        self._update_bounding_box(self.x - radius, self.y - radius)
        self._update_bounding_box(self.x + radius, self.y + radius)
    
    def dot(self, size=5):
        phys_x, phys_y = self._to_physical(self.x, self.y)
        phys_size = size * self.supersample
        self.draw.ellipse(
            [phys_x - phys_size, phys_y - phys_size, phys_x + phys_size, phys_y + phys_size],
            fill=self.pen_color
        )
        # Update bounding box with the dot's extents
        self._update_bounding_box(self.x - size/self.supersample, self.y - size/self.supersample)
        self._update_bounding_box(self.x + size/self.supersample, self.y + size/self.supersample)
    
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
                phys_points = [self._to_physical(x, y) for x, y in fill['path']]
                self.draw.polygon(phys_points, fill=fill['color'])
                # Update bounding box with all points in the fill path
                for x, y in fill['path']:
                    self._update_bounding_box(x, y)
    
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
        # Downscale for anti-aliasing
        if self.supersample > 1:
            final_image = self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        else:
            final_image = self.image
        final_image.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Calculate the maximum extent from center in x and y directions
        max_extent_x = max(abs(self.min_x), abs(self.max_x))
        max_extent_y = max(abs(self.min_y), abs(self.max_y))
        
        # Return both the image data and the maximum extents
        return f"data:image/png;base64,{img_str}", (max_extent_x, max_extent_y)
    
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
                font_size = int(kwargs.get('font_size', 12)) * self.supersample
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
        self._update_bounding_box(self.x, self.y)