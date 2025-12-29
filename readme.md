# 🗑️ Scavengethingier

Welcome to **Scavengethingier** – the infinite trash heap adventure where the world **never ends**, only piles higher and deeper!

## 🔧 Features

- Procedural infinite trash chunks
- Walk left, right, and jump on garbage
- Break trash with physics (eventually™)
- Hysteresis-powered chunk loading so you don’t wiggle the world to death
- Saving + loading (soon!)
- Kururin-compatible
- Optimized for minty chaos 🍃

## 🌀 How it Works

The world is split into **chunks**, and only chunks near the player are:
- 🪄 Generated (on first entry)
- 📦 Saved (eventually)
- 🧹 Unloaded (when far)

This keeps memory usage low and trash pile HIGH.

## 🕹️ Controls

| Key     | Action         |
|---------|----------------|
| ← / →   | Move left/right |
| SPACE   | Jump           |
| ESC     | Exit (if rage-quitting trash) |

## 🚧 Roadmap

- [x] Player movement
- [x] Procedural chunk generator
- [ ] Saving/loading to disk (important)
- [ ] Trash breaking
