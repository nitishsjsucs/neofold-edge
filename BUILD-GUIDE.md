# NeoFold Edge — Verified Build Guide (HP ZGX Nano / GB10)

**Status:** Phase 0 viability gate **PASSED**. Boltz-2 runs end-to-end on the Nano, offline, producing real 3D structures in under a minute.
**Verified:** 2026-09-22/23 on `zgx-81a8` by direct SSH execution. Everything in §1–§5 was *run*, not looked up.
**Hackathon:** Edge AI Hack 2026, final Sat Sept 26.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Does Boltz-2 run on the GB10? | **Yes.** 383-residue peptide–HLA complex in **58 s wall / 27 s inference**. |
| Does it run offline? | **Yes** — single-sequence mode (`msa: empty`), no MSA server, no cloud. |
| Real GPU work? | **Yes** — peak **96% GPU util, 38 W**, 2.3 GB GPU memory. |
| Do I need the community GB10 fork? | **No.** Stock `pip install boltz==2.2.1` + 4 fixes below. |
| Do I need sudo? | **No** — I found a no-sudo workaround for the one blocker that needs root. |
| Can Boltz confidence rank candidates? | **No.** See §6 — this is the single most important finding. |
| **How accurate is it, really?** | **0.32–0.51 Å** peptide backbone RMSD vs two crystal structures, two alleles. See §6A. |
| Does the screen work? | **Yes.** MHCflurry ranks both published KRAS G12D epitopes **#1 and #2 of 38**. See §6B. |

---

## 1. Verified machine state

```
host      zgx-81a8        Ubuntu 24.04.5 LTS, aarch64 (ARM64)
GPU       NVIDIA GB10     compute capability 12.1 (sm_121), driver 580.173.02
CUDA      13.0            /usr/local/cuda/bin (NOT on PATH by default)
memory    121 GB unified  ~116 GB free
disk      3.6 TB          3.4 TB free
CPU       20 cores
python    3.12.3          system, PEP-668 managed -> venv required
docker    available       hp1 now in docker group (works)
sudo      PASSWORD REQUIRED  <- constrains everything; see §3.4
```

Measured raw throughput, torch 2.14.0+cu132: **43.4 TFLOPS bf16** (8192³ matmul).

---

## 2. The install that works

Copy-paste verbatim. Takes ~15 min, ~10 GB download.

```bash
# 1. venv (PEP-668 means you cannot pip install to system python)
mkdir -p ~/neofold && cd ~/neofold
python3 -m venv .venv-boltz
. .venv-boltz/bin/activate
pip install --upgrade pip wheel setuptools

# 2. PyTorch for ARM64 + CUDA 13. cu132 is the newest stable and works on the 13.0 driver.
pip install "numpy<2.0" torch==2.14.0+cu132 \
  --index-url https://download.pytorch.org/whl/cu132 \
  --extra-index-url https://pypi.org/simple

# 3. gemmi: Boltz pins ==0.6.5, which has NO aarch64 wheel and needs python3-dev to
#    compile. 0.7.5 HAS a prebuilt aarch64 wheel. Install it first, then Boltz --no-deps.
pip install gemmi==0.7.5
pip install boltz==2.2.1 --no-deps
pip install hydra-core==1.3.2 pytorch-lightning==2.5.0 "rdkit>=2024.3.2" dm-tree==0.1.8 \
  requests==2.32.3 "pandas>=2.2.2" types-requests einops==0.8.0 einx==0.3.0 \
  fairscale==0.4.13 mashumaro==3.14 modelcif==1.2 wandb==0.18.7 click==8.1.7 \
  pyyaml==6.0.2 biopython==1.84 scipy==1.13.1 numba==0.61.0 scikit-learn==1.6.1 \
  chembl_structure_pipeline==1.2.2

# 4. cuEquivariance for CUDA 13 (Boltz's [cuda] extra pins the CUDA-12 build, which
#    is wrong for this machine). cp312 aarch64 wheels exist.
pip install "cuequivariance-torch>=0.9.1" "cuequivariance-ops-torch-cu13>=0.9.1"

# 5. Python headers WITHOUT sudo (Triton needs Python.h to build its CUDA shim)
cd ~ && mkdir -p pkgtmp pylocal && cd pkgtmp
apt-get download libpython3.12-dev python3.12-dev     # no root needed to DOWNLOAD
for d in *.deb; do dpkg-deb -x "$d" ~/pylocal; done
```

Then **every** Boltz run needs these three lines:

```bash
. ~/neofold/.venv-boltz/bin/activate
export PATH=/usr/local/cuda/bin:$PATH
export CPATH=$HOME/pylocal/usr/include/python3.12:$HOME/pylocal/usr/include
```

And **always** pass `--num_workers 0` (see §3.1).

> If you can get the root password, `sudo apt install python3.12-dev build-essential` replaces
> step 5 and also lets you use the correct `gemmi==0.6.5` pin. Cleaner, but not required.

---

## 3. The four bugs I hit, and the fixes

### 3.1 Silent dataloader deadlock — the dangerous one
**Symptom:** `Predicting: 0/? [00:00<?, ?it/s]` forever. 0% GPU, 0% CPU, process alive, **no error, no timeout**. I lost 25 minutes to this twice.
**Cause:** PyTorch Lightning's default multiprocess dataloader deadlocks on this ARM64 setup.
**Fix:** `--num_workers 0`.
**Why it matters:** this fails *silently and forever*. On stage it looks like your demo froze. Bake `--num_workers 0` into every call path.

### 3.2 `gemmi==0.6.5` won't build
**Symptom:** `Failed building wheel for gemmi` → `Could NOT find Python (missing: Interpreter Development.Module)`.
**Cause:** no aarch64 wheel at that version + no Python headers.
**Fix:** `gemmi==0.7.5` (prebuilt aarch64 wheel) + `boltz --no-deps`. pip prints a version-conflict warning; it is cosmetic, Boltz runs fine.

### 3.3 `ModuleNotFoundError: cuequivariance_torch`
**Cause:** Boltz's `[cuda]` extra pins `cuequivariance_ops_cu12` — CUDA **12** — on a CUDA **13** machine. Installing the extra actively breaks it.
**Fix:** skip the extra, install the `-cu13` packages (step 4). Verified: recognizes GB10 as cc 12.1, 128 SMs.

### 3.4 Triton can't compile: `Python.h: No such file`
**Cause:** Triton builds a small CUDA shim at runtime and needs Python dev headers. `sudo` needs a password here.
**Fix:** step 5 above — `apt-get download` needs no root, `dpkg-deb -x` unpacks into `$HOME`, `CPATH` makes gcc find them. Verified compiling.

### Non-issues (so you don't waste time)
- **sm_121 support:** a non-problem. `sm_120` SASS is valid on cc ≥ 12.0. No custom wheel, no fork needed.
- **Triton ptxas:** triton 3.8.0 ships both a CUDA 12.9 `ptxas` and a 13.3 `ptxas-blackwell`, and picks correctly.
- **`fairscale`/`modelcif`** have no ARM wheels but build from source fine.

---

## 4. Measured results (1 Nano, single-sequence mode)

Four cases, `--recycling_steps 3 --diffusion_samples 1 --sampling_steps 200`:

| Case | Chains | Residues | Wall | Exit |
|---|---|---|---|---|
| `kras_g12d_c0802_gdom` | α1α2 + peptide | 189 | **44 s** | 0 |
| `kras_g12d_c0802` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |
| `cmv_a0201_correct` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |
| `cmv_a0301_wrong` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |

Of the 58 s, **~27 s is GPU inference**; the rest is process start + model load (amortizable across a batch).

**GPU telemetry during inference:** peak **96% utilization**, **38 W**, 46 °C, 2,304 MiB process memory.
Idle baseline ~3.5 W. That power delta is a clean, honest "real work is happening" signal.

**Telemetry gotcha:** `nvidia-smi --query-gpu=memory.total` returns `[N/A]` on GB10 (unified memory, no discrete VRAM). But these **do** work: `utilization.gpu`, `power.draw`, `temperature.gpu`, and `--query-compute-apps=pid,used_memory` for per-process memory. `dmon`/`pmon` report memory as `0` — silently wrong, don't use them.

---

## 5. Demo case: use this one

**KRAS G12D → HLA-C\*08:02**, ground truth **PDB 6ULN**.

- Variant: GRCh38 `chr12:25,245,350 C>T` (minus strand; genomic C>T, not G>A), MANE `NM_004985.5`
- Peptide: **`GADGVGKSA`** (published epitope: Tran *NEJM* 2016; Sim *PNAS* 2020)
- HLA-C\*08:02 ectodomain: IMGT/HLA `HLA:HLA00446`, mature residues 1–275
- B2M: UniProt `P61769` mature 99-mer (use 99, not the 100 in crystals — that Met is an artifact)

All three chains are **byte-identical to the corresponding chains in PDB 6ULN**. That is a strong, true stage claim: *"our pipeline reconstructed a known experimentally-solved complex end-to-end on-device in 58 seconds, and the peptide was derived from a VCF row, not typed in."*

Be honest that this is **retrospective** — 6ULN may be in Boltz-2's training data.

> ⚠️ **Bug I made, don't repeat it:** UniProt **P04439 is HLA-A\*03:01, not A\*02:01** (byte-identical to `HLA:HLA00037`; 19 mismatches vs A\*02:01 across the ectodomain, 14 inside the binding groove). For A\*02:01 use IMGT `HLA:HLA00005`.

---

## 6. ⚠️ The finding that changes the architecture

I ran a deliberate negative control: the CMV epitope `NLVPMVATV` on its **correct** allele (A\*02:01) and on the **wrong** allele (A\*03:01, whose F-pocket chemistry rejects that peptide's anchor).

| Case | ipTM | pLDDT | peptide–HLA ipTM |
|---|---|---|---|
| Correct allele (A\*02:01) | 0.987 | 0.986 | 0.996 |
| **Wrong allele (A\*03:01)** | **0.988** | 0.986 | 0.994 |

**The wrong pairing scored marginally *higher*.** Boltz returns a confident-looking pose for a complex that should not form.

**Consequences, and they are not optional:**
1. **Never rank or filter candidates by Boltz confidence.** It does not discriminate binders from non-binders here.
2. **MHCflurry does the discrimination.** Boltz is the *explanation and visualization* layer.
3. **Say this out loud in the pitch.** It is a credibility asset: it shows you validated your own tool. A sharp judge may probe exactly here, and "we tested that and here are the numbers" is a much better answer than being surprised.

> ⚠️ **Word this carefully.** Say confidence is **"weak and unreliable for this purpose"**, *not* "meaningless". Our negative control is n=1, and the published position (Motmaen et al.) is that confidence gives *some* discrimination. The true, narrow claim is damning enough, and the overclaim is the one thing here a sharp judge could actually break.

Supporting context from the research: the best published pro-structure neoantigen result drops from AUC 0.73 in-sample to **0.60 held-out**; the TESLA consortium found only **37/608 (6%)** predicted neoantigens were immunogenic. Structure is not a validated discriminator, and you should not imply it is.

---

## 6A. Accuracy, measured against a crystal structure

ipTM is a self-reported score, and §6 shows it is untrustworthy here. So I measured real accuracy: superpose the predicted complex onto **PDB 6ULN** on the MHC heavy chain, then ask how close the *peptide* landed. This is the standard pMHC metric. Script: `rmsd.py` on the Nano.

| Configuration | MHC CA RMSD | **Peptide backbone RMSD** | Peptide CA | Wall time |
|---|---|---|---|---|
| Single-sequence (`msa: empty`) | 0.970 Å | **0.560 Å** | 0.464 Å | 58 s |
| **With MSA (cached, offline)** | **0.748 Å** | **0.486 Å** | **0.357 Å** | 58 s* |
| With MSA (fetching from server) | — | — | — | 132 s |

\* once the MSA is cached; the 132 s run includes the one-time online fetch.

**A second, independent validation.** The CMV epitope `NLVPMVATV` on **HLA-A\*02:01** against crystal **3GSO**: MHC CA **0.33 Å**, peptide backbone **0.321 Å**. Different allele, different deposition, same sub-Ångström result — much harder to dismiss as luck than a single case.

| Case | Crystal | Peptide backbone RMSD |
|---|---|---|
| KRAS G12D `GADGVGKSA` / C\*08:02 | 6ULN | **0.509 Å** |
| CMV `NLVPMVATV` / A\*02:01 | 3GSO | **0.321 Å** |

**Sub-Ångström peptide placement.** For scale, that is within the coordinate uncertainty of many crystal structures. Per-residue deviation is highest at the peptide termini (P1 0.55 Å, P9 0.52 Å) and lowest in the middle — the expected pattern, since the termini are anchored but the crystal has a TCR bound that we do not model.

**Say this honestly:** 6ULN was published in 2020 and may well be in Boltz-2's training data. This is a **retrospective reconstruction**, not a blind prediction. The claim to make is *"our pipeline reconstructs a known complex end-to-end on-device to 0.49 Å in under a minute"* — which is true, verifiable, and still impressive.

### The MSA insight that makes accuracy free

MSAs cost 74 s extra to fetch — but **only once**. The HLA and B2M chains are *identical for every candidate peptide from the same patient*; only the 9-mer changes, and short peptides use `msa: empty` anyway.

So: **generate the HLA + B2M MSA once while online, cache it, and every subsequent candidate is both offline and MSA-accurate at no extra cost.** Cached MSAs live in `~/neofold/msa_cache/` (`hla_c0802.csv` 3.8 MB, `b2m.csv` 725 KB) and are referenced per-chain:

```yaml
  - protein: { id: A, sequence: <HLA>, msa: ./msa_cache/hla_c0802.csv }
  - protein: { id: B, sequence: <B2M>, msa: ./msa_cache/b2m.csv }
  - protein: { id: C, sequence: GADGVGKSA, msa: empty }
```

**Pre-cache one MSA per HLA allele you intend to demo, before going offline.**

---

## 6B. The screening layer works — and this is the scientific heart of the demo

MHCflurry 2.2.0 (PyTorch backend, installs clean on ARM64), `HLA-C*08:02`, 38 peptide windows spanning KRAS residue 12:

| Peptide | Affinity | Presentation | Note |
|---|---|---|---|
| `GADGVGKSAL` | **38.9 nM** | 0.950 | **rank 1/38** — published epitope (Sim *PNAS* 2020) |
| `GADGVGKSA` | **74.1 nM** | 0.570 | **rank 2/38** — published epitope (Tran *NEJM* 2016) |
| `VGADGVGKSAL` | 230 nM | 0.341 | |
| … | | | |

**Neoantigen specificity — run the wild-type as a control:**

| | Mutant (G12D) | Wild-type | Fold change |
|---|---|---|---|
| `GADGVGKSA` vs `GAGGVGKSA` | 74.1 nM | 3,656 nM | **49× stronger** |
| `GADGVGKSAL` vs `AGGVGKSAL` | 38.9 nM | 1,355 nM | **35× stronger** |

This is the demo's real story: **a single G>A substitution creates a peptide the immune system can see, and the normal version of that protein is invisible.** That is the whole premise of a personalized cancer vaccine, shown with measured numbers on-device, against epitopes independently published in *NEJM* and *PNAS*.

Always show the wild-type control. It is the difference between "the model gave us a number" and "the mutation is why this candidate exists."

---

## 6C. The proposed additions, assessed

Three additions were proposed on top of the working pipeline. Two are worth building, one is not.

### ❌ Multi-seed Boltz ensembles — do NOT build

The idea was to run Boltz several times per candidate and use the spread between predictions as an uncertainty signal. **Reading the Boltz source kills it:**

- In `boltz2.py` the **trunk runs once**; `s_trunk`/`s_inputs` are `repeat_interleave`d across diffusion samples. The only difference between samples is `torch.randn` noise in `diffusionv2.py`.
- `inferencev2.py` **hard-codes `seed = 42`** for the featurizer RNG, so `--seed` never reaches MSA subsampling — it only touches the torch RNG.
- Therefore **`--seed S` and `--diffusion_samples N` vary the identical quantity**, and multi-seed is strictly dominated at N× the cost.

The AF2 multi-seed folklore does not transfer: AF2 pairs seeds with MSA subsampling and inference dropout, and Boltz-2 does neither.

Critically, **ensemble spread would almost certainly NOT have caught our wrong-allele error** — that failure lives in the trunk, and the samples do not sample the trunk. Spread measures *where atoms land given the model already decided the peptide is in the groove*. Presenting it as uncertainty about *whether the peptide binds* would be the single biggest honesty trap in this project.

**Ship it as a pre-registered negative result instead.** "We tested whether ensemble spread adds information, read the architecture, and concluded it cannot — here's why" is a better slide than a chart that means nothing. If you want the empirical version, a 2×2 allele swap (`NLVPMVATV` and `KLGGALQAK`, each on A\*02:01 and A\*03:01) settles it in ~25 minutes.

### ✅ Tumour vs normal side-by-side — build it, but let chemistry carry it

The naive version is false: Boltz will produce a confident, plausible pose for the wild-type peptide too, so "mutant looks good / wild-type looks bad" would not survive scrutiny.

**This case has a real discriminator, and I verified it.** HLA-C\*08:02 prefers **Asp at peptide position 3** (Rasmussen, *J Immunol* 2014). G12D is precisely what puts Asp at p3 in `GADGVGKSA`, and crystal structure 6ULN shows that p3 Asp salt-bridging **Arg156** in the D pocket. Measured with `neofold/contacts.py`:

| Structure | p3 residue | Distance to Arg156 | Salt bridge |
|---|---|---|---|
| Crystal 6ULN | ASP3 | **2.73 Å** | yes |
| Boltz prediction | ASP3 | **2.52 Å** | yes |
| Wild-type (`GAGGVGKSA`) | **Gly** | — | **impossible** |

Two things make this honest rather than fishing: the contact was **specified in advance from an experimental structure**, and the wild-type failure is **chemical, not predictive** — glycine has no side chain, so the interaction cannot exist at any confidence level.

This is not our inference. Sim *et al.* (*PNAS* 2020) report that "only mutant G12D but not the wild-type peptides stabilized HLA-C\*08:02", with the most peptide side-chain contacts at p3 where the Asp salt-bridges Arg156; Mariuzza *et al.* (*Front Immunol* 2023) state plainly that "this salt bridge cannot form with P3 Gly, which probably explains the instability of wild-type KRAS–HLA-C complexes."

**Caption to use:** *"The G12D substitution places an aspartate at peptide position 3, where HLA-C\*08:02 has a charged pocket. In the crystal structure that aspartate forms a 2.7 Å salt bridge to Arg156; our local prediction reproduces it at 2.5 Å. The normal protein has glycine here — no side chain, no contact possible."*

> ⚠️ **The caveat that must accompany the panel.** Do not let anyone read binding strength off the picture. For a published wild-type/mutant pair on HLA-A\*03:01 (PDB **7L1B** / **7L1C**, Chandran *et al.*, *Nat Med* 2022), a **70× difference in complex half-life** (0.078 h vs 5.497 h) corresponds to just **0.73 Å** of peptide backbone RMSD. Almost none of the binding signal is visible as geometry. Say so — it is why the panel measures one named contact and takes its ranking from the sequence-based screen.
>
> Two further honest limits: modelling protocols such as PANDORA and APE-Gen place anchors in pockets **by construction**, so burial depth in a model is an artifact, not evidence. And non-binders do not crystallise, so the PDB contains **no control group** for any "non-binder geometry" claim.

### ⚠️ OpenMM stability test — feasible, but frame it as a negative filter only

Verdict: **GO**, with a downgraded timescale.

- OpenMM now publishes **first-party PyPI aarch64 wheels** (`openmm-8.6.1-cp312-...-aarch64`, plus `openmm_cuda_13`). No conda, no sudo, no compiling — this inverts the usual "OpenMM is conda-only" assumption.
- **sm_121 should work** for a structural reason: OpenMM generates kernels at runtime via NVRTC rather than shipping pre-compiled fatbins, which is the root cause of every other sm_121 failure.
- **Install into a separate venv** — `openmm[cuda13]` drags in its own `nvidia-*` stack that would fight the Boltz environment's.
- **Pin `nvidia-cuda-nvrtc==13.0.88`.** CUDA minor-version compatibility explicitly excludes PTX JIT, and the default pull (13.4.x) can emit PTX a 13.0 driver rejects.
- **Budget ~0.5 ns, not 1–3 ns**, plus 20–65 s fixed NVRTC compilation overhead — so batch all candidates in one process.

**The honesty limit is severe and must be stated.** The largest relevant study (2,883 HLA-A2 peptides, 200 ns each) got AUC 0.81 from MD features versus 0.80 from sequence alone — and discarded its first 30 ns as equilibration, roughly 60× your entire production run. Measured pMHC half-lives are in *hours*; you would sample ~10⁻¹³ of that.

**Defensible:** "physics immediately rejects this pose." **Not defensible:** any claim about stability, affinity or immunogenicity.

**Kill criterion:** if a calibration run reports under 150 ns/day, cut MD and spend the time on the demo.

---

## 6D. ⚠️ The hardware fault, and the fix

The Nano powered itself off ~11 times during development. Diagnosis, because it cost hours:

**It is a GPU boost-clock fault.** Capping the maximum SM clock at **2,500 MHz** stops it.

```bash
sudo nvidia-smi -lgc 300,2500      # does NOT survive a reboot -- re-apply after every boot
sudo nvidia-smi -rgc               # reset
```

**Evidence trail**, in case it recurs:

| Test | Result |
|---|---|
| 20-core CPU stress, 60 s | ✅ survived, 50–53 °C |
| `nvidia-smi` polling | ✅ survived |
| Sustained bf16 matmul, **53.4 TFLOPS** | ✅ survived, 42 W |
| 16 GB unified allocation | ✅ survived |
| Boltz-2 real workload | ❌ powered off |
| Boltz with `--no_kernels` | ❌ powered off (so **not** cuEquivariance) |

Never an Xid, thermal event, OOM or kernel panic — journald is persistent, so a panic would have been captured. Temps stayed 34–46 °C. The tell was in the telemetry: the GPU **auto-boosts to 2,522 MHz** at stock settings, just above 2,500. Note also that **GB10 exposes no software power cap** (`Power Limit: N/A`), so clock capping is the only software lever.

Two false leads worth recording so nobody re-runs them: it is *not* cuEquivariance (`--no_kernels` still died), and it is *not* concurrent load from another user (that only happened once, late).

**Also**: a reboot leaves **zero-byte JSON** in Boltz's `records/` cache, and every later run then dies in `Record.load` with a bare `JSONDecodeError`. Always run this before resuming:

```bash
find ~/neofold -name "*.json" -size 0 -delete
```

---

## 7. Recommended stack for the remaining build

| Layer | Choice | Note |
|---|---|---|
| Fast screen | **MHCflurry 2.2.0** ✅ **installed & validated** | PyTorch backend, no TensorFlow. In `~/neofold/.venv-mhc` on **CPU-only torch** — deliberately, so the GPU stays free for Boltz. Models fetched: 198 MB in `~/.local/share/mhcflurry`. 14,884 alleles. |
| Structure | **Boltz-2** | Installed and verified. MIT licensed — a real advantage over AlphaFold 3, whose weights are non-commercial. |
| 3D viewer | **Mol\* 5.11.0** vendored from npm | Zero external URLs in the CSS; verified offline-safe. Has a `plddt-confidence` theme that reads the B-factor column. |
| Local LLM | **Ollama** (arm64 build), `qwen3:8b` | Unload with `keep_alive: 0` before folding so it doesn't hold memory. **Verify `ollama ps` says `100% GPU`** — it can silently fall back to CPU on sm_121. |
| API | **FastAPI + single asyncio worker** | One worker serializes GPU access for free. Set `docs_url=None` — `/docs` pulls Swagger from jsDelivr at runtime. |

**Offline traps to disable:** Streamlit phones `api.segment.io` even with `gatherUsageStats=false`; Gradio *hangs* on blocked `fonts.googleapis.com`. Prefer plain HTML/JS.

**pLDDT scale trap:** the confidence JSON reports pLDDT on **0–1**, but the CIF B-factor column is **0–100**. Mol\*'s AlphaFold color bands expect 0–100. Use the B-factor column and your colors are correct for free.

---

## 8. Scaling story — what's true

- HP's datasheet says **1,000 TOPS FP4**, not "1 PFLOP". NVIDIA's petaFLOP figure carries a hidden *"with sparsity"* qualifier. Don't quote the PFLOP number unqualified.
- **NVIDIA's DGX Spark clustering exists to run models too big for one device — capacity, not throughput.** Your workload is independent jobs, so it needs none of that: a work queue and an SSH key. Say this crisply; it is a likely judge question.
- **The cloud-egress cost argument does not survive scrutiny** — a WES pair costs ~$5.40 to move. Lead with *governance* instead: local compute removes a data-use-agreement / institutional-certification step rather than merely satisfying one.
- **⛔ DNA is NOT one of HIPAA's 18 Safe Harbor identifiers.** Do not claim it is; it's checkable in the CFR and would damage credibility.
- Label every multi-node number **"projected from measured single-node throughput"**. You have one Nano.

---

## 9. What's left

**Done:**
- Phase 0 gate — Boltz-2 installed, offline prediction verified, 4-case benchmark, GPU telemetry
- Demo case chosen and validated to **0.49 Å** against crystal structure 6ULN
- MSAs generated, cached, and shown to improve accuracy at zero marginal cost
- MHCflurry installed, models fetched, and **validated against two published epitopes with a wild-type control**

**Next, in order:**
1. ~~MHCflurry~~ ✅ done
2. VCF → peptide windows (`research/neopep.py` is a starting point; the window logic in `screen_test.py` on the Nano already works)
3. FastAPI + job queue wrapping the verified Boltz call
4. Vendor Mol\*, render `cached_out/.../*.cif`
5. Ollama + local summary, with the `ollama ps` → `100% GPU` check
6. **Full offline rehearsal with the cable physically out**
7. Benchmark at 5 / 20 / 50 candidates for the scaling chart

**Unfinished:** the offline-with-dead-proxy verification run was interrupted when the Nano dropped off the network. Re-run `~/neofold/run_cached.sh` — it is written and ready.

**Pre-offline download checklist:** Boltz weights (~6.2 GB, cached in `~/.boltz`) ✅, MHCflurry models (198 MB) ✅, **MSA cache per HLA allele** ✅ for C\*08:02 — add any other allele you plan to demo, Ollama model ⬜, Mol\* bundle ⬜.

**Venue network warning:** the Nano dropped off Tailscale mid-session, along with several other machines on that tailnet simultaneously. Assume the venue network is unreliable — which is an argument *for* the project's premise, and a reason to have everything cached locally well before Saturday.

---

## 10. Research appendix

Four deep-dive documents in `research/`, ~4,200 lines, sourced:

| File | Contents |
|---|---|
| `research-boltz-gb10.md` | Boltz/GB10 install paths, MSA strategy, fallback models |
| `research-screen-and-data.md` | MHCflurry, 13 verified hotspot variants w/ GRCh38 coords, IMGT sequences, licensing, metric glosses |
| `research-app-stack.md` | Mol\* offline, Ollama on GB10, NVML telemetry code, offline traps |
| `research-scaling-and-pitch.md` | HP/NVIDIA spec verification, scaling math, 28-question judge Q&A bank |

Artifacts on the Nano: `~/neofold/` — `cases/*.yaml`, `bench/timings.csv`, `bench/gpu_trace.csv`, `bench/*/…/*.cif`.
