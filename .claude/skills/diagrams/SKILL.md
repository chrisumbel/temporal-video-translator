---
name: diagrams
description: Generate or refresh the project architecture SVGs (temporal.svg, infra.svg, flow.svg) from the current code, chart, and Azure layout. Use when the user asks to create or update architecture/flow diagrams. Optional arg: temporal | infra | flow | all (default all).
---

# Architecture diagram generator

Produce hand-authored SVG diagrams in `docs/diagrams/`. Never invent
architecture from memory: read the sources of truth below first, every time,
because queues, activities, pools, and Azure resources change.

## Sources of truth (read before drawing)

- `workflows.py` — step order, which steps run in parallel (asyncio.gather),
  which task queue each activity is routed to, retry/timeout posture.
- `activities.py` + `worker.py` — the full activity list and which worker pool
  (WORKER_QUEUES role) hosts each one, plus per-pool concurrency caps.
- `shared.py` — queue names and cap defaults.
- `helm/temporal-video-translator/values.yaml` — deployments, replica counts,
  images, the in-cluster temporal server (auto-setup + postgres + UI), the
  public LoadBalancer + DNS label, and non-secret env.
- `.env.example` — the Azure resources (storage account/containers, Video
  Indexer, Translator, OpenAI deployment).
- `Makefile` — image names/registry.
- For infra.svg, optionally confirm live state: `az resource list
  --resource-group temporal-video-translator --output table` and
  `kubectl get nodes` / `get deploy` (context `tvt-aks`).

## The three diagrams

### temporal.svg — Temporal architecture
Boxes and connections for: clients (start.py / test.sh with API key), the
Temporal server stack (frontend service + public LB/DNS, postgres, web UI),
every task queue (with its concurrency cap), and the worker deployments
(replicas, image variant, which queues each polls, which activities each
hosts). Group activities under the pool that registers them.

### infra.svg — cloud + deliverables
One outer box for the Azure resource group containing: AKS cluster (node
pools with VM sizes; inside it the kube deployments), ACR (both image repos),
the storage account with every container labeled public or private, the three
AI services (Video Indexer, Translator, OpenAI + deployment name), the
service principal, and the public IP/DNS entry point. Show the deliverable
software (worker images, helm chart) and key data flows: ACR -> AKS image
pulls, workers -> AI services and storage, client -> LB -> temporal frontend.

### flow.svg — workflow execution order
A top-to-bottom flowchart of one VideoTranslatorWorkflow run. Sequential
steps in a single column; parallel work drawn side-by-side inside a visually
distinct "parallel" region with fork/join points, so order and concurrency
are obvious at a glance. Include the queue each activity runs on and end with
the returned result/artifacts (JSON, PDF, screenshot URLs).

## Style (keep the three visually consistent)

- Canvas ~1200-1350 wide, height as needed; `font-family="Helvetica, Arial,
  sans-serif"`; background white.
- Palette: headers/borders `#16324f`, accents/arrows `#2a6fb0`, box fills
  `#eef3f8` (light blue) and `#f7f9fb` (near-white), queue/cap highlights
  `#b7791f` on `#fdf3e3`, public-access tags green `#1c7c43` on `#e6f4ea`,
  private tags gray `#667`.
- Rounded rects (`rx="8"`), 1.5px borders, one shared `<marker>` arrowhead.
- Title + one-line subtitle at top-left; small "generated from code on
  <date>" note at bottom-right.
- Text must not overflow boxes; size boxes generously.

## Process

1. Read the sources of truth; list the current queues, activities, pools,
   replicas, and Azure resources.
2. Author each requested SVG by hand into `docs/diagrams/`.
3. Validate each file parses: `python3 -c "import xml.dom.minidom,sys;
   xml.dom.minidom.parse(sys.argv[1])" docs/diagrams/<name>.svg`.
4. Rasterize for a visual check and inspect the PNG for overlaps and
   overflowing labels; fix before finishing. Use cairosvg (pip install
   cairosvg): `python3 -c "import cairosvg; cairosvg.svg2png(url='<svg>',
   write_to='<png>', scale=0.75)"`. Avoid ImageMagick's built-in SVG
   renderer — it silently drops markers, dashes, and polylines, so its output
   is not a faithful review copy.
