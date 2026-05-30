# image2prompt

A searchable static gallery of [GPT Image 2.0](https://openai.com) (GPT-4o native image gen) prompts and outputs.

Live: https://image2prompt.carlfung.dev

## Source

All cases are sourced from [EvoLinkAI/awesome-gpt-image-2-prompts](https://github.com/EvoLinkAI/awesome-gpt-image-2-prompts) (Apache 2.0). Each card preserves the original author handle and source link. Images are loaded directly from the upstream GitHub raw URLs — this gallery only re-renders the metadata in a browseable form.

## How it works

`build.py` clones the upstream repo into `.cache/`, parses every `cases/<category>.md` file, and inlines the structured data into `template.html` to produce `index.html`. The output is a single static HTML file with no build step or runtime dependencies — Vercel serves it directly.

## Develop

```bash
python3 build.py             # clones (or pulls) upstream and rebuilds index.html
python3 -m http.server 8765  # preview locally → http://localhost:8765
```

## Deploy

Connected to Vercel; pushing `main` redeploys. To force a rebuild after upstream adds new cases:

```bash
python3 build.py && git add index.html && git commit -m "data: refresh cases" && git push origin main
```
