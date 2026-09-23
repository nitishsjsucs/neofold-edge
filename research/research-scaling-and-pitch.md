# NeoFold Edge — Scaling, Benchmark & Pitch-Credibility Research

**Compiled:** 2026-09-22 · **Target:** Edge AI Hack 2026 (SJSU), final 2026-09-26 · **Platform:** 1× HP ZGX Nano G1n AI Station (NVIDIA GB10)

## How to read this document

Every factual line is tagged with one of three labels. **Use these tags verbatim on your slides.** The single fastest way to lose a technical judge is to present a projection as a measurement.

| Tag | Meaning | Slide rule |
|---|---|---|
| **[MEASURED]** | You ran it on your own hardware and have the log | Show the command and the raw output |
| **[VENDOR]** | HP or NVIDIA published claim — not independently verified by you | Say "HP claims" / "NVIDIA specs say" out loud |
| **[THIRD-PARTY]** | Published by an independent reviewer/researcher, not by you, not by the vendor | Name the source on the slide |
| **[PROJECTION]** | A model, not an observation | Put the word PROJECTED on the slide in the same font size as the number |

---

## ⚡ Executive summary — the twelve things that change what you say

1. **HP never claims "1 PFLOP."** HP's datasheet says **1,000 TOPS FP4**. The petaFLOP figure is NVIDIA's, and it carries the qualifier *"at FP4 precision **with sparsity**."* They are the same 10¹⁵ ops/s, not two separate capabilities. (§1.2)
2. **🔴 NVIDIA explicitly supports GB10/DGX Spark for Boltz-2** — *"Added support for GB10 DGX Spark SKUs with sequence lengths up to 1536 residues."* Your ARM64 container risk is far lower than expected. (§5.1)
3. **🚨 But the MSA Search NIM wants 24 CPU cores and the Nano has 20**, plus 1,660 GB of database on NVMe. **The MSA stage, not the GPU, is your bottleneck and your day-1 risk.** (§5.1, §5.7a)
4. **NVIDIA's clustering is for models too big for one box**, verbatim: *"workloads that cannot fit onto a single device."* Ours is the opposite shape. Make the distinction proactively — it makes your scaling story stronger, not weaker. (§2.3)
5. **⛔ DNA is NOT one of HIPAA's 18 Safe Harbor identifiers.** Item (P) is fingerprints and voice prints. Saying otherwise in front of a compliance-literate judge is fatal. (§4.4)
6. **The egress-cost argument does not work.** A WES tumour/normal pair costs ~$5.40 to move, and AWS gives 100 GB/month free. **Your argument is governance, not dollars.** (§4.5)
7. **NVIDIA's own runtime docs make your architecture argument for you:** *"Ray does not split one prediction across multiple GPUs or reduce its individual latency."* (§5.2)
8. **Power is hard to measure on GB10.** NVIDIA: *"the wattage displayed measures only GPU power."* Borrow a $20 wall meter or drop the energy metric. (§7.2)
9. **⭐ The licensing card is your best slide.** AlphaFold3's **weights** are non-commercial, non-redistributable, *"only… if received directly from Google,"* and *"not intended, validated, or approved for clinical use."* **Boltz is MIT — code and weights, commercial use included.** That's not a preference, it's the only option for something that wants to become a product. (§B5)
10. **⭐ Memorise the 6%.** TESLA: 25 expert groups, 608 top-ranked neoantigens, **37 immunogenic**. That's the state of the art, and quoting it makes you the most credible team in the room. (§B3)
11. **🔴 You cannot HLA-type from a VCF.** Every production typer needs reads. pVACseq takes HLA alleles as a *required user-supplied argument*. This is a favourite trap question — put your assumption on the architecture slide. (§B6)
12. **🔴 Structure probably does NOT improve ranking, and you must not claim it does.** The best pro-structure result drops from AUC 0.73 in-sample to **0.60 held-out**; a 0.46 Å pMHC modelling pipeline still lost to NetMHCIIpan-4.0 because data beats structure. **Position structure as the explanation layer, not the discriminator.** (§B8)

**Numbers to delete from any draft slide:** "20 seconds per Boltz-2 affinity prediction" (unverifiable), "NA12878 BAM 233 GB" (traces to a patent filing), MHCflurry ">7,000 predictions/sec" (unverified, and it's a v1.2.0 figure), "6–8 week vaccine turnaround" (secondary sources only — use the peer-reviewed 9.4 weeks), any cloud latency figure you did not measure.

---

# 1. HP ZGX Nano G1n spec verification

## 1.1 What HP actually says (primary source)

HP's own datasheet (document c09208797, dated April 2026) is the authoritative marketing document. I downloaded and read all 5 pages.

**Source:** HP ZGX Nano G1n AI Station Datasheet — https://h20195.www2.hp.com/v2/GetPDF.aspx/c09208797
**Source:** HP product page — https://www.hp.com/us-en/workstations/zgx-nano-ai-station.html

### Verified spec table

| Spec | HP's stated value | Tag | Notes / corrections |
|---|---|---|---|
| Superchip | "NVIDIA GB10 Grace Blackwell Superchip (20-core Arm, 10 Cortex-X925, 10 Cortex-A725, 16 MB L2 cache) with NVIDIA Blackwell GPU Architecture" | [VENDOR] | ✅ Claim confirmed exactly |
| Unified memory | "128 GB LPDDR5x (unified, onboard)" | [VENDOR] | ✅ Confirmed. HP's **QuickSpecs** (doc c09212373, https://h20195.www2.hp.com/v2/GetDocument.aspx?docname=c09212373) uses the exact phrase **"128 GB LPDDR5x coherent unified system memory"** in three separate places — so "coherent unified" is HP's own wording and is safe to quote verbatim. |
| Memory bandwidth | "Memory bandwidth up to 273 GB/s" | [VENDOR] | ✅ Confirmed — and **note the "up to"**. NVIDIA's DGX Spark hardware page gives the same 273 GB/s over a 256-bit LPDDR5X-8533 interface. |
| AI performance | "1,000 TOPS of FP4 AI performance" | [VENDOR] | ⚠️ **CORRECTION: HP never says "1 PFLOP" anywhere in the datasheet.** HP says 1,000 TOPS FP4. |
| Storage | "2 TB PCIe NVMe OPAL M.2 SSD" or "4 TB PCIe NVMe OPAL M.2 SSD" | [VENDOR] | ✅ Confirmed. Footnote 3: *"2TB or 4TB storage configuration must be selected at time of purchase."* Not user-upgradable at order time. |
| Networking | "NVIDIA ConnectX-7 200 GbE Ethernet Controller"; ports: "2 QSFP 200 Gbps signaling rate"; "1 RJ-45 (10Gbps)"; LAN: "Realtek RTL8127 10 GbE Ethernet Controller" | [VENDOR] | ✅ ConnectX-7 confirmed by name in HP's spec table |
| Wireless | "WLAN: AzureWave AW-EM637-NV Wi-Fi 7 and Bluetooth 5.4"; also *"Available in certain countries without WLAN and Bluetooth Module"* | [VENDOR] | There is a **radio-free SKU** — HP markets it as "HP ZGX Nano for Secure & Regulated Environments … without bluetooth or WiFi radios, designed for environments with heightened security requirements." **This is a gift for our pitch — see §4.5.** |
| Power | "240W external USB Type-C power adapter, 89% efficiency, active PFC" | [VENDOR] | ✅ |
| OS | "NVIDIA DGX OS" (datasheet); reviewers add Ubuntu 24.04 | [VENDOR] | **No Windows support.** ARM64/aarch64 only. |
| Dimensions | 150 × 150 × 51 mm (5.9 × 5.9 × 2.01 in) without feet | [VENDOR] | ✅ |
| Weight | "Starting at 2.76 lb; Starting at 1.25 kg" | [VENDOR] | ✅ |
| Compliance | "TAA compliant" | [VENDOR] | Relevant for US federal/health-system procurement |

### The 200B / 405B claims — exact quotes

> **"Unified system memory** — Run AI development and testing workloads with AI models of up to 200 billion parameters at your desk with 128 GB of coherent unified system memory."
> — HP ZGX Nano G1n Datasheet, p.2

> **"NVIDIA ConnectX Networking** — Work with even larger AI models locally—up to 405 billion parameters—by connecting two HP ZGX Nano systems together to scale local compute resources.⁴"
> — HP ZGX Nano G1n Datasheet, p.2

> **Footnote 4:** "Requires compatible QSFP cable. Sold separately."
> — HP ZGX Nano G1n Datasheet, p.5

**Analysis — what HP does and does not commit to:** [VENDOR]

- HP's *only* qualification on the 405B claim is that you need to buy a cable. HP does **not** state the quantisation, the software stack, the context length, or the achievable tokens/sec. A 405B-parameter model in 256 GB of combined memory necessarily implies roughly 4-bit quantisation (405B params × 4 bits ≈ 203 GB, before KV cache) — HP leaves this unsaid.
- HP does **not** claim you can connect *more* than two units. NVIDIA does (see §2).
- **Do not repeat the 405B number on stage.** It is irrelevant to our workload (we run many small models, not one huge one) and inviting a judge to probe it is a self-inflicted wound. See §2.4.

## 1.2 The "1 PFLOP" figure — where it comes from and its hidden qualifier

HP says **1,000 TOPS FP4**. NVIDIA's DGX Spark documentation says:

> "Up to 1,000 TOPS (trillion operations per second) inference and up to 1 PFLOP (petaFLOP) at FP4 precision with sparsity"
> — NVIDIA DGX Spark User Guide, Hardware Overview, https://docs.nvidia.com/dgx/dgx-spark/hardware.html

**Two things a judge can catch you on:** [VENDOR]

1. **"with sparsity."** The 1 PFLOP figure assumes 2:4 structured sparsity. Dense FP4 is half that. Neither number is achievable by a structure-prediction model that runs in BF16/FP16.
2. **1,000 TOPS and 1 PFLOP are the same number**, expressed as integer-ops vs floating-point-ops (both 10¹⁵ ops/s). They are not additive. If a slide says "1000 TOPS **and** 1 PFLOP" as two capabilities, that's a mistake.

**Safe phrasing:** *"NVIDIA rates the GB10 at up to 1 petaFLOP of FP4 with sparsity. Our workload runs in BF16, so that number is not our number — here is what we actually measured."* Then show your measurement. Saying this unprompted converts a vulnerability into a credibility win.

## 1.3 ZGX Nano vs. DGX Spark — HP's build of an NVIDIA reference design

**This distinction matters and you should state it proactively.** The ZGX Nano G1n is HP's implementation of NVIDIA's GB10 / DGX Spark reference design. Silicon, memory, and NIC are NVIDIA's; the chassis, BIOS/firmware security, service contract and the "ZGX Toolkit" software layer are HP's.

> "all of the GB10 SFF systems [are] remarkably consistent from one vendor to another." HP's differentiation comes through "support and services."
> — ServeTheHome, HP ZGX Nano G1n Review, https://www.servethehome.com/hp-zgx-nano-g1n-review-the-hp-take-on-the-nvidia-gb10/ [THIRD-PARTY]

**Practical consequence for us:** NVIDIA's DGX Spark documentation, playbooks and container images apply to the ZGX Nano. When a judge asks "where are your docs for clustering," the correct answer is *NVIDIA's DGX Spark docs*, not HP's. Good news for a 4-day build; also means **don't credit HP for GB10 silicon performance** in front of an HP-sponsored panel — credit HP for the things HP actually built (see §1.4).

## 1.4 What is genuinely HP-specific (worth saying at an HP-sponsored hack)

These are HP contributions, verifiable, and not NVIDIA's: [VENDOR] / [THIRD-PARTY]

- **Self-encrypting OPAL NVMe as the factory default.** Datasheet: "2 or 4 TB of NVMe M.2 self-encrypted storage to work efficiently with large files and keep more of your data local and secure." StorageReview confirms it is "factory-installed as a self-encrypting OPAL NVMe drive." — https://www.storagereview.com/review/hp-zgx-nano-g1n-ai-station-review-a-secure-sustainable-desk-side-ai-node
- **TPM 2.0 in FIPS 140-2-certified mode, Common Criteria EAL4+**, BIOS-level secure boot and PXE controls. [THIRD-PARTY, StorageReview]
- **The radio-free SKU** for regulated environments (datasheet, p.2).
- **TAA compliance** (datasheet, p.4) — required for US federal procurement.
- **HP ZGX Toolkit** — "open-source frameworks, MLflow tracking, and Ollama testing… instant discovery, sync, and export." Footnote 1: provided free of charge; requires a client device running Windows 11 or Ubuntu 24.04 with VS Code.
- **Sustainability spec:** "40% post-consumer recycled plastic… at least 20% post-industrial recycled steel; 75% recycled aluminum" (datasheet, p.4).

For a clinical-genomics pitch, the SED + TPM + FIPS + no-radios + TAA combination is a *substantive* compliance story, not decoration. This is the strongest HP-specific angle available.

## 1.5 Independently measured figures (not vendor claims)

These come from StorageReview's review unit — **cite them as third-party, never as yours.**
Source: https://www.storagereview.com/review/hp-zgx-nano-g1n-ai-station-review-a-secure-sustainable-desk-side-ai-node [THIRD-PARTY]

| Metric | Measured value |
|---|---|
| Idle power | ~36–38 W |
| Peak system power | ~228 W |
| Thermal dissipation at peak | ~780 BTU/hr |
| CPU peak temp | 77.3 °C |
| GPU peak temp | 69 °C |
| Noise | 22 dBA idle / 27.6 dBA under load |
| GPUDirect Storage read | 4.6 GiB/s @16K blocks; 5.5 GiB/s plateau @1M blocks |
| GPUDirect Storage write | 3.3 GiB/s @16K; 3.7 GiB/s @1M |

The storage numbers are directly relevant: **if your pipeline's I/O stage runs slower than ~3 GiB/s you are not storage-bound**, and you can say so with a citation.

## 1.6 Price

- CDW lists the 4 TB config (CZ2V8UT#ABA) at **$4,206.99** — https://www.cdw.com/product/hp-zgx-nano-g1n-ai-station/8552279 [THIRD-PARTY reseller listing, 2026-09-22]
- HP's own store page did not return a machine-readable list price at time of research. **Use the reseller figure and label it as such.** For cost-per-candidate math (§7), a reseller price is defensible; an invented MSRP is not.

---

# 2. How two units actually connect — and why it is *not* what we need

## 2.1 The physical link

**Primary source:** NVIDIA DGX Spark User Guide → ConnectX-7 Networking — https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html [VENDOR]

Verbatim:

> "Each DGX Spark has two QSFP ports (sometimes called 'ConnectX-7 ports') on the back of the device. Each port provides up to 200 Gigabits per second (Gb/s), but the incoming speed is also determined by the cable that you use."

> "The QSFP ports support **Ethernet configuration only.** Approved cables are: Amphenol: NJAAKK-N911 (QSFP to QSFP112, 32AWG, 400mm, LSZH), NJAAKK0006 is the 0.5m version of this cable; Luxshare: LMTQF022-SD-R (QSFP112 400G DAC Cable, 400mm, 30AWG)"

> "Using a cable with higher speed is not beneficial, because the port itself is capped at 200 Gb/s."

**Is it RDMA?** Yes — RoCE (RDMA over Converged Ethernet), not native InfiniBand:

> "Each Ethernet interface has a corresponding RoCE interface (typically called a 'RoCE device') for InfiniBand communication."

**The PCIe topology gotcha** (worth knowing, it explains the bandwidth numbers below):

> "The NIC connects independently to the two external QSFP ports, and it connects to the SoC through **two independent PCIe Gen 5 x4 links.** As a result, each QSFP port has two PCIe addresses… Each QSFP port appears as **two independent Linux Ethernet interfaces.** As a result, plugging in two cables shows a total of four Linux Ethernet interfaces."

So one physical QSFP port = 2 Ethernet netdevs + 2 RoCE devices. NVIDIA's NCCL playbook confirms the consequence:

> "Full bandwidth can be achieved with just one QSFP cable. When two QSFP cables are connected, all four interfaces must be assigned IP addresses to obtain full bandwidth."
> — https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/nccl/README.md [VENDOR]

**Also note the cables are ~400 mm (0.4 m).** Two Nanos must physically sit next to each other. This is a *desk-side pair*, not a rack.

## 2.2 Topologies and node limits

**Source:** NVIDIA DGX Spark Playbooks — https://github.com/NVIDIA/dgx-spark-playbooks [VENDOR]

| Nodes | Topology | Playbook |
|---|---|---|
| 2 | Direct QSFP cable | "Connect Two Sparks" — https://build.nvidia.com/spark/connect-two-sparks/overview |
| 3 | Ring (3 cables, both ports on each unit) | "Connect Three DGX Spark in a Ring Topology" — https://build.nvidia.com/spark/connect-three-sparks/three-sparks-ring |
| 4 | Via a switch | NCCL playbook covers "two, three, or four DGX Spark systems" |

The "Connect Two Sparks" playbook's own description: [VENDOR]

> "Configure two DGX Spark systems for high-speed inter-node communication using 200GbE direct QSFP connections." … enabling "distributed workloads across multiple DGX Spark nodes by establishing network connectivity and configuring SSH authentication."

It sets up **network interfaces + passwordless SSH.** That is it. The NCCL playbook then builds NCCL from source with Blackwell support for "multi-node distributed training workloads," after which NVIDIA suggests you "try running a larger distributed workload such as TRT-LLM or vLLM inference."

## 2.3 What the clustering is FOR — the sentence that settles it

This is the single most important quote in this document:

> **"You can connect multiple DGX Spark systems with cables to create a cluster that allows you to run workloads that cannot fit onto a single device."**
> — NVIDIA DGX Spark User Guide, ConnectX-7 Networking, https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html [VENDOR]

**"Workloads that cannot fit onto a single device."** NVIDIA's clustering story is *capacity*, not *throughput*. It exists so a 405B-parameter model that does not fit in 128 GB can be sharded across 256 GB via tensor or pipeline parallelism, coordinated by Ray/NCCL under vLLM, SGLang or TensorRT-LLM.

### Measured reality of that interconnect [THIRD-PARTY]

An independent dual-node benchmark is worth knowing because it shows the interconnect is the weak point of model-parallel scaling:

| Test | Result |
|---|---|
| Raw RDMA (`ib_write_bw`) | ~197 Gb/s ≈ **24.6 GB/s** — near line rate |
| NCCL all-reduce bus bandwidth | **~10.2 GB/s** — ~40% of raw RDMA |
| NCCL send/recv (point-to-point) | ~9 GB/s |

Root cause given by the author: GPUDirect RDMA was not engaged (`GDR 0` in NCCL logs), so "GPU tensor data must travel through system memory before reaching the NIC — adding a PCIe copy step." Conclusion: "the effective GPU communication bandwidth available to vLLM is around 9–10 GB/s, not 25 GB/s."
Source: https://multimodalflow.net/en/blog/dgx-spark-dual-node-nccl-rdma/

Other independently reported figures cluster in the same region (~23.2 GB/s busbw on a 16 GB all_gather in one report; ~17 GB/s in a mixed DGX Spark ↔ EdgeXpert pairing per the NVIDIA developer forum — https://forums.developer.nvidia.com/t/dgx-spark-edgexpert-nccl-only-17-gb-s-over-200gbe/366055). **Treat all of these as indicative, not authoritative: they are individual user reports, and we have not reproduced any of them.**

## 2.4 The distinction to land in front of a judge

**Our workload is not NVIDIA's clustering use case, and that is a strength, not a gap.**

| | NVIDIA's DGX Spark clustering | NeoFold Edge |
|---|---|---|
| Why you'd add a second box | One model doesn't fit in 128 GB | You have more candidate peptides than one box can fold in the time available |
| What crosses the wire | Activations/KV cache, every forward pass, latency-critical | A job descriptor (a peptide sequence + HLA allele — **bytes**) and a result file (**a few MB**) |
| Bottleneck when you scale | Interconnect bandwidth (measured ~10 GB/s NCCL) | Job dispatch and shared storage |
| Required software | Ray + NCCL + vLLM/TRT-LLM/SGLang, RoCE tuning, topology-aware config | A work queue and SSH |
| Scaling behaviour | Sub-linear, interconnect-limited | **Near-linear, bounded by job granularity** |
| Failure mode | Whole model fails | One job retries |

**The line to say on stage:**

> "NVIDIA ships a clustering guide for DGX Spark, but it's for splitting a model too big for one box across several. We don't need it. Our workload is *embarrassingly parallel* — every peptide is folded independently, nothing crosses the wire but a job descriptor and a result file. So a second Nano needs a work queue and an SSH key, not NCCL, RoCE tuning and tensor parallelism. That's why our scaling story is *more* credible than a model-parallel one, not less."

**The follow-up a sharp judge will ask:** *"Then why buy a Nano at all — why not a cheap GPU?"* The answer is **not** speed. It is the 128 GB of coherent unified memory: it lets one box hold a folding model, a binding predictor, and a large working set simultaneously without swapping, at 240 W in 150 mm³. Be ready with your measured peak memory high-water mark (§7).

**Honest caveat to volunteer before you're asked:** we do not have two Nanos, so **every multi-node number in this deck is a projection from a single-node measurement**, computed with the model in §3.

---

# 3. A defensible scaling model

## 3.1 The workload's actual shape

NeoFold Edge per tumour sample:
1. **Serial head** — parse VCF/MAF, call variants→peptides, HLA handling, rank candidates. Runs once. Cost `t_head`.
2. **Parallel body** — fold/score `J` independent candidates. Each costs `t_job`. **No inter-job communication.**
3. **Serial tail** — aggregate, rank, render report. Cost `t_tail`.

This is a classic bag-of-tasks. The right model is **makespan**, not "speedup."

## 3.2 The formula

Let:
- `T₁` = **[MEASURED]** sustained single-node throughput in jobs/hour, from a batch run of ≥30 min with the model already resident
- `N` = number of Nanos
- `J` = number of candidate jobs in the batch
- `η` = scaling efficiency ∈ (0,1]

### Level 1 — the naive claim (state it, then immediately correct it)

```
T_N = N × T₁            ← only true as J → ∞ and with zero shared-resource contention
```

### Level 2 — granularity-corrected (this is the one to put on the slide)

Identical jobs, N workers, perfect dispatch, zero overhead. The last "round" is ragged:

```
Makespan(N) = t_head + ceil(J / N) × t_job + t_tail

Speedup_parallel_body(N) = J / ceil(J / N)      ≤ N
```

**This upper bound is free, exact, and honest.** It shows a judge you understand that N boxes do not help if you don't have N× the work.

### Level 3 — full model with contention

```
T_N = N × T₁ × η_gran × η_queue × η_io × η_thermal

where  η_gran    = J / (N × ceil(J/N))          ← exactly computable, no guessing
       η_queue   = dispatch/scheduling overhead
       η_io      = shared storage & DB contention
       η_thermal = sustained-vs-burst clock derating
```

### Level 4 — Amdahl's law on the end-to-end report (what the customer feels)

The serial head+tail never parallelises. If `s = (t_head + t_tail) / T_total_1node`:

```
End-to-end speedup(N) = 1 / ( s + (1 - s)/N )      and is capped at 1/s as N → ∞
```

**Report this number, not the parallel-body speedup.** If the serial stages are 20% of your wall clock, your end-to-end speedup with 2 nodes is 1.67×, not 2×, and with infinite nodes it is 5×. A judge who knows Amdahl will respect you for pre-empting this; if you claim 2.0× end-to-end they will assume you don't know.

*(For completeness: the Universal Scalability Law, `C(N) = N / (1 + α(N−1) + βN(N−1))`, adds a coherency term β. For independent jobs with no shared mutable state β ≈ 0 and USL collapses to the Amdahl form above. Mentioning that you checked β ≈ 0 and why is a strong signal. Source: Gunther, *Guerrilla Capacity Planning*.)*

## 3.3 Worked example

**Placeholder measurement — replace with your real number before the pitch.**

**[MEASURED]** `T₁ = 12 jobs/hour` sustained; `t_job = 5 min`; `t_head + t_tail = 6 min`; `J = 40` candidates.

Single node: `6 + ceil(40/1)×5 = 206 min` → 3 h 26 min end-to-end. `s = 6/206 = 2.9%`.

**[PROJECTION] 2 nodes:**
- `η_gran = 40 / (2 × ceil(40/2)) = 40/40 = 1.00` (perfect — 40 divides by 2)
- assume `η_queue = 0.98`, `η_io = 0.99`, `η_thermal = 0.97` → combined 0.94
- `T₂ = 2 × 12 × 0.94 = 22.6 jobs/hour`
- Makespan ≈ `6 + (20 × 5)/0.94 = 112 min` → **1 h 52 min**; end-to-end speedup **1.84×** (not 2.0×)

**[PROJECTION] 3 nodes, same J=40:**
- `η_gran = 40 / (3 × ceil(40/3)) = 40 / (3×14) = 0.952` ← **the ragged tail costs you 5% before any overhead**
- combined with 0.94 → 0.895
- `T₃ = 3 × 12 × 0.895 = 32.2 jobs/hour`; makespan ≈ `6 + 14×5/0.94 = 80 min`; speedup **2.58×**

Note the 3-node case is *worse than* 3× for a reason you can name precisely. That is the whole point of showing the formula.

## 3.4 Projecting to a bigger multi-GPU workstation

**You cannot multiply the Nano's throughput by GPU count.** You must cross two independent gaps: *more GPUs* and *different GPUs*.

```
T_workstation ≈ G × T₁ × (P_target / P_GB10) × η
```

where `P` is a **performance proxy you must name and justify**:

| If your workload is… | Use proxy P = | GB10 value |
|---|---|---|
| Memory-bandwidth-bound (most transformer decode) | memory bandwidth GB/s | **273 GB/s** [VENDOR] |
| Compute-bound (attention/Evoformer-style folding, large batch) | dense BF16/FP16 TFLOPS | — |
| Capacity-bound (does the working set fit?) | usable memory GB | **128 GB unified** [VENDOR] |

**This is where the Nano's honest weakness lives.** 273 GB/s is modest against a discrete datacentre GPU. If your pipeline is memory-bandwidth-bound, a single big GPU will beat a Nano per-unit by a wide margin and you must say so. **The Nano's win is capacity and deployability per watt and per cubic centimetre, not raw speed.** A judge will trust you far more if you concede this than if you don't.

**Minimum honest practice:** state the proxy, state the ratio, state that you did not run on the target hardware, and give a range rather than a point estimate.

## 3.5 What erodes near-linear scaling in practice

Ranked by how likely it is to bite *this* workload:

1. **Job granularity / ragged tail** — quantified exactly by `η_gran`. Biggest effect at small J. **Mitigation: make jobs small and numerous.**
2. **Shared reference-data access.** If every worker reads the same sequence DB or MSA cache over one NFS share, that share serialises you. This is the classic killer for folding pipelines, where MSA/database search is I/O- and CPU-bound rather than GPU-bound — **the MSA stage is the least parallel-friendly part of the whole pipeline.** Mitigation: replicate reference data to each node's local NVMe. The Nano has 2–4 TB of it; use it. (You have ~4.6 GiB/s local read headroom per §1.5.)
3. **Model load time.** Loading weights per job destroys throughput. Amortise with a **persistent warm worker** per node. State explicitly whether your `T₁` includes load time — if it doesn't, say so.
4. **Thermal/power derating.** GB10 SoC TDP is 140 W of a 240 W system budget [VENDOR, §7.2]; the ZGX Nano was independently measured at ~228 W peak and GPU 69 °C [THIRD-PARTY, §1.5]. There are active NVIDIA developer-forum threads about GB10 power/clock behaviour and performance variability (e.g. https://forums.developer.nvidia.com/t/dgx-spark-performance-degradation-gpu-power-draw-issue/361294). **Measure sustained, not burst.**
5. **Dispatch overhead** — negligible for minute-scale jobs; material if jobs are seconds.
6. **Head/tail serial fraction** — Amdahl cap, §3.2 Level 4.

## 3.6 What would make the projection DISHONEST

Print this list and check it before the pitch.

1. ❌ **Presenting a projection without the word "projected"** on the same slide, in the same weight as the number.
2. ❌ **Extrapolating from one warm job.** A single fast job ignores thermal derating, queue effects and variance. Minimum honest basis: a ≥30-minute sustained batch, reported as **median and p95**, never best-of-N.
3. ❌ **Timing with the model pre-loaded and presenting it as end-to-end.** Either include load time or state clearly that you excluded it.
4. ❌ **Claiming linear (η = 1.0).** Zero-overhead distributed systems do not exist, and `η_gran` alone is usually < 1. A projection with η = 1.0 is a tell that you never thought about it.
5. ❌ **Crossing GPU generations by TOPS ratio when the workload is memory-bound** (or by bandwidth ratio when it's compute-bound). Name your proxy or don't project.
6. ❌ **Projecting past your actual queue depth.** "We'd scale to 10 Nanos" is meaningless if a sample only ever produces 40 jobs — `η_gran` collapses.
7. ❌ **Quoting peak FP4-with-sparsity as if it were your achieved throughput** (§1.2).
8. ❌ **Citing someone else's benchmark as your measurement.** The StorageReview and NCCL numbers in this document are [THIRD-PARTY]. Say so.
9. ❌ **Inventing a cloud baseline to compare against** (§4 exists to prevent exactly this).
10. ❌ **Reporting a speedup without stating J.** Speedup is meaningless without the batch size it was computed at.

**The safe formulation:**

> "We measured X jobs/hour sustained on one Nano over a 30-minute batch. Our workload is embarrassingly parallel, so we *project* roughly 1.8–1.9× on two nodes for this batch size — not 2×, because the serial parse-and-rank stages don't parallelise and the last round is ragged. We have one Nano, so that second number is a model, not a measurement. Here's the formula."

---

# 4. Cloud-vs-edge comparison framing that survives scrutiny

**Rule zero: do not invent a cloud latency number.** Everything below is a published figure with a URL. Where a figure could not be verified it is marked ❌ and **must not be used**.

## 4.1 Real data sizes — measured from the NCI GDC corpus

Queried live from the **NCI GDC public files API** on 2026-09-22 (n=500 random files per stratum; "Files in GDC" is the true corpus count). API docs: https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/ [THIRD-PARTY, reproducible]

| Stratum | Files in GDC | p25 | **Median** | p75 | p90 |
|---|---|---|---|---|---|
| BAM, WXS (exome) | 49,218 | 16.3 GB | **30.4 GB** | 37.3 GB | 47.5 GB |
| BAM, WGS | 41,099 | 85.5 GB | **118.4 GB** | 197.9 GB | 391.3 GB |
| VCF, Annotated Somatic Mutation, WXS | 93,348 | 0.12 MB | **0.30 MB** | 1.36 MB | 3.01 MB |
| VCF, Raw Simple Somatic Mutation, WXS | 93,514 | 0.03 MB | **0.05 MB** | 0.34 MB | 0.64 MB |
| VCF, Annotated Somatic Mutation, WGS | 37,178 | 1.56 MB | **2.43 MB** | 7.74 MB | 19.2 MB |
| MAF, Masked Somatic Mutation (per-case) | 26,766 | 0.023 MB | **0.037 MB** | 0.095 MB | 0.19 MB |
| MAF, Aggregated Somatic Mutation (project-level) | 44,770 | 0.148 MB | **0.226 MB** | 0.352 MB | 0.564 MB |

**Three caveats you must state:**
1. Each GDC BAM is **one aliquot**. A tumour/normal *pair* is two files → **WES pair ≈ 60 GB median, WGS pair ≈ 240 GB median.**
2. **The GDC stores zero CRAM files.** Its BAMs are uncompressed-reference, which is why WGS medians are ~118 GB rather than ~40–60 GB.
3. Compression format changes the headline by 2–3×. Bonfield JK, "CRAM 3.1: advances in the CRAM file format," *Bioinformatics* 38(6):1497–1503 (2022), DOI 10.1093/bioinformatics/btac010 — https://pmc.ncbi.nlm.nih.gov/articles/PMC8896640/ — states CRAM 3.1 is *"50–70% smaller than the corresponding BAM file."* So "118 GB" and "~35–60 GB" are both true for the same WGS sample. **Say which you mean.**

**The Gb/GB trap — the single likeliest way a genomics-literate judge catches you.** Illumina's NovaSeq X Plus specification page (https://www.illumina.com/systems/sequencing-platforms/novaseq-x-plus/specifications.html) states: *"Human genomes assumes > 120 Gb of data per sample to achieve 30× genome coverage"* and *"Exomes assumes ~11.3 Gb or ~56.5M paired reads per sample to achieve 100x coverage."* **Those are gigaBASES, not gigabytes.** Do not convert them 1:1.

**❌ Do not cite:** the widely circulated "NA12878: SAM 966 GB / BAM 233 GB / CRAM 155 GB" table — it traces to a patent filing, not to Broad or the 1000 Genomes Project. Also unverified: a "~65 GB per sample at 35×" figure attributed to *Sci Rep* 2025 (DOI 10.1038/s41598-025-00491-8) — paywalled, not opened.

## 4.2 Real cloud egress pricing

### AWS — data transfer OUT to internet, us-east-1 [VENDOR, published]
Source: https://aws.amazon.com/ec2/pricing/on-demand/

| Tier | $/GB |
|---|---|
| First 100 GB/month (all regions, all services) | **$0.00** |
| Next 10 TB/month | **$0.09** |
| Next 40 TB/month | **$0.085** |
| Next 100 TB/month | **$0.07** |
| > 150 TB/month | **$0.05** |

> "AWS customers receive 100 GB of free data transfer out to the internet free each month, aggregated across all AWS Services and Regions (except China and GovCloud)."

### Google Cloud — Premium Tier internet egress, per GiB/month [VENDOR, published]
Source: https://cloud.google.com/vpc/network-pricing

| Destination | 0–1 GiB | 1–1,024 GiB | 1,024–10,240 GiB | >10,240 GiB |
|---|---|---|---|---|
| North America | free | **$0.12** | **$0.11** | **$0.08** |
| Europe | free | $0.12 | $0.11 | $0.085 |
| Australia / Korea / Indonesia / South America / Saudi | — | $0.19 | $0.18 | $0.15 |

Standard Tier is cheaper ($0.085 / $0.065 / $0.045 by tier). **Inbound transfer is free** — uploading to the cloud costs nothing; only getting results out is billed.

### The 2024 "exit fee" waivers — know these before a judge raises them
- AWS, 2024-03-05: *"starting today, we're waiving data transfer out to the internet (DTO) charges when you want to move outside of AWS"* — https://aws.amazon.com/blogs/aws/free-data-transfer-out-to-internet-when-moving-out-of-aws/. The post says the move *"follows the direction set by the European Data Act."*
- Google, 2024-01-11: free transfer when migrating off Google Cloud — https://cloud.google.com/blog/products/networking/eliminating-data-transfer-fees-when-migrating-off-google-cloud
- Legal driver: **EU Data Act, Regulation (EU) 2023/2854** (article text not independently fetched — cite EUR-Lex if you need a specific article).

⚠️ **Both waivers require a support request, approval, and completion of a full exit within 60–90 days. They do not apply to routine pipeline egress.** If you imply they do, or if you imply egress is unavoidably expensive, a cloud-literate judge will correct you either way.

## 4.3 Real published GPU instance pricing

### AWS on-demand, Linux, us-east-1 [VENDOR, published]
Source: https://aws.amazon.com/ec2/pricing/on-demand/

| Instance | GPUs | $/hr on-demand | ≈$/GPU-hr |
|---|---|---|---|
| `p6-b300.48xlarge` | 8× B300 (Blackwell Ultra) | **$142.416** | $17.80 |
| `p6-b200.48xlarge` | 8× **B200 (Blackwell)** | **$113.933** | **$14.24** |
| `p5en.48xlarge` | 8× H200 | $63.296 | $7.91 |
| `p5.48xlarge` | 8× H100 | $55.04 | $6.88 |
| `p5.4xlarge` | **1× H100** | **$6.88** | $6.88 |
| `p4d.24xlarge` | 8× A100 40GB | $21.958 | $2.74 |
| `g6e.xlarge` | 1× L40S | $1.861 | $1.86 |

### Google Cloud [VENDOR, published]
Source: https://cloud.google.com/products/compute/pricing/accelerator-optimized

| Machine type | GPUs | On-demand $/hr |
|---|---|---|
| `a4-highgpu-8g` | 8× B200 | **no on-demand rate published** — DWS Flex-start $64.44/hr; Spot $39.63/hr; 3-yr CUD $56.71/hr |
| `a3-ultragpu-8g` | 8× H200 | $84.807 (Spot $50.874) |
| `a3-highgpu-8g` | 8× H100 | $88.490 (Spot $52.962) |
| `a2-ultragpu-1g` | 1× A100 80GB | $5.069 |

⚠️ **Mandatory disclosure if you use these:** these are on-demand **list** prices. Spot and committed-use are 30–60% lower (GCP's 8×B200 Spot is $39.63/hr vs AWS's $113.93/hr on-demand list). **Quoting on-demand list against a purchased box you got for free is the most attackable number you could put on a slide.** If you do a cost comparison, show the spot price too. ❌ Also: `p5e.48xlarge` is not offered in us-east-1/us-west-2 — the "$1.84/hr" figure on third-party aggregator sites is an artifact.

## 4.4 Regulatory and privacy framing — primary sources only

### HIPAA de-identification: 45 CFR 164.514 [PRIMARY — verbatim from the CFR]
Source: https://www.ecfr.gov/current/title-45/section-164.514 (also https://www.govinfo.gov/content/pkg/CFR-2024-title45-vol2/xml/CFR-2024-title45-vol2-sec164-514.xml)

**(b)(2)(i) Safe Harbor enumerates 18 identifiers, (A) through (R).** They are: names; geographic subdivisions smaller than a State; dates (except year) and ages over 89; telephone; fax; email; SSN; medical record numbers; health plan beneficiary numbers; account numbers; certificate/license numbers; vehicle identifiers; device identifiers; URLs; IP addresses; **(P) "Biometric identifiers, including finger and voice prints"**; full-face images; and **(R) "Any other unique identifying number, characteristic, or code."**

> ### ⛔ **DNA, genome, and genetic sequence are NOT on the Safe Harbor list.**
> Item (P) reads only *"Biometric identifiers, including finger and voice prints."* It does not say DNA. Many blog posts claim otherwise; the regulation does not. **Saying "DNA is one of HIPAA's 18 identifiers" in front of a compliance-literate judge destroys your credibility on everything else you say.**

The clause that actually bites is **(b)(2)(ii)**: the covered entity must have *"no actual knowledge that the information could be used alone or in combination with other information to identify an individual."* Combined with the re-identification literature below, that is hard to satisfy honestly for a genomic file.

The alternative route, **(b)(1) Expert Determination**, requires a qualified person to determine *"that the risk is very small that the information could be used, alone or in combination with other reasonably available information, by an anticipated recipient to identify an individual"* and to document the method.

### Genetic information IS health information — the GINA amendment [PRIMARY]
Source: **78 FR 5566**, HIPAA Omnibus Final Rule, 2013-01-25 — https://www.govinfo.gov/content/pkg/FR-2013-01-25/html/2013-01073.htm

Amended 45 CFR 160.103:
> **"Health information means any information, including genetic information, whether oral or recorded in any form or medium…"**
> **"Genetic test means an analysis of human DNA, RNA, chromosomes, proteins, or metabolites, if the analysis detects genotypes, mutations, or chromosomal changes."**

**The precise, defensible position:** genetic information is PHI *when individually identifiable and held by a covered entity* — **but** the Safe Harbor list doesn't name DNA, so you cannot de-identify a genome by deleting 18 fields. That tension is the honest story, and stating it precisely is far more impressive than the crude version.

⚠️ HHS.gov's de-identification guidance page returned HTTP 403 to all retrieval attempts, so OCR's commentary on genomic data under Safe Harbor is **unverified**. Use the CFR and Federal Register text above instead — both are authoritative.

### Genomic re-identification literature [PRIMARY]

1. **Gymrek M, McGuire AL, Golan D, Halperin E, Erlich Y.** "Identifying Personal Genomes by Surname Inference." *Science* 339(6117):321–324 (2013). DOI **10.1126/science.1229566** — https://www.science.org/doi/10.1126/science.1229566
   Recovered surnames by profiling **Y-chromosome STRs** against recreational genealogy databases, then combining with age and state.
   ⚠️ **Scope limit — state it before a judge does:** male subjects only, germline Y-STR markers, dependent on genealogy-database coverage. **"Gymrek showed any genome can be re-identified" is an overclaim.**

2. **Homer N, Szelinger S, Redman M, et al.** "Resolving Individuals Contributing Trace Amounts of DNA to Highly Complex Mixtures Using High-Density SNP Genotyping Microarrays." *PLoS Genetics* 4(8):e1000167 (2008). DOI **10.1371/journal.pgen.1000167** — https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1000167
   **This is the strongest single citation for "file size and privacy risk are uncorrelated."** Aggregate allele-frequency summary statistics alone were shown to reveal an individual's presence in a pool — which is why NIH and Wellcome withdrew open-access aggregate GWAS data.

3. **Erlich Y, Narayanan A.** "Routes for breaching and protecting genetic privacy." *Nature Reviews Genetics* 15:409–421 (2014). DOI **10.1038/nrg3723** — https://www.nature.com/articles/nrg3723
   Best single citation for a taxonomy of attacks (identity tracing, attribute disclosure, completion attacks).

### GA4GH [PRIMARY]
- **Framework for Responsible Sharing of Genomic and Health-Related Data** — https://www.ga4gh.org/framework/ ; also *The HUGO Journal* 8:3 (2014), DOI **10.1186/s11568-014-0003-1**. Quotable: §4.4 *"Establish proportionate data security measures that mitigate the risk of unauthorized access, data loss and misuse"*; §4.5 *"Forego any attempt to re-identify anonymized data unless where expressly authorized by law."*
- **Federated Analysis Work Stream** — https://www.ga4gh.org/work_stream/federated_analysis/
  > "The Federated Analysis Work Stream develops standards that help **'bring the algorithms to the data'** — running experiments in the cloud rather than downloading the data first."

  ⚠️ **Read that second clause before you quote it.** GA4GH's framing is *"in the cloud rather than downloading first."* It endorses **not moving data** — it does **not** endorse on-prem over cloud. Cite it for data locality, never as a GA4GH endorsement of edge hardware.

### NIH Genomic Data Sharing Policy & dbGaP controlled access [PRIMARY]
Source: **NOT-OD-14-124** — https://grants.nih.gov/grants/guide/notice-files/not-od-14-124.html

> "Requests for controlled-access data are reviewed by NIH Data Access Committees (DACs). DAC decisions are based primarily upon conformance of the proposed research as described in the access request to the data use limitations established by the submitting institution."
> "NIH expects that investigators who are approved to use controlled-access data will follow guidance on security best practices that outlines expected data security protections (e.g., physical security measures and user training)."

- **Institutional Certification** — https://grants.nih.gov/policy-and-compliance/policy-topics/sharing-policies/gds/institutional-certifications — signed by investigator *and* an institutional signing official.
- **Model Data Use Certification Agreement** — https://osp.od.nih.gov/wp-content/uploads/Model_DUC.pdf
- **dbGaP two-tier access** — https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/about.html
- **GDC access tiers** — https://gdc.cancer.gov/access-data/data-access-processes-and-tools:
  > "Controlled data generally includes individually identifiable data such as low level genomic sequencing data, germline variants, SNP6 genotype data, and certain clinical data elements."

## 4.5 The strongest TRUE statement

### First, do the arithmetic — because it does not say what you might want it to

| Move | Size | AWS egress @ $0.09/GB |
|---|---|---|
| WES tumour/normal BAM pair | ~60 GB | **~$5.40** |
| WGS tumour/normal BAM pair | ~240 GB | **~$21** |
| One somatic VCF (WXS) | 0.30 MB | **$0.00003** |
| One masked somatic MAF | 0.037 MB | **$0.000003** |
| 1,000 WGS T/N pairs | ~240 TB | ~$16,700 (tiered) |

**Egress cost is NOT your argument at single-patient scale.** $5.40. AWS gives you 100 GB/month free. Do not build a slide on it.

### The claim to make

> **For this workload the binding constraint is legal and contractual, not bandwidth or dollars.**
>
> Tumour/normal alignments are controlled-access by construction. NIH's GDS Policy requires a Data Use Certification signed by the investigator *and* an institutional signing official, plus DAC review against data-use limitations set by the submitting institution (NOT-OD-14-124). The GDC classifies low-level sequence and germline variants as controlled precisely because they are individually identifiable.
>
> Meanwhile HIPAA's Safe Harbor list at 45 CFR 164.514(b)(2)(i)(A)–(R) **does not contain DNA at all** — so you cannot de-identify a genome by deleting fields. You fall back on (R)'s catch-all and on (b)(2)(ii)'s "actual knowledge" clause, which Homer 2008, Gymrek 2013 and Erlich & Narayanan 2014 make hard to satisfy honestly.
>
> **A pipeline that never emits the variant file off the institution's own hardware removes that entire class of questions — approvals, DUC scope, cross-border transfer, breach surface — rather than answering them.** That is exactly the principle GA4GH's Federated Analysis work stream codifies as "bring the algorithms to the data."

Note the *shape* of that claim: it is about **eliminating a governance step, not saving money**. Every element is quoted from a primary source. That is why it survives scrutiny.

**And the HP hook:** the ZGX Nano ships with factory OPAL self-encrypting storage, TPM 2.0 in FIPS 140-2 mode, secure boot, an optional **radio-free SKU**, and TAA compliance (§1.4). For a controlled-access dataset under NIH "security best practices," that is a *substantive* answer to physical-security requirements, not marketing.

## 4.6 Overclaims — the kill list

| ❌ Do NOT say | Why it fails |
|---|---|
| "Cloud egress fees make this prohibitively expensive" | $5.40 for a WES pair; first 100 GB/month is free. A judge with an AWS bill will laugh. |
| "DNA is one of HIPAA's 18 identifiers" | Flatly false — not in (A)–(R). Item (P) is fingerprints and voice prints. |
| "HIPAA/NIH prohibits genomic data in the cloud" | False. NIH contemplates cloud use under its security best practices; all three hyperscalers host dbGaP-authorized workloads under BAAs. The true claim is *"local removes a control-verification burden."* |
| "Gymrek showed any genome can be re-identified" | Overstated — male subjects, Y-STRs, genealogy-database dependent. |
| "Even a somatic VCF/MAF is identifying PHI" | ⚠️ **Contestable, and the best judge in the room will contest it.** NCI publishes Masked Somatic Mutation MAFs as **open access** precisely because likely-germline variants are filtered (https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/). **If your demo consumes only masked somatic calls, your privacy argument is materially weaker — say so.** If it consumes T/N BAMs, unmasked MAFs, or anything with germline genotypes, your argument is strong. **Be precise about your actual input.** |
| "Egress is free now anyway" (inverse overclaim) | The 2024 waivers apply only to full migration off the provider, need approval, and run a 60–90 day clock. |
| "GA4GH endorses on-prem/edge" | GA4GH says *"in the cloud rather than downloading the data first."* Quote it for locality, not for local hardware. |
| Cloud $/hr on-demand list vs. "our box is free" | Ignores spot (−30–60%) and ignores the $4,207 hardware cost. Show both sides or don't do the comparison. |

## 4.7 The paragraph to actually say on stage

> "Moving 60 gigabytes costs about five dollars. That's not the problem. The problem is that moving it at all converts a local computation into a regulated disclosure — one that needs a Data Use Certification, a Data Access Committee review, and an institutional signing official. And HIPAA can't rescue you with Safe Harbor, because DNA isn't on the list of eighteen identifiers. We run the whole variant-to-structure pipeline on the institution's own Blackwell device, so the file never becomes a transfer. Compute cost is a real secondary benefit at cohort scale — eight B200s list at $114 an hour on AWS, though spot is a third of that — but our primary claim is that we **delete** a compliance step rather than satisfy one."

# 5. Precedent — this workload class is throughput-scaled, not latency-bound

## 5.1 🔴 READ THIS FIRST — NVIDIA officially supports GB10/DGX Spark for Boltz-2

This is the most actionable finding in the entire document.

> **"Added support for GB10 DGX Spark SKUs with sequence lengths up to 1536 residues"** (v1.5.0)
> Earlier: v1.3.0 added *"support for GB200 GPU with ARM architecture"* and *"Enhanced compatibility with ARM-based systems."*
> — NVIDIA Boltz-2 NIM Release Notes, https://docs.nvidia.com/nim/bionemo/boltz2/1.5.0/release-notes.html [VENDOR]

> **MSA Search NIM**: *"x86_64 / amd64 for typical discrete-GPU servers, and aarch64 / arm64 for NVIDIA Grace-based platforms"* — GH200, GB200, GB300, **GB10**. v2.5.0 *"added B300 and GB10 (128GB unified memory) support."*
> — https://docs.nvidia.com/nim/bionemo/msa-search/latest/prerequisites.html [VENDOR]

**Why this matters enormously for a 4-day build:** the usual edge-AI-hackathon failure mode is "the container doesn't exist for ARM64." Here NVIDIA names your exact SKU in its release notes. You can say *"NVIDIA ships a supported Boltz-2 container for this exact chip"* and point at the page.

**Three caveats you must state in the same breath:**
1. ⚠️ **The GB10 path is capped at 1536 residues**, vs 4096 (PyTorch backend) / 2048 (TensorRT) on datacentre GPUs. For pMHC complexes (peptide 8–11aa + HLA ~365aa + β2m ~100aa ≈ 480 residues) you are comfortably inside the cap — **but verify this for your actual constructs and say the cap out loud.**
2. ⚠️ **GB10 is NOT in the BioNeMo Inference Runtime's release-qualified GPU list** (that list is H200, H100, A100, L40S, GB200, GB300 — https://docs.nvidia.com/bionemo/inference-runtime/install/). GB10 support is documented **per-NIM** (Boltz-2, MSA Search), not as a BioIR qualification. Do not claim "BioNeMo is qualified on the Nano."
3. 🚨 **BUILD RISK — check this on day 1.** The MSA Search NIM's stated prerequisites are **24 CPU cores, 64 GB RAM, 1,660 GB NVMe** for pre-indexed databases, and ≥48 GB GPU memory (https://docs.nvidia.com/nim/bionemo/msa-search/latest/prerequisites.html). GB10 *is* explicitly on its supported-GPU list — *"Starting with version 2.5.0, the MSA Search NIM adds support for NVIDIA B300 and GB10 (DGX Spark)"* — **but the ZGX Nano has only 20 CPU cores (10 Cortex-X925 + 10 Cortex-A725), below the stated 24-core minimum**, and 1,660 GB of database leaves little room on a 2 TB unit. **This, not the GPU, is your real resource constraint.** Mitigations to decide early: use a reduced/small MSA database, use single-sequence mode if your model supports it, or pre-compute MSAs offline and ship them with the demo. Whichever you choose, **say it on stage** — "we pre-compute MSAs because the database stage is CPU- and I/O-bound, not GPU-bound" is a strong, informed answer (see §5.7a).

## 5.2 The quote that proves the thesis — from NVIDIA's own runtime docs

> "For large batches of independent inputs, use the Ray executor to improve end-to-end throughput."
> "The inference stage assigns **one complete model replica to each GPU**, which lets available GPUs process different inputs concurrently."
> **"Ray does not split one prediction across multiple GPUs or reduce its individual latency."**
> — NVIDIA BioNeMo Inference Runtime, https://docs.nvidia.com/bionemo/inference-runtime/overview/ [VENDOR]

**That last sentence is the single best citation in this section.** NVIDIA's own structure-prediction runtime *explicitly declines* to do model-parallel latency reduction and instead scales by replicating whole models per GPU and streaming independent jobs through them. That is the definition of a throughput-scaled batch workload — and it is exactly the architecture we are proposing, stated by the vendor.

NVIDIA's technical blog says the same:
> "Biomolecular structure prediction is now often run at **proteome scale**, where the goal is to move an **entire worklist** through the pipeline efficiently."
> "Ray can increase worklist throughput by overlapping CPU stages with GPU folding and by running full-model replicas on separate GPUs for independent inputs."
> — https://developer.nvidia.com/blog/high-throughput-structure-prediction-with-bionemo-inference-runtime/ [VENDOR]

**Vendor throughput datapoint:** *"BioIR-accelerated Boltz-2 delivered 58.5K successfully folded residues per allocated GPU-hour versus 20.2K for a torch-compiled open-source implementation, a 2.90× improvement"* (3 recycles, 200 sampling steps, 5 diffusion samples/target; on 8×H100/H200). Same URL. **Note the unit: residues per GPU-hour, not structures — because structure count is meaningless without sequence length. Adopt that unit.**

Models supported end-to-end by BioIR: *"OpenFold2, AlphaFold2, OpenFold3, Boltz-1, or Boltz-2."*

Also note the AlphaFold2 NIM deliberately splits MSA from folding *"if you want to batch prediction on different nodes"* and warns *"the structural prediction module scales quadratically with sequence length"* — https://docs.nvidia.com/nim/bionemo/alphafold2/latest/endpoints.html

## 5.3 Boltz-1 / Boltz-2 — what they are and what they actually claim

| | Reference |
|---|---|
| **Boltz-1** (Wohlwend, Corso et al., MIT Jameel Clinic) | bioRxiv DOI 10.1101/2024.11.19.624167 — https://www.biorxiv.org/content/10.1101/2024.11.19.624167v1 |
| **Boltz-2** (MIT + Recursion) — joint structure *and* binding affinity | bioRxiv DOI 10.1101/2025.06.14.659707 — https://www.biorxiv.org/content/10.1101/2025.06.14.659707v1 · full text https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/ |
| **Code + weights** | https://github.com/jwohlwend/boltz — *"All the code and weights are provided under MIT license, making them freely available for both academic and commercial uses."* |

**The efficiency claim — use the paper's wording, not the press release's:**
> *"at least 1000× more computationally efficient than FEP"* and *"approaches the performance of free-energy perturbation (FEP) methods in estimating small molecule–protein binding affinity"*
> — https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/

> *"On the standard FEP+ (OpenFE) affinity benchmark, whose targets were held out of training, Boltz-2 achieves an average Pearson of 0.62—comparable to OpenFE."* — https://boltz.com/boltz2

❌ **Do NOT say "20 seconds per affinity prediction."** That figure circulates in press coverage but could not be verified in the paper or on boltz.com. Use the "≥1000× more efficient than FEP" wording, which is in the paper.

⚠️ **Do NOT say Boltz-2 "beats AlphaFold3."** The paper is modest: Boltz-2 *"lags a bit behind AlphaFold3"* on structure prediction across most modalities, though it *"edges the other commercially available models Chai-1 and ProteinX."* **Boltz-2's real claim is affinity + efficiency + an MIT licence — not structural supremacy.**

**Batch is the native interface:** the repo takes *"a directory of YAML files for batched processing"* (https://github.com/jwohlwend/boltz). The paper itself screens commercial libraries of **460,160 and 64,960 compounds**, and a generative run over Enamine's 76B REAL space used **117k Boltz-2 evaluations**. [THIRD-PARTY, peer-reviewed preprint]

⚠️ Runtime/memory per prediction is **not** in the paper. A cloud-vendor engineering blog (Nebius, **not peer-reviewed**) reports ~40–60 s per protein–ligand prediction, ~11 GB for structure + ~7–8 GB for affinity on an L40S, and *"hundreds of inference jobs can run concurrently"* — https://nebius.com/blog/posts/running-boltz-2-inference-at-scale. Cite only with the vendor-blog caveat.

## 5.4 Batch folding at scale — published throughput numbers

| Source | Reported figure |
|---|---|
| **ParaFold** (Zhong et al., HPC Asia 2022) — https://arxiv.org/abs/2111.06340 | *"running ParaFold inferences of **19,704 small proteins in five hours on one NVIDIA DGX-2**"*; *"a **13.8× average speedup** over AlphaFold"* |
| **Summit / ORNL** — https://arxiv.org/abs/2201.10024 | *"**35,634 protein sequences** … using **under 4,000 total Summit node hours**, equivalent to using the majority of the supercomputer for one hour"*; relaxation optimisation gave *"up to a **14-fold speedup**"* |
| **MassiveFold** (*Nat Comput Sci* 2024) — https://www.nature.com/articles/s43588-024-00714-4 | *"a structure inference **split into many batches on GPUs**"*; *"The program can run many instances in parallel, **down to a single prediction per GPU**"*; *"reducing the computing time from **several months to hours**"* |
| **APACE** — https://arxiv.org/abs/2308.07954 | *"Using up to **300 ensembles, distributed across 200 NVIDIA A100 GPUs** … up to **two orders of magnitude faster** … reducing time-to-solution from weeks to minutes"* |
| **AlphaFold DB** (*NAR* 2024) — https://academic.oup.com/nar/article/52/D1/D368/7337620 | *"structure coverage for over **214 million** protein sequences"* — ⚠️ **compute cost is NOT disclosed; do not invent one** |
| AlphaFold2 human proteome — *Nature* 596:590 (2021) — https://www.nature.com/articles/s41586-021-03828-1 | 98.5% of human proteins covered |

⚠️ **A derived comparison worth making, because it shows sophistication:** ParaFold's DGX-2 is 16×V100 → ≈246 small proteins/GPU-hour. A Summit node is 6×V100 → ≈1.4 structures/GPU-hour. **That ~175× gap is real and explainable** — longer sequences, 5-model ensembles, full relaxation. *(Both ratios are my arithmetic from the papers' stated figures, not quoted numbers — label them derived.)* The lesson to state out loud: **"structures per GPU-hour" is meaningless without stating sequence length and sampling settings.** Saying this pre-empts a judge asking why your number differs from a paper's.

## 5.5 Neoantigen prediction as a parallel-for

**pVACtools/pVACseq's architecture is literally a parallel-for over peptides.** From the docs (https://pvactools.readthedocs.io/en/latest/pvacseq/run.html):
> `--n-threads`: *"Number of threads to use for **parallelizing peptide-MHC binding prediction calls**."*
> `-e1` Class I epitope lengths default **[8, 9, 10, 11]**; `-e2` Class II default **[12–18]**
> 25+ supported algorithms (NetMHCpan, MHCflurry, MHCnuggets, BigMHC, PRIME, DeepImmuno, …)

**The combinatorial blow-up is the pitch:** candidates ≈ (variants) × (epitope lengths) × (registers per variant) × (~6 class I HLA alleles) × (algorithms). Every one is an independent scoring call with zero cross-talk.

- pVACtools: Hundal et al., *Cancer Immunol Res* 8(3):409 (2020) — https://aacrjournals.org/cancerimmunolres/article/8/3/409/469797/
- pVAC-Seq: Hundal et al., *Genome Medicine* 8:11 (2016), DOI 10.1186/s13073-016-0264-5 — https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-016-0264-5
- NetMHCpan-4.1: Reynisson et al., *NAR* 48(W1):W449 (2020) — https://academic.oup.com/nar/article/48/W1/W449/5837056 ⚠️ **accuracy paper only — contains no throughput claims; do not cite it for speed**
- MHCflurry 2.0: O'Donnell et al., *Cell Systems* 11(1):42 (2020) — https://www.sciencedirect.com/science/article/pii/S2405471220302398 ⚠️ the popular *">7,000 predictions/sec, 396× faster than NetMHCpan 4.0"* figure is from **MHCflurry 1.2.0** (*Cell Systems* 2018) and could **not** be verified at source (cell.com 403). Verify before slide use.

**Real per-sample scale [THIRD-PARTY]:**
- ImmunoNX (https://arxiv.org/abs/2512.08226): *"identifying **78 high-confidence neoantigen candidates from 322 initial predictions**"* (HCC1395); *"supported over **185 patients across 11 clinical trials**"*; *"enables vaccine design in under three months"* — and notably runs on **Cromwell/WDL on Google Cloud**, i.e. a distributed batch workflow engine. **Useful as precedent that this is a batch workflow; also a fair counter-example that people do run it in the cloud — be ready for that.**
- *Nature Biotechnology* (https://www.nature.com/articles/s41587-023-01945-y): *"more than 24,000 possible neoepitope-HLA combinations"* narrowed to *"844 unique candidates"*; and *"considering only 15 HLA alleles and 50 shared cancer neoantigens, **more than 28,000 neoepitope-HLA pairs** could theoretically be formed."*

## 5.6 "Embarrassingly parallel" — sourcing the phrase honestly

❌ **Important correction:** I found **no peer-reviewed protein-structure-prediction paper that uses the phrase "embarrassingly parallel" verbatim.** In particular it does **not** appear in the Summit paper (arXiv:2201.10024) despite circulating summaries suggesting so.

✅ If you want the phrase on a slide, cite the adjacent virtual-screening literature:
> *"Given its **embarrassingly parallel** nature and the computation effort required by extreme-scale virtual screening campaign…"*
> — Accordi, Beltrame, Gadioli, Palermo, *Performance-Portable Extreme-Scale Virtual Screening on Heterogeneous HPC Systems*, PASC26 — https://zenodo.org/records/21072879

✅ Title-level support: ParaFold — *"high-throughput structure predictions"*; NeoPredPipe — *"high-throughput neoantigen prediction and recognition potential pipeline"*, *BMC Bioinformatics* 20:264 (2019), https://link.springer.com/article/10.1186/s12859-019-2876-4.

**Best practice: let the BioNeMo quotes in §5.2 carry the structure-prediction case, and use "embarrassingly parallel" as your own engineering characterisation rather than attributing it to a folding paper.**

## 5.7 🔬 The honest counterpoints — own these, don't hide them

**This is the strongest part of the pitch if you volunteer it.** A judge who hears you name your own bottleneck will trust everything else you say.

**(a) MSA generation is the real bottleneck, and it is CPU/IO-bound, not GPU-bound.** The best quote against our own thesis:
> *"The AlphaFold framework is a mixture of two types of workloads: MSA construction based on CPUs and model inference on GPUs. **The first CPU stage dominates the overall runtime, taking hours for a single protein** due to the large database sizes and I/O bottlenecks. However, **GPUs in this CPU stage remain idle.**"*
> — ParaFold, https://arxiv.org/abs/2111.06340

**(b) Shared filesystems serialise "independent" jobs.** From the Summit paper (https://ar5iv.labs.arxiv.org/html/2201.10024): *"the number of file reading tasks performed by one alignment to the database can be large, and this **becomes the bottleneck on shared filesystems**."* N jobs are only independent if they don't all hammer the same 1.6 TB database. **On a single Nano with local NVMe this is much less bad — which is a genuine architectural argument in our favour (§3.5 item 2).**

**(c) The database footprint is a per-node fixed cost that does not shard.** 1,660 GB NVMe + 64 GB RAM + 24 CPU cores *per node*, regardless of how many sequences you fold.

**(d) But MSA is a solvable bottleneck, not a permanent one.** NVIDIA's MMseqs2-GPU work reports **177× faster than JackHMMER** on a 128-core CPU using one L40S; *"0.475 s/sequence on one GPU vs 84.295 s with JackHMMER"*; ColabFold end-to-end from ~40 min to ~90 s — https://developer.nvidia.com/blog/boost-alphafold2-protein-structure-prediction-with-gpu-accelerated-mmseqs2/. The same post quotes VantAI's CTO: *"Protein structure prediction inference has long been known to be limited by the MSA computation step."* **Acknowledging the bottleneck and then naming the fix is a better story than pretending it doesn't exist.**

**(e) Every GPU needs full weights resident.** BioIR's "one complete model replica per GPU" means no weight sharing. Short jobs amortise load time badly — hence the persistent-warm-worker recommendation in §3.5.

**(f) Jobs are wildly non-uniform, so naive round-robin wastes GPUs.** Structure prediction *"scales quadratically with sequence length."* A mixed-length worklist is embarrassingly parallel but **badly load-balanced** — which is exactly why BioIR uses a Ray work-stealing executor rather than static partitioning. **Design implication for us: use a shared work queue with dynamic pull, not a static round-robin split.** Cheap to implement, and directly defensible.

**(g) Sequence-length ceiling on GB10** — 1536 residues (§5.1).

**(h) For neoantigens specifically, only the inner loop is a clean map.** Variant calling, HLA typing, expression quantification and phasing are **sequential, dependency-laden upstream stages**, and the final ranking is a **global sort/aggregation — a reduction, not a map.** This is precisely the serial head and tail in the Amdahl model of §3.2 Level 4. The two analyses agree, which is a good sign.

# 6. Judge-question bank

**How to use this.** Each entry has an **honest answer** and a **🚫 boundary** — the thing you must not claim. The boundary line is the important half. A judge remembers the team that said "we don't know that" more than the team that had an answer for everything.

**Three rules for the whole Q&A:**
1. *"We didn't measure that"* is a complete, respectable answer. *"Probably around X"* is not.
2. Concede the weak point **before** the judge reaches it. You control the framing once; after that they do.
3. Never defend a number you cannot source. Drop it mid-sentence if you have to.

---

## Block A — Architecture, scaling and hardware

### A1. "Why not just use the cloud?"
**Answer:** Cost isn't the argument — moving a WES tumour/normal pair is about $5.40 in AWS egress, and the first 100 GB/month is free. The argument is governance: tumour/normal data is controlled-access by construction, and sending it out turns a local computation into a regulated disclosure needing a Data Use Certification, DAC review, and an institutional signing official (NIH NOT-OD-14-124). HIPAA's Safe Harbor can't help you, because DNA isn't among the 18 identifiers at 45 CFR 164.514(b)(2)(i). Running on the institution's own device deletes that step rather than satisfying it.
**🚫 Boundary:** Don't say cloud is forbidden or prohibitively expensive. NIH explicitly contemplates cloud use under its security best practices, and all three hyperscalers host dbGaP-authorized workloads under BAAs. Don't claim egress fees are a blocker. (Full detail: §4.)

### A2. "You have one box. How do you know it scales to several?"
**Answer:** We don't *know* — we project, and the projection is labelled. What we measured is sustained single-node throughput over a [N]-minute batch. The workload is independent jobs with no inter-node communication, so the scaling model is a makespan model: `Makespan(N) = t_head + ceil(J/N) × t_job + t_tail`, with granularity efficiency `η_gran = J/(N × ceil(J/N))` computed exactly, not guessed. For our batch size that gives ~1.8× on two nodes, not 2×, because the parse and ranking stages don't parallelise. Here's the formula. (§3)
**🚫 Boundary:** Never present a multi-node number as measured. Never claim η = 1.0.

### A3. "Isn't NVIDIA's DGX Spark clustering meant for something else entirely?"
**Answer:** Yes — and that's the point. NVIDIA's docs say clustering lets you *"run workloads that cannot fit onto a single device"* (https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html). That's model sharding for a 405B model across 256 GB, using Ray + NCCL + RoCE. Our workload is the opposite shape: every peptide folds independently, and the only thing crossing the wire is a job descriptor and a result file. A second Nano needs a work queue and an SSH key, not tensor parallelism. That makes our scaling *more* credible than a model-parallel story, because we're not bottlenecked on an interconnect that independent measurements put at ~10 GB/s effective NCCL bandwidth. (§2)
**🚫 Boundary:** Don't claim you clustered anything. You have one box.

### A4. "Then why do you need a $4,200 Blackwell box? Why not a cheap GPU?"
**Answer:** Not for speed — GB10's 273 GB/s of memory bandwidth is modest against a discrete datacentre GPU. It's for **capacity in a deployable envelope**: 128 GB of coherent unified memory at a 240 W total system budget in a 150 mm box. Our measured peak memory high-water mark was **[X] GB** — that doesn't fit on a 24 GB consumer card. And it's deployable where the data already is: a hospital cupboard, no rack, no data-centre power.
**🚫 Boundary:** Never claim the Nano is faster than a datacentre GPU per unit. Concede this first — it buys you credibility for the capacity argument. **Have your real peak-memory number ready; this question is where it earns its keep.** (§3.4, §7)

### A5. "Your slide says 1 petaFLOP. Is that real?"
**Answer:** It's NVIDIA's number and it carries a qualifier most people drop: *"up to 1 PFLOP at FP4 precision **with sparsity**"* (https://docs.nvidia.com/dgx/dgx-spark/hardware.html). Dense FP4 is half that, and our workload runs in BF16, so that figure is not our number. HP's own datasheet says 1,000 TOPS FP4 and never claims a petaFLOP. What we measured is [X].
**🚫 Boundary:** Never quote peak FP4-sparse as achieved throughput. Never list "1000 TOPS **and** 1 PFLOP" as two capabilities — they're the same 10¹⁵ ops/s. (§1.2)

### A6. "What's your energy per candidate? Can you even measure power on this thing?"
**Answer (if you have a wall meter):** [X] joules per candidate, measured at the wall, idle subtracted.
**Answer (if you don't):** We didn't measure it properly, and I'd rather not give you a number than a bad one. NVIDIA states that *"when measuring power usage via NVIDIA-smi, the wattage displayed measures only GPU power"* — the SoC TDP is 140 W of a 240 W system budget, so `nvidia-smi` misses the platform. What I can give you is a hard vendor-spec bound: this box physically cannot exceed 240 W, versus up to 700 W of configurable TDP for a single H100 SXM board.
**🚫 Boundary:** Don't present `nvidia-smi` watts as system power. (§7.2)

### A7. "How do we know your throughput number isn't a cherry-picked best run?"
**Answer:** It's the median over [N] runs with p95 alongside, from a ≥30-minute sustained batch so the box reaches thermal steady state, at batch size J=[X], with model load time [included/excluded — state which]. The logs are in this terminal if you want to see them.
**🚫 Boundary:** Don't report best-of-N. Don't report a speedup without stating J. (§7.3)

### A8. "Does any of this software even run on ARM64?"
**Answer:** Yes, and NVIDIA names this exact chip. The Boltz-2 NIM release notes say *"Added support for GB10 DGX Spark SKUs with sequence lengths up to 1536 residues"* (v1.5.0), and the MSA Search NIM lists GB10 and ships aarch64 images. The cap matters: 1536 residues on GB10 vs 4096 on the datacentre PyTorch backend — our pMHC complexes are well inside it.
**🚫 Boundary:** Don't say "BioNeMo is qualified on the Nano." GB10 is **not** in the BioNeMo Inference Runtime's release-qualified GPU list (H200/H100/A100/L40S/GB200/GB300); support is documented per-NIM. (§5.1)

### A9. "What actually breaks first when you scale this?"
**Answer:** Not the GPU — the MSA/database-search stage. ParaFold puts it plainly: *"The first CPU stage dominates the overall runtime, taking hours for a single protein due to the large database sizes and I/O bottlenecks. However, GPUs in this CPU stage remain idle."* The Summit team found database reads *"becomes the bottleneck on shared filesystems."* That's why we [pre-compute MSAs / keep the database on local NVMe / use reduced DBs] — and it's also why a single box with 4 TB of local NVMe at ~4.6 GiB/s avoids the shared-filesystem failure mode that bites clusters. **Also worth flagging: the MSA Search NIM asks for 24 CPU cores and the Nano has 20.**
**🚫 Boundary:** Don't claim the whole pipeline is embarrassingly parallel. Only the folding/scoring inner loop is. (§5.7)

### A10. "Is this workload really embarrassingly parallel, or is that just a word?"
**Answer:** NVIDIA's own inference runtime says it for us: *"The inference stage assigns one complete model replica to each GPU, which lets available GPUs process different inputs concurrently"* and **"Ray does not split one prediction across multiple GPUs or reduce its individual latency."** Their runtime explicitly declines model-parallel latency reduction and scales by streaming independent jobs. That's the architecture we're proposing, described by the vendor.
**🚫 Boundary:** No folding paper uses the literal phrase "embarrassingly parallel" — if you want a verbatim citation for the phrase, it's from the virtual-screening literature (PASC26/LiGen), not from AlphaFold work. Use it as your own engineering characterisation. (§5.6)

### A11. "If you had ten Nanos, would you get ten times the throughput?"
**Answer:** No, and the formula says why. Speedup is capped by `J/ceil(J/N)` — with 40 candidates and 10 nodes you'd get 40/4 = 10× on the parallel body, but the serial parse-and-rank head and tail cap end-to-end speedup at 1/s under Amdahl. If a sample only ever yields 40 jobs, past a certain N you're buying idle boxes. The honest ceiling is set by our queue depth, not our budget.
**🚫 Boundary:** Don't project past your actual queue depth. (§3.6 item 6)

### A12. "What's the failure mode if one node dies mid-run?"
**Answer:** One job retries. That's the structural advantage of independent jobs over model parallelism — in a sharded-model cluster, losing a node kills the whole inference. Ours degrades to a slower queue.
**🚫 Boundary:** Only claim this if you actually implemented retry. If you didn't, say "that's the design; we didn't implement retry in four days."

---

## Block B — Science and clinical

### 🎯 Three lines to memorise before you walk in

1. **On prediction quality:** *"TESLA, Cell 2020 — 25 expert groups, 608 top-ranked peptides, 37 immunogenic. Six percent. Our shortlist is a triage tool, not a truth claim."*
2. **On HLA:** *"You cannot get HLA type from a somatic VCF. OptiType, xHLA, HLA-HD, arcasHLA all need reads. We take it as an input; in production it comes from the same BAM."*
3. **On structure:** *"There's no published evidence that pMHC structure beats NetMHCpan for immunogenicity ranking. Structure is our explanation layer, not our discriminator — and Boltz being MIT-licensed is why we can ship it at all."*

### B1. "Does this actually make a vaccine?"
**Answer:** No. Absolutely not. We produce a **ranked shortlist of candidate peptides with structural evidence** — a prioritisation tool that sits at the front of a pipeline. Everything downstream — synthesis, immunogenicity validation, formulation, manufacturing, regulatory, clinical delivery — is out of scope and is where essentially all the cost and risk live.
**🚫 Boundary:** Never say "designs a vaccine," "generates a vaccine," or "personalised vaccine in N minutes." Say **"prioritises candidates for a vaccine design workflow."** This is the single easiest way to lose a scientific judge's trust, and the easiest to avoid.

### B2. "Is the prediction validated?"
**Answer:** No. We validated the *system* — that the pipeline runs end to end on this hardware, produces deterministic output, and hits the throughput we claim. We did **not** validate the *biology*: no wet-lab confirmation, no T-cell assay, no held-out benchmark against known immunogenic epitopes. In four days we built an engineering artefact, not a scientific result.
**🚫 Boundary:** Never call your structure output "validated," "accurate," or "confirmed." If you had time to run against a public benchmark set, say exactly which one and report the number honestly — including if it's bad.

### B3. "What's your false-positive rate?" ⭐ *the most important answer in this document*
**Answer (the honest one):** We don't have one, because we never measured immunogenicity. But the field's number is sobering, and I'd rather quote it than pretend. **TESLA** was a global blinded bake-off: ~25 expert groups from academia, pharma and biotech each submitted ranked neoantigen predictions from shared tumour sequencing data. **608 top-ranked epitopes were tested for T-cell recognition. 37 were immunogenic — 6%.** That is the state of the art, from the people who do this professionally. Our shortlist is a triage tool, not a truth claim.

**Citations:**
- **[VERIFIED verbatim via NCBI eutils]** Wells DK, van Buuren MM, Dang KK, et al.; Tumor Neoantigen Selection Alliance. "Key Parameters of Tumor Epitope Immunogenicity Revealed Through a Consortium Approach Improve Neoantigen Prediction." *Cell* 183(3):818–834.e13 (2020). **DOI 10.1016/j.cell.2020.09.015 · PMID 33038342 · PMC7652061** — https://www.cell.com/cell/fulltext/S0092-8674(20)31156-9
  Abstract verbatim: *"608 epitopes were subsequently assessed for T cell binding in patient-matched samples. By integrating peptide features associated with presentation and recognition, we developed a model of tumor epitope immunogenicity that **filtered out 98% of non-immunogenic peptides with a precision above 0.70**… validated in an independent cohort of 310 epitopes."*
- ⚠️ **The 37/608 = 6% figure is in the paper's Results, NOT the abstract.** It is corroborated by independent peer-reviewed citing papers, e.g. *Front Immunol* 2024 (DOI 10.3389/fimmu.2024.1347542): *"the Tumour Neoantigen Selection Alliance (TESLA) global consortium identified 608 top-ranked neoantigens in 6 solid cancer samples, of which **only 37 (6%) could be recognised by matched patient T cells**."* If challenged, point to the paper's Results/Figure 1, not the abstract.

**Supporting scale statistic (use carefully):** Müller M, et al. "Machine learning methods and harmonized datasets improve immunogenic neoantigen prediction." *Immunity* 56(11):2650–2663.e6 (2023), DOI 10.1016/j.immuni.2023.09.002 — across 131 patients they *"identified 46,017 somatic single-nucleotide variant mutations and 1,781,445 neo-peptides, of which 212 mutations and 178 neo-peptides were immunogenic."* ⚠️ **Do not present this as a measured positive predictive value** — not all 1.78M peptides were individually screened. It is a statement about the size of the search space, which is precisely why throughput matters.

**Even the best immunogenicity scorers have high FP rates:** on 297 TESLA-confirmed non-immunogenic strong binders, *"The best performers were score from MixMHCpred with 30% (90) and rank from NetMHCpan with 31% (92) of FP… DeepHLApan with 100% (297) and DeepImmuno with 79% (234)"* — Buckley PR et al., *Front Immunol* 2023, DOI 10.3389/fimmu.2023.1094236.

**🚫 Boundary:** Do not present the 6% as *your* system's performance — you didn't measure anything. Present it as the field's baseline and as the reason a shortlist needs to be short.

### B4. "Why not just use the cloud?" *(scientific-judge variant)*
**Answer:** See A1 — the argument is governance, not cost. The scientific-judge variant usually continues: *"but everyone runs these pipelines in the cloud."* That's true and you should concede it — the ImmunoNX neoantigen workflow supporting 185 patients across 11 clinical trials runs on Cromwell/WDL on Google Cloud (https://arxiv.org/abs/2512.08226). Our claim is not that cloud doesn't work; it's that a local device removes a compliance step for institutions that would rather not take it.
**🚫 Boundary:** Don't claim cloud pipelines are non-compliant or that this is how it "should" be done.

### B5. "Isn't Boltz just AlphaFold with a different name?" ⭐ *your strongest answer — the licensing card*
**Answer:** No, and the difference is legal before it's technical. Boltz-1 and Boltz-2 are from MIT's Jameel Clinic (Boltz-2 with Recursion). Boltz-1 claims *"Alphafold3-level accuracy"* and releases *"training and inference code, model weights, datasets, and benchmarks under the **MIT open license**."* Boltz-2 adds **joint binding-affinity prediction**, *"at least 1000× more computationally efficient than FEP."*

**Then the card:**
> "If this demo used AlphaFold 3, we could not ship it. DeepMind's AF3 weights are **not** open — they're *'only available for non-commercial use by, or on behalf of, non-commercial organizations'*, you *'must not publish or share AlphaFold 3 model parameters'*, you may *'only use AlphaFold 3 model parameters if received directly from Google'*, and their own terms say AF3 and its output *'are not intended, validated, or approved for clinical use.'* Boltz is MIT — code **and** weights, academic **and** commercial. For anything that wants to become a product in a hospital, that's not a preference, it's the only option."

**Citations [VERIFIED at source]:**
- Boltz-1 — bioRxiv DOI 10.1101/2024.11.19.624167, PMID 39605745, PMC11601547
- Boltz-2 — bioRxiv DOI 10.1101/2025.06.14.659707 · https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/
- Boltz repo — https://github.com/jwohlwend/boltz : *"All the code and weights are provided under MIT license, making them freely available for both academic and commercial uses."*
- AlphaFold 3 — Abramson J, Adler J, et al., *Nature* 630:493–500 (2024), DOI 10.1038/s41586-024-07487-w, PMID 38718835
- **AF3 weights terms (verbatim)** — https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md. Code is Apache 2.0; **weights are under separate restrictive terms**, which also prohibit using AF3 output *"to train machine learning models or related technology for biomolecular structure prediction similar to AlphaFold 3."*
- **Contrast with AlphaFold 2**: code Apache 2.0, **parameters CC BY 4.0** — i.e. AF2 weights *are* commercially usable. AF3 was a deliberate tightening. https://github.com/google-deepmind/alphafold
- **The openness controversy** (optional colour, only if asked): AF3 published 8 May 2024 with no code; **over 1,000 scientists signed an open letter**; code released for non-commercial use 11 Nov 2024 with weights only on request; AlphaFold Server capped at 20 predictions/day with no custom small molecules. — https://www.nature.com/articles/d41586-024-01463-0 · https://www.nature.com/articles/d41586-024-03708-4 · https://alphafoldserver.com/prohibited-use

**🚫 Boundary:** Never claim Boltz-2 beats AlphaFold3 **on structure** — the Boltz-2 paper itself says it *"lags a bit behind AlphaFold3."* Its claim is affinity + efficiency + licence. Never quote *"20 seconds per affinity prediction"* — unverifiable. State the licensing facts flatly and neutrally; don't editorialise about DeepMind.

### B5b. "Has anyone independently evaluated Boltz-2? Is it actually reliable?" *(the follow-up to B5 — be ready)*
**Answer:** Yes, and at least one independent evaluation is critical, so let me give it to you rather than have you find it. *J Chem Theory Comput* (2026), DOI 10.1021/acs.jctc.6c01334, PMID 42579383, reports: *"Structural analysis reveals significant global RMSD variations, indicating that Boltz-2 predicts multiple protein conformations and ligand binding positions rather than a single converged pose… **Our results show that Boltz-2 lacks the energetic resolution required for lead identification.**"* That's on small-molecule drug-discovery targets, not pMHC, so it doesn't transfer directly — but it's a fair warning that the affinity head is not a solved problem, and it's another reason we don't lean on structure as our discriminator (B8).
**🚫 Boundary:** Don't dismiss this by saying "different domain" and moving on. Concede it, then explain why your use (visual/physical sanity check on a short list) is less exposed to it than lead identification is.

### B6. "How do you know the patient's HLA type?" ⚠️ *favourite trap question*
**Answer:** We don't infer it from the variant file, because **you cannot get HLA type from a somatic VCF.** HLA typing is an allele-matching problem against a hyper-polymorphic locus — it needs the underlying **reads**. Every production typer consumes FASTQ/BAM, not variant calls: **OptiType** (*Bioinformatics* 2014, *"overall accuracy of 97%"* at 4-digit, **class I only**), **xHLA** (*PNAS* 2017, *"99–100% four-digit typing accuracy for both class I and II"* on 30× WGS/WES, ~3 min/sample), **HLA-HD** (*Hum Mutat* 2017, 6-digit), **arcasHLA** (*Bioinformatics* 2020, RNA-seq, *"100% at two-field resolution for Class I genes, and over 99.7% for Class II"*). And pVACseq proves the point structurally: HLA alleles are a **required positional argument** supplied by the user, not derived from the VCF.

In our demo we [take HLA type as an explicit input / use a fixed common allele set for the synthetic sample]. In production it comes from the same BAM the variants were called from.

**The one honest nuance, if a judge presses:** there *is* a VCF-based route — HLA **imputation** from dense **germline** SNP genotypes across the MHC region (SNP2HLA, HIBAG, CookHLA; CookHLA reports 97.6% vs SNP2HLA 93.4%, *Nat Commun* 12:1264, 2021). That needs a germline genotype VCF with MHC-region SNPs, **not** a somatic tumour VCF. And it degrades badly outside European reference panels — *"Most currently available HLA imputation tools are based on European reference populations and are not suitable for direct application to non-European populations."*

**Citations:** OptiType DOI 10.1093/bioinformatics/btu548 (PMID 25143287) · xHLA DOI 10.1073/pnas.1707945114 (PMID 28674023) · HLA-HD DOI 10.1002/humu.23230 (PMID 28419628) · arcasHLA DOI 10.1093/bioinformatics/btz474 (PMID 31173059) · CookHLA https://www.nature.com/articles/s41467-021-21541-5 · pVACseq https://pvactools.readthedocs.io/en/latest/pvacseq/getting_started.html
**🚫 Boundary:** **Never claim you derive HLA type from the VCF.** Put the assumption on your architecture slide. Don't quote a headline accuracy for HLA-HD — its abstract gives none. Note that all these accuracies are on curated, largely European-ancestry benchmark panels, not clinical FFPE tumour samples at low depth.

### B7. "What happens with indels and frameshifts?"
**Answer:** They're simultaneously the most valuable class and the one naive pipelines most often get wrong. A frameshift creates a novel open reading frame — an entirely non-self downstream tract until the next stop codon — rather than a single altered residue in an otherwise self peptide. Turajlic et al. quantified this across 5,777 solid tumours in 19 cancer types: *"enrichment of indel mutations for high-affinity binders was **three times** that of non-synonymous SNV mutations… neoantigens derived from indel mutations were **nine times enriched for mutant specific binding**… **frameshift indel count [was] significantly associated with checkpoint inhibitor response across three separate melanoma cohorts (p=4·7 × 10⁻⁴)**."*

**Where tools break — concrete and checkable:**
1. **Plain VEP annotation does not give you the frameshifted protein.** pVACseq requires two extra VEP plugins — **Frameshift** (*"apply a frameshift mutation to a transcript sequence to compute the full mutated protein sequence"*) and **Wildtype**. Without them a pipeline silently produces no or wrong frameshift peptides.
2. **Proximal variants need phasing** — pVACseq lists *"Creating a phased VCF of proximal variants"* as a required prep step. Two nearby variants on the same haplotype yield a different peptide than either alone.
3. **Indel calling is itself less reliable than SNV calling** — higher false-positive rates, no gold-standard caller.
4. **Novel-ORF peptides may coincidentally exist elsewhere in the proteome** and need proteome matching to filter out.
5. **Nonsense-mediated decay** of frameshifted transcripts is a real filter most tools don't model (⚠️ keep this qualitative — no clean quantitative source found).

In our demo we [state exactly what you support]. If you only handle SNVs, **say so plainly** — *"we support SNVs; indel and frameshift handling is the obvious next step, and by the literature it's the higher-value half"* is a strong, informed answer.
**Citations:** Turajlic S, et al., *Lancet Oncol* 18(8):1009–1021 (2017), **DOI 10.1016/S1470-2045(17)30516-8, PMID 28694034** · VEP plugins https://pvactools.readthedocs.io/en/latest/pvacseq/input_file_prep/vep.html
**🚫 Boundary:** Don't claim full indel/frameshift support unless you tested it against a case with a known expected peptide.

### B8. "Does structure prediction actually improve neoantigen ranking over sequence-based predictors?"
**🔴 This is the weakest link in the entire pitch. Rehearse this one out loud.**

**Answer (give it in full — the completeness is what saves you):**
> "That's the right question, and the honest answer is no — there's no published evidence that pMHC structure prediction beats NetMHCpan or MHCflurry for immunogenicity ranking in a prospective held-out setting.
>
> The strongest pro-structure result, Riley et al. 2019, got AUC 0.73 in-sample but only **0.60 on 291 held-out peptides**, and it was restricted to HLA-A2 9-mers — the authors call it a proof of concept. Motmaen et al. 2023 fine-tuned AlphaFold and *'approaches the overall performance of the state-of-the-art NetMHCpan'* — approaches, not exceeds, and that's binding, not immunogenicity. And the most telling one: Mikhaylov et al. in *Structure* 2024 model pMHC to **0.46 Å** median peptide-core RMSD — excellent structures — and when they used those structures to improve binding prediction, *'Both seqnn and seqnn-f outperformed netMHCIIpan version 3.2 but not version 4.0.'* Data beat structure, because NetMHCIIpan-4.0 has roughly ten times the training set.
>
> Even the NetMHCpan authors' own 4.2 release, which adds structural features, reports that *'performance gains are modest.'*
>
> So: **we are not claiming structure improves ranking. The ranking is sequence-based. Structure is the explanation layer — an interpretable, physical sanity check on the top few candidates that an immunologist can actually look at — and it costs us nothing legally because Boltz is MIT. What we built is the infrastructure that makes it cheap enough to find out whether it helps.**"

**One more caution worth volunteering:** Mikhaylov also found that TFold *"produces some fairly inaccurate models… and the pLDDT score for them is not lower"* — **your confidence score does not tell you when you're wrong** — and that *"even for 9-mer peptides, inaccurate models can substantially misrepresent the molecular features seen by a TCR."* If you display a structure with a confidence score, say that the score is not a reliability guarantee.

**Citations:** Riley TP, et al., *Front Immunol* 10:2047 (2019), DOI 10.3389/fimmu.2019.02047 · Motmaen A, et al., *PNAS* 120(9):e2216697120 (2023), DOI 10.1073/pnas.2216697120 · Mikhaylov V, et al., *Structure* 32(2):228–241.e4 (2024), DOI 10.1016/j.str.2023.11.011, PMID 38113889 · NetMHCpan-4.2, *Front Immunol* (2025), DOI 10.3389/fimmu.2025.1616113
**🚫 Boundary:** **Never claim your structural step improves ranking accuracy.** Never conflate binding prediction with immunogenicity prediction. If pushed, concede cleanly: *"we can't show it helps; we can show you could now find out."*

### B9. "Your input is a synthetic variant file. Doesn't that make the whole demo synthetic?"
**Answer:** The *input* is synthetic; the *computation* is real. The folding model, the binding predictor, the memory footprint and the throughput are all genuine — swapping in a real controlled-access VCF changes the data, not the pipeline or the performance. We used synthetic data precisely because we didn't have dbGaP authorisation, which is itself a small demonstration of the governance point we're making.
**🚫 Boundary:** Don't imply you ran on real patient data. Don't claim your candidate rankings are biologically meaningful — synthetic variants produce synthetic peptides.

### B10. "How many candidates does a real tumour actually produce, and is your J realistic?"
**Answer:** Candidate counts explode combinatorially: variants × epitope lengths (pVACtools defaults to 8/9/10/11 for class I) × registers × ~6 class I alleles × prediction algorithms. Published examples: one *Nature Biotechnology* study narrowed *"more than 24,000 possible neoepitope-HLA combinations"* to 844 candidates; ImmunoNX reports *"78 high-confidence neoantigen candidates from 322 initial predictions."* Our J of [X] is [realistic / a deliberately reduced demo subset — say which].
**Citations:** https://www.nature.com/articles/s41587-023-01945-y · https://arxiv.org/abs/2512.08226 · https://pvactools.readthedocs.io/en/latest/pvacseq/run.html
**🚫 Boundary:** If your J is small for demo reasons, say so — it directly affects your scaling claim via `η_gran` (§3.2), and a judge who spots the inconsistency will doubt the scaling story too.

### B11. "Is there clinical precedent, or is this science fiction?" ⭐ *the timing is unusually good for you*
**Answer:** There's real, recent clinical evidence — and one landmark landed last month.
- **Melanoma, Phase 2b (KEYNOTE-942):** personalised mRNA neoantigen therapy + pembrolizumab vs pembrolizumab alone, 157 patients. *"Recurrence-free survival was longer with combination versus monotherapy (HR 0·561 [95% CI 0·309–1·017]; two-sided **p=0·053**)… 18-month recurrence-free survival was 79% versus 62%."* **Note p=0.053 — the primary endpoint did not cross conventional significance**; the study was powered at one-sided α=0.1. Say that yourself.
- **Melanoma, Phase 3 (INTerpath-001), announced August 2026:** 1,137 patients, met primary (RFS) and key secondary (DMFS) endpoints. Per the sponsors, *"the first positive Phase 3 readout for an individualized neoantigen therapy (INT) and for an mRNA-based cancer therapy."* OS still maturing.
- **Pancreatic, Phase 1 (autogene cevumeran):** 16 patients vaccinated, **8/16 (50%)** generated detectable T-cell responses; responders' median RFS not reached vs **13.4 months** for non-responders (P=0.003), holding at 3.2-year follow-up.
- **The negative precedent — volunteer it, it buys enormous credibility:** BioNTech **terminated** the Phase 2 trial of autogene cevumeran as adjuvant monotherapy in ctDNA-positive resected colorectal cancer (Aug 2026). The modality is not a guaranteed win.

**Regulatory status:** **No personalised neoantigen cancer vaccine is FDA-approved.** The FDA-approved therapeutic cancer vaccines remain sipuleucel-T (2010), BCG, and talimogene laherparepvec — none is a personalised neoantigen vaccine. The Phase 3 sponsors say they *"will engage with regulators on filing submissions"*; nothing is publicly submitted.

**Citations:** Weber JS, et al., *Lancet* 403(10427):632–644 (2024), **DOI 10.1016/S0140-6736(23)02268-7, PMID 38246194**, NCT03897881 · Rojas LA, Sethna Z, et al., *Nature* 618:144–150 (2023), **DOI 10.1038/s41586-023-06063-y, PMID 37165196** · Sethna Z, et al., *Nature* 639:1042–1051 (2025), DOI 10.1038/s41586-024-08508-4 · Phase 3 INTerpath-001 (NCT05933577) sponsor releases, Aug 2026
**🚫 Boundary:** **Never claim approval.** Quote p=0.053 for the Phase 2b rather than implying significance. Mention the terminated colorectal trial — a judge who knows the field will respect it, and if they raise it first you look selective.

### B12. "What turnaround time would this need to hit, and do you hit it?"
**Answer:** Our stage is a small slice of a long clinical clock, and the bottleneck is manufacturing and release testing, not compute. The only peer-reviewed per-patient figure I'd quote is from the pancreatic trial, which pre-registered production benchmarks — *"produce vaccines in ≤6 weeks… administer first dose of the vaccine in ≤9 weeks"* — and achieved a **median 9.4 weeks (range 7.4–11.0) from surgery to first dose.** Sequencing and neoantigen selection are a small fraction of that.

**And the number I'd actually put on a slide:** in that trial, *"**only 1 patient out of 19 (5%) had insufficient neoantigens that led to non-manufacture of the vaccine**."* That's the most honest statistic in the field — it says candidate *generation* is rarely the failure point, which is precisely why better *prioritisation* is where the value is.
**Citation:** Rojas LA, et al., *Nature* 618:144–150 (2023), DOI 10.1038/s41586-023-06063-y
**🚫 Boundary:** **Never imply your runtime is the clinical turnaround time.** "We turn a variant file into a ranked shortlist in X minutes" is true; "we make a personalised vaccine in X minutes" is not. ⚠️ Do **not** quote the "6–8 week turnaround" figure attached to the melanoma programme — it appears only in secondary sources and is not in the *Lancet* paper. Use the 9.4-week Rojas number.

### B13. "Why structure at all? Why not just run the sequence predictors, which are far cheaper?"
**Answer:** For most ranking work you should — and we do run sequence-based scoring as the first-pass filter. Structure is the second stage, applied only to the top few, where it gives you something sequence scores can't: an inspectable physical model of the peptide–MHC complex that a human immunologist can look at. That's a *fit for the hardware* argument as much as a scientific one: the 128 GB unified memory is what lets us hold the folding model and the shortlist together on one desk-side box.
**🚫 Boundary:** Don't claim structure supersedes sequence predictors. Position it as a second-stage, low-N, high-information step. Be honest that its added ranking value is unproven (B8).

### B14. "What about tumour heterogeneity, clonality and expression? A mutation in 5% of cells is a bad target."
**Answer:** Correct, and we don't handle it. Clonality (is the variant in most tumour cells or a minor subclone?) and expression (is the transcript actually made?) are standard, important filters in mature pipelines — pVACseq takes coverage and expression inputs for exactly this. Our demo prioritises on predicted binding and structure only. This is a real gap, not a design choice.
**🚫 Boundary:** Don't hand-wave that "it could be added." Name it as a missing filter and say where it would slot in.

### B15. "You're at an edge-AI hackathon. Is 'edge' doing any real work here, or is it a framing device?"
**Answer (the hardest question in the set — answer it head-on):** It's doing real work in one specific sense and not in another. It is **not** doing latency work — nothing here is real-time, and a judge should be suspicious of any edge pitch that claims low latency for a batch workload. What edge buys is **locality**: the computation happens where the controlled-access data already sits, which removes a transfer and the governance apparatus around it, in a 240 W, 150 mm box that fits in a hospital cupboard without a rack or data-centre power. That's an *edge* argument about data gravity and deployability, not about milliseconds.
**🚫 Boundary:** Never make a latency argument for this workload. It's batch, it's throughput-bound, and NVIDIA's own runtime docs say the scaling model *"does not… reduce its individual latency."* Claiming real-time is both false and unnecessary.

---

# 7. Metrics that impress — ranked

## 7.1 The ranking

| # | Metric | Credibility | Why |
|---|---|---|---|
| **1** | **End-to-end time-to-report** (VCF in → ranked report out, wall clock) | ★★★★★ | Impossible to game, requires no trust in your instrumentation, and it is the only number that maps to user value. A clinician does not care about GPU utilisation. **Lead with this.** Report median and p95 over ≥3 runs, and state J. |
| **2** | **Peak unified-memory high-water mark** | ★★★★★ | This is **the** metric that justifies the hardware. It is the direct answer to "why not a cheap GPU?" If your peak is >24 GB you have proven the workload does not fit on a consumer card; if it's >48 GB you've excluded most workstation cards too. Cheap to measure, hard to argue with. **This is your differentiator metric — do not omit it.** |
| **3** | **Sustained throughput (jobs/hour) over a ≥30-min batch** | ★★★★☆ | The input to every projection in §3. Credible *only* if sustained and reported with variance. A burst number is worth nothing. |
| **4** | **Cost per 1,000 candidates** | ★★★★☆ | Strong with a technical *and* a business judge — but only if every input is cited: real hardware price (§1.6), stated amortisation period and utilisation assumption, measured energy, published electricity rate, and a **published** cloud comparator (§4). One invented input voids the whole number. Label it a model. |
| **5** | **GPU utilisation %** | ★★☆☆☆ | Weak alone and easily misread — high utilisation can indicate inefficiency, and on GB10 utilisation reporting has known quirks. Useful only as a **diagnostic**: "GPU util sat at ~90%, so we're compute-bound, not I/O-bound" is a good supporting sentence. Never a headline. |
| **6** | **Energy per candidate (J or Wh per peptide)** | ★★☆☆☆ *(★★★★ if measured at the wall)* | Genuinely compelling for an *edge* AI hackathon — but see the measurement caveat in §7.2. Only report it if you measured at the wall with a meter. |
| **7** | **Achieved TFLOPS / TOPS** | ★☆☆☆☆ | Nobody in this room cares, you will never approach the FP4-sparse peak, and quoting it invites the §1.2 correction. **Skip.** |

## 7.2 Can you actually measure power on GB10? — read this before promising an energy metric

**NVIDIA staff statement, NVIDIA Developer Forums** (https://forums.developer.nvidia.com/t/dgx-spark-power-clarification/349668): [VENDOR]

> "DGX Spark's peak total system power is 240W."
> "The TDP of the GB10 SOC which includes the GPU and the CPU is 140W."
> "The rest of the system which includes the ConnectX-7, SSD and provisions for USB-C devices is 100W."
> **"When measuring power usage via NVIDIA-smi, the wattage displayed measures only GPU power."**

**So `nvidia-smi` on GB10 gives you a partial number, and its accuracy is actively disputed by users.** On the "Max observed wattage" thread (https://forums.developer.nvidia.com/t/max-observed-wattage/362719) one user reports 87 W via `nvidia-smi`/`nvitop` against ~180 W at the wall, and another writes: "the power drawn at the wall is entirely disconnected from what `nvidia-smi` measures." Related threads report `nvidia-smi` showing Power Limits as N/A. [THIRD-PARTY — individual user reports, unverified by us]

**Recommendation:**

- ✅ **If you can borrow a $20 wall power meter (Kill A Watt or similar), do it.** Measure idle, then measure across the full batch, subtract idle, divide by candidates. That is a **[MEASURED]** number nobody can attack, and for an *Edge* AI hackathon "X joules per peptide candidate, measured at the wall" is a genuinely memorable stat.
- ⚠️ If you only have `nvidia-smi`, either **caveat it explicitly** ("GPU-domain power only, per NVIDIA's own note, excludes the ~100 W platform budget") or drop the metric. Do not silently present `nvidia-smi` watts as system power.
- ✅ A defensible fallback needing **no** instrumentation: quote the 240 W system budget as a hard ceiling — *"even at absolute worst case this box cannot exceed 240 W; a single H100 SXM is up to 700 W of configurable TDP for the board alone."* That's a bound, not a measurement, and it is unimpeachable because both halves come from vendor specs — HP's 240 W adapter spec (datasheet p.4) and NVIDIA's H100 datasheet (https://resources.nvidia.com/en-us-gpu-resources/h100-datasheet-24306), which lists H100 SXM max TDP as "up to 700W (configurable)". [VENDOR]

## 7.3 Measurement hygiene checklist

- [ ] Report **median and p95** over ≥3 runs, never best-of-N
- [ ] State **J** (batch size) alongside every throughput and speedup number
- [ ] State whether model **load time** is included
- [ ] Run the throughput batch for **≥30 min** so thermal steady state is reached
- [ ] Record the **peak memory high-water mark** for every run — this is metric #2
- [ ] Log **software versions** (DGX OS / CUDA / container tags) — an ARM64 stack is unusual enough that judges may ask
- [ ] Keep the **raw logs** open in a terminal tab; offering to show them is worth more than any slide

---

# Appendix — master source index

## Hardware (HP)
- HP ZGX Nano G1n Datasheet (c09208797, April 2026) — https://h20195.www2.hp.com/v2/GetPDF.aspx/c09208797
- HP ZGX Nano G1n QuickSpecs (c09212373) — https://h20195.www2.hp.com/v2/GetDocument.aspx?docname=c09212373
- HP product page — https://www.hp.com/us-en/workstations/zgx-nano-ai-station.html
- CDW listing (price) — https://www.cdw.com/product/hp-zgx-nano-g1n-ai-station/8552279

## Hardware (NVIDIA)
- DGX Spark Hardware Overview — https://docs.nvidia.com/dgx/dgx-spark/hardware.html
- DGX Spark ConnectX-7 Networking / clustering — https://docs.nvidia.com/dgx/dgx-spark/spark-clustering.html
- DGX Spark Playbooks — https://github.com/NVIDIA/dgx-spark-playbooks
- Connect Two Sparks — https://build.nvidia.com/spark/connect-two-sparks/overview
- Connect Three Sparks (ring) — https://build.nvidia.com/spark/connect-three-sparks/three-sparks-ring
- NCCL playbook — https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/nccl/README.md
- DGX Spark Power Clarification (NVIDIA staff) — https://forums.developer.nvidia.com/t/dgx-spark-power-clarification/349668
- Max observed wattage thread — https://forums.developer.nvidia.com/t/max-observed-wattage/362719
- GPU power-draw/perf thread — https://forums.developer.nvidia.com/t/dgx-spark-performance-degradation-gpu-power-draw-issue/361294
- H100 datasheet (700 W SXM TDP) — https://resources.nvidia.com/en-us-gpu-resources/h100-datasheet-24306

## Independent hardware reviews
- StorageReview (measured power/thermals/GDS throughput) — https://www.storagereview.com/review/hp-zgx-nano-g1n-ai-station-review-a-secure-sustainable-desk-side-ai-node
- ServeTheHome — https://www.servethehome.com/hp-zgx-nano-g1n-review-the-hp-take-on-the-nvidia-gb10/
- Dual-node NCCL/RDMA measurements (individual, unverified) — https://multimodalflow.net/en/blog/dgx-spark-dual-node-nccl-rdma/
- DGX Spark ↔ EdgeXpert NCCL thread — https://forums.developer.nvidia.com/t/dgx-spark-edgexpert-nccl-only-17-gb-s-over-200gbe/366055

## BioNeMo / model stack
- BioNeMo Inference Runtime overview — https://docs.nvidia.com/bionemo/inference-runtime/overview/
- BioIR install / qualified GPUs — https://docs.nvidia.com/bionemo/inference-runtime/install/
- High-throughput structure prediction blog — https://developer.nvidia.com/blog/high-throughput-structure-prediction-with-bionemo-inference-runtime/
- Boltz-2 NIM release notes (GB10 support) — https://docs.nvidia.com/nim/bionemo/boltz2/1.5.0/release-notes.html
- MSA Search NIM prerequisites — https://docs.nvidia.com/nim/bionemo/msa-search/latest/prerequisites.html
- AlphaFold2 NIM endpoints — https://docs.nvidia.com/nim/bionemo/alphafold2/latest/endpoints.html
- MMseqs2-GPU blog — https://developer.nvidia.com/blog/boost-alphafold2-protein-structure-prediction-with-gpu-accelerated-mmseqs2/

## Models & methods papers
- Boltz-1 — https://www.biorxiv.org/content/10.1101/2024.11.19.624167v1
- Boltz-2 — https://www.biorxiv.org/content/10.1101/2025.06.14.659707v1 · https://pmc.ncbi.nlm.nih.gov/articles/PMC12262699/
- Boltz repo (MIT licence) — https://github.com/jwohlwend/boltz
- AlphaFold2 (Jumper et al., Nature 2021) — https://www.nature.com/articles/s41586-021-03819-2
- AlphaFold human proteome — https://www.nature.com/articles/s41586-021-03828-1
- AlphaFold DB (NAR 2024) — https://academic.oup.com/nar/article/52/D1/D368/7337620
- ParaFold — https://arxiv.org/abs/2111.06340
- Summit proteome-scale AF2 — https://arxiv.org/abs/2201.10024
- MassiveFold — https://www.nature.com/articles/s43588-024-00714-4
- APACE — https://arxiv.org/abs/2308.07954
- LiGen / PASC26 ("embarrassingly parallel") — https://zenodo.org/records/21072879

## Neoantigen tooling
- pVACtools docs — https://pvactools.readthedocs.io/en/latest/pvacseq/run.html
- pVACtools paper — https://aacrjournals.org/cancerimmunolres/article/8/3/409/469797/
- pVAC-Seq (Genome Medicine 2016) — https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-016-0264-5
- NetMHCpan-4.1 — https://academic.oup.com/nar/article/48/W1/W449/5837056
- MHCflurry 2.0 — https://www.sciencedirect.com/science/article/pii/S2405471220302398
- NeoPredPipe — https://link.springer.com/article/10.1186/s12859-019-2876-4
- ImmunoNX — https://arxiv.org/abs/2512.08226

## Data sizes
- NCI GDC API — https://docs.gdc.cancer.gov/API/Users_Guide/Search_and_Retrieval/
- GDC variant-calling pipeline (masked MAF) — https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/
- CRAM 3.1 (Bonfield 2022) — https://pmc.ncbi.nlm.nih.gov/articles/PMC8896640/
- Illumina NovaSeq X Plus specs — https://www.illumina.com/systems/sequencing-platforms/novaseq-x-plus/specifications.html

## Cloud pricing
- AWS EC2 on-demand + data transfer — https://aws.amazon.com/ec2/pricing/on-demand/
- GCP network pricing — https://cloud.google.com/vpc/network-pricing
- GCP accelerator pricing — https://cloud.google.com/products/compute/pricing/accelerator-optimized
- AWS egress waiver (2024) — https://aws.amazon.com/blogs/aws/free-data-transfer-out-to-internet-when-moving-out-of-aws/
- GCP egress waiver (2024) — https://cloud.google.com/blog/products/networking/eliminating-data-transfer-fees-when-migrating-off-google-cloud

## Regulatory / privacy
- 45 CFR 164.514 — https://www.ecfr.gov/current/title-45/section-164.514
- 78 FR 5566 (HIPAA Omnibus / GINA) — https://www.govinfo.gov/content/pkg/FR-2013-01-25/html/2013-01073.htm
- NIH GDS Policy NOT-OD-14-124 — https://grants.nih.gov/grants/guide/notice-files/not-od-14-124.html
- NIH Institutional Certifications — https://grants.nih.gov/policy-and-compliance/policy-topics/sharing-policies/gds/institutional-certifications
- NIH Model DUC — https://osp.od.nih.gov/wp-content/uploads/Model_DUC.pdf
- dbGaP access tiers — https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/about.html
- GDC access processes — https://gdc.cancer.gov/access-data/data-access-processes-and-tools
- GA4GH Framework — https://www.ga4gh.org/framework/
- GA4GH Federated Analysis — https://www.ga4gh.org/work_stream/federated_analysis/
- Gymrek et al. 2013, DOI 10.1126/science.1229566 — https://www.science.org/doi/10.1126/science.1229566
- Homer et al. 2008, DOI 10.1371/journal.pgen.1000167 — https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1000167
- Erlich & Narayanan 2014, DOI 10.1038/nrg3723 — https://www.nature.com/articles/nrg3723

## Clinical & immunology (Block B)
- TESLA — Wells DK et al., *Cell* 183(3):818 (2020), DOI 10.1016/j.cell.2020.09.015, PMID 33038342 — https://www.cell.com/cell/fulltext/S0092-8674(20)31156-9
- TESLA 6% corroboration — *Front Immunol* (2024), DOI 10.3389/fimmu.2024.1347542
- Müller M et al., *Immunity* 56(11):2650 (2023), DOI 10.1016/j.immuni.2023.09.002
- Buckley PR et al., *Front Immunol* (2023), DOI 10.3389/fimmu.2023.1094236
- OptiType — *Bioinformatics* 30(23):3310 (2014), DOI 10.1093/bioinformatics/btu548
- xHLA — *PNAS* 114(30):8059 (2017), DOI 10.1073/pnas.1707945114
- HLA-HD — *Hum Mutat* 38(7):788 (2017), DOI 10.1002/humu.23230
- arcasHLA — *Bioinformatics* 36(1):33 (2020), DOI 10.1093/bioinformatics/btz474
- CookHLA — *Nat Commun* 12:1264 (2021) — https://www.nature.com/articles/s41467-021-21541-5
- pVACseq getting started (HLA is a required arg) — https://pvactools.readthedocs.io/en/latest/pvacseq/getting_started.html
- pVACseq VEP plugins (Frameshift/Wildtype) — https://pvactools.readthedocs.io/en/latest/pvacseq/input_file_prep/vep.html
- Turajlic S et al., *Lancet Oncol* 18(8):1009 (2017), DOI 10.1016/S1470-2045(17)30516-8, PMID 28694034
- AlphaFold 3 — Abramson J et al., *Nature* 630:493 (2024), DOI 10.1038/s41586-024-07487-w
- **AF3 weights terms of use** — https://github.com/google-deepmind/alphafold3/blob/main/WEIGHTS_TERMS_OF_USE.md
- AlphaFold 2 repo (weights CC BY 4.0) — https://github.com/google-deepmind/alphafold
- AF3 openness coverage — https://www.nature.com/articles/d41586-024-01463-0 · https://www.nature.com/articles/d41586-024-03708-4
- Boltz-2 independent critique — *J Chem Theory Comput* (2026), DOI 10.1021/acs.jctc.6c01334, PMID 42579383
- Riley TP et al., *Front Immunol* 10:2047 (2019), DOI 10.3389/fimmu.2019.02047
- Motmaen A et al., *PNAS* 120(9):e2216697120 (2023), DOI 10.1073/pnas.2216697120
- Mikhaylov V et al., *Structure* 32(2):228 (2024), DOI 10.1016/j.str.2023.11.011, PMID 38113889
- NetMHCpan-4.2 — *Front Immunol* (2025), DOI 10.3389/fimmu.2025.1616113
- KEYNOTE-942 — Weber JS et al., *Lancet* 403(10427):632 (2024), DOI 10.1016/S0140-6736(23)02268-7, PMID 38246194
- Rojas LA, Sethna Z et al., *Nature* 618:144 (2023), DOI 10.1038/s41586-023-06063-y, PMID 37165196
- Sethna Z et al., *Nature* 639:1042 (2025), DOI 10.1038/s41586-024-08508-4

---

## ⚠️ Master "do not cite" list

| Claim | Why |
|---|---|
| Boltz-2 "20 seconds per affinity prediction" | Press coverage only; not in paper or boltz.com |
| "NA12878: BAM 233 GB / CRAM 155 GB" | Traces to a patent filing, not Broad or 1000 Genomes |
| MHCflurry ">7,000 predictions/sec, 396× NetMHCpan" | Unverified at source; also a v1.2.0 figure, not 2.0 |
| "~65 GB fastq.gz at 35× WGS" (*Sci Rep* 2025) | Paywalled, not opened |
| mRNA-4157 "6–8 week turnaround" | Secondary sources only; not in the *Lancet* paper. Use Rojas 9.4 weeks |
| "Of 170 NetMHC-predicted neoepitopes, 7 found by MS, 2 immunogenic" | Primary study not located |
| "Embarrassingly parallel" attributed to the Summit AlphaFold paper | Phrase confirmed **absent** from arXiv:2201.10024 |
| HLA-HD headline accuracy % | Its abstract states no overall accuracy figure |
| "DNA is one of HIPAA's 18 identifiers" | Flatly false — not in 45 CFR 164.514(b)(2)(i)(A)–(R) |
| Any FDA approval of a personalised neoantigen vaccine | None exists as of 2026-09-22 |
| TESLA "6%" sourced to the abstract | It's in the Results, not the abstract — cite Figure 1 / Results |
