# artist-tools

AI-powered publishing and creative tools for independent artists.

Built for [myerman.art](https://myerman.art) — a portfolio of Indigenous digital art by Tom Myer.

---

## Tools

| Command | What it does |
|---------|-------------|
| `publish-print` | Publish a new print: optimize images, generate AI copy, update site files |
| `extract-palette` | *(coming soon)* Extract a color palette from an artwork image |
| `next-painting` | *(coming soon)* Analyze a body of work and suggest what to paint next |
| `patreon-plan` | *(coming soon)* Generate a Patreon content calendar from recent work |

---

## publish-print

Automates adding a new print to the site: converts a source PNG into optimized web images, generates an artist statement and search tags via Claude, renders the print page HTML, and updates `search.json` and `feed.xml`.

### Install

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
export MYERMAN_ART_DIR=/path/to/myerman-art   # defaults to ~/Desktop/code/myerman-art
```

### Usage

```bash
publish-print \
  --file ~/Desktop/new-art-for-site/png-archive/abstract-9.png \
  --title "Abstract 9" \
  --sku ABSTRACT-9 \
  --size 12x12 \
  --prompt "swirling earth tones, geometric patterns suggesting movement and transformation"
```

**Options:**

| Flag | Required | Description |
|------|----------|-------------|
| `--file` / `-f` | ✓ | Source PNG file |
| `--title` / `-t` | ✓ | Print title |
| `--sku` / `-s` | ✓ | SKU (e.g. `ABSTRACT-9`) |
| `--size` / `-z` | ✓ | `12x12`, `12x9`, `9x12`, `18x12`, `4x6`, `4x4` |
| `--prompt` / `-p` | ✓ | Short artist note — fed to Claude for copy generation |
| `--slug` | | URL slug (derived from title if omitted) |
| `--price` | | Price in USD (default: 30) |
| `--dry-run` | | Preview what would happen without writing files |

### What it does

1. **Generates AI copy** — sends your prompt to Claude (Haiku) and gets back a 2–4 sentence artist statement in Tom's voice, plus search tags
2. **Optimizes images** — converts PNG → `display.jpg` (2400px), `thumb.jpg` (480×480 square), `hero.jpg` (1600×900) using macOS `sips`
3. **Renders print page** — fills `templates/print_page.html` and writes `prints/[slug]/index.html`
4. **Updates search.json** — prepends the new print to the site search index
5. **Updates feed.xml** — prepends a new RSS item
6. **Prints a report** — lists completed actions and remaining manual steps

### After running

The tool reminds you of the two manual steps that remain:
- Add the SKU to `SKU_TO_SIZE` in `js/cart.js`
- Add the slug to the 404 page's random print list

Then `git add . && git commit && git push` to publish.

---

## Requirements

- Python 3.10+
- macOS (uses `sips` for image processing — no ImageMagick needed)
- `ANTHROPIC_API_KEY` for AI copy generation

---

## Development

```bash
pip install -e .
python -m pytest tests/ -v
```
