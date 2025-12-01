from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="Logo & Shape Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogoRequest(BaseModel):
    shape: str = "none"
    text: str = ""
    color: str = "black"
    text_color: str = "white"
    scale: float = 1.0
    font_size: int = 24
    text_x: int = 150
    text_y: int = 350

SHAPES_LIBRARY = {
    "chair": lambda c="brown", s=1.0: f"""
push graphic-context
  stroke {c} 
  stroke-width {8*s}
  stroke-linecap round
  line {80*s},{50*s} {80*s},{200*s}
  line {220*s},{50*s} {220*s},{200*s}
  line {80*s},{80*s} {220*s},{80*s}
  line {60*s},{200*s} {240*s},{200*s}
  line {60*s},{250*s} {240*s},{250*s}
pop graphic-context""",
    
    "table": lambda c="oak", s=1.0: f"""
push graphic-context
  stroke {c}
  stroke-width {10*s}
  roundrectangle {50*s},{50*s} {250*s},{100*s} {10*s},{10*s}
  line {60*s},{100*s} {60*s},{180*s}
  line {240*s},{100*s} {240*s},{180*s}
pop graphic-context""",

    "car": lambda c="red", s=1.0: f"""
push graphic-context
  stroke {c}
  stroke-width {6*s}
  roundrectangle {50*s},{100*s} {250*s},{160*s} {20*s},{10*s}
  fill black
  circle {80*s},{170*s} {60*s},{170*s}
  circle {220*s},{170*s} {240*s},{170*s}
pop graphic-context""",

    "house": lambda c="brown", s=1.0: f"""
push graphic-context
  stroke {c}
  stroke-width {8*s}
  polygon {100*s},{150*s} {200*s},{150*s} {200*s},{250*s} {100*s},{250*s}
  polygon {80*s},{150*s} {160*s},{100*s} {240*s},{150*s}
  fill red
  rectangle {140*s},{200*s} {160*s},{250*s}
pop graphic-context""",

    "none": lambda c="transparent", s=1.0: ""
}

SHAPES_LIST = list(SHAPES_LIBRARY.keys())

# Create directory for generated images
GENERATED_DIR = "generated"
os.makedirs(GENERATED_DIR, exist_ok=True)

def generate_logo_cmds(request: LogoRequest) -> str:
    cmds = ""
    
    if request.shape != "none":
        cmds += SHAPES_LIBRARY[request.shape](request.color, request.scale)
    
    if request.text:
        cmds += f"""
push graphic-context
  font-size {request.font_size}
  fill {request.text_color}
  stroke black
  stroke-width 1
  text-undercolor rgba(0,0,0,0.1)
  text {request.text_x},{request.text_y} '{request.text}'
pop graphic-context"""
    
    return cmds

@app.post("/generate-logo")
def generate_logo(request: LogoRequest):
    if request.shape not in SHAPES_LIBRARY:
        return {"error": f"Shape not found. Available: {SHAPES_LIST}"}
    
    cmds = generate_logo_cmds(request)
    
    # Sanitize filename
    safe_text = "".join(c if c.isalnum() else "_" for c in request.text)
    filename = f"logo_{safe_text}_{request.shape}.png"
    filepath = os.path.join(GENERATED_DIR, filename)
    cmds_path = os.path.join(GENERATED_DIR, "cmds.txt")
    
    with open(cmds_path, 'w') as f:
        f.write(cmds)
    
    subprocess.run([
        'magick', '-size', '400x500', 'xc:white', 
        '-draw', f'@{cmds_path}', filepath
    ], check=True)
    
    return {"image": filename, "url": f"/images/{filename}", "request": request.dict()}

@app.get("/generate-logo-simple")
def generate_logo_simple(
    shape: str = "none",
    text: str = "LOGO",
    color: str = "black",
    text_color: str = "white",
    scale: float = 1.0,
    font_size: int = 32
):
    request = LogoRequest(
        shape=shape, text=text, color=color, text_color=text_color,
        scale=scale, font_size=font_size, text_x=200, text_y=400
    )
    return generate_logo(request)

@app.get("/shapes")
def list_shapes():
    return {"shapes": SHAPES_LIST, "total": len(SHAPES_LIST)}

@app.get("/images/{filename}")
def get_image(filename: str):
    filepath = os.path.join(GENERATED_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="image/png")
    return {"error": "Image not found"}

# Serve frontend at root
@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

# Mount static files (CSS, JS if you split them later)
app.mount("/static", StaticFiles(directory="static"), name="static")
