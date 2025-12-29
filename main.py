# main.py
import pygame
import random
import math
import os
import json

# --- Trash Types ---
TRASH_TYPES = [
    {
        "id": 0,
        "name": "Organic wadte",
        "color": (34, 139, 34), # gween
        "texture": "textures/organic.png",
    },
    {
        "id": 1,
        "name": "Plastic junk",
        "color": (70, 130, 180), # bwue
        "texture": "textures/plastic.png",
    },
    {
        "id": 2,
        "name": "Metal scrap",
        "color": (192, 192, 192), # silwer
        "texture": "textures/metal.png",
    },
    {
        "id": 3,
        "name": "Glass shards",
        "color": (135, 206, 235), # wight bwue
        "texture": "textures/glass.png",
    },
    {
        "id": 4,
        "name": "Puddle of mystery fluid",
        "color": (138, 43, 226), # puwple
        "texture": "textures/mystery_fluid.png",
    }
]
ORGANIC_WADTE = 0
PLASTIC_JUNK = 1
METAL_SCRAP = 2
GLASS_SHARDS = 3
MYSTERY_FLUID = 4


TRASH_TYPE_BY_ID = {t["id"]: t for t in TRASH_TYPES}

def get_trash_type(trash_id):
    return TRASH_TYPE_BY_ID.get(trash_id, TRASH_TYPES[0])

def load_trash_texture(trash_type):
    path = trash_type["texture"]
    if os.path.isfile(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except Exception:
            pass
    return None

TRASH_TEXTURES = {t["id"]: load_trash_texture(t) for t in TRASH_TYPES}

pygame.init()

# Screen
WIDTH, HEIGHT = 800, 600
TILESIZE = 40
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("Infinite Trash Heap")

# Player
player = pygame.Rect(WIDTH // 2, HEIGHT // 2, TILESIZE, TILESIZE * 2)
vel = [0, 0]
on_ground = False

# World data
CHUNK_SIZE = 8  # in tiles
loaded_chunks = {}
hysteresis_margin = 2  # how many chunks extra to keep loaded

def chunk_key(cx, cy):
    return f"{cx}_{cy}"


# --- Simple Perlin-like noise for ground generation ---
def lerp(a, b, t):
    return a + t * (b - a)

def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def grad(hash, x):
    return (hash & 1) * 2 - 1 * x

def hash_coords(x):
    # Simple hash for repeatability
    return int((math.sin(x * 127.1) * 43758.5453) % 256)

def perlin1d(x):
    x0 = int(math.floor(x))
    x1 = x0 + 1
    sx = fade(x - x0)
    n0 = grad(hash_coords(x0), x - x0)
    n1 = grad(hash_coords(x1), x - x1)
    return lerp(n0, n1, sx)

def get_ground_height(tx):
    # tx: world x in tiles
    # Adjust scale and offset for worldgen
    base = 10  # base ground height in tiles
    amp = 5    # amplitude
    freq = 0.08  # frequency
    noise = perlin1d(tx * freq)
    return int(base + amp * noise)

def generate_chunk(cx, cy):
    """Noise-based ground generator with trash types"""
    blocks = []
    for x in range(CHUNK_SIZE):
        tx = cx * CHUNK_SIZE + x
        ground_y = get_ground_height(tx)
        for y in range(CHUNK_SIZE):
            ty = cy * CHUNK_SIZE + y
            if ty >= ground_y:
                # Assign trash type randomly
                trash_id = random.randint(0, len(TRASH_TYPES) - 1)
                blocks.append((tx, ty, trash_id))
    return blocks

def chunk_filename(cx, cy):
    dirpath = os.path.join(os.getcwd(), "chunks")
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    return os.path.join(dirpath, f"{cx}_{cy}.json")

def save_chunk(cx, cy, blocks):
    fn = chunk_filename(cx, cy)
    # convert tuples to lists for JSON
    data = [[int(x), int(y), int(tid)] for x, y, tid in blocks]
    try:
        with open(fn, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_chunk(cx, cy):
    fn = chunk_filename(cx, cy)
    if not os.path.isfile(fn):
        return None
    try:
        with open(fn, "r") as f:
            data = json.load(f)
        # convert lists back to tuples (with trash id)
        return [(int(x), int(y), int(tid) if len(row) > 2 else 0) for row in data for x, y, *tid in [row]]
    except Exception:
        return None

def save_all_chunks():
    for key, chunk in loaded_chunks.items():
        try:
            cx, cy = map(int, key.split("_"))
        except Exception:
            continue
        save_chunk(cx, cy, chunk)

def get_visible_chunks(px, py):
    cx = px // (CHUNK_SIZE * TILESIZE)
    cy = py // (CHUNK_SIZE * TILESIZE)
    return [
        (cx + dx, cy + dy)
        for dx in range(-1 - hysteresis_margin, 2 + hysteresis_margin)
        for dy in range(-1 - hysteresis_margin, 2 + hysteresis_margin)
    ]

def load_chunks_near_player():
    global loaded_chunks
    visible = get_visible_chunks(player.centerx, player.centery)
    visible_keys = set(chunk_key(cx, cy) for cx, cy in visible)
    
    # Load new
    for cx, cy in visible:
        key = chunk_key(cx, cy)
        if key not in loaded_chunks:
            # try load from disk first
            loaded = load_chunk(cx, cy)
            if loaded is not None:
                loaded_chunks[key] = loaded
            else:
                loaded_chunks[key] = generate_chunk(cx, cy)

    # Unload far
    for key in list(loaded_chunks.keys()):
        if key not in visible_keys:
            # persist chunk before unloading
            try:
                ucx, ucy = map(int, key.split("_"))
                save_chunk(ucx, ucy, loaded_chunks[key])
            except Exception:
                pass
            del loaded_chunks[key]

 # --- Inventory system ---
inventory = {tid: 0 for tid in TRASH_TYPE_BY_ID}
pending_inventory = []

# Main loop
gravity = 1
camera = type('Camera', (), {'x': 0, 'y': 0})()
run = True
font = pygame.font.SysFont("Arial", 18)
SOLID = {ORGANIC_WADTE, METAL_SCRAP, GLASS_SHARDS, PLASTIC_JUNK}
TOXIC = {MYSTERY_FLUID}
health_points = 100
prev_health = 0
aaaaaaa = 0
while run:
    screen.fill((30, 30, 30))
    load_chunks_near_player()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    keys = pygame.key.get_pressed()
    # detect
    l = keys[pygame.K_LEFT] or keys[pygame.K_a]
    r = keys[pygame.K_RIGHT] or keys[pygame.K_d]
    t = r - l
    # player goes spe
    #vel[0] = t * 8 # BAD
    vel[0] += t * 2
    # friction
    vel[0] *= 0.8
    if keys[pygame.K_SPACE] and on_ground:
        vel[1] = -18
        on_ground = False


    vel[1] += gravity


    # --- Improved axis-by-axis movement and collision ---
    # Horizontal movement
    player.x += int(round(vel[0]))
    for chunk in loaded_chunks.values():
        for tx, ty, tiletype in chunk:
            block_rect = pygame.Rect(tx * TILESIZE, ty * TILESIZE, TILESIZE, TILESIZE)
            if tiletype not in SOLID:
                continue
            if player.colliderect(block_rect):
                if vel[0] > 0:
                    player.right = block_rect.left
                elif vel[0] < 0:
                    player.left = block_rect.right
                vel[0] = 0

    # Vertical movement
    player.y += int(round(vel[1]))
    on_ground = False
    for chunk in loaded_chunks.values():
        for tx, ty, tiletype in chunk:
            block_rect = pygame.Rect(tx * TILESIZE, ty * TILESIZE, TILESIZE, TILESIZE)
            if tiletype not in SOLID:
                continue
            if player.colliderect(block_rect):
                if vel[1] > 0:
                    player.bottom = block_rect.top
                    on_ground = True
                elif vel[1] < 0:
                    player.top = block_rect.bottom
                vel[1] = 0

    # toxic is fangerous
    for chunk in loaded_chunks.values():
        for tx, ty, tiletype in chunk:
            if tiletype not in TOXIC:
                continue
            block_rect = pygame.Rect(tx * TILESIZE, ty * TILESIZE, TILESIZE, TILESIZE)
            if player.colliderect(block_rect):
                health_points -= 1

    if player.bottom >= 1000:
        health_points -= 5000000000
    
    # Remove invisible floor: no more if player.bottom >= HEIGHT
    # death area
    if prev_health > health_points:
        aaaaaaa = 30
    prev_health = health_points
    if aaaaaaa > 0:
        aaaaaaa -= 1
    else:
        health_points += .1
    health_points = min(health_points, 100)
    if health_points <= 0:
        print("you deid")
        raise RuntimeError("perished")
    # draw red line
    pygame.draw.line(screen, (255, 0, 0), (0, 1000 - camera.y + HEIGHT//2), (WIDTH, 1000 - camera.y + HEIGHT//2), 2)


    # Smooth camera follow
    camera.x += (player.centerx - camera.x) * 0.1
    camera.y += (player.centery - camera.y) * 0.1

    # Draw trash
    mouse_pos = pygame.mouse.get_pos()
    hovered_trash = None
    for chunk in loaded_chunks.values():
        for tx, ty, tid in chunk:
            bx = tx * TILESIZE
            by = ty * TILESIZE
            draw_rect = pygame.Rect(bx - camera.x + WIDTH//2, by - camera.y + HEIGHT//2, TILESIZE, TILESIZE)
            trash_type = get_trash_type(tid)
            tex = TRASH_TEXTURES.get(tid)
            if tex:
                screen.blit(pygame.transform.scale(tex, (TILESIZE, TILESIZE)), draw_rect)
            else:
                #pygame.draw.rect(screen, trash_type["color"], draw_rect)
                if tid == 4:
                    # effect: fills bottom 2/5 of tile and sine wiggles
                    fill_height = TILESIZE * 2 // 5
                    offset = int(5 * math.sin(pygame.time.get_ticks() / 200 + (tx + ty)))
                    fill_rect = pygame.Rect(draw_rect.x, draw_rect.y + TILESIZE - fill_height - offset, TILESIZE, fill_height + offset)
                    pygame.draw.rect(screen, trash_type["color"], fill_rect)
                else:
                    pygame.draw.rect(screen, trash_type["color"], draw_rect)
            # Mouse hover for name
            if draw_rect.collidepoint(mouse_pos):
                hovered_trash = trash_type["name"]

    # Draw player
    pygame.draw.rect(screen, (200, 200, 50), (player.x - camera.x + WIDTH//2, player.y - camera.y + HEIGHT//2, player.width, player.height))
    # temporary helbtj BAR_: outframe is black, background is dark ged, bar is green, and theres a white text that shows hp slash hep
    #hp_text = font.render(f"HP: {health_points}", True, (255, 255, 255))
    hp_bar_width = 200
    hp_bar_height = 20
    hp_bar_x = WIDTH - hp_bar_width - 20
    hp_bar_y = 20
    # outframe
    pygame.draw.rect(screen, (0, 0, 0), (hp_bar_x - 2, hp_bar_y - 2, hp_bar_width + 4, hp_bar_height + 4))
    # background
    pygame.draw.rect(screen, (50, 50, 50), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
    # health bar
    current_hp_width = int(hp_bar_width * (health_points / 100))
    pygame.draw.rect(screen, (0, 255, 0), (hp_bar_x, hp_bar_y, current_hp_width, hp_bar_height))
    # text
    health_pointsc = f"{int(health_points)}/100"
    ahp_text = font.render(f"HP: {health_pointsc}", True, (0, 0, 0))
    hp_text = font.render(f"HP: {health_pointsc}", True, (255, 255, 255))
    screen.blit(ahp_text, (hp_bar_x + hp_bar_width // 2 - ahp_text.get_width() // 2 + 1, hp_bar_y + hp_bar_height // 2 - ahp_text.get_height() // 2 + 1))
    screen.blit(ahp_text, (hp_bar_x + hp_bar_width // 2 - ahp_text.get_width() // 2 - 1, hp_bar_y + hp_bar_height // 2 - ahp_text.get_height() // 2 - 1))
    screen.blit(ahp_text, (hp_bar_x + hp_bar_width // 2 - ahp_text.get_width() // 2 + 1, hp_bar_y + hp_bar_height // 2 - ahp_text.get_height() // 2 - 1))
    screen.blit(ahp_text, (hp_bar_x + hp_bar_width // 2 - ahp_text.get_width() // 2 - 1, hp_bar_y + hp_bar_height // 2 - ahp_text.get_height() // 2 + 1))
    screen.blit(hp_text, (hp_bar_x + hp_bar_width // 2 - hp_text.get_width() // 2, hp_bar_y + hp_bar_height // 2 - hp_text.get_height() // 2))


    # Show trash name if hovered
    if hovered_trash:
        name_text = font.render(hovered_trash, True, (255,255,255))
        screen.blit(name_text, (mouse_pos[0]+10, mouse_pos[1]-10))

    # Trash destruction (mouse click)
    if pygame.mouse.get_pressed()[0]:
        mx, my = mouse_pos
        world_x = int((mx - WIDTH//2 + camera.x) // TILESIZE)
        world_y = int((my - HEIGHT//2 + camera.y) // TILESIZE)
        for chunk in loaded_chunks.values():
            for i, (tx, ty, tid) in enumerate(chunk):
                if tx == world_x and ty == world_y:
                    # Add destroyed trash to inventory (to be implemented)
                    if 'pending_inventory' not in globals():
                        global pending_inventory
                        pending_inventory = []
                    pending_inventory.append(tid)
                    del chunk[i]
                    break

    # --- Inventory collection ---
    if pending_inventory:
        for tid in pending_inventory:
            if tid in inventory:
                inventory[tid] += 1
            else:
                inventory[tid] = 1
        pending_inventory.clear()

    # Inventory display
    inv_x = 10
    inv_y = 40
    for tid, count in inventory.items():
        trash_type = get_trash_type(tid)
        name = trash_type["name"]
        color = trash_type["color"]
        inv_text = font.render(f"{name}: {count}", True, color)
        screen.blit(inv_text, (inv_x, inv_y))
        inv_y += 22

    # FPS
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (255, 255, 255))
    screen.blit(fps_text, (10, 10)) 

    pygame.display.flip()
    
    clock.tick(60)

pygame.quit()
