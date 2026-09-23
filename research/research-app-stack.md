# NeoFold Edge — App Stack Research

Target: HP ZGX Nano / NVIDIA GB10 (Grace Blackwell, **sm_121**), Ubuntu 24.04.5 **aarch64**,
driver 580.173.02, CUDA 13.0, 121 GB unified memory, 20 cores, Python 3.12.3, docker.
Hackathon: Edge AI Hack 2026, final 2026-09-26. Demo must run with the network cable pulled.

Everything below was checked against primary sources on 2026-09-22. Version numbers verified live:
**molstar 5.11.0**, **ollama v0.34.3** (2026-09-19).

---

## TL;DR recommended stack

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI + uvicorn**, single in-process `asyncio.Queue` worker | No Redis, no Celery, GPU serialisation is free |
| Job exec | `asyncio.create_subprocess_exec` per stage; state in a dict + append-only JSONL | Crash-visible, restartable, zero deps |
| Frontend | **Plain HTML/JS served by `StaticFiles`**, live updates over **SSE** | Zero CDN, zero telemetry, zero build step |
| 3D | **Mol\* 5.11.0 vendored from the npm tarball** (`build/viewer/molstar.js` + `.css`) | Verified: bundle contains **no external font/CSS references** |
| LLM | **Ollama v0.34.3** (`ollama-linux-arm64.tar.zst`), model `qwen3:8b`, unloaded with `keep_alive: 0` before folding | arm64+CUDA ships in-box; `ollama stop` frees memory on demand |
| LLM fallback | **llama.cpp built with `-DCMAKE_CUDA_ARCHITECTURES=121`** | The only build guaranteed to hit sm_121 |
| GPU panel | **NVML (nvidia-ml-py) for util/power/temp/clocks + per-PID memory, `/proc/meminfo` for the unified pool** | `nvmlDeviceGetMemoryInfo` is NOT_SUPPORTED on GB10 |
| No-cloud proof | `nft` egress-drop table with a **live packet counter** + Boltz stage in `docker run --network=none` | Visible, reversible, doesn't kill your SSH/UI link |
| Bench | `time.perf_counter_ns()` stage spans + 5 Hz telemetry thread → CSV → matplotlib `Agg` | Joules/job is the credible number nobody else will have |

**Biggest risk:** Ollama's bundled llama.cpp silently skipping the GPU on sm_121. Mitigation and
detection in §2.4.

---

# 1. Offline 3D molecular viewer — Mol\*

## 1.1 Vendoring it, fully offline

The standalone viewer is two files inside the npm tarball. Do this **while you still have network**:

```bash
mkdir -p ~/neofold/static/vendor/molstar
cd /tmp
curl -LO https://registry.npmjs.org/molstar/-/molstar-5.11.0.tgz
tar xzf molstar-5.11.0.tgz
cp package/build/viewer/molstar.js  ~/neofold/static/vendor/molstar/
cp package/build/viewer/molstar.css ~/neofold/static/vendor/molstar/
# optional dark skin instead of molstar.css:
cp package/build/viewer/theme/dark.css ~/neofold/static/vendor/molstar/
```

Or, if you prefer the CDN mirror (same files, also verified live):

```bash
curl -LO https://cdn.jsdelivr.net/npm/molstar@5.11.0/build/viewer/molstar.js
curl -LO https://cdn.jsdelivr.net/npm/molstar@5.11.0/build/viewer/molstar.css
```

**Offline-safety audit I actually ran on the 5.11.0 tarball:**

```bash
grep -o "https\?://[^\")' ]*" build/viewer/molstar.css   # -> ZERO matches. No Google Fonts, no CDN.
grep -o "https://[a-zA-Z0-9.-]*" build/viewer/molstar.js | sort | uniq -c | sort -rn
#   13 https://www.ebi.ac.uk        <- default PDBe download provider
#   10 https://github.com           <- comments/attribution
#    3 https://ds.litemol.org       <- volume streaming server
#    2 https://webchem.ncbr.muni.cz <- plugin state ("remote state") server
#    2 https://files.rcsb.org  ...
```

Those hosts are **defaults for features you never invoke**. Nothing is fetched at load time.
Belt-and-braces: turn the features off in `Viewer.create` (see below) so no judge can click a
button that produces a DNS lookup:

- `layoutShowRemoteState: false` → kills `webchem.ncbr.muni.cz`
- `volumeStreamingDisabled: true` → kills `ds.litemol.org`
- never call `viewer.loadPdb()`, `loadEmdb()`, `loadAlphaFoldDb()`, `loadModelArchive()` — those
  are the only methods that reach the internet. Use `loadStructureFromUrl()` pointed at **your own
  FastAPI route**, or `loadStructureFromData()` with the text inlined.

`molstar.js` is ~5.0 MB uncompressed. Serve it with gzip (`uvicorn` + `GZipMiddleware`).

## 1.2 Loading a Boltz CIF and colouring by pLDDT — the key fact

Mol\* ships a colour theme literally named **`plddt-confidence`**, and — this is the load-bearing
detail — **it falls back to the B-factor column when no ModelArchive quality-assessment category is
present**. From `src/extensions/model-archive/quality-assessment/color/plddt.ts` (v5.11.0):

```ts
let score = metric?.get(unit.model.atomicHierarchy.residueAtomSegments.index[element]);
if (typeof score !== 'number') {
    score = unit.model.atomicConformation.B_iso_or_equiv.value(element);
}
if (score < 0)        return DefaultColor;       // 0xaaaaaa
else if (score <= 50) return Color(0xff7d45);    // Very Low   orange
else if (score <= 70) return Color(0xffdb13);    // Low        yellow
else if (score <= 90) return Color(0x65cbf3);    // Confident  light blue
else                  return Color(0x0053d6);    // Very High  dark blue
```

and its applicability test:

```ts
isApplicable: (ctx) => !!ctx.structure?.models.some(m =>
    QualityAssessment.isApplicable(m, 'pLDDT') ||
    (m.atomicConformation.B_iso_or_equiv.isDefined && !Model.isExperimental(m)))
```

Boltz writes a predicted (non-experimental) mmCIF with per-token pLDDT, so this theme applies
straight out of the box and you get the exact AlphaFold colour bands for free.

> ⚠️ **Scale gotcha — check this on day 1.** Boltz reports `complex_plddt` in `confidence_*.json`
> on a **0–1** scale. If the CIF's `B_iso_or_equiv` column also comes out 0–1, every residue will
> render orange ("Very Low"). Verify with:
> ```bash
> awk '$1=="ATOM"{print $15}' pred.cif | sort -n | tail -1   # column index may differ; eyeball it
> ```
> If the max is ≤ 1.0, rescale ×100 in your post-processing step (a 5-line gemmi/regex pass), or
> use the `uncertainty` theme with a custom `domain: [0, 1]` instead. Do not discover this on stage.

The generic B-factor theme is `uncertainty` (`src/mol-theme/color/uncertainty.ts`), params
`{ domain: PD.Interval([0,100]), list: PD.ColorList('red-white-blue', {presetKind:'scale'}) }`,
built with `reverse: true` — i.e. **high B-factor = red**. That is the wrong polarity for pLDDT,
which is another reason to prefer `plddt-confidence`.

## 1.3 Minimal working HTML + JS (paste-ready)

`static/viewer.html`:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>NeoFold Edge — structure</title>
  <link rel="stylesheet" href="/static/vendor/molstar/molstar.css">
  <style>
    html,body { margin:0; height:100%; background:#101418; }
    #app { position:absolute; inset:0; }
    #hud { position:absolute; left:12px; top:12px; z-index:10; font:13px/1.4 system-ui,sans-serif;
           color:#e6edf3; background:#0008; padding:8px 12px; border-radius:6px; }
    .sw { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; }
  </style>
</head>
<body>
  <div id="app"></div>
  <div id="hud">
    <div><b>pLDDT</b></div>
    <div><span class="sw" style="background:#0053d6"></span>Very high (&gt;90)</div>
    <div><span class="sw" style="background:#65cbf3"></span>Confident (70–90)</div>
    <div><span class="sw" style="background:#ffdb13"></span>Low (50–70)</div>
    <div><span class="sw" style="background:#ff7d45"></span>Very low (&lt;50)</div>
  </div>

  <script src="/static/vendor/molstar/molstar.js"></script>
  <script>
  (async function () {
    const jobId = new URLSearchParams(location.search).get('job');

    const viewer = await molstar.Viewer.create('app', {
      // --- clean demo chrome ---
      layoutIsExpanded: true,
      layoutShowControls: false,       // no left/right param panels
      layoutShowLeftPanel: false,
      layoutShowSequence: false,
      layoutShowLog: false,
      viewportShowExpand: false,
      viewportShowAnimation: false,
      viewportShowSelectionMode: false,
      viewportShowSettings: false,
      viewportBackgroundColor: '#101418',
      // --- hard offline switches ---
      layoutShowRemoteState: false,    // no webchem.ncbr.muni.cz
      volumeStreamingDisabled: true,   // no ds.litemol.org
      // --- looks ---
      illumination: true,              // ambient occlusion; costs ~nothing on GB10, looks great
      pixelScale: 1,
    });
    window.viewer = viewer;            // handy for live debugging on stage

    // Local file only. This route is served by YOUR FastAPI app.
    await viewer.loadStructureFromUrl(
      `/api/jobs/${jobId}/model.cif`, 'mmcif', /*isBinary*/ false,
      { representationParams: { theme: { globalName: 'plddt-confidence' } } }
    );

    // Belt-and-braces: force the theme on every representation after load.
    const plugin = viewer.plugin;
    const structs = plugin.managers.structure.hierarchy.current.structures;
    for (const s of structs) {
      await plugin.managers.structure.component.updateRepresentationsTheme(
        s.components, { color: 'plddt-confidence' }
      );
    }

    // Clean initial camera: fit everything, then let the focus below take over.
    plugin.managers.camera.reset();
  })();
  </script>
</body>
</html>
```

`updateRepresentationsTheme(components, params)` is the real public signature from
`src/mol-plugin-state/manager/structure/component.ts`.

## 1.4 Peptide chain vs HLA chain — use MolViewSpec, not ad-hoc selections

Hand-rolling MolScript selections against the minified bundle is the single most likely place to
burn half a day. Mol\* has a **declarative JSON format (MolViewSpec / `.mvsj`)** that the Viewer
loads with `viewer.loadMvsData(json, 'mvsj')`. Your backend emits the JSON per job; the frontend
stays dumb. This gives you per-chain colour, per-chain representation, labels, camera focus and
background in one document.

Verified syntax, lifted from `examples/mvs/1cbs-focus.mvsj` in the molstar repo:

```python
# backend: build_mvsj.py  —  peptide = chain B, HLA = chain A
import json

def build_mvsj(job_id: str, hla_chain: str = "A", pep_chain: str = "B",
               peptide_seq: str = "", allele: str = "HLA-A*02:01") -> str:
    def node(kind, params, children=None):
        n = {"kind": kind, "params": params}
        if children:
            n["children"] = children
        return n

    hla = node("component", {"selector": {"label_asym_id": hla_chain}}, [
        node("representation", {"type": "cartoon"}, [
            node("color", {"color": "#3a4a5a"}),                    # muted groove
        ]),
        node("label", {"text": allele}),
    ])

    peptide = node("component", {"selector": {"label_asym_id": pep_chain}}, [
        # Camera flies to the peptide — this is the money shot.
        node("focus", {"direction": [0.5, 0, -1], "up": [0.365, 0.913, 0.183]}),
        node("representation", {"type": "ball_and_stick"}, [
            # per-residue pLDDT bands, generated server-side (see below)
            node("color_from_uri", {
                "uri": f"/api/jobs/{job_id}/plddt.json",
                "format": "json",
                "schema": "all_atomic",
            }),
        ]),
        node("tooltip", {"text": f"peptide {peptide_seq}"}),
        node("label", {"text": peptide_seq}),
    ])

    tree = node("root", {}, [
        node("download", {"url": f"/api/jobs/{job_id}/model.cif"}, [
            node("parse", {"format": "mmcif"}, [
                node("structure", {"type": "model"}, [hla, peptide]),
            ]),
        ]),
        node("canvas", {"background_color": "#101418"}),
    ])
    return json.dumps({
        "metadata": {"title": f"NeoFold Edge {job_id}", "version": "1"},
        "root": tree,
    })
```

The annotation file `plddt.json` is a flat list; verified format from `examples/mvs/1h9t_domains.json`:

```json
[
  {"label_asym_id": "B", "beg_label_seq_id": 1, "end_label_seq_id": 3,
   "color": "#0053d6", "tooltip": "pLDDT 94.2 — very high"},
  {"label_asym_id": "B", "beg_label_seq_id": 4, "end_label_seq_id": 5,
   "color": "#65cbf3", "tooltip": "pLDDT 81.7 — confident"}
]
```

Generate it by reading the B-factor column per residue with `gemmi` and bucketing into the four
AlphaFold colours (same thresholds as §1.2). Frontend then becomes one line:

```js
const mvsj = await (await fetch(`/api/jobs/${jobId}/view.mvsj`)).text();
await viewer.loadMvsData(mvsj, 'mvsj');
```

**Recommendation:** ship §1.3 first (30 minutes, guaranteed to work), then upgrade to §1.4 on day 2
if time allows. Keep §1.3 as the live fallback path behind a `?simple=1` query param.

## 1.5 Backups

| Viewer | Bundle | Verdict for this demo |
|---|---|---|
| **Mol\*** 5.11.0 | 1 JS + 1 CSS from the npm tarball, `build/viewer/` | **Use this.** Only one with a built-in `plddt-confidence` theme and a declarative scene format. Heaviest (~5 MB JS). |
| **NGL** | `npm i ngl` → `dist/ngl.js`, single UMD file, ~1 MB | `stage.loadFile(new Blob([cifText]), {ext:'cif'})`; colour with `{color:'bfactor', colorScale:'RdYlBu', colorDomain:[50,90]}`; chain select `":A"` / `":B"`. Much smaller API. But **no pLDDT banding** — you get a continuous scale, and you must set `colorReverse` yourself. Lower ceiling, lower risk. |
| **3Dmol.js** | `npm i 3dmol` → `build/3Dmol.js`. **Do not use `3Dmol-min.min.js`** — the upstream docs warn the CDN autominifier produces broken code; `3Dmol-min.js` is already minified. | Simplest possible API: `viewer.setStyle({chain:'B'}, {stick:{colorscheme:{prop:'b', gradient:'roygb', min:50, max:90}}})`. ~400 KB. Genuinely 15 minutes end-to-end. Weakest visuals — no ambient occlusion, flatter cartoons. Good emergency parachute. |

All three are self-hostable with no CDN. If you are behind schedule on day 3, 3Dmol.js is the
honest downgrade.

Sources: <https://github.com/molstar/molstar>, <https://molstar.org/docs/plugin/instance/>,
<https://www.npmjs.com/package/molstar>, <https://github.com/3dmol/3Dmol.js/blob/master/doc.md>,
<https://github.com/molstar/molstar/tree/master/examples/mvs>

---

# 2. Local LLM on GB10 (aarch64, sm_121)

## 2.1 The sm_121 trap (read this first)

GB10 is **compute capability 12.1 (sm_121)**. This is *not* the same as datacenter Blackwell
(sm_100) or consumer Blackwell (sm_120). Anything compiled only for sm_100/sm_120 will either
JIT-fall-back or be skipped outright. The canonical failure signature, from a community bug report:

```
skipping CUDA device — compute capability not in compiled architectures device="NVIDIA GB10" cc=1210
```

That report was against a **third-party repackaged** Ollama (StartOS), not the official build.
Mainline Ollama does drive the GB10 GPU — the upstream issue tracker has multiple 2026 reports of
*CUDA kernel* bugs on DGX Spark (e.g. `ollama/ollama#17596` "CUDA illegal memory access in
`ggml_cuda_flash_attn_ext_mma_f16_case<256,256,8,8>` on DGX Spark (GB10)"), which is only possible
if CUDA is in use. Still: **verify on your box, day 1, before you build anything on top of it.**

## 2.2 Ollama — recommended (install + pre-pull)

Official installer detects `aarch64` automatically. Release **v0.34.3** ships
`ollama-linux-arm64.tar.zst` (1.55 GB — the size is the bundled CUDA runtime).

```bash
# --- with network, day 1 ---
curl -fsSL https://ollama.com/install.sh | sh
ollama --version

# Put weights on the big disk and make them survive a reinstall.
sudo mkdir -p /srv/models/ollama
sudo chown -R ollama:ollama /srv/models/ollama
sudo systemctl edit ollama    # add the override below
```

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MODELS=/srv/models/ollama"
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_KEEP_ALIVE=0"
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_NOHISTORY=1"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart ollama

# --- PRE-PULL EVERYTHING NOW ---
ollama pull qwen3:8b       # ~5.2 GB  <- recommended primary
ollama pull qwen3:4b       # ~2.6 GB  <- emergency lightweight
ollama pull gpt-oss:20b    # ~13 GB   <- the "impressive" option, if memory allows

ollama ls
# Back it up so a reinstall never needs the network again:
sudo tar czf ~/ollama-models-backup.tgz -C /srv/models ollama
```

All tags above verified present in the Ollama library on 2026-09-22.

**Model choice.** `qwen3:8b` is the right default: ~5.2 GB resident, strong instruction-following
for "write a plain-language clinical-ish summary of these ranked peptides", and it leaves
>110 GB of the unified pool for Boltz-2. `qwen3:14b` (~9 GB) is a reasonable upgrade if your
summaries read thin. Avoid `gpt-oss:20b` as the primary — note `ollama/ollama#18522`,
"gpt-oss:20b (MXFP4) deterministic llama-server abort in CUDA ADD_ID" **on GB10** (closed, but it
tells you MXFP4 paths on sm_121 are newer and less exercised).

Turn thinking off in your request so the summary doesn't stream 400 tokens of chain-of-thought at
a judge; Qwen3 supports `"think": false`.

## 2.3 Keeping the LLM out of Boltz's way

Unified memory means the LLM and Boltz compete for **the same 121 GB**. Ollama gives you explicit
control, straight from the upstream FAQ:

> "By default models are kept in memory for 5 minutes before being unloaded. If you want to
> immediately unload a model from memory, use the `ollama stop` command"

and `keep_alive` accepts:

> "a duration string (such as "10m" or "24h") … a number in seconds … any negative number which
> will keep the model loaded in memory (e.g. -1 or "-1m") … '0' which will unload the model
> immediately after generating a response"

Concrete orchestration for the pipeline — **summarise last, fold first**:

```python
import httpx

OLLAMA = "http://127.0.0.1:11434"

async def unload_llm(model: str = "qwen3:8b"):
    """Free unified memory before the Boltz stage. Returns immediately."""
    async with httpx.AsyncClient(timeout=30) as c:
        await c.post(f"{OLLAMA}/api/generate",
                     json={"model": model, "keep_alive": 0})

async def preload_llm(model: str = "qwen3:8b"):
    """Empty request = preload. ~2-4 s; do it while Boltz is writing output."""
    async with httpx.AsyncClient(timeout=300) as c:
        await c.post(f"{OLLAMA}/api/generate",
                     json={"model": model, "keep_alive": "10m"})

async def summarize(prompt: str, model: str = "qwen3:8b") -> str:
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(f"{OLLAMA}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False,
            "think": False, "keep_alive": 0,          # unload right after
            "options": {"temperature": 0.2, "num_ctx": 8192},
        })
        return r.json()["response"]
```

CLI equivalents for the stage script / your demo runbook:

```bash
ollama stop qwen3:8b                      # unload now
ollama ps                                 # shows SIZE and "100% GPU" / "100% CPU"  <-- GPU CHECK
curl -s localhost:11434/api/generate -d '{"model":"qwen3:8b","keep_alive":0}'
```

## 2.4 GPU verification + the llama.cpp fallback

**Day-1 acceptance test.** Run this before you commit to Ollama:

```bash
ollama run qwen3:8b "hi" >/dev/null &
sleep 5
ollama ps                       # PROCESSOR column MUST say "100% GPU"
journalctl -u ollama -n 200 --no-pager | grep -i -E "cuda|compute capability|skipping"
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

If `ollama ps` says `100% CPU`, or you see `skipping CUDA device`, **switch to llama.cpp**. The
Arm/NVIDIA learning path gives the exact sm_121 build:

```bash
sudo apt-get install -y build-essential cmake libcurl4-openssl-dev git
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
mkdir -p build-gpu && cd build-gpu
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_F16=ON \
  -DCMAKE_CUDA_ARCHITECTURES=121 \
  -DCMAKE_C_COMPILER=gcc \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCMAKE_CUDA_COMPILER=nvcc
make -j"$(nproc)"
./bin/llama-server --version         # must print "compute capability 12.1"
```

Build takes 2–4 min on the Grace CPU. Serve with an OpenAI-compatible API:

```bash
./bin/llama-server -m /srv/models/gguf/Qwen3-8B-Q4_K_M.gguf \
  -ngl 99 -c 8192 --host 127.0.0.1 --port 8081 --no-webui
```

`-ngl 99` offloads all layers. `llama-server` has **no built-in unload**; to free memory you must
kill the process — so wrap it in a systemd unit and `systemctl stop llama-server` before folding.
That extra plumbing is exactly why Ollama is the primary recommendation.

## 2.5 What NOT to use

- **vLLM** — the prebuilt wheels/containers target up to sm_120; sm_121 needs a rebuilt PyTorch
  *and* rebuilt vLLM. Tracked in `vllm-project/vllm#31128` ("Add support of Blackwell SM121
  (DGX Spark)") and `#36821` ("No sm_121 (Blackwell) support on aarch64"). There are community
  containers and `nvcr.io/nvidia/vllm-openai:cu130-*` tags, but you would be spending day 1 on
  container archaeology for throughput you do not need — your LLM does **one** summary per job.
- **LM Studio / Open WebUI** — extra GUI surface, extra offline auditing, zero judge value.
- **TensorRT-LLM** — best single-stream tok/s, worst time-to-first-working-thing.
- Anything **x86-only**: pre-built `.deb`/`.AppImage` from vendors without `arm64` assets, most
  conda channels' CUDA builds, and any Docker image without a `linux/arm64` manifest. Always
  `docker manifest inspect <image> | grep -i arm64` before pulling.

Sources: <https://github.com/NVIDIA/dgx-spark-playbooks>,
<https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/ollama/README.md>,
<https://raw.githubusercontent.com/ollama/ollama/main/docs/faq.mdx>,
<https://github.com/ollama/ollama/releases>,
<https://learn.arm.com/learning-paths/laptops-and-desktops/dgx_spark_llamacpp/2_gb10_llamacpp_gpu/>,
<https://github.com/vllm-project/vllm/issues/31128>,
<https://community.start9.com/t/ollama-performance-report-cpu-only-on-dgx-spark-gb10/5381>

---

# 3. GPU telemetry on GB10 — what actually works

## 3.1 The ground truth

Your observation is correct and officially acknowledged. NVIDIA's own answer:

> "The DGX Spark has a unified memory architecture. NVIDIA-SMI only reports memory utilization
> when there is a dedicated GPU VRAM."

and the DGX Spark *Known Issues* page:

> "`nvidia-smi` reports `Memory-Usage: Not Supported` on iGPU platforms, though **per-process GPU
> memory is displayed**."

That second clause is your way in.

### Verified matrix

| Source | GB10 status |
|---|---|
| `nvidia-smi --query-gpu=memory.total,memory.used,memory.free` | ❌ `[N/A]` |
| `nvidia-smi --query-gpu=utilization.memory` | ❌ `[N/A]` |
| `nvidia-smi dmon` / `pmon` memory columns | ❌ reports `0` (worse than N/A — silently wrong) |
| `nvidia-smi --query-gpu=utilization.gpu` | ✅ works |
| `nvidia-smi --query-gpu=power.draw` | ✅ works |
| `nvidia-smi --query-gpu=temperature.gpu` | ✅ works |
| `nvidia-smi --query-gpu=clocks.sm,clocks.gr` | ✅ works |
| `nvidia-smi --query-gpu=clocks.mem` | ❌ `N/A` (no discrete mem controller) |
| `nvidia-smi --query-gpu=fan.speed` | ❌ `N/A` (chassis-managed) |
| `nvidia-smi --query-gpu=pcie.link.gen.current` | ⚠️ bogus `1@1x` — it's NVLink-C2C, not PCIe |
| **`nvidia-smi --query-compute-apps=pid,process_name,used_memory`** | ✅ **works — per-process** |
| NVML `nvmlDeviceGetUtilizationRates` | ✅ |
| NVML `nvmlDeviceGetPowerUsage` | ✅ (milliwatts) |
| NVML `nvmlDeviceGetTemperature` | ✅ |
| NVML `nvmlDeviceGetClockInfo(SM/GRAPHICS)` | ✅ |
| NVML `nvmlDeviceGetMemoryInfo` | ❌ `NVML_ERROR_NOT_SUPPORTED` / `total == 0` |
| **NVML `nvmlDeviceGetComputeRunningProcesses_v3`** | ✅ **`usedGpuMemory` per PID** |
| NVML `nvmlDeviceGetFanSpeed` | ❌ |
| `/proc/meminfo` | ✅ **this is your unified-memory total/used** |
| `torch.cuda.mem_get_info()` / `cudaMemGetInfo` | ✅ works, but NVIDIA notes it *"does not account for memory that could be reclaimed from SWAP"* → under-reports available |
| `torch.cuda.max_memory_allocated()` | ✅ **best number for "what Boltz actually used"** |
| `tegrastats` | ⚠️ present, but it's a Jetson tool; useful for SoC temps (`sudo tegrastats --interval 1000`). Don't build the dashboard on it. |
| `jtop` / jetson-stats | ❌ targets Jetson Orin/Xavier/Nano. GB10 is not a Jetson. Don't. |
| DCGM | ⚠️ not a supported/validated path on GB10; the k8s-device-plugin tracker (`NVIDIA/k8s-device-plugin#1482`) shows GB10 support is still being worked out. Too much yak-shaving for 4 days. |
| `/sys/devices/gpu.0/load` (Tegra sysfs) | ❌ Jetson-only path; not present on GB10. |

### The HugePages trap

The Known Issues page and the `nv-monitor` source both flag it: DGX Spark reserves HugePages, and
**`MemAvailable` in `/proc/meminfo` is then inaccurate**. Use `HugePages_Free × Hugepagesize`
instead, and treat swap as effectively 0 (hugetlbfs pages are not swappable). The snippet below
does this.

## 3.2 Probe script — run this FIRST on the box

Don't trust my table; produce your own evidence and paste it into your slides.

```bash
#!/usr/bin/env bash
# probe_gb10.sh — establishes exactly which telemetry fields are live on THIS machine.
set -u
F=(name driver_version compute_cap utilization.gpu utilization.memory \
   memory.total memory.used memory.free power.draw power.limit enforced.power.limit \
   temperature.gpu clocks.sm clocks.gr clocks.mem fan.speed \
   pcie.link.gen.current pstate)
for f in "${F[@]}"; do
  v=$(nvidia-smi --query-gpu="$f" --format=csv,noheader 2>&1 | head -1)
  printf '%-28s %s\n' "$f" "$v"
done
echo
echo "--- compute apps (per-process) ---"
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
echo
echo "--- unified memory (/proc/meminfo) ---"
grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree|HugePages_Total|HugePages_Free|Hugepagesize)' /proc/meminfo
echo
echo "--- NVML via python ---"
python3 - <<'PY'
import pynvml as n
n.nvmlInit(); h = n.nvmlDeviceGetHandleByIndex(0)
def t(label, fn, *a):
    try: print(f"  {label:38s} OK    {fn(*a)}")
    except Exception as e: print(f"  {label:38s} FAIL  {e}")
t("nvmlDeviceGetName", n.nvmlDeviceGetName, h)
t("nvmlDeviceGetUtilizationRates", lambda: n.nvmlDeviceGetUtilizationRates(h).gpu)
t("nvmlDeviceGetMemoryInfo", lambda: n.nvmlDeviceGetMemoryInfo(h).total)
t("nvmlDeviceGetPowerUsage(mW)", n.nvmlDeviceGetPowerUsage, h)
t("nvmlDeviceGetTemperature", n.nvmlDeviceGetTemperature, h, n.NVML_TEMPERATURE_GPU)
t("nvmlDeviceGetClockInfo(SM)", n.nvmlDeviceGetClockInfo, h, n.NVML_CLOCK_SM)
t("nvmlDeviceGetFanSpeed", n.nvmlDeviceGetFanSpeed, h)
t("ComputeRunningProcesses", lambda: [(p.pid, p.usedGpuMemory) for p in n.nvmlDeviceGetComputeRunningProcesses(h)])
PY
echo
echo "--- dmon (note: mem columns are known-bogus zeros on GB10) ---"
timeout 3 nvidia-smi dmon -c 2 || true
which tegrastats && echo "tegrastats present" || echo "tegrastats absent"
```

## 3.3 Working Python poller (paste-ready)

```bash
pip install nvidia-ml-py      # NOT the old 'pynvml' package
```

```python
#!/usr/bin/env python3
"""gb10_telemetry.py — GPU telemetry for NVIDIA GB10 (DGX Spark / ZGX Nano).

Built around the GB10 realities:
  * nvmlDeviceGetMemoryInfo  -> NVML_ERROR_NOT_SUPPORTED (unified memory, no discrete VRAM)
  * nvidia-smi dmon/pmon memory columns report 0, which is WRONG, not merely missing
  * utilization / power / temperature / SM clock all work via NVML
  * per-process GPU memory works via nvmlDeviceGetComputeRunningProcesses
  * the unified pool total/used comes from /proc/meminfo, HugePages-aware
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, asdict, field

import pynvml as nvml  # provided by the nvidia-ml-py package

KB = 1024


def _safe(fn, *args, default=None):
    try:
        return fn(*args)
    except Exception:
        return default


# ----------------------------------------------------------------- unified memory
def read_unified_memory() -> dict:
    """Unified LPDDR5X pool from /proc/meminfo. HugePages-aware (see DGX Spark known issues:
    MemAvailable is inaccurate when HugePages are reserved)."""
    vals: dict[str, int] = {}
    with open("/proc/meminfo", "r") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                vals[key] = int(parts[0])

    total_kb = vals.get("MemTotal", 0)
    free_kb = vals.get("MemFree", 0)
    avail_kb = vals.get("MemAvailable", free_kb)
    bufcache_kb = vals.get("Buffers", 0) + vals.get("Cached", 0)

    hp_total = vals.get("HugePages_Total", 0)
    hp_free = vals.get("HugePages_Free", 0)
    hp_size_kb = vals.get("Hugepagesize", 0)
    hugepages_active = hp_total > 0 and hp_size_kb > 0
    if hugepages_active:
        avail_kb = hp_free * hp_size_kb

    app_kb = max(total_kb - free_kb - bufcache_kb, 0)
    return {
        "unified_total_gb": total_kb / KB / KB,
        "unified_app_gb": app_kb / KB / KB,       # real application memory, excl. page cache
        "unified_avail_gb": avail_kb / KB / KB,
        "unified_bufcache_gb": bufcache_kb / KB / KB,
        "hugepages_active": hugepages_active,
    }


# ----------------------------------------------------------------- per-process
def _proc_name(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            raw = fh.read().replace(b"\x00", b" ").strip()
        return (raw.decode("utf-8", "replace") or f"pid{pid}")[:80]
    except OSError:
        return f"pid{pid}"


def _proc_rss_bytes(pid: int) -> int | None:
    try:
        with open(f"/proc/{pid}/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * KB
    except OSError:
        pass
    return None


# ----------------------------------------------------------------- sampler
@dataclass
class Sample:
    ts: float
    gpu_util_pct: int | None = None
    power_w: float | None = None
    temp_c: int | None = None
    sm_clock_mhz: int | None = None
    unified_total_gb: float = 0.0
    unified_app_gb: float = 0.0
    unified_avail_gb: float = 0.0
    unified_bufcache_gb: float = 0.0
    hugepages_active: bool = False
    procs: list = field(default_factory=list)


class GB10Telemetry:
    UNKNOWN_MEM = 0xFFFFFFFFFFFFFFFF  # NVML sentinel for "usedGpuMemory unavailable"

    def __init__(self, index: int = 0):
        nvml.nvmlInit()
        self.h = nvml.nvmlDeviceGetHandleByIndex(index)
        name = _safe(nvml.nvmlDeviceGetName, self.h, default=b"?")
        self.name = name.decode() if isinstance(name, bytes) else str(name)
        # Probe once so the dashboard can honestly label what it can't show.
        self.has_fb_memory = _safe(
            lambda: nvml.nvmlDeviceGetMemoryInfo(self.h).total, default=0
        ) not in (0, None)

    def close(self):
        _safe(nvml.nvmlShutdown)

    def compute_processes(self) -> list[dict]:
        procs = (
            _safe(nvml.nvmlDeviceGetComputeRunningProcesses_v3, self.h, default=None)
            or _safe(nvml.nvmlDeviceGetComputeRunningProcesses, self.h, default=[])
            or []
        )
        out = []
        for p in procs:
            used = getattr(p, "usedGpuMemory", None)
            if used in (None, 0, self.UNKNOWN_MEM):
                used = None
            out.append({
                "pid": p.pid,
                "name": _proc_name(p.pid),
                "gpu_mem_gb": (used / KB / KB / KB) if used else None,
                "host_rss_gb": (lambda r: r / KB / KB / KB if r else None)(_proc_rss_bytes(p.pid)),
            })
        out.sort(key=lambda d: d["gpu_mem_gb"] or 0, reverse=True)
        return out

    def sample(self) -> Sample:
        util = _safe(nvml.nvmlDeviceGetUtilizationRates, self.h)
        pw_mw = _safe(nvml.nvmlDeviceGetPowerUsage, self.h)
        s = Sample(
            ts=time.time(),
            gpu_util_pct=util.gpu if util else None,
            power_w=(pw_mw / 1000.0) if pw_mw is not None else None,
            temp_c=_safe(nvml.nvmlDeviceGetTemperature, self.h, nvml.NVML_TEMPERATURE_GPU),
            sm_clock_mhz=_safe(nvml.nvmlDeviceGetClockInfo, self.h, nvml.NVML_CLOCK_SM),
            procs=self.compute_processes(),
        )
        for k, v in read_unified_memory().items():
            setattr(s, k, v)
        return s


class TelemetryThread(threading.Thread):
    """Background 5 Hz sampler. `latest` drives the live panel; `history` drives the CSV."""

    def __init__(self, hz: float = 5.0, keep: int = 3600):
        super().__init__(daemon=True)
        self.t = GB10Telemetry()
        self.period = 1.0 / hz
        self.keep = keep
        self.latest: Sample | None = None
        self.history: list[Sample] = []
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def run(self):
        while not self._stop.is_set():
            s = self.t.sample()
            with self._lock:
                self.latest = s
                self.history.append(s)
                if len(self.history) > self.keep:
                    del self.history[: len(self.history) - self.keep]
            self._stop.wait(self.period)

    def snapshot(self) -> dict:
        with self._lock:
            return asdict(self.latest) if self.latest else {}

    def window(self, t0: float, t1: float) -> list[Sample]:
        with self._lock:
            return [s for s in self.history if t0 <= s.ts <= t1]

    def stop(self):
        self._stop.set()


if __name__ == "__main__":
    tel = GB10Telemetry()
    print(f"device: {tel.name}   discrete FB memory: {tel.has_fb_memory}")
    try:
        while True:
            s = tel.sample()
            print(
                f"util {s.gpu_util_pct:>3}%  {s.power_w:>6.1f} W  {s.temp_c:>3}C  "
                f"sm {s.sm_clock_mhz} MHz  unified {s.unified_app_gb:6.1f}/"
                f"{s.unified_total_gb:.0f} GB  procs={len(s.procs)}"
            )
            for p in s.procs[:3]:
                g = f"{p['gpu_mem_gb']:.2f} GB" if p["gpu_mem_gb"] else "n/a"
                print(f"    pid {p['pid']:>7}  gpu {g:>9}  rss {p['host_rss_gb'] or 0:.2f} GB  {p['name'][:50]}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        tel.close()
```

Wire it into FastAPI as SSE:

```python
import asyncio, json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()
tel = TelemetryThread(hz=5.0); tel.start()

@app.get("/api/gpu/stream")
async def gpu_stream():
    async def gen():
        while True:
            yield f"data: {json.dumps(tel.snapshot())}\n\n"
            await asyncio.sleep(0.2)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
```

## 3.4 Panel design (what to put on screen)

Three numbers, big, updating at 5 Hz:

1. **GPU utilization %** — a bar plus a 60-second sparkline. This is the "real GPU work" proof.
2. **Power draw (W)** — the most visceral signal. Idle GB10 sits low; a Boltz forward pass slams it.
   A judge watching the watts jump the instant you hit Run is worth more than any log line.
3. **Unified memory: app / total GB** — label it **"Unified memory (LPDDR5X, shared CPU+GPU)"**, not
   "VRAM". Then add a one-line footnote: *"GB10 has no discrete framebuffer; `nvidia-smi` reports
   Memory-Usage: Not Supported by design. We read the unified pool from /proc/meminfo and per-process
   allocations from NVML."* **Turn the platform quirk into a credibility signal** — it shows you
   actually understand the hardware rather than copy-pasting a dashboard.

Plus a process table row for the Boltz PID with its NVML `usedGpuMemory`.

Sources: <https://nvidia.custhelp.com/app/answers/detail/a_id/5775/>,
<https://docs.nvidia.com/dgx/dgx-spark/known-issues.html>,
<https://forums.developer.nvidia.com/t/dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark/367765>,
<https://github.com/Syllo/nvtop/issues/426>,
<https://github.com/mostlygeek/llama-swap/issues/782>,
<https://github.com/wentbackward/nv-monitor> (read the source — it is the best-documented
GB10-aware collector and confirms the NVML/`/proc/meminfo`/HugePages split)

---

# 4. App architecture for 4 days

## 4.1 Recommendation: FastAPI + in-process asyncio queue + plain HTML

**Do not add Redis or Celery.** You have one GPU, one user, and four days. A single worker
coroutine consuming an `asyncio.Queue` gives you the property you actually need — **only one job
touches the GPU at a time** — for free, with no broker to explain, no extra process to die on
stage, and no extra container to prove is offline.

```
neofold/
├── app.py                # FastAPI: routes, SSE, queue, worker
├── pipeline/
│   ├── ingest.py         # parse synthetic VCF/TSV -> candidate peptides
│   ├── rank.py           # scoring -> ranked list
│   ├── fold.py           # subprocess -> boltz predict
│   └── summarize.py      # Ollama call
├── telemetry/gb10.py     # §3.3
├── bench/harness.py      # §6
├── static/
│   ├── index.html  app.js  app.css
│   └── vendor/molstar/{molstar.js,molstar.css}
└── jobs/<job_id>/{input.vcf,ranked.json,model.cif,plddt.json,view.mvsj,summary.md,metrics.json}
```

```python
# app.py (skeleton)
import asyncio, json, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

JOBS = Path("jobs"); JOBS.mkdir(exist_ok=True)
queue: asyncio.Queue[str] = asyncio.Queue()
state: dict[str, dict] = {}
subscribers: set[asyncio.Queue] = set()


def publish(job_id: str):
    payload = json.dumps(state[job_id])
    for q in list(subscribers):
        q.put_nowait(payload)


async def run_stage(job_id: str, name: str, coro):
    state[job_id]["stage"] = name
    state[job_id]["stages"][name] = {"t0": time.time()}
    publish(job_id)
    try:
        result = await coro
    except Exception as exc:
        state[job_id].update(status="failed", error=f"{name}: {exc}")
        publish(job_id)
        raise
    st = state[job_id]["stages"][name]
    st["t1"] = time.time(); st["seconds"] = st["t1"] - st["t0"]
    publish(job_id)
    return result


async def worker():
    """Exactly one of these. Serialises all GPU access."""
    while True:
        job_id = await queue.get()
        d = JOBS / job_id
        try:
            state[job_id].update(status="running", started=time.time())
            peptides = await run_stage(job_id, "ingest",    ingest(d))
            ranked   = await run_stage(job_id, "rank",      rank(d, peptides))
            await     run_stage(job_id, "unload_llm",       unload_llm())
            await     run_stage(job_id, "fold",             fold(d, ranked[0]))
            await     run_stage(job_id, "summarize",        summarize_job(d, ranked))
            state[job_id].update(status="done", finished=time.time())
        except Exception:
            pass
        finally:
            publish(job_id)
            queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tel.start()
    task = asyncio.create_task(worker())
    yield
    task.cancel(); tel.stop()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)  # docs_url=None: no CDN swagger!
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.post("/api/jobs")
async def create_job(f: UploadFile = File(...)):
    job_id = uuid.uuid4().hex[:8]
    d = JOBS / job_id; d.mkdir(parents=True)
    (d / "input.vcf").write_bytes(await f.read())
    state[job_id] = {"id": job_id, "status": "queued", "stage": None, "stages": {}}
    await queue.put(job_id)
    publish(job_id)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/model.cif")
async def model_cif(job_id: str):
    return FileResponse(JOBS / job_id / "model.cif", media_type="chemical/x-mmcif")


@app.get("/api/events")
async def events():
    q: asyncio.Queue = asyncio.Queue()
    subscribers.add(q)
    async def gen():
        try:
            while True:
                yield f"data: {await q.get()}\n\n"
        finally:
            subscribers.discard(q)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/", StaticFiles(directory="static", html=True), name="root")
```

> ⚠️ **`docs_url=None, redoc_url=None` is not cosmetic.** FastAPI's default `/docs` and `/redoc`
> pages load Swagger UI and ReDoc **from `cdn.jsdelivr.net` at runtime**. Leave them on and you have
> shipped a CDN dependency into a "no cloud" demo. Either disable them or self-host the assets.

If you need durability across a crash, append every state change to `jobs/<id>/events.jsonl` and
rehydrate `state` on startup. That is ~15 lines and beats SQLite/Redis here. If you genuinely want
a DB, use `sqlite3` in WAL mode from the worker thread only — but you almost certainly don't.

**Run it:**

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
```

`--workers 1` is mandatory: multiple workers = multiple queues = two jobs on the GPU at once.

## 4.2 Streamlit / Gradio — why not

Both are faster to a first screen and **both phone home by default**. Judged on a "hard no-cloud
guarantee", that is a self-inflicted wound.

### Streamlit

| Leak | Fix |
|---|---|
| Telemetry to **`api.segment.io/v1/batch`** | `browser.gatherUsageStats = false` in `.streamlit/config.toml`, or `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`. **But** `streamlit/streamlit#11205` reports Segment uploads still being attempted with the flag set (`Max retries exceeded with url: /v1/batch`). Assume the flag is necessary, not sufficient. |
| Frontend `analytics.js` | Served from the wheel; disabled by the flag above, but see above. |
| Version-check / "new version available" | `global.showWarningOnDirectExecution=false`, `--browser.serverAddress` pinned |
| Custom fonts | Streamlit ≥1.50 supports **inline font definitions** — use them, or self-hosted `.woff2`. Never a `fonts.googleapis.com` URL in a theme. |
| `st.dataframe` / components fetching CDN assets on a LAN deploy | Known problem; audit with DevTools offline |

```toml
# .streamlit/config.toml
[browser]
gatherUsageStats = false
[server]
headless = true
fileWatcherType = "none"
[global]
showWarningOnDirectExecution = false
```

### Gradio

| Leak | Fix |
|---|---|
| Analytics ping | `os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"` **before `import gradio`**, and `gr.Blocks(analytics_enabled=False)` |
| PyPI version check | Same env var suppresses it |
| **`fonts.googleapis.com`** — themes fetch IBM Plex Mono / Source Sans Pro CSS; the UI **hangs** when blocked | `gr.themes.Soft(font=["system-ui","sans-serif"], font_mono=["ui-monospace","monospace"])` |
| Share tunnel | `demo.launch(share=False)` (default, but be explicit) |
| SSR font fetch | `gradio-app/gradio#10101` — avoid SSR / newer theme paths in an air-gapped run |

```python
import os
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
import gradio as gr
demo = gr.Blocks(analytics_enabled=False,
                 theme=gr.themes.Soft(font=["system-ui", "sans-serif"],
                                      font_mono=["ui-monospace", "monospace"]))
demo.launch(share=False, server_name="127.0.0.1", inline=False, show_api=False)
```

**Verdict:** you need custom Mol\* embedding, a custom GPU panel and an SSE stream anyway. Both
frameworks fight you on all three. Plain HTML/JS is *less* work here, not more — and it lets you
say "zero third-party JS except a vendored Mol\* file I can show you on disk."

## 4.3 Global offline hygiene checklist

```bash
# In the systemd unit / launch script for the demo:
export GRADIO_ANALYTICS_ENABLED=False
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export HF_HUB_OFFLINE=1            # HuggingFace: never reach out
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export DO_NOT_TRACK=1
export NO_PROXY='*'
export MPLBACKEND=Agg              # matplotlib: no GUI, no font download prompts
export TOKENIZERS_PARALLELISM=false
export OLLAMA_NOHISTORY=1
export PYTHONDONTWRITEBYTECODE=1
```

Audit your own HTML before the demo:

```bash
grep -rniE 'https?://(?!localhost|127\.0\.0\.1)' static/*.html static/*.js
grep -rn 'cdn\.\|googleapis\|jsdelivr\|unpkg\|fonts\.' static/
```

Anything that matches must be vendored or deleted.

---

# 5. Proving "no cloud" to judges

## 5.1 Layered strategy (do all four — they cost minutes and compound)

Ranked by *convincingness ÷ risk*:

### Layer 1 — Physical, and the only one judges truly believe

Connect the Mac to the ZGX Nano with a **direct Ethernet cable** (or USB-C/Thunderbolt networking),
static IPs, **no router, no DHCP, no internet path**. Then the "pull the cable" moment is pulling
the *uplink*, which does not kill the demo link.

```bash
# On the ZGX Nano — pick the interface facing the Mac
ip -br link
sudo nmcli con add type ethernet ifname enP2p1s0 con-name demo-direct \
     ipv4.method manual ipv4.addresses 10.42.0.1/24 ipv6.method ignore
sudo nmcli con up demo-direct
# On the Mac: System Settings -> Network -> that adapter -> Manually -> 10.42.0.2 / 255.255.255.0
# Browser goes to http://10.42.0.1:8000 ; VS Code Remote SSH to 10.42.0.1
```

Then bring the uplink down on stage:

```bash
nmcli device status
sudo nmcli device disconnect wlp1s0          # wifi
sudo nmcli con down "Wired connection 1"     # uplink ethernet (NOT demo-direct)
```

`nmcli device disconnect` is far safer than `ip link set ... down` — NetworkManager remembers state
and `nmcli device connect` restores it cleanly.

### Layer 2 — The on-screen network indicator (the crowd-pleaser)

A persistent badge in the UI header, updated every 2 s, driven by real system state:

```python
# netstatus.py
import asyncio, json, shutil, socket

async def _sh(*cmd) -> str:
    if not shutil.which(cmd[0]):
        return ""
    p = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    out, _ = await p.communicate()
    return out.decode(errors="replace").strip()


async def net_status() -> dict:
    # nmcli general: STATE:CONNECTIVITY  e.g. "disconnected:none"
    gen = await _sh("nmcli", "-t", "-f", "STATE,CONNECTIVITY", "general")
    state, _, conn = gen.partition(":")

    # Per-interface carrier straight from the kernel, no daemon in the middle.
    links = await _sh("ip", "-j", "-br", "link")
    up = []
    try:
        for l in json.loads(links or "[]"):
            if l.get("ifname") != "lo" and l.get("operstate") == "UP":
                up.append(l["ifname"])
    except json.JSONDecodeError:
        pass

    # Active TCP egress check: can we reach anything off-box?  Must FAIL.
    reachable = False
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            _, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.0)
            w.close(); reachable = True; break
        except Exception:
            pass

    # Firewall drop counter — the number that goes up when something TRIES to leave.
    nft = await _sh("nft", "-j", "list", "counter", "inet", "demo", "egress_blocked")
    blocked_pkts = None
    try:
        for o in json.loads(nft or "{}").get("nftables", []):
            if "counter" in o:
                blocked_pkts = o["counter"].get("packets")
    except json.JSONDecodeError:
        pass

    return {
        "nm_state": state or "unknown",
        "nm_connectivity": conn or "unknown",   # 'none' == no internet, per NetworkManager
        "interfaces_up": up,
        "internet_reachable": reachable,        # render RED if True
        "egress_blocked_packets": blocked_pkts,
        "hostname": socket.gethostname(),
    }
```

Render as: **`🔒 OFFLINE — 0 interfaces up · connectivity: none · egress blocked: 0 pkts`**, and
flip to a red `⚠ NETWORK REACHABLE` the instant `internet_reachable` is true. Judges love a badge
that *can* go red — it proves it isn't a painted-on sticker. Demo that: plug the uplink back in
mid-talk, watch it turn red, unplug, watch it turn green.

### Layer 3 — nftables egress kill-switch with a visible counter

This is the strongest *software* evidence, and it's fully reversible.

```bash
#!/usr/bin/env bash
# demo_lockdown.sh — block all egress except loopback and the judge-facing link.
set -euo pipefail
DEMO_NET="${DEMO_NET:-10.42.0.0/24}"

sudo nft delete table inet demo 2>/dev/null || true
sudo nft add table inet demo
sudo nft add counter inet demo egress_blocked
sudo nft 'add chain inet demo out { type filter hook output priority 0 ; policy accept ; }'
sudo nft add rule inet demo out oifname lo accept
sudo nft add rule inet demo out ip daddr "$DEMO_NET" accept
sudo nft add rule inet demo out ip daddr 169.254.0.0/16 accept     # link-local fallback
sudo nft add rule inet demo out counter name egress_blocked drop   # <- everything else dies here
echo "locked down. showing ruleset:"
sudo nft list table inet demo
```

```bash
#!/usr/bin/env bash
# demo_unlock.sh
sudo nft delete table inet demo && echo "egress restored"
```

Prove it live, on screen:

```bash
sudo nft list counter inet demo egress_blocked   # e.g. "packets 0 bytes 0"
curl -m 3 https://api.openai.com/v1/models ; echo "exit=$?"   # hangs then fails
sudo nft list counter inet demo egress_blocked   # counter has gone UP. Nothing got out.
```

`policy accept` + an explicit final `drop` is deliberate: if you typo a rule you lose the
kill-switch, not your SSH session. Add the demo subnet accept **before** running this over SSH.

### Layer 4 — Run the heavy stage with `--network=none`

An unfakeable, 10-second demonstration for the inference container specifically:

```bash
# Proof that --network=none means what it says:
docker run --rm --network=none alpine sh -c 'ping -c1 -W2 8.8.8.8 || echo "NO NETWORK NAMESPACE"'

# The actual fold stage:
docker run --rm \
  --runtime=nvidia --gpus all \
  --network=none \
  -v /srv/models/boltz:/models:ro \
  -v "$PWD/jobs/$JOB_ID:/work" \
  neofold/boltz:arm64 \
  boltz predict /work/input.yaml --out_dir /work --cache /models --use_msa_server=false
```

`--network=none` gives the container an empty network namespace — it has no interfaces at all, so
there is literally nothing to egress through. **Make sure `--use_msa_server=false`** (or whatever
the equivalent flag is in your Boltz version): Boltz's default MSA path calls a remote server, and
that single flag is the difference between a working offline demo and a hang.

A shell-only equivalent if you skip Docker: `sudo unshare --net --fork --pid --mount-proc <cmd>`.

## 5.2 Which to lead with

**Lead with Layer 1 + Layer 2.** Physically hold up the unplugged cable, point at the badge, run a
job. Keep Layer 3 as the answer to "but how do we *know*?" (show the drop counter climbing while
`curl` to a public API fails), and Layer 4 as the answer to "could the model be calling out?"

**Do not** make the demo *depend* on Layers 3–4. A firewall rule that accidentally blocks your own
`127.0.0.1:11434` Ollama call at minute 3 of a 5-minute pitch is how demos die. Test the lockdown
script end-to-end at least twice, including a full job run, before the final.

### Pre-demo rehearsal checklist

```bash
sudo ./demo_lockdown.sh
sudo nmcli device disconnect wlp1s0
sudo nmcli con down "Wired connection 1"
# ... run a full job start to finish, twice ...
curl -m 3 https://pypi.org 2>&1 | tail -1          # must fail
sudo nft list counter inet demo egress_blocked     # must be > 0 after the curl
sudo ./demo_unlock.sh                              # and confirm everything comes back
```

---

# 6. Benchmark harness

## 6.1 Timing + telemetry per job → CSV

```python
# bench/harness.py
import csv, json, os, statistics, time
from contextlib import contextmanager
from pathlib import Path

STAGES = ["ingest", "rank", "unload_llm", "fold", "summarize"]


class JobBench:
    """One instance per job. Records stage spans and integrates GPU telemetry over each span."""

    def __init__(self, job_id: str, tel, outdir: Path):
        self.job_id, self.tel, self.outdir = job_id, tel, Path(outdir)
        self.spans: dict[str, dict] = {}
        self.t_start = time.time()
        self.pc_start = time.perf_counter()

    @contextmanager
    def stage(self, name: str):
        t0, p0 = time.time(), time.perf_counter()
        try:
            yield
        finally:
            t1, p1 = time.time(), time.perf_counter()
            self.spans[name] = {"t0": t0, "t1": t1, "seconds": p1 - p0,
                                **self._gpu_over(t0, t1)}

    def _gpu_over(self, t0: float, t1: float) -> dict:
        samples = self.tel.window(t0, t1)
        if not samples:
            return {}
        utils = [s.gpu_util_pct for s in samples if s.gpu_util_pct is not None]
        powers = [(s.ts, s.power_w) for s in samples if s.power_w is not None]
        mem = [s.unified_app_gb for s in samples]

        # Trapezoidal integration of watts over wall time -> joules. This is the credible one.
        joules = 0.0
        for (ta, pa), (tb, pb) in zip(powers, powers[1:]):
            joules += (pa + pb) / 2.0 * (tb - ta)

        return {
            "gpu_util_mean": statistics.fmean(utils) if utils else None,
            "gpu_util_p95": (sorted(utils)[int(0.95 * (len(utils) - 1))] if utils else None),
            "gpu_busy_frac": (sum(1 for u in utils if u >= 50) / len(utils)) if utils else None,
            "power_mean_w": statistics.fmean(p for _, p in powers) if powers else None,
            "power_peak_w": max((p for _, p in powers), default=None),
            "energy_j": round(joules, 1),
            "unified_peak_gb": max(mem, default=None),
            "unified_delta_gb": (max(mem) - min(mem)) if mem else None,
            "n_samples": len(samples),
        }

    def finish(self, extra: dict | None = None) -> dict:
        total = time.perf_counter() - self.pc_start
        row = {"job_id": self.job_id, "t_start_iso": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(self.t_start)), "total_seconds": round(total, 3)}
        for s in STAGES:
            d = self.spans.get(s, {})
            row[f"{s}_s"] = round(d.get("seconds", 0.0), 3)
            for k in ("gpu_util_mean", "power_mean_w", "power_peak_w",
                      "energy_j", "unified_peak_gb", "gpu_busy_frac"):
                row[f"{s}_{k}"] = d.get(k)
        row["energy_total_j"] = round(sum(
            (self.spans.get(s, {}).get("energy_j") or 0.0) for s in STAGES), 1)
        row["energy_total_wh"] = round(row["energy_total_j"] / 3600.0, 4)
        row.update(extra or {})

        self.outdir.mkdir(parents=True, exist_ok=True)
        (self.outdir / "metrics.json").write_text(json.dumps(row, indent=2))
        append_csv(Path("bench/results.csv"), row)
        return row


def append_csv(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if new:
            w.writeheader()
        w.writerow(row)
```

Usage in the worker:

```python
b = JobBench(job_id, tel, JOBS / job_id)
with b.stage("ingest"):     peptides = await ingest(d)
with b.stage("rank"):       ranked   = await rank(d, peptides)
with b.stage("unload_llm"): await unload_llm()
with b.stage("fold"):       await fold(d, ranked[0])
with b.stage("summarize"):  await summarize_job(d, ranked)
b.finish(extra={"n_variants": len(peptides), "n_candidates": len(ranked),
                "model_len": ranked[0]["length"], "cold_start": is_first_job,
                "llm_model": "qwen3:8b", "boltz_recycles": 3,
                "output_sha256": sha256_of(d / "model.cif")})
```

Also dump the raw 5 Hz stream per job for the timeline chart:

```python
with (JOBS / job_id / "telemetry.csv").open("w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["ts", "gpu_util_pct", "power_w", "temp_c", "sm_clock_mhz", "unified_app_gb"])
    for s in tel.window(b.t_start, time.time()):
        w.writerow([f"{s.ts:.3f}", s.gpu_util_pct, s.power_w, s.temp_c,
                    s.sm_clock_mhz, f"{s.unified_app_gb:.2f}"])
```

## 6.2 Metrics a technical judge respects

For **a throughput-oriented workload made of independent jobs**, report these — in this order:

1. **Stage breakdown (median of N ≥ 20 runs), with cold excluded and stated separately.**
   "Cold start 41.2 s (weight load) / warm median 8.7 s" is honest; a single number is not.
2. **Sustained throughput: jobs/minute over a 10-minute run**, not `60 / median_latency`.
   Queueing, thermals and allocator churn make those two differ, and judges know it.
3. **Latency distribution: p50 / p90 / p99 and max**, on ≥ 20 jobs. Give the N. Everyone reports a
   mean; reporting p99 and the sample size signals you measured rather than cherry-picked.
4. **Energy per job (joules, and Wh)** — integrated from NVML power. *This is your differentiator.*
   "3.1 kJ per neoantigen, 0.86 Wh — a cloud A100 round-trip costs more in network egress than we
   spend folding" is a line no other team will have, and it is only possible because power is one
   of the NVML fields GB10 *does* expose.
5. **GPU busy fraction during the fold stage** (`% of samples with util ≥ 50`). This is your
   honest answer to "is this really GPU work?" and it pre-empts the "your GPU panel is a
   random-number generator" question. Expect a number well under 100% — say so.
6. **Peak unified-memory delta per job**, labelled as unified memory with the `/proc/meminfo`
   caveat. Pair it with `torch.cuda.max_memory_allocated()` from inside the fold process, which
   measures the CUDA caching allocator directly and works fine on GB10.
7. **Determinism**: SHA-256 of `model.cif` across 3 runs with a fixed seed. Either it matches
   (say so — reproducibility is a clinical-adjacent virtue) or it doesn't (say that too, and why).
8. **Scaling**: latency vs. peptide length / number of candidates, 3–4 points. Shows the system
   under varying load rather than one hero run.

**Anti-patterns that lose credibility:** a single run with no N; a mean with no distribution;
"GPU utilization 100%" claimed with no methodology; comparing against a cloud latency you did not
measure; reporting memory as "VRAM" on a machine with no VRAM.

## 6.3 Charts (matplotlib, fully offline)

matplotlib needs no network. Force `Agg` and vendor the data:

```python
# bench/plots.py
import csv, matplotlib
matplotlib.use("Agg")                       # no GUI, no display, no X11
import matplotlib.pyplot as plt

PL = {"ingest": "#5B8FF9", "rank": "#61DDAA", "unload_llm": "#9270CA",
      "fold": "#F6BD16", "summarize": "#7262FD"}


def stage_breakdown(csv_path="bench/results.csv", out="bench/stages.png"):
    """Chart 1: stacked horizontal bars, one per job. Instantly shows where time goes."""
    rows = list(csv.DictReader(open(csv_path)))
    fig, ax = plt.subplots(figsize=(10, 0.35 * len(rows) + 2))
    left = [0.0] * len(rows)
    ys = range(len(rows))
    for st, color in PL.items():
        vals = [float(r.get(f"{st}_s") or 0) for r in rows]
        ax.barh(list(ys), vals, left=left, color=color, label=st, height=0.7)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_yticks(list(ys)); ax.set_yticklabels([r["job_id"] for r in rows], fontsize=7)
    ax.set_xlabel("seconds"); ax.invert_yaxis()
    ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.12), frameon=False)
    ax.set_title("NeoFold Edge — pipeline stage breakdown (local, GB10)")
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def gpu_timeline(tel_csv, stages: dict, out="bench/timeline.png"):
    """Chart 2 — THE MONEY SHOT. GPU util + power over one job, with stage bands shaded."""
    rows = list(csv.DictReader(open(tel_csv)))
    t0 = float(rows[0]["ts"])
    t = [float(r["ts"]) - t0 for r in rows]
    util = [float(r["gpu_util_pct"] or 0) for r in rows]
    pw = [float(r["power_w"] or 0) for r in rows]

    fig, ax = plt.subplots(figsize=(11, 4.2))
    for name, (a, b) in stages.items():
        ax.axvspan(a - t0, b - t0, color=PL.get(name, "#ccc"), alpha=0.16, lw=0)
        ax.text((a + b) / 2 - t0, 103, name, ha="center", fontsize=8, color="#444")
    ax.plot(t, util, lw=1.6, color="#1f77b4", label="GPU utilization %")
    ax.set_ylim(0, 110); ax.set_ylabel("GPU utilization (%)"); ax.set_xlabel("seconds since job start")

    ax2 = ax.twinx()
    ax2.plot(t, pw, lw=1.3, color="#d62728", alpha=0.85, label="power (W)")
    ax2.set_ylabel("power draw (W)")

    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", frameon=False)
    ax.set_title("GB10 GPU utilization and power draw during one NeoFold Edge job")
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)


def latency_cdf(csv_path="bench/results.csv", out="bench/latency.png"):
    """Chart 3: empirical CDF with p50/p90/p99 annotated. Shows you understand distributions."""
    lat = sorted(float(r["total_seconds"]) for r in csv.DictReader(open(csv_path)))
    n = len(lat)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(lat, [(i + 1) / n for i in range(n)], where="post", lw=1.8, color="#2a9d8f")
    for q, c in ((0.50, "#264653"), (0.90, "#e76f51"), (0.99, "#8d0801")):
        v = lat[min(int(q * n), n - 1)]
        ax.axvline(v, ls="--", lw=1, color=c)
        ax.text(v, 0.04, f" p{int(q*100)}={v:.1f}s", rotation=90, fontsize=8, color=c)
    ax.set_xlabel("end-to-end latency (s)"); ax.set_ylabel("cumulative fraction of jobs")
    ax.set_title(f"End-to-end latency CDF (n={n} jobs, warm)")
    fig.tight_layout(); fig.savefig(out, dpi=160); plt.close(fig)
```

**If you only build one chart, build `gpu_timeline`.** A utilization curve that visibly slams to
90%+ exactly when the "fold" band starts, with power tracking it, is the single most persuasive
artifact you can produce for "visible real GPU work" — and it doubles as your evidence that the
live panel isn't faked.

Pre-render all three at the end of every run so a fresh PNG is always sitting in `static/bench/`
ready to show, and serve them from the app. Never render on-demand during the pitch.

---

# 7. Day-by-day risk ordering

| Day | Do first | Failure mode you are buying down |
|---|---|---|
| 1 | Run `probe_gb10.sh`. Run the Ollama GPU acceptance test (`ollama ps` → `100% GPU`). Pull **all** weights (Ollama + Boltz) and back them up. Vendor `molstar.js`/`.css`. | sm_121 skip; no-network-on-demo-day |
| 1 | Fold one hard-coded peptide–HLA pair end to end in a shell, offline, with `--use_msa_server=false`. Check the CIF B-factor scale (§1.2). | Boltz MSA phoning home; orange-everything viewer |
| 2 | FastAPI skeleton + queue + SSE + Mol\* §1.3 path + GPU panel | integration risk |
| 3 | MVSJ chain colouring, LLM summary, bench harness, lockdown scripts | polish |
| 4 | **Rehearse the offline run twice, end to end, from a cold boot.** Pre-render charts. | everything |

---

## Appendix — source URLs

**Mol\***
- <https://github.com/molstar/molstar>
- <https://molstar.org/docs/plugin/instance/>
- <https://www.npmjs.com/package/molstar> (v5.11.0)
- <https://github.com/molstar/molstar/blob/master/src/extensions/model-archive/quality-assessment/color/plddt.ts>
- <https://github.com/molstar/molstar/blob/master/src/mol-theme/color/uncertainty.ts>
- <https://github.com/molstar/molstar/blob/master/src/apps/viewer/options.ts>
- <https://github.com/molstar/molstar/tree/master/examples/mvs>
- <https://molstar.org/mol-view-spec-docs/tree-schema/>
- <https://github.com/3dmol/3Dmol.js/blob/master/doc.md>

**GB10 / DGX Spark**
- <https://docs.nvidia.com/dgx/dgx-spark/known-issues.html>
- <https://docs.nvidia.com/dgx/dgx-spark/hardware.html>
- <https://nvidia.custhelp.com/app/answers/detail/a_id/5775/>
- <https://forums.developer.nvidia.com/t/dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark/367765>
- <https://forums.developer.nvidia.com/t/nvml-support-for-dgx-spark-grace-blackwell-unified-memory-community-solution/358869>
- <https://forums.developer.nvidia.com/t/dgx-spark-gb10-faq/347344>
- <https://github.com/Syllo/nvtop/issues/426>
- <https://github.com/mostlygeek/llama-swap/issues/782>
- <https://github.com/wentbackward/nv-monitor>
- <https://build.nvidia.com/spark>
- <https://github.com/NVIDIA/dgx-spark-playbooks>

**LLM serving**
- <https://raw.githubusercontent.com/ollama/ollama/main/docs/faq.mdx>
- <https://github.com/ollama/ollama/releases> (v0.34.3)
- <https://learn.arm.com/learning-paths/laptops-and-desktops/dgx_spark_llamacpp/2_gb10_llamacpp_gpu/>
- <https://github.com/vllm-project/vllm/issues/31128>
- <https://github.com/vllm-project/vllm/issues/36821>
- <https://community.start9.com/t/ollama-performance-report-cpu-only-on-dgx-spark-gb10/5381>

**Offline / telemetry hygiene**
- <https://github.com/streamlit/streamlit/issues/11205>
- <https://docs.streamlit.io/develop/concepts/configuration/options>
- <https://docs.streamlit.io/develop/tutorials/configuration-and-theming/external-fonts>
- <https://github.com/gradio-app/gradio/issues/10101>
- <https://gradio.app/guides/theming-guide>

**Boltz**
- <https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md>
