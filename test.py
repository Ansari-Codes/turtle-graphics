from PIL import Image, ImageDraw

class TurtlePIL:
    def __init__(self, width=800, height=800, bg="white"):
        self.image = Image.new("RGB", (width, height), bg)
        self.draw = ImageDraw.Draw(self.image)
        self.x, self.y = width/2, height/2
        self.heading = 0
        self.pen_down = True
        self.pen_color = "black"
        self.pen_size = 2
    
    def forward(self, dist):
        import math
        theta = math.radians(self.heading)
        new_x = self.x + dist * math.cos(theta)
        new_y = self.y - dist * math.sin(theta)
        if self.pen_down:
            self.draw.line(
                [(self.x, self.y), (new_x, new_y)],
                fill=self.pen_color,
                width=self.pen_size
            )
        self.x, self.y = new_x, new_y
    
    def backward(self, dist):
        self.forward(-dist)
    
    def left(self, angle):
        self.heading += angle
    
    def right(self, angle):
        self.heading -= angle
    
    def penup(self):
        self.pen_down = False
    
    def pendown(self):
        self.pen_down = True
    
    def save(self, filename):
        self.image.save(filename, "PNG")
t = TurtlePIL()
for _ in range(36):
    t.forward(100)
    t.backward(100)
    t.left(10)
t.save("fractal.png")
