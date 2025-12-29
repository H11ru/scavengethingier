# main.py
import pygame
import random
import os
import json

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

def generate_chunk(cx, cy):
    """Fake trash block generator"""
    blocks = []
    for x in range(CHUNK_SIZE):
        for y in range(CHUNK_SIZE):
            if random.random() < 0.2:
                blocks.append((cx * CHUNK_SIZE + x, cy * CHUNK_SIZE + y))
    return blocks

def chunk_filename(cx, cy):
    dirpath = os.path.join(os.getcwd(), "chunks")
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    return os.path.join(dirpath, f"{cx}_{cy}.json")

def save_chunk(cx, cy, blocks):
    fn = chunk_filename(cx, cy)
    # convert tuples to lists for JSON
    data = [[int(x), int(y)] for x, y in blocks]
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
        # convert lists back to tuples
        return [(int(x), int(y)) for x, y in data]
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

# Main loop
gravity = 1
camera = type('Camera', (), {'x': 0, 'y': 0})()
run = True
font = pygame.font.SysFont("Arial", 18)
while run:
    screen.fill((30, 30, 30))
    load_chunks_near_player()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            run = False

    keys = pygame.key.get_pressed()
    vel[0] = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 5
    if keys[pygame.K_SPACE] and on_ground:
        vel[1] = -18
        on_ground = False


    vel[1] += gravity

    # Horizontal movement and collision
    player.x += vel[0]
    for chunk in loaded_chunks.values():
        for tx, ty in chunk:
            block_rect = pygame.Rect(tx * TILESIZE, ty * TILESIZE, TILESIZE, TILESIZE)
            if player.colliderect(block_rect):
                if vel[0] > 0 and player.right - vel[0] <= block_rect.left:
                    player.right = block_rect.left
                    vel[0] = 0
                elif vel[0] < 0 and player.left - vel[0] >= block_rect.right:
                    player.left = block_rect.right
                    vel[0] = 0

    # Vertical movement and collision
    player.y += vel[1]
    on_ground = False
    for chunk in loaded_chunks.values():
        for tx, ty in chunk:
            block_rect = pygame.Rect(tx * TILESIZE, ty * TILESIZE, TILESIZE, TILESIZE)
            if player.colliderect(block_rect):
                if vel[1] > 0 and player.bottom - vel[1] <= block_rect.top:
                    player.bottom = block_rect.top
                    vel[1] = 0
                    on_ground = True
                elif vel[1] < 0 and player.top - vel[1] >= block_rect.bottom:
                    player.top = block_rect.bottom
                    vel[1] = 0

    # Remove invisible floor: no more if player.bottom >= HEIGHT
    # death area
    if player.bottom >= 500:
        print("you deid")
        raise RuntimeError("perished")

    # Smooth camera follow
    camera.x += (player.centerx - camera.x) * 0.1
    camera.y += (player.centery - camera.y) * 0.1

    # Draw player
    pygame.draw.rect(screen, (200, 200, 50), (player.x - camera.x + WIDTH//2, player.y - camera.y + HEIGHT//2, player.width, player.height))

    # Draw trash
    for chunk in loaded_chunks.values():
        for tx, ty in chunk:
            bx = tx * TILESIZE
            by = ty * TILESIZE
            pygame.draw.rect(screen, (100, 80, 60), (bx - camera.x + WIDTH//2, by - camera.y + HEIGHT//2, TILESIZE, TILESIZE))
    # FPS
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, (255, 255, 255))
    screen.blit(fps_text, (10, 10)) 

    pygame.display.flip()
    
    clock.tick(60)

pygame.quit()
