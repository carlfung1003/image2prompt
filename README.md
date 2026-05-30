# image2prompt

A searchable static gallery of [GPT Image 2.0](https://openai.com/index/introducing-4o-image-generation/) prompts and outputs, merging the best public prompt libraries into one browseable view.

**Live:** https://image2prompt.carlfung.dev · **Repo:** https://github.com/carlfung1003/image2prompt

Filter by source, filter by category, search across titles + authors + prompt text, click any card for a full-size view with copy-to-clipboard.

## Sources

Cases are pulled from multiple upstream repos and merged together. Each card preserves its original author handle, source link, and shows a small badge for which upstream it came from. Images are loaded directly from the upstream GitHub raw URLs — this gallery only re-renders the metadata in a browseable form.

| Source | License | Format | Approx. cases |
|---|---|---|---|
| [EvoLinkAI/awesome-gpt-image-2-prompts](https://github.com/EvoLinkAI/awesome-gpt-image-2-prompts) | CC0-1.0 | `cases/<category>.md`, daily batch curation | ~530 |
| [ZeroLu/awesome-gpt-image](https://github.com/ZeroLu/awesome-gpt-image) | MIT | `README.md` with `##` sections + `###` cases, X/Twitter-sourced | ~70 |
| `cases-local/<category>.md` | (yours) | Same as EvoLink format | grows as you add |

## How it works

```
build.py                       template.html
  ├─ clone .cache/evolink         └─ HTML/CSS/JS shell with
  ├─ clone .cache/zerolu             __CASES_JSON__ placeholder
  ├─ run each source parser
  ├─ merge + tag with `source`
  └─ inject into template ─────→ index.html  (single static file, served by Vercel)
```

Each source has its own parser function in `build.py`. New sources plug in by appending to the `SOURCES` list:

```python
SOURCES = [
    {"id": "evolinkai", "repo_url": "...", "dir": "...", "parser": parse_evolink},
    {"id": "zerolu",    "repo_url": "...", "dir": "...", "parser": parse_zerolu},
]
```

The parser returns a list of dicts shaped like:

```python
{
  "id": "<source>-<category>-<n>",   # unique across all sources
  "source": "evolinkai" | "zerolu" | "local",
  "category": "poster" | "portrait" | ...,
  "num": 1, "title": "...", "image": "https://...",
  "prompt": "...", "author": "...", "author_url": "...", "source_url": "...",
}
```

## Categories

7 from EvoLink + 5 new ones introduced by ZeroLu, merged where they overlap:

- `poster`, `portrait`, `character`, `ad-creative`, `ecommerce`, `comparison`, `ui`
- `photography`, `game`, `video`, `infographics`, `image-editing`

Each category has its own badge color in `template.html` (`.badge.<category>`).

## Develop

```bash
git clone https://github.com/carlfung1003/image2prompt.git
cd image2prompt
python3 build.py             # clones upstreams into .cache/ and rebuilds index.html
python3 -m http.server 8765  # preview locally → http://localhost:8765
```

Build options:

```bash
python3 build.py                       # all sources
python3 build.py --only evolinkai      # one source (fast iteration)
python3 build.py --only evolinkai,zerolu
```

## Add a local case

Drop a case into `cases-local/<category>.md` using the EvoLink format:

```markdown
### Case 1: [My Title](https://source-url)

by [@author](https://x.com/author)

<img src="https://path-to-image.png" />

**Prompt:**

```
your prompt text here
```
```

Then `python3 build.py` and your card shows up with a violet `LOCAL` badge.

## Refresh + deploy

```bash
bash refresh.sh
```

Pulls all upstreams, rebuilds, deploys to Vercel prod. Output is appended to `.refresh.log`. A `launchd` plist (`dev.image2prompt.refresh.plist`) can run this on a schedule — load with `launchctl load`.

## Project layout

```
build.py                  Multi-source build script
template.html             HTML/CSS/JS shell
index.html                Built output (committed so Vercel can serve directly)
cases-local/              Your own local case markdown files
refresh.sh                Pull + rebuild + deploy
.cache/                   Upstream clones (gitignored)
LICENSE-upstream          Copy of EvoLink's CC0-1.0
vercel.json               Vercel config
```

## License

The build pipeline itself (this repo's code) is MIT.

Prompt content comes from the upstream repos and remains under their respective licenses (EvoLinkAI: CC0-1.0, ZeroLu: MIT). Each card preserves author attribution and a link back to the original source.
