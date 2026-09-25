# The hardware, the edge argument, and how it scales

*What the HP ZGX Nano is, what we measured on it, why local compute is the right call here, and the fault we had to diagnose to get any of it done.*

---

## 1. The machine

| | |
|---|---|
| **System** | HP ZGX Nano |
| **Superchip** | NVIDIA GB10 Grace Blackwell — 20-core Arm (10× Cortex-X925, 10× Cortex-A725), 16 MB L2, Blackwell GPU |
| **Memory** | 128 GB LPDDR5x "coherent unified system memory" (HP's phrase) — 121 GB visible to the OS |
| **Memory bandwidth** | up to 273 GB/s over a 256-bit LPDDR5X-8533 interface |
| **Vendor AI rating** | 1,000 TOPS FP4 |
| **OS** | Ubuntu 24.04.5, aarch64 |
| **Driver / CUDA** | 580.173.02 / CUDA 13.0 |
| **Form factor** | desktop; runs off a wall socket |

### On the "1 petaFLOP" figure — say this before a judge does

HP's datasheet says **1,000 TOPS FP4**. It does not say "1 PFLOP" anywhere. The petaFLOP number is NVIDIA's, and it carries a qualifier that usually gets dropped:

> "Up to 1,000 TOPS inference and up to 1 PFLOP at FP4 precision **with sparsity**"

Two things follow. **1,000 TOPS and 1 PFLOP are the same 10¹⁵ ops/s**, expressed as integer versus floating-point — they are not two additive capabilities, and a slide claiming both is wrong. And the figure assumes 2:4 structured sparsity; dense FP4 is half of it.

Our workload runs in **BF16**, so neither number is ours. What we measured:

> **53.4 TFLOPS sustained BF16** — 8192³ matmul, 30 iterations.

Volunteering this converts the most obvious attack on an edge-hardware pitch into a credibility win.

### And the honest weakness

**273 GB/s is modest.** An H100 has 3.35 TB/s — about 12× more. Boltz-2 inference is attention- and bandwidth-bound, so a single datacentre GPU beats a Nano per-unit by a wide margin, and we say so. The Nano's advantage is capacity, deployability, and power — not raw speed. 121 GB of unified memory on a desk that draws 38 W under load is a genuinely different kind of machine, and pretending it is fast instead is the wrong argument.

---

## 2. What we measured

Every number here was taken on the Nano during development. Nothing is estimated; projections are in §6 and are labelled.

### Structure prediction

| Configuration | Residues | MSA | Wall time |
|---|---|---|---|
| G-domain crop, single-sequence | 189 | — | 44 s |
| Full complex, minimal sampling (`--recycling_steps 0 --sampling_steps 10`) | 383 | — | 39 s |
| Full complex, single-sequence | 383 | — | 55 s |
| **Full complex, cached MSA** ← the production setting | **383** | cached | **62–66 s** (mean **64.3 s**, n=7) |
| Full complex, MSA generated online | 383 | generated | 132 s |
| **Full pMHC:TCR complex** | **812** | cached | **133 s** |
| **Offline proof**, all egress blocked | 383 | cached | **64 s** |

Two things this table says:

**MSA caching is the single biggest lever.** Generating an MSA doubles the job. The HLA α-chain and β2M MSAs are identical for every candidate from one patient, so you pay once and reuse. That is why the offline run is not slower than the online one.

**Scaling with size is roughly linear at this range.** 812 residues in 133 s against 383 in 64 s — 2.1× the residues, 2.1× the time. Useful, and not what you would get from a quadratic-attention model without optimisation.

### Where the time actually goes

From the run logs, which report inference separately from wall time:

| | |
|---|---|
| Inference, single-sequence | 27 s |
| Inference, with MSA | 32 s |
| **Fixed overhead** | **32 s** |

Half the job is process start, loading a 2.3 GB checkpoint, and writing output. That overhead is **per invocation**, which is exactly what batching amortises — see §6.

### Telemetry under load

| | Measured |
|---|---|
| GPU utilisation, peak | **96%** |
| Power, peak | **38 W** (42.2 W on the 812-residue complex) |
| Power, idle | 3.5 W |
| Temperature, peak | **46 °C** |
| Process GPU memory | 2,304 MiB |

38 watts. A gaming laptop charger is 180 W. This is the number that makes "one per lab bench" a sentence you can say without flinching.

A GB10 quirk worth knowing: **`nvidia-smi --query-gpu=memory.total` returns N/A** on unified memory — there is no discrete framebuffer to report. Per-process memory via `--query-compute-apps` works. `telemetry.py` handles both.

### The screening stage (CPU)

| | |
|---|---|
| Throughput | ~430 peptides/s |
| Demo run | 50 variants → **1,890 candidates in 8.8 s** |
| Predictions performed | 3,780 — mutant *and* germline for every candidate |

No GPU. MHCflurry 2.2.1 on the PyTorch backend, which matters because the TensorFlow backend does not build cleanly on aarch64.

### The local language model

| | |
|---|---|
| Model | qwen3:8b |
| Backend | Ollama, CUDA (cuda_v13) |
| Placement | **100% GPU** |
| Throughput | 5.7 tok/s |
| GPU utilisation | 91% |
| Power | 29.3 W |
| SM clock | 2,411 MHz |
| Unload | `keep_alive: 0` frees the GPU for Boltz in ~3 s |

5.7 tok/s is slow — this is a bandwidth-bound decode workload on a 273 GB/s bus, and it shows. For a 4-second paragraph it does not matter. The `keep_alive: 0` detail does matter: without it, Ollama holds GPU memory and the next Boltz job contends with it.

---

## 3. Why the edge, honestly

This is where edge-AI pitches usually overreach, so here is the argument with the weak parts removed first.

### What we do **not** claim

**❌ "Cloud egress is prohibitively expensive."** A whole-exome tumour/normal pair is about 60 GB. AWS egress at $0.09/GB is **$5.40**, and the first 100 GB/month is free. A judge with an AWS bill would laugh, correctly. *(The 2024 egress waivers do not rescue the argument in the other direction either — they apply only to full migration off a provider, require approval, and run a 60–90 day clock.)*

**❌ "DNA is one of HIPAA's 18 Safe Harbor identifiers."** It is not. 45 CFR 164.514(b)(2)(i) lists (A) through (R); item **(P) is "Biometric identifiers, including finger and voice prints."** It does not say DNA. This claim circulates widely and is checkable in the CFR in about thirty seconds.

**❌ "Regulations prohibit genomic data in the cloud."** False. NIH explicitly contemplates cloud use under its security best practices, and all three hyperscalers host dbGaP-authorised workloads under BAAs.

### What we **do** claim

**Moving the file converts a local computation into a regulated disclosure.**

Tumour/normal sequencing data is controlled-access by construction. Sending it to an external processor adds a Data Use Certification, a Data Access Committee review, and an institutional signing official — process steps that exist whether or not the destination is secure.

The HIPAA angle is subtler and more interesting than the crude version. Genetic information **is** PHI when individually identifiable and held by a covered entity. But because DNA is not on the Safe Harbor list, **you cannot de-identify a genome by deleting eighteen fields.** You fall back on (R)'s catch-all and on (b)(2)(ii)'s requirement of *"no actual knowledge that the information could be used… to identify an individual"* — which the re-identification literature makes hard to satisfy honestly. Gymrek *et al.* (*Science* 2013) inferred surnames from Y-STR markers via genealogy databases. *(Scope limit, stated before anyone else does: male subjects, germline Y-STRs, dependent on database coverage. "Any genome can be re-identified" is an overclaim.)*

So:

> **Local compute removes a governance step rather than satisfying one.** That is the claim, it is narrow, and it holds.

### The secondary benefits, in order of honesty

| Benefit | Strength |
|---|---|
| **No external processor in scope** | strong — this is the real argument |
| **Works with the network dead** | strong, and demonstrated: `scripts/verify_offline.sh` |
| **Fixed cost at cohort scale** | real but secondary — eight B200s list at $114/hour on AWS; spot is about a third |
| Latency | irrelevant. Nobody needs a shortlist in 50 ms. |
| Egress cost | negligible. We do not use it. |

### The offline proof

The demo UI shows a live **outbound connection count**, served from `/api/network`. It reads zero. That is not a decoration — it is why Mol\* is vendored, why `docs_url=None`, why no web fonts, and why MSAs are cached. Any one of those omissions would turn the badge red the moment egress is blocked.

---

## 4. Software: what aarch64 + CUDA 13 costs you

Most of the Python ML ecosystem assumes x86-64 and CUDA 12. Six install problems had to be solved. Full commands in [BUILD-GUIDE.md](../BUILD-GUIDE.md); the summary matters because "does the ecosystem work on ARM" is a fair question.

| Problem | Symptom | Fix |
|---|---|---|
| **Dataloader deadlock** | Boltz hangs forever at 0% GPU. No error, no timeout, no log line. | **`--num_workers 0`** |
| `gemmi==0.6.5` | No aarch64 wheel | gemmi 0.7.5 + `boltz --no-deps` |
| cuEquivariance | Hard CUDA-12 pin | install the `-cu13` packages; skip the `[cuda]` extra |
| Triton build | `Python.h: No such file` | `apt-get download` + `dpkg-deb -x` into `$HOME/pylocal`, then `CPATH` — **no sudo needed** |
| MHCflurry | TensorFlow backend won't build | PyTorch backend (2.2.1 supports it) |
| Zero-byte JSON after a hard power loss | Silent downstream parse failures | `find ~/neofold -name '*.json' -size 0 -delete` before resuming |

The deadlock deserves its emphasis. It is the worst failure mode in the whole build: no diagnostic, and it looks exactly like a slow model.

---

## 5. The power fault

Diagnosing this took most of a day and cost roughly eight unplanned reboots, so it is written down.

### Symptom

The machine powers off mid-job. Not a crash — a power-off.

- No `Xid` error
- No thermal event in the logs (peak recorded 46 °C)
- No kernel panic, no OOM killer
- The log simply **stops mid-write**

### What it was not

I proposed two causes and was wrong twice.

**"cuEquivariance kernels."** Plausible — a custom CUDA kernel on a brand-new architecture. Running with `--no_kernels` still died.

**"A teammate's concurrent GPU benchmark."** Also plausible, also wrong. The user corrected this directly: *"he only ran it once and that was this time that's all, it is definitely not the cause."* Correlation, one data point, confidently misread.

### What it was

The user asked the question that solved it: *"what was the max GPU clock speed you were setting, did you set it higher than 2500?"*

I had set nothing. **The GPU auto-boosts to 2,522 MHz**, and at that clock the transient current draw exceeds what the supply can deliver. The machine does not crash; it browns out.

### The fix

```bash
sudo nvidia-smi -lgc 0,2450
```

**This does not survive a reboot.** Re-apply after every boot. The demo checklist has it as a pre-flight step.

Working recipe: **cap the clocks, and run one job at a time.** Under that discipline: **12 consecutive structure predictions, zero reboots.**

### Why it is in the documentation

Because the two wrong diagnoses are more instructive than the right one. Both were reasonable inferences from thin evidence, stated with more confidence than the evidence supported. The correct diagnosis came from the person with physical access, asking about the one variable I had not considered because I had not set it.

---

## 6. Scaling

### Measured: batching on one node

The 32-second fixed overhead is per-invocation, not per-candidate. Five candidates in a single Boltz process load the checkpoint once:

| | Sequential | **Batched (n=5)** |
|---|---|---|
| Per candidate | 64.3 s | **36.0 s** |
| Per hour | 56 | **100** |
| Speedup | — | **1.79×** |

**This is measured, not projected.** 180 s of wall time for five candidates. A 1.79× throughput gain from a scheduling change with no accuracy cost.

That 100/hour figure is the useful one for a claim about practicality: a tumour producing 22 predicted-presented candidates is **13 minutes of GPU time**.

### Projected: multiple nodes

Candidates are independent jobs. There is no gradient to synchronise and no shared state, so more Nanos is a work queue, not a rewrite:

| Nodes | Candidates/hour | Status |
|---|---|---|
| 1 | **100** | **measured** |
| 2 | ~200 | projection |
| 4 | ~400 | projection |

**We had one Nano.** Every multi-node number in the UI is labelled a projection, and there is a reason to be careful even about linear scaling. Published DGX Spark cluster work measures **NCCL all-reduce bus bandwidth at ~10.2 GB/s — about 40% of raw RDMA** — because GPUDirect RDMA does not engage, so tensor data makes an extra hop through system memory. That is a serious constraint for *distributed inference on one model*. It is close to irrelevant for *independent jobs on a queue*, which is our case — but the distinction is exactly the kind of thing that separates a projection you can defend from one you cannot.

### What erodes the projection

Named, because a projection without failure modes is a guess:

- Per-invocation model load (32 s) unless jobs are batched in one process
- Queue and scheduling overhead
- Storage I/O when writing many structures
- Sustained thermal and power behaviour over long runs — **especially given §5**

### The stage the GPU is not the bottleneck for

Worth keeping in proportion: the screen handles 1,890 candidates in 8.8 s on CPU. Structure prediction is only ever applied to a shortlist of ~5. **The GPU is not the throughput bottleneck for a single patient — it is what makes the evidence layer possible at all.** If you wanted to fold all 1,890, that would be 19 hours batched, and the honest answer is that you would not, because confidence does not discriminate (see [SCIENCE.md](SCIENCE.md) §2) so the structures would not help you rank.

---

## Sources

- HP ZGX Nano QuickSpecs, document c09212373 — the "128 GB LPDDR5x coherent unified system memory" wording is HP's own.
- NVIDIA DGX Spark hardware documentation — 273 GB/s over 256-bit LPDDR5X-8533; the FP4-with-sparsity qualifier.
- 45 CFR 164.514(b)(2) — HIPAA de-identification, Safe Harbor list (A)–(R).
- 78 FR 5566 — HIPAA Omnibus Final Rule, 2013-01-25.
- Gymrek *et al.*, "Identifying Personal Genomes by Surname Inference", *Science* 339:321 (2013), DOI 10.1126/science.1229566.
- NIH Genomic Data Sharing Policy, NOT-OD-14-124; dbGaP two-tier controlled access.
- GA4GH Framework for Responsible Sharing of Genomic and Health-Related Data, *The HUGO Journal* 8:3 (2014).
