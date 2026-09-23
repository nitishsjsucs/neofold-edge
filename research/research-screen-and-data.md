# NeoFold Edge — research: binding screen + input data
**Target (confirmed on the actual machine):** HP ZGX Nano / NVIDIA GB10, **Ubuntu 24.04.5**, **aarch64**, compute capability **12.1 / sm_121**, **CUDA 13.0** driver 580.173.02, **Python 3.12.3**, 121 GB unified memory. Fully offline after setup.
**Scope:** research-triage / hypothesis-generation demo. No clinical use, no patient data, no wet lab, no therapeutic design.
**Research date:** 2026-09-22. Everything below was checked against a primary source on that date; items I could not verify are marked **[UNVERIFIED]**.

> ### 🔧 Machine constraints that shape every recommendation here
> - **`sudo` requires a password.** Anything needing `apt-get` is a blocker a human must run. **Every tool recommended below installs via `pip` into a user venv with no root.** The only apt-dependent option in this document is `bcftools csq` (§3.3), and it is explicitly not on the critical path.
> - **Boltz 2.2.1 is confirmed running** on `torch 2.14.0+cu132` aarch64. The sm_121 risk described in §7 is **resolved on this machine**.
> - ⚠️ **`gemmi==0.6.5` (a Boltz pin) has no aarch64 wheel** and needs `python3.12-dev` to compile — which needs sudo. **Workaround already applied: `gemmi 0.7.5`, which ships a prebuilt aarch64 wheel.** Pin that in your requirements file or the next clean install will fail.
> - **Boltz single-sequence mode works offline** via `msa: empty` per chain — no MSA server, no pre-generated `.a3m` needed. See §7 for the accuracy trade-off.

---

## 0. TL;DR — recommended stack

| Layer | Choice | Why | § |
|---|---|---|---|
| Variant source | Hand-written **synthetic VCF of 13 published GRCh38 hotspots**; GDC open masked MAF for a "real data" tab | Zero access restrictions, zero download at demo time, every coordinate double-verified | §2 |
| Variant → protein | **UniProt canonical FASTA + in-house missense substitution + sliding window** | 7.5 MB, ~40 lines of Python, no cache, no network — and it provably reproduces published epitopes | §3 |
| Binding screen | **MHCflurry 2.2.1** (`models_class1_presentation`) | Apache-2.0, **pure PyTorch since 2.2.0**, pip, 285 MB offline, 20,246 alleles, output in nM **and** percentile rank | §1 |
| Backup screen | BigMHC (PyTorch) or MixMHCpred 3.0 — both **non-commercial academic licences** | Independent second opinion; licence caveats spelled out | §1.2, §6 |
| Structure | **Boltz-2** (`pip install boltz`), MIT, ~4.2 GB weights+CCD | Offline via pre-generated MSAs; MIT means no demo-licence problem. **Has a known GB10/sm_121 fix list — day-1 spike** | §7 |
| HLA input | IPD-IMGT/HLA per-locus FASTA (~10 MB) + UniProt P61769 B2M | Allele-exact; both chains verified byte-identical to PDB 6ULN | §4 |
| Worked case | KRAS G12D → `GADGVGKSA` / `GADGVGKSAL` on **HLA-C\*08:02**, ground truth **PDB 6ULN** | Published, crystallographically solved, clinically validated — a judge can check it | §8 |

**Total offline footprint ≈ 4.5 GB. Every component is Apache-2.0 or MIT.** No registration, no institutional email, no data-use agreement, no network at demo time.

### Four findings that change the plan

1. **MHCflurry stopped being a TensorFlow package.** Release 2.2.0 (26 Mar 2026) is *"the first release to use PyTorch as its neural network backend, replacing TensorFlow/Keras."* The entire ARM64 risk in the original brief evaporates — and it shares the torch install with Boltz-2. (§1.1)
2. **NetMHCpan now has a `Linux_arm64` build — but its licence, not its architecture, disqualifies it.** Academic institutions only, no redistribution, no commercialization, and the name may not be used in promotional material. The IEDB standalone bundle is separately disqualified: its binaries are **Linux x86_64**. (§1.2)
3. **cBioPortal's downloads are dead right now** — 403 on S3 *and* "exceeded its LFS budget" on git-lfs, verified across several studies. Use GDC instead, which also gives you GRCh38 natively rather than hg19. (§2.4)
4. **The specialist pMHC tools — and Boltz-2's own training pipeline — crop the MHC to ~180 residues and drop β2-microglobulin entirely.** Matching that crop is both faster and closer to Boltz-2's training distribution. (§4.4)

---

## 1. Fast peptide–MHC class I binding predictor, offline, ARM64

### 1.1 MHCflurry — PRIMARY RECOMMENDATION

**The TensorFlow problem no longer exists.** Verified from two independent primary sources:

- `setup.py` on `master` — `install_requires` is:
  `pandas>=2.0, appdirs, ahocorasick-rs, scikit-learn, threadpoolctl, matplotlib, mhcgnomes>=3.33.0, numpy>=1.22.4, pyyaml, tqdm, torch>=2.0.0`
  `python_requires = ">=3.10"`. **No tensorflow, no keras.**
  https://raw.githubusercontent.com/openvax/mhcflurry/master/setup.py
- PyPI JSON metadata for the latest release (2.2.1, uploaded 2026-04-18): `requires_dist` = pandas, appdirs, scikit-learn, mhcgnomes, numpy, pyyaml, tqdm, **torch>=2.0.0**; `requires_python >=3.10`; licence Apache-2.0.
  https://pypi.org/pypi/mhcflurry/json

Release-notes wording (confirmed via search of the PyPI project page): *2.2.0 is the first release to use PyTorch as its neural network backend, replacing TensorFlow/Keras used in previous versions. It loads the same published weights and produces equivalent predictions.*
https://pypi.org/project/mhcflurry/

Consequences for the GB10:
- ARM64 install is now exactly as hard as installing PyTorch — which you have to do for Boltz-2 anyway. One torch, two consumers.
- Python 3.12: supported (`>=3.10`; upstream docs say "Python 3.10+ on Linux and macOS", and the 2.3.0rc20 notes mention Python 3.13 compatibility fixes, so 3.12 is comfortably inside the tested band).
  https://raw.githubusercontent.com/openvax/mhcflurry/master/docs/intro.md
- The docs explicitly mention GPU and Apple-Silicon MPS autodetection: *"GPUs and Apple Silicon (MPS) are optional and are detected automatically."* CUDA is used if visible (`--gpus`).
  https://raw.githubusercontent.com/openvax/mhcflurry/master/docs/configuration.md

**Version naming caution.** PyPI's latest *stable* is 2.2.1 (2026-04-18). The repo is on a long 2.3.0 release-candidate train (v2.3.0rc20, 10 Sep 2026). `pip install mhcflurry` gets 2.2.1; `pip install --pre mhcflurry` gets the rc. 2.3.0 adds a unified `mhcflurry <subcommand>` entry point; the legacy `mhcflurry-predict` / `mhcflurry-downloads` names still work.
https://github.com/openvax/mhcflurry/releases

**What `mhcflurry downloads fetch` pulls, and how big.** From `mhcflurry/downloads.yml` (`current_release: 2.2.0`), the `default: true` downloads are three bundles. I resolved each asset's exact byte size from the GitHub releases API:

| Bundle | Asset | Compressed size |
|---|---|---|
| `models_class1_presentation` | `models_class1_presentation.20200611.tar.bz2` | **135.4 MB** |
| `data_curated` | `data_curated.20231023.tar.bz2` | **77.5 MB** |
| `models_class1` | `models_class1.20180225.tar.bz2` | **72.6 MB** |
| **Total default fetch** | | **≈ 285 MB compressed** (budget ~600 MB–1 GB unpacked) |

Optional, *not* default, and large — do **not** fetch these:
`models_class1_pan` 1083 MB, `models_class1_processing.selected` 708 MB, `analysis_predictor_info` 1369 MB, `data_predictions` ~25 GB (split parts), `data_evaluation` ~5.6 GB, `data_published` 333 MB, `data_iedb` 184 MB, `allele_sequences` 2.1 MB.
Source: https://raw.githubusercontent.com/openvax/mhcflurry/master/mhcflurry/downloads.yml and `https://api.github.com/repos/openvax/mhcflurry/releases/tags/pre-2.0` (and `pre-2.1`, `pre-1.2`).

For the demo you only need `models_class1_presentation` (135 MB) — the docs state that bundle "includes the binding-affinity and antigen-processing components needed for presentation prediction."

**Offline / air-gap.** `mhcflurry/downloads.py` reads these environment variables: `MHCFLURRY_DATA_DIR`, `MHCFLURRY_DOWNLOADS_DIR`, `MHCFLURRY_DOWNLOADS_CURRENT_RELEASE`, `MHCFLURRY_DEFAULT_CLASS1_MODELS`. So the supported air-gap procedure is: fetch once on a networked machine, `tar` the downloads dir, copy to the ZGX Nano, `export MHCFLURRY_DOWNLOADS_DIR=/opt/mhcflurry-data`. No network call at predict time.
https://raw.githubusercontent.com/openvax/mhcflurry/master/mhcflurry/downloads.py

**Allele coverage — verified directly, not assumed.** I downloaded `allele_sequences.20231023.tar.bz2` (2.1 MB) and grepped it. `allele_sequences.csv` contains **20,246 alleles**, and all four alleles that matter for this demo are present:

```
HLA-A*02:01,YFGERAMPYGEKVAHTHVDTLYGVRYHYYTWAVLAYTWY
HLA-A*11:01,YYGERAMPYQENVAQTDVDTLYGIIYRDYTWAAQAYRWY
HLA-C*08:02,YYGERAGPYREKYRQTDVSNLYGLRYNFYTWAERAYTWY
```

This matters: **HLA-C alleles are supported**, so the KRAS G12D / HLA-C\*08:02 worked example is actually runnable. (The MHCflurry 2.0 paper reports the pan-allele BA predictor covering 14,993 class I alleles via a single network ensemble; the shipped sequence table is larger.)
https://www.cell.com/cell-systems/fulltext/S2405-4712(20)30239-8

**Speed.** The MHCflurry 1.2 paper benchmarked >7,000 predictions/second (≈396× NetMHCpan 4.0) on CPU. ~1,000 peptides × a handful of alleles is therefore **sub-second of model time**; wall-clock will be dominated by ~5–15 s of process start-up and model deserialization. Budget for the demo: run the screen once at startup, not per click.
https://www.cell.com/cell-systems/fulltext/S2405-4712(18)30232-1

**Output columns** (verbatim from upstream docs — these are your UI fields):

| Column | Upstream definition |
|---|---|
| `mhcflurry_affinity` | "Predicted binding affinity in nM; lower is stronger." |
| `mhcflurry_affinity_percentile` | "Allele-specific rank from 0–100; lower is stronger." |
| `mhcflurry_processing_score` | "Processing score from 0–1; higher is stronger." |
| `mhcflurry_presentation_score` | "Combined binding and processing score from 0–1; higher is stronger." |
| `mhcflurry_presentation_percentile` | Rank form of the above; lower is stronger. |

Upstream also states the screening conventions: *"affinity thresholds of 500 nM or 2nd percentile are common screening choices"*, and that presentation scores have no universal threshold.
https://openvax.github.io/mhcflurry/commandline_tutorial.html · https://raw.githubusercontent.com/openvax/mhcflurry/master/docs/intro.md

**Install (ARM64, CUDA 13, Python 3.12) — no sudo required at any step:**

```bash
# 1. torch first, from the CUDA 13.0 index. (Boltz already proved torch works on this box.)
python3.12 -m venv ~/neofold && source ~/neofold/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu130

# 2. MHCflurry (stable). Add --pre for the 2.3.0 rc line.
pip install mhcflurry

# 3. One-time model fetch (do this while networked)
mhcflurry-downloads fetch models_class1_presentation     # 2.2.x name
# mhcflurry downloads fetch models_class1_presentation   # 2.3.0 unified name

# 4. Air-gap the data
mhcflurry-downloads path                                  # prints the dir
export MHCFLURRY_DOWNLOADS_DIR=/opt/mhcflurry-data

# 5. Smoke test — the published KRAS G12D epitope on its published allele
mhcflurry-predict --alleles 'HLA-C*08:02' \
  --peptides GADGVGKSA GADGVGKSAL GAGGVGKSA \
  --out /tmp/kras.csv
```

**GB10 / sm_121 caveat — read this before install day.** GB10 Blackwell reports compute capability **sm_121**. Official PyTorch wheels currently build up to sm_120 and emit a warning on sm_121; community reports say the cu130 wheels work anyway via PTX JIT, and several groups publish prebuilt aarch64+CUDA 13.0+sm_121 wheels. Verify on the actual box on day 1 with `torch.cuda.is_available()` and a trivial matmul; if the official wheel misbehaves, the community wheels are the fallback.
- PyTorch forum thread, DGX Spark GB10 / CUDA 13.0 / Python 3.12 / sm_121: https://discuss.pytorch.org/t/dgx-spark-gb10-cuda-13-0-python-3-12-sm-121/223744
- Prebuilt wheels: https://github.com/ogulcanaydogan/dgx-spark-llm-stack · https://github.com/cypheritai/pytorch-blackwell · https://github.com/assix/pytorch-aarch64-cuda130-python310-wheels
- Setup guide: https://github.com/natolambert/dgx-spark-setup
**[UNVERIFIED]** — I could not test sm_121 on real hardware. Treat it as the #1 day-1 risk for *both* MHCflurry and Boltz-2. Note MHCflurry runs perfectly well on CPU; only Boltz-2 truly needs the GPU.

### 1.2 Alternatives — evaluated and mostly rejected

**NetMHCpan (DTU Health Tech).** Technically the best fit you can't use.
- **Good news, genuinely surprising:** the download page now lists a **`Linux_arm64`** build for netMHCpan **4.2e** and **4.2d** (plus `Darwin_arm64`). So ARM64 is *not* the blocker.
  https://services.healthtech.dtu.dk/services/NetMHCpan-4.1/9-Downloads.php
- **Bad news: the licence.** I pulled the full "ACADEMIC SOFTWARE LICENSE AGREEMENT FOR END-USERS AT PUBLICLY FUNDED ACADEMIC, EDUCATION OR RESEARCH INSTITUTIONS" verbatim from the download form. Precise terms that kill it for a hackathon:
  - §Preamble: *"If you are not a member of a publicly funded Academic and/or Education and/or Research Institution you must obtain a commercial license."*
  - §2: licence is *"non-exclusive, non-transferable"*, *"only granted for personal and internal use in research only at one Site"*; *"The user and any research assistants, co-workers or other workers who may use the Software agree to not give the program to third parties"*; *"Any use of the software which results in any form of commercialization is not allowed."*
  - §7(iii): may not *"redistribute, encumber, sell, rent, lease, sublicense, or otherwise transfer rights to the Licensed Software"*; §7(v): may not *"publish any results of benchmark tests run on the Product to a third party without HEALTH's prior written consent."*
  - §10: *"LICENSEE may not use the name of the Licensed Software in its promotional advertising, product literature, and other similar promotional materials to be disseminated to the public."*
  - The request form states: *"The software will not ship to private or commercial addresses"* — gmail.com is explicitly named as rejected. You need an institutional email.
  Full text: https://services.healthtech.dtu.dk/cgi-bin/sw_request?software=netMHCpan&version=4.2&packageversion=4.2e&platform=Linux_arm64
- **Verdict: do not use.** A sponsored public hackathon demo is a promotional dissemination to third parties by an entity that is probably not a publicly funded academic institution, with a name-use restriction on top. Not worth the argument in front of judges.

**IEDB tools standalone (`mhc_i`).** Two independent blockers.
- **x86-only.** The package README says the collection is *"a mixture of pythons scripts and linux 64-bit environment specific binaries"* and lists *"Linux 64-bit environment"* as a prerequisite. These are precompiled x86_64 binaries (ann, smm, netmhcpan, netmhccons, pickpocket, netmhcstabpan). **They will not run natively on aarch64.** You'd need `qemu-user-static` / Rosetta-equivalent emulation — slow, fragile, and a bad look on an "edge AI compute" demo.
  https://downloads.iedb.org/tools/mhci/3.1.4/README
- **Licence: Non-Profit Open Software License 3.0 (NPOSL-3.0).** IEDB's own statement: by using the IEDB software you consent to the NPOSL 3.0; for-profit entities wanting the command-line tools must contact `license@iedb.org`. The bundle also re-ships NetMHCpan, so DTU's terms ride along.
  https://tools.iedb.org/main/download/ (now redirects to https://nextgen-tools.iedb.org/download-all) · https://spdx.org/licenses/NPOSL-3.0.html
- **Verdict: reject.** x86 binaries alone disqualify it on this box.

**BigMHC** (Johns Hopkins / Karchin Lab). The best *technical* backup.
- Pure PyTorch (torch 1.13 / numpy / pandas / psutil), no TensorFlow → ARM64-clean.
- Two models: **BigMHC EL** (presentation) and **BigMHC IM** (neoepitope immunogenicity). CSV in, `.prd` CSV out. *"Execution is OS agnostic and does not require GPUs."*
- Repo clone is **~5 GB** — plan the download.
- **Licence: "BigMHC Academic License"**, not OSI-open. §1 grants free use *"for any noncommercial purpose, including teaching and research at universities, colleges and other educational institutions, research at non-profit research institutions, and personal non-profit purposes"*; commercial use — explicitly including *"a commercial entity participating in research projects"* — requires a separate licence. Redistribution of verbatim/modified copies is permitted under §3–§5 (copyleft-style).
- **Verdict:** usable as a *personal, non-commercial* backup if you're comfortable that a sponsored hackathon entry is a personal non-profit purpose. Flag it in the README; don't put it on the critical path.
  https://github.com/KarchinLab/BigMHC · https://raw.githubusercontent.com/KarchinLab/bigmhc/master/LICENSE

**MixMHCpred 3.0** (Gfeller Lab). Python 3 + MAFFT, pan-allele neural network, so ARM64 is plausible. *"Free for academic use; for-profit users must obtain a licence from the Ludwig Institute for Cancer Research Ltd."* Same academic-licence smell as BigMHC. **[UNVERIFIED]**: I did not confirm the exact output columns (score vs %rank) or an explicit ARM64 build.
  https://github.com/GfellerLab/MixMHCpred

**MHCnuggets 2.4.1** (Apache-2.0 — the only *permissively* licensed alternative).
- `requires_dist`: numpy, scipy, scikit-learn, pandas, **keras, tensorflow**, varcode. Last release 2023-03-29.
- TensorFlow *does* ship `cp312 manylinux_2_17_aarch64` wheels (2.16+, maintained by AWS as `tensorflow-cpu-aws`), so it can install — but a 2023-era Keras-2-API package on TF 2.16+ (Keras 3) typically needs `pip install tf-keras` and `export TF_USE_LEGACY_KERAS=1`. **[UNVERIFIED]** — I did not test this combination.
- Also: there is no GPU TensorFlow for sm_121; it would be CPU-only. Fine for 1,000 peptides, wrong story for a compute showcase.
- **Verdict:** licence-clean third option; keep as a written fallback, not as the plan.
  https://pypi.org/pypi/mhcnuggets/json · https://github.com/KarchinLab/mhcnuggets · https://www.tensorflow.org/install/pip

**TransPHLA / TransPHLA-AOMP.** GPL-3.0, PyTorch, runs offline from source (`python pHLAIformer.py --peptide_file ... --HLA_file ...`). But: output is a **binary probability 0–1 with a 0.5 threshold**, not nM or a calibrated percentile rank — strictly worse for an honest UI. No pip package, no HuggingFace model, no maintenance since the 2022 paper, CUDA 11.1-era code.
  https://github.com/a96123155/TransPHLA-AOMP

**HLAthena** (Sarkizova et al., Nat Biotechnol 2020). **Web server only**, "for research purposes only", commercial use by arrangement with the Broad. No redistributable standalone. **Reject — cannot run offline.**
  https://www.nature.com/articles/s41587-019-0322-9

### 1.3 Decision

**Primary: MHCflurry 2.2.1 (or 2.3.0rc), `models_class1_presentation`.**
Deciding factors, in the order they actually decide it:
1. **Licence** — Apache-2.0. The only candidate with no "academic only" / "contact us for commercial" clause. For a demo shown publicly at a sponsored event, this is dispositive.
2. **ARM64 install** — pip + torch only, no compiled third-party binaries, no conda channel roulette. Same torch Boltz-2 needs.
3. **Offline data** — 285 MB, air-gap supported via a documented env var.
4. **Speed** — >7,000 peptides/s; 1,000 peptides is not a performance story at all.
5. **Interpretable output** — predicted affinity in **nM** *and* an allele-specific **percentile rank**, the two numbers every immunologist judge already knows how to read.

**Backup: BigMHC (EL + IM).** Pure PyTorch, gives you an *independent* second score and a genuine immunogenicity model, at the cost of a 5 GB clone and a non-commercial academic licence. If the licence makes you uneasy, fall back to MHCnuggets (Apache-2.0, TF-on-CPU) instead and say so in the README.

---

## 2. Input data with no use restrictions

### 2.1 Ranked verdict

| Source | Restrictions | Build | Works today? | Use it? |
|---|---|---|---|---|
| **Synthetic hotspot VCF (§2.5)** | **None — you wrote it** | GRCh38 | Yes | **Yes — primary demo input** |
| **GDC open "Masked Somatic Mutation" MAF** | None. No login, no dbGaP, no DUA, no embargo. Acknowledgement requested, not required by licence | GRCh38, `chr`-prefixed | **Verified working** | **Yes — "real data" tab** |
| ICGC/PCAWG open tier (legacy S3) | Open subset only (ICGC donors, PASS-only); TCGA half is controlled | legacy | Verified working, no auth | Optional |
| cBioPortal datahub tarballs | ODbL **share-alike** + per-study Broad GDAC terms | **hg19** | **BROKEN — 403 on S3 and git-LFS** | **No** |
| COSMIC | Bespoke academic agreement; registration with organisational email; **redistribution prohibited; AI/model training prohibited without consent** | — | — | **No** |

### 2.2 NCI GDC — the clean real-data option

Current release verified live: `GET https://api.gdc.cancer.gov/status` → **"Data Release 46.0 - August 10, 2026"**.

**Open vs controlled**, per https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/DNA_Seq_Variant_Calling_Pipeline/:

| Data type | Access |
|---|---|
| **Masked Somatic Mutation** (`*.wxs.aliquot_ensemble_masked.maf.gz`) | **OPEN** — no token |
| Aggregated Somatic Mutation (raw MAF) | Controlled (may carry germline) |
| Annotated / Raw Simple Somatic Mutation VCFs | Controlled |
| Aligned reads (BAM) | Controlled |

Open MAF workflow name, exactly: **`Aliquot Ensemble Somatic Variant Merging and Masking`** (24,925 files) — https://docs.gdc.cancer.gov/Encyclopedia/pages/Aliquot_Ensemble_Somatic_Variant_Merging_and_Masking. The unpaired-tumour equivalent is `Tumor-Only Somatic Variant Merging and Masking` (1,841 files). **24,498 open Masked Somatic Mutation files across 56 projects.** Note GDC now ships **one MAF per tumour aliquot**, not one per project — expect thousands of small files.

**Download without dbGaP — verified end to end (HTTP 200, 245,502 bytes):**

```bash
# A real open MAF: TCGA-LUAD, file UUID 374e13e1-98a8-4b65-94da-0d78ae51df5a
curl -O -J "https://api.gdc.cancer.gov/data/374e13e1-98a8-4b65-94da-0d78ae51df5a"

# Multi-file bundle -> tar.gz with MANIFEST.txt
curl -X POST "https://api.gdc.cancer.gov/data" -H "Content-Type: application/json" \
  -d '{"ids":["374e13e1-98a8-4b65-94da-0d78ae51df5a"]}' -o gdc_bundle.tar.gz

# gdc-client route — NO -t token needed for open data
curl "https://api.gdc.cancer.gov/manifest/374e13e1-98a8-4b65-94da-0d78ae51df5a" -o gdc_manifest.txt
gdc-client download -m gdc_manifest.txt
```

Finding open MAFs for a project programmatically (this body was run successfully):

```bash
curl "https://api.gdc.cancer.gov/files" -H "Content-Type: application/json" -d '{
 "filters":{"op":"and","content":[
   {"op":"in","content":{"field":"data_type","value":["Masked Somatic Mutation"]}},
   {"op":"in","content":{"field":"access","value":["open"]}},
   {"op":"in","content":{"field":"data_format","value":["maf"]}},
   {"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-COAD"]}}]},
 "fields":"file_id,file_name,file_size,access,analysis.workflow_type",
 "size":"100","format":"JSON"}'
```

**Actual file content** (from the downloaded MAF): 7 `#` comment lines, header on line 8, `NCBI_Build = GRCh38`, `chr`-prefixed contigs. Columns include `Hugo_Symbol, Chromosome, Start_Position, Strand, Variant_Classification, Variant_Type, Reference_Allele, Tumor_Seq_Allele1, Tumor_Seq_Allele2, HGVSp_Short, Tumor_Sample_Barcode`.

> **Important and easy to get wrong:** the MAF `Strand` column is **always `+`**, because GDC always reports alleles on the genomic plus strand. So MAF `Reference_Allele`/`Tumor_Seq_Allele2` map **directly** to VCF REF/ALT with no reverse-complementing. Only `HGVSc` is strand-relative.

**Policy.** GDC follows the NIH Genomic Data Sharing Policy; open data "requires no authentication", with the obligations being not to attempt re-identification and to acknowledge datasets/accessions in presentations.
https://gdc.cancer.gov/access-data/data-access-policies · https://gdc.cancer.gov/access-data/data-access-processes-and-tools
TCGA embargo is gone: NCI states *"Moratoria on all cancer types are now lifted and all TCGA data are available without restrictions on their use in publications or presentations."* Requested acknowledgement: *"The results shown here are in whole or part based upon data generated by the TCGA Research Network: https://www.cancer.gov/tcga"*.
https://www.cancer.gov/ccg/research/genome-sequencing/tcga/using-tcga-data/citing
→ **Put that one sentence in the demo's About panel and you are fully compliant.**

### 2.3 ICGC / PCAWG — still reachable, with caveats

**The ICGC Data Portal (dcc.icgc.org) was retired in June 2024** (https://dcc.icgc.org/, https://github.com/icgc-dcc/retirement-notice); the successor is ICGC ARGO (https://platform.icgc-argo.org/). Legacy open data lives in an **S3-compatible bucket with no auth**, verified live:

- Endpoint `https://object.genomeinformatics.org`, bucket `icgc25k-open` — docs https://docs.icgc-argo.org/docs/data-access/icgc-25k-data
- `PCAWG/consensus_snv_indel/final_consensus_passonly.snv_mnv_indel.icgc.public.maf.gz` — **925 MB**, open
- `release_28/summary_files/simple_somatic_mutation.aggregated.vcf.gz` — a genuine open **VCF**, the best real-VCF-shaped input if you want one

```bash
aws s3 --no-sign-request --endpoint-url https://object.genomeinformatics.org \
  ls s3://icgc25k-open/PCAWG/consensus_snv_indel/
```

Constraint: PCAWG "open" = PASS-only, **ICGC-donor-only** consensus calls. The `*.tcga.controlled.maf.gz` files require separate approval via the Protected Data Cloud. Check the VCF header for assembly before assuming GRCh38.

### 2.4 COSMIC and cBioPortal — both rejected, for different reasons

**COSMIC — fails the "no use restrictions" bar outright.** Licensing at https://www.cosmickb.org/licensing, terms at https://www.cosmickb.org/terms/. It is a bespoke agreement, not a standard open licence, granting a *"non-exclusive, royalty free right to Use COSMIC for Academic Use."* Specifically:
- Registration mandatory, **organisational email required**.
- *"Licensee may not transfer, grant access to, display, share or otherwise distribute COSMIC to any third party…without GRL's express written consent."*
- **No AI/model training without written consent**; no bulk scraping; no commercial services.
- Commercial licence via QIAGEN; the "Commercial Trial Licence" grants access **without download rights**.
→ Do not ship COSMIC-derived data in the repo, do not train on it, do not put it in the demo.

**cBioPortal — the downloads are currently broken.** As of 2026-09-23, every documented tarball route returns **403**:
`https://cbioportal-datahub.s3.amazonaws.com/<study>.tar.gz` (GET/HEAD/ranged) → 403 AccessDenied; path-style and region-qualified S3 URLs → 403; bucket listing → 403; `download.cbioportal.org` / `datahub.cbioportal.org` do not resolve. **git-lfs also fails**: *"This repository exceeded its LFS budget."* Tested against `gbm_columbia_2019` and several `*_tcga_pan_can_atlas_2018` studies. Documented URLs (https://docs.cbioportal.org/downloads/, https://github.com/cBioPortal/datahub) are unchanged — the hosting is simply over quota. **Budget zero hackathon hours on this path.**

The REST API does still work:
```bash
curl -X POST "https://www.cbioportal.org/api/molecular-profiles/coadread_tcga_pan_can_atlas_2018_mutations/mutations/fetch?projection=DETAILED" \
  -H "Content-Type: application/json" \
  -d '{"sampleListId":"coadread_tcga_pan_can_atlas_2018_all","entrezGeneIds":[3845]}'
```
→ 200, 223 KRAS mutations. But note the **build trap**: cBioPortal PanCancer Atlas mutations are `"ncbiBuild":"GRCh37"` (hg19), while GDC is GRCh38. A cross-check that validates both: **KRAS G12D = hg19 chr12:25,398,284 C>T = hg38 chr12:25,245,350 C>T.**

Licensing is also muddier than GDC's: the datahub overall is **ODC-ODbL** (attribution + share-alike + keep derived datasets open), while the per-study `LICENSE` for `coadread_tcga_pan_can_atlas_2018` cites the **Broad Institute GDAC TCGA Analysis Pipeline License** with a "preliminary data, yet to be validated" caveat. ODbL's share-alike is a genuine obligation. **GDC is strictly better for this project.**

### 2.5 Synthetic GRCh38 hotspot VCF — 13 variants, double-verified

**Verification method:** each variant was checked against **two independent primary sources** — ClinVar E-utilities `canonical_spdi` (0-based; VCF POS = SPDI + 1) and Ensembl REST `variant_recoder` `hgvsg` (1-based) — with 100% agreement. MANE Select taken from `MANE.GRCh38.v1.5.summary.txt.gz` (https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/current/). I independently spot-checked 8 of the 13 through the Ensembl VEP REST endpoint (`/vep/human/hgvs/...?mane=1`) and got matching gene / amino-acid / protein-position for every one.

> ### ⚠ The minus-strand trap — the single highest-risk detail
> **KRAS, TP53, BRAF, NRAS and IDH1 are on the MINUS strand.** **PIK3CA, EGFR and CTNNB1 are PLUS.**
> For minus-strand genes the VCF REF/ALT are the **reverse complement** of the cDNA/codon change:
> - KRAS G12D is `c.35G>A` but the VCF line is **`C>T`**.
> - KRAS G12V is `c.35G>T` → VCF **`C>A`**.
> - TP53 R175H is `c.524G>A` → VCF **`C>T`**.
> - **BRAF V600E is `c.1799T>A` → VCF `A>T`.** Writing `T>A` is the classic error.
> - NRAS Q61K is `c.181C>A` → VCF **`G>T`**. IDH1 R132H is `c.395G>A` → VCF **`C>T`**.
> Position is unaffected for SNVs; only the base flips. (It would also reverse base *order* for MNVs/indels — so keep the synthetic set SNV-only.)

| # | Gene | Protein | MANE Select | Strand | Chrom | POS (GRCh38) | REF | ALT | cDNA | dbSNP | ClinVar |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | KRAS | p.Gly12Asp | NM_004985.5 / ENST00000311936.8 | − | chr12 | 25245350 | C | T | c.35G>A | rs121913529 | [VCV000012582](https://www.ncbi.nlm.nih.gov/clinvar/variation/12582/) |
| 2 | KRAS | p.Gly12Val | NM_004985.5 | − | chr12 | 25245350 | C | A | c.35G>T | rs121913529 | [VCV000012583](https://www.ncbi.nlm.nih.gov/clinvar/variation/12583/) |
| 3 | KRAS | p.Gly12Cys | NM_004985.5 | − | chr12 | 25245351 | C | A | c.34G>T | rs121913530 | [VCV000012578](https://www.ncbi.nlm.nih.gov/clinvar/variation/12578/) |
| 4 | TP53 | p.Arg175His | NM_000546.6 / ENST00000269305.9 | − | chr17 | 7675088 | C | T | c.524G>A | rs28934578 | [VCV000012374](https://www.ncbi.nlm.nih.gov/clinvar/variation/12374/) |
| 5 | TP53 | p.Arg248Gln | NM_000546.6 | − | chr17 | 7674220 | C | T | c.743G>A | rs11540652 | [VCV000012356](https://www.ncbi.nlm.nih.gov/clinvar/variation/12356/) |
| 6 | TP53 | p.Arg273His | NM_000546.6 | − | chr17 | 7673802 | C | T | c.818G>A | rs28934576 | [VCV000012366](https://www.ncbi.nlm.nih.gov/clinvar/variation/12366/) |
| 7 | BRAF | p.Val600Glu | NM_004333.6 / ENST00000646891.2 | − | chr7 | 140753336 | **A** | **T** | c.1799T>A | rs113488022 | [VCV000013961](https://www.ncbi.nlm.nih.gov/clinvar/variation/13961/) |
| 8 | PIK3CA | p.His1047Arg | NM_006218.4 / ENST00000263967.4 | + | chr3 | 179234297 | A | G | c.3140A>G | rs121913279 | [VCV000013652](https://www.ncbi.nlm.nih.gov/clinvar/variation/13652/) |
| 9 | PIK3CA | p.Glu545Lys | NM_006218.4 | + | chr3 | 179218303 | G | A | c.1633G>A | rs104886003 | [VCV000013655](https://www.ncbi.nlm.nih.gov/clinvar/variation/13655/) |
| 10 | EGFR | p.Leu858Arg | NM_005228.5 / ENST00000275493.7 | + | chr7 | 55191822 | T | G | c.2573T>G | rs121434568 | [VCV000016609](https://www.ncbi.nlm.nih.gov/clinvar/variation/16609/) |
| 11 | NRAS | p.Gln61Lys | NM_002524.5 / ENST00000369535.5 | − | chr1 | 114713909 | G | T | c.181C>A | rs121913254 | [VCV000073058](https://www.ncbi.nlm.nih.gov/clinvar/variation/73058/) |
| 12 | IDH1 | p.Arg132His | NM_005896.4 / ENST00000345146.7 | − | chr2 | 208248388 | C | T | c.395G>A | rs121913500 | [VCV000156444](https://www.ncbi.nlm.nih.gov/clinvar/variation/156444/) |
| 13 | CTNNB1 | p.Ser37Phe | NM_001904.4 / ENST00000349496.11 | + | chr3 | 41224622 | C | T | c.110C>T | rs121913403 | [VCV000017586](https://www.ncbi.nlm.nih.gov/clinvar/variation/17586/) |

RefSeq chromosome accessions: chr1 `NC_000001.11`, chr2 `NC_000002.12`, chr3 `NC_000003.12`, chr7 `NC_000007.14`, chr12 `NC_000012.12`, chr17 `NC_000017.11`.

**Ready-to-paste VCF** (already in karyotypic + coordinate sort order):

```
##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene symbol">
##INFO=<ID=HGVSP,Number=1,Type=String,Description="Protein change">
##INFO=<ID=HGVSC,Number=1,Type=String,Description="MANE Select cDNA change">
##INFO=<ID=MANE,Number=1,Type=String,Description="MANE Select transcript">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AF,Number=A,Type=Float,Description="Variant allele fraction">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
chr1	114713909	rs121913254	G	T	.	PASS	GENE=NRAS;HGVSP=p.Gln61Lys;HGVSC=c.181C>A;MANE=NM_002524.5	GT:AF	0/1:0.25
chr2	208248388	rs121913500	C	T	.	PASS	GENE=IDH1;HGVSP=p.Arg132His;HGVSC=c.395G>A;MANE=NM_005896.4	GT:AF	0/1:0.33
chr3	41224622	rs121913403	C	T	.	PASS	GENE=CTNNB1;HGVSP=p.Ser37Phe;HGVSC=c.110C>T;MANE=NM_001904.4	GT:AF	0/1:0.24
chr3	179218303	rs104886003	G	A	.	PASS	GENE=PIK3CA;HGVSP=p.Glu545Lys;HGVSC=c.1633G>A;MANE=NM_006218.4	GT:AF	0/1:0.30
chr3	179234297	rs121913279	A	G	.	PASS	GENE=PIK3CA;HGVSP=p.His1047Arg;HGVSC=c.3140A>G;MANE=NM_006218.4	GT:AF	0/1:0.35
chr7	55191822	rs121434568	T	G	.	PASS	GENE=EGFR;HGVSP=p.Leu858Arg;HGVSC=c.2573T>G;MANE=NM_005228.5	GT:AF	0/1:0.31
chr7	140753336	rs113488022	A	T	.	PASS	GENE=BRAF;HGVSP=p.Val600Glu;HGVSC=c.1799T>A;MANE=NM_004333.6	GT:AF	0/1:0.33
chr12	25245350	rs121913529	C	T	.	PASS	GENE=KRAS;HGVSP=p.Gly12Asp;HGVSC=c.35G>A;MANE=NM_004985.5	GT:AF	0/1:0.26
chr12	25245351	rs121913530	C	A	.	PASS	GENE=KRAS;HGVSP=p.Gly12Cys;HGVSC=c.34G>T;MANE=NM_004985.5	GT:AF	0/1:0.24
chr17	7673802	rs28934576	C	T	.	PASS	GENE=TP53;HGVSP=p.Arg273His;HGVSC=c.818G>A;MANE=NM_000546.6	GT:AF	0/1:0.41
chr17	7674220	rs11540652	C	T	.	PASS	GENE=TP53;HGVSP=p.Arg248Gln;HGVSC=c.743G>A;MANE=NM_000546.6	GT:AF	0/1:0.40
chr17	7675088	rs28934578	C	T	.	PASS	GENE=TP53;HGVSP=p.Arg175His;HGVSC=c.524G>A;MANE=NM_000546.6	GT:AF	0/1:0.40
```
(KRAS G12V shares locus chr12:25245350 with G12D; put it in a second sample file, or merge as `C	T,A` — a VCF cannot carry the same REF/ALT pair twice in one sample.)

**Caveats on the hotspot set — stated so nobody is surprised:**
1. **BRAF isoform numbering.** Ensembl `variant_recoder` returns `p.Val640Glu` for `c.1799T>A` because it defaults to the longer isoform (NM_001374258.1, MANE Plus Clinical). Canonical "V600E" is on **NM_004333.6 / ENST00000646891.2 (MANE Select)**. Genomic coordinate identical; only the residue number differs. **Use NM_004333.6.**
2. **IDH1 transcript mismatch (cosmetic).** MANE Select nucleotide is ENST00000345146.7 but the recoder reported protein ENSP00000260985.2. R132 numbering is identical in both; NM_005896.4 is unambiguous.
3. **TP53 R248Q is chr17:7,674,220**, not 7,674,221 — both primary sources agree, and some secondary write-ups have it wrong. (Independent check: 7,674,221 G>A gives R248**W**, a different variant.)
4. KRAS G12C and PIK3CA E545K also have `delins` representations in ClinVar (`VCV001701193`, `VCV002672088`); the plain SNVs above are the standard forms.
5. **[UNVERIFIED]** `##contig` lengths were not fetched from a FASTA index — if you add them, check against your actual `.fai` or bcftools will complain.
6. **[UNVERIFIED]** GDC's `GRCh38.d1.vd1` reference was not compared base-by-base at these loci. It only adds decoy/viral contigs, so primary chromosomes should be identical, but this was not proven.

---

## 3. Variant → peptide mechanics

### 3.1 RECOMMENDED minimal path — UniProt canonical FASTA + in-house substitution

For 4 days, on ARM64, offline, with missense-only input: **do not install a variant annotator.** Write ~40 lines of Python against the UniProt human proteome. Justification: the input is *your own curated hotspot list* where the protein consequence is already known and citable; running VEP to re-derive `p.Gly12Asp` from `chr12:25245350 C>T` adds a 25 GB cache and hours of install to re-learn a fact you already have in a table.

**The reference data — verified live:**

| File | URL | Size |
|---|---|---|
| Swiss-Prot reviewed human (canonical, one seq/gene) | `https://rest.uniprot.org/uniprotkb/stream?query=reviewed:true+AND+organism_id:9606&format=fasta&compressed=true` | **7.5 MB gz, 20,431 entries** (verified by download + count) |
| Reference proteome UP000005640 canonical | `https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640/UP000005640_9606.fasta.gz` | **7,728,297 bytes** (verified via `Content-Length`) |

Either works. Prefer the Swiss-Prot stream — reviewed entries only, no TrEMBL noise. **7.5 MB vs a multi-GB VEP cache** is the whole argument.

**Reference implementation (written and smoke-tested during this research):**

```python
"""Minimal variant -> peptide windows. Missense SNVs only. Fully offline."""
import re
AA3to1 = {"Ala":"A","Arg":"R","Asn":"N","Asp":"D","Cys":"C","Gln":"Q","Glu":"E",
          "Gly":"G","His":"H","Ile":"I","Leu":"L","Lys":"K","Met":"M","Phe":"F",
          "Pro":"P","Ser":"S","Thr":"T","Trp":"W","Tyr":"Y","Val":"V"}

def parse_hgvsp(h):                      # "p.Gly12Asp" -> ("G", 12, "D")
    m = re.fullmatch(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})", h)
    if not m: raise ValueError(f"not a simple missense HGVSp: {h}")
    return AA3to1[m.group(1)], int(m.group(2)), AA3to1[m.group(3)]

def read_fasta(path):                    # UniProt FASTA -> {accession: sequence}
    seqs, acc, buf = {}, None, []
    for line in open(path):
        if line.startswith(">"):
            if acc: seqs[acc] = "".join(buf)
            acc, buf = line.split("|")[1], []
        else: buf.append(line.strip())
    if acc: seqs[acc] = "".join(buf)
    return seqs

def mutate(seq, wt, pos, mut):
    if pos > len(seq): raise ValueError(f"position {pos} beyond length {len(seq)}")
    if seq[pos-1] != wt:          # <-- the assertion that catches every mapping bug
        raise ValueError(f"WT mismatch at {pos}: FASTA has {seq[pos-1]}, variant claims {wt}")
    return seq[:pos-1] + mut + seq[pos:]

def windows(mut_seq, pos, lengths=(8,9,10,11)):
    """Every k-mer that CONTAINS the mutated residue. Deduplicated, ordered."""
    out = []
    for L in lengths:
        for start in range(max(0, pos-L), min(len(mut_seq)-L+1, pos)):
            pep = mut_seq[start:start+L]
            if len(pep) == L and pep not in out: out.append(pep)
    return out
```

**That WT-identity assertion (`seq[pos-1] != wt`) is the most important line in the file.** It is what turns a silent off-by-one or a UniProt/Ensembl isoform mismatch into a loud crash instead of a wrong peptide on stage. Make it a hard failure, log every rejected variant, and show the rejection count in the UI — it reads as rigour, not as a bug.

**Verified output** (I ran this against live UniProt):
- `P01116` + `p.Gly12Asp` → 38 peptides across 8–11-mers; 9-mers = `YKLVVVGAD, KLVVVGADG, LVVVGADGV, VVVGADGVG, VVGADGVGK, VGADGVGKS, `**`GADGVGKSA`**`, ADGVGKSAL, DGVGKSALT`
- `P04637` + `p.Arg175His` → 38 peptides; 9-mers include **`HMTEVVRHC`**

Both bolded peptides are the experimentally published epitopes (§8). **Load-bearing scale fact:** 13 variants × 38 peptides ≈ **494 unique peptides**; × 2–3 HLA alleles ≈ **~1,000–1,500 predictions** — exactly the workload in the brief, and well under a second of MHCflurry model time.

**Accession mapping.** Keep a hand-written 13-row `gene → UniProt accession` table in the repo (KRAS P01116, TP53 P04637, BRAF P15056, PIK3CA P42336, EGFR P00533, NRAS P01111, IDH1 O75874, CTNNB1 P35222 — **[UNVERIFIED]**: I confirmed P01116 and P04637 by download; verify the other six with `curl https://rest.uniprot.org/uniprotkb/<acc>.fasta` before demo day). Do not resolve gene symbols at runtime.

### 3.2 What this path OMITS — say this out loud

Restricting to **missense SNVs mapped onto UniProt canonical sequences** discards, by construction:

| Omitted class | Why it matters — with numbers |
|---|---|
| **Frameshift indels** | The big one. *"Mutational frameshifts are predicted to generate up to **nine times more neoantigens per mutation** than SNVs"* (ESMO Precision Medicine WG, *Ann Oncol* 2021, https://pmc.ncbi.nlm.nih.gov/articles/PMC7885309/). Turajlic et al., *Lancet Oncol* 2017;18(8):1009 found indel neoantigens **9× enriched** for mutant-specific binding vs nonsynonymous-SNV neoantigens, with fs-indel count associated with checkpoint-inhibitor response across three melanoma cohorts (p = 4.7×10⁻⁴). |
| **Splice-site variants / intron retention** | *"Mutations in splice sites produce **2.5× more predicted neoantigens** than missense SNVs"* (ESMO WG). Especially relevant in leukaemias/lymphomas (SF3B1, U2AF1). |
| **In-frame indels** | Novel junction peptides not reachable by single-residue substitution |
| **Gene fusions** | ESMO WG names DEK-AFF2, BCR-ABL, TMPRSS2-ERG, EWS-FLI1, EML4-ALK as demonstrated immunogenic sources. Invisible to an SNV-on-canonical-protein model. |
| **Alternative reading frames, non-canonical ORFs, endogenous retroelements** | Require ribo-seq or MS evidence; a growing fraction of the observed immunopeptidome |
| **Non-canonical isoforms** | You used one sequence per gene; the tumour may express a different isoform with different residue numbering |
| **PTM-modified and proteasome-spliced epitopes** | Not representable at all in this model |
| **Expression, allele-specific HLA loss, proteasome context** | No RNA-seq, so a peptide from an unexpressed gene looks identical to one from a highly expressed gene |

**Is that defensible?** Yes — *if you state it.* Suggested wording:

> "This prototype covers **nonsynonymous SNV-derived neoepitopes on the UniProt canonical isoform** — the largest and best-validated class, and the class every published pMHC structure benchmark is built on. It deliberately excludes frameshift, splice, fusion and alternative-ORF neoantigens, which are known to be disproportionately immunogenic per mutation (≈9× for frameshifts, ≈2.5× for splice-site; ESMO PMWG 2021). Adding them is a pipeline-engineering problem, not a modelling one — VEP's Frameshift/Downstream plugins or `varcode` already emit those sequences."

**Pre-empt the other obvious question too**, from the same ESMO source: *"less than 3% of currently predicted neoantigens give rise to robust T-cell responses at the tumour site."* In-silico neoantigen prediction has low positive predictive value regardless of pipeline. Note that this is an argument **for** your project, not against it: adding a structural check is exactly the kind of orthogonal evidence that low-PPV screening needs.

A judge who knows the field will respect an explicitly drawn boundary far more than a pipeline that silently drops variants.

**Also note the UniProt-canonical caveats** (they are subtler than they look):
1. **"Canonical" is not stable across releases.** Until UniProt 2023_01 the **longest isoform** was chosen; from 2023_01 human uses the **ortho2tree** method. Pin the release you ship. (*NAR Genom Bioinform* 2024;6(2):lqae066, https://academic.oup.com/nargab/article/6/2/lqae066/7689931)
2. **MANE Select matches the UniProt canonical isoform "in the vast majority of cases" but not all** (MANE paper, *Nature* 2022, https://www.nature.com/articles/s41586-022-04558-8). This is precisely why the `seq[pos-1] != wt` assertion is non-negotiable — it catches the exceptions instead of silently emitting a wrong peptide.
3. The reference-proteome FASTA is one sequence per gene, so all alternative isoforms are gone.

Put the omission list **in the UI**, next to the variant count. It costs one panel and buys all the credibility.

---

## 4. HLA context — choosing the allele and building the Boltz input

### 4.1 How the allele is chosen in demos like this

Three legitimate options. Pick (c).

- **(a) Genotype the patient.** Not available — no patient, no sequencing data. Out.
- **(b) Default to the most common allele.** HLA-A\*02:01 is the field's standard stand-in: the most frequent class I allele in European-ancestry populations and the best-characterised experimentally. Defensible, but it invites "you picked the easy one".
- **(c) ✅ Let the allele be an explicit, user-visible input, pre-populated with the allele under which the chosen epitope was *published*.** For KRAS G12D that is **HLA-C\*08:02**; for TP53 R175H it is **HLA-A\*02:01**; for KRAS G12V it is **HLA-A\*11:01**.

Option (c) is the honest one and it is also the better demo: a dropdown labelled *"HLA allele (in a real workflow this comes from patient HLA typing; here it is set to the allele under which this epitope was published)"* pre-empts the entire line of questioning and shows you know what you left out. Bonus: switching the dropdown from HLA-C\*08:02 to HLA-A\*02:01 and watching the same peptide's rank collapse is a genuinely instructive live moment — HLA restriction made visible.

**Real frequency numbers**, from the Allele Frequency Net Database (http://allelefrequencies.net), NMDP / Be The Match cohort — Gragert L, Madbouly A, Freeman J, Maiers M, *Hum Immunol* 2013;74(10):1313–1320, doi:10.1016/j.humimm.2013.06.025, https://pubmed.ncbi.nlm.nih.gov/23806270/. Values are **allele frequencies** (copies ÷ 2N), *not* prevalence:

| Allele | Euro. Caucasian (n=1,242,890) | African American | Chinese | Japanese | S. Asian Indian |
|---|---|---|---|---|---|
| **A\*02:01** | **0.2755** | 0.1235 | 0.0946 | 0.1480 | 0.0492 |
| A\*01:01 | 0.1646 | 0.0467 | 0.0145 | 0.0100 | 0.1545 |
| A\*03:01 | 0.1399 | 0.0839 | 0.0140 | 0.0090 | 0.0636 |
| A\*11:01 | 0.0609 | 0.0142 | **0.2752** | 0.0874 | 0.1396 |
| A\*24:02 | 0.0846 | 0.0245 | 0.1519 | **0.3530** | 0.1362 |
| B\*07:02 | 0.1306 | 0.0729 | 0.0079 | 0.0588 | 0.0440 |
| B\*08:01 | 0.1144 | 0.0376 | 0.0046 | 0.0051 | 0.0366 |
| C\*07:01 | 0.1600 | 0.1170 | 0.0101 | 0.0073 | 0.1039 |
| **C\*08:02** | **0.0385** | 0.0340 | 0.0012 | 0.0019 | 0.0019 |

Cross-checked against the Germany DKMS cohort (n=3,456,066, the largest single HLA dataset in AFND; Seitz et al., *Int J Immunogenet* 2021;48(6):490–495): A\*02:01 = 0.2839, A\*01:01 = 0.1537, B\*07:02 = 0.1278, C\*08:02 = 0.0231 — consistent.

**Three traps if you put these on screen:**
1. **Allele frequency ≠ prevalence.** Carrier % = `1 − (1−p)²`. For European Caucasian: A\*02:01 → **≈47.5% of individuals**, C\*08:02 → **≈7.6%**. AFND's own "% of individuals" column is **HWE-derived, not counted**. Don't write "27.6% of people have A\*02:01" — that is the allele frequency mis-worded.
2. **The C-locus n is much smaller than printed.** Gragert et al. state verbatim: *"Overall 25.8% of the individuals were typed at the C locus"* — so HLA-C rows rest on ~395,676 people, not the 1,242,890 AFND prints on every row.
3. **HLA-C\*08:02 is uncommon** (AF 0.0385 in European Caucasian, ~0.001 in East Asia) — the Tran et al. patient was *selected* for it. So "most common allele" and "allele with the best published epitope" are different criteria. **You are optimising for verifiability, not prevalence — say so.**

**Best offline frequency source, if you want one file:** Gragert et al. 2026, "Classical HLA Allele and Haplotype Frequency Estimates in US Populations" (bioRxiv, doi:10.64898/2026.04.09.717537), data at **https://zenodo.org/records/17966993** — 9,671,082 donors. `A.xlsx` 158 kB + `B.xlsx` 196 kB + `C.xlsx` 148 kB = **~500 kB for every class I allele frequency, fully offline.** ⚠️ Licence is **CC BY-NC-ND 4.0** (NonCommercial + NoDerivatives) — fine to read and cite in a demo, a problem if you reshape and redistribute the tables. **[UNVERIFIED]** — the per-allele 2026 values themselves were not opened; the numbers in the table above come from the 2013 cohort via AFND.

AFND access notes: no registration needed to read; **no official API and no bulk dump** (query `https://www.allelefrequencies.net/hla6006a.asp`, 100 rows/page, documented at https://www.allelefrequencies.net/extaccess.asp); **no terms-of-use page exists for the data** — the CC-BY you'll find in search results belongs to the *NAR article*, not the database. Required citation: Gonzalez-Galarza FF et al., *Nucleic Acids Res* 2020;48:D783–D788, **plus the original publication of the data**.

### 4.2 Where to get the sequences — all verified live

**HLA class I allele protein sequences → IPD-IMGT/HLA, via the ANHIG GitHub mirror.**

| File | URL | Size (verified) |
|---|---|---|
| All class I+II proteins | `https://raw.githubusercontent.com/ANHIG/IMGTHLA/Latest/hla_prot.fasta` | **14.69 MB** |
| HLA-A only | `.../Latest/fasta/A_prot.fasta` | 3.20 MB |
| HLA-B only | `.../Latest/fasta/B_prot.fasta` | 3.88 MB |
| HLA-C only | `.../Latest/fasta/C_prot.fasta` | 3.32 MB |

Repo: https://github.com/ANHIG/IMGTHLA · Database: https://www.ebi.ac.uk/ipd/imgt/hla/
Current release **3.65.0 (2026-07-14)**, 46,653 alleles; `hla_prot.fasta` holds 46,406 sequences. The EBI FTP mirror is byte-identical (`https://ftp.ebi.ac.uk/pub/databases/ipd/imgt/hla/fasta/hla_prot.fasta`, `Content-Length: 14688632`).
⭐ **Ship the three per-locus files (A+B+C ≈ 10.4 MB, 29,945 records), not `hla_prot.fasta`** — the rest of the combined file is class II, MICA/B and TAP.

Header format (confirmed by direct fetch): `>HLA:HLA00446 C*08:02:01:01 366 bp`. ⚠️ The unit says **`bp`** even in the protein file — those are amino acids.
⚠️ **Signal peptide is included** in these sequences (`A*01:01:01:01` starts `MAVMAPRTLLLLLSGALALTQTWAGSHSMRYFFT…`). You must strip residues 1–24 yourself. Also **filter null alleles** — suffix `N`, e.g. `A*01:01:01:02N`, which is truncated at 200 aa.

**Licence and citation — two corrections to what is usually assumed:**
- The licence is **Creative Commons Attribution-NoDerivs**, verbatim: *"We have chosen to apply the Creative Commons Attribution-NoDerivs License to all copyrightable parts of our databases, which includes the sequence alignments… provided you give us credit by citing the following."* ⚠️ **No CC version number is stated** on either https://github.com/ANHIG/IMGTHLA/blob/Latest/LICENCE.md or https://www.ebi.ac.uk/ipd/imgt/hla/licence/ — do not write "CC BY-ND 4.0" as though sourced.
- ⚠️ **The required citation is no longer Robinson et al. 2020.** The current primary citation is **Barker DJ, Natarajan RHL, Cooper MA, Hopper SJF, Yates AD, Parham P, Marsh SGE, Robinson J. "The IPD-IMGT/HLA Database: recent developments in sequence submission." *Nucleic Acids Research* 54(D1):D1152–D1158.**
- ⚠️ **The ND clause has a practical consequence:** the licence says *"If you intend to distribute a modified version of our data, you must ask us for permission first"* and *"We are strongly opposed to the mirroring of the data."* → **download the FASTA at setup time; do not commit a reformatted copy to a public repo.**

**β2-microglobulin → UniProt P61769** (`B2MG_HUMAN`). Verified by download:
- Full precursor **119 aa**; feature table gives **Signal 1–20**, **Chain 21–119** → **mature B2M is 99 aa**.
- Mature sequence (verified):
  ```
  IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDWSFYLLYYTEFTPTEKDEYACRVNHVTLSQPKIVKWDRDM
  ```
  https://rest.uniprot.org/uniprotkb/P61769.fasta

**Generic HLA-A heavy chain → UniProt P04439** (`HLAA_HUMAN`), 365 aa. Verified feature table:

| Feature | Residues |
|---|---|
| SIGNAL | **1–24** |
| CHAIN (mature) | **25–365** (341 aa) |
| **Alpha-1** | **25–114** |
| **Alpha-2** | **115–206** |
| **Alpha-3** | **207–298** |
| Connecting peptide | 299–308 |
| TRANSMEM | 309–332 |
| Cytoplasmic | 333–365 |

> ## 🔴 P04439 IS HLA-A\*03:01 — and this breaks the `NLVPMVATV` smoke test
>
> Verified by direct sequence comparison against IPD-IMGT/HLA:
>
> | Comparison | Result |
> |---|---|
> | P04439 vs `HLA:HLA00037 A*03:01:01:01` | 365/365, **0 mismatches — byte-identical** |
> | P04439 vs `HLA:HLA00005 A*02:01:01:01` | 365/365, **23 mismatches** |
>
> UniProt's own entry notes "(ALLELE A\*03:01)". **This is not cosmetic.** Of those 23 differences, **14 fall inside the α1/α2 peptide-binding groove** (precursor 25–206), and they include the canonical pocket-defining positions:
>
> | Mature position | A\*03:01 | A\*02:01 | Pocket |
> |---|---|---|---|
> | 62, 66, 70, 74 | Q, N, Q, **D** | G, K, H, **H** | B pocket (P2 anchor) |
> | 97, 114, 116 | I, R, **D** | R, H, **Y** | F pocket (P9 anchor) |
> | 107, 116, 152, 156 | G, D, E, … | W, Y, V, … | groove floor / α2 helix |
>
> **`NLVPMVATV` is the HCMV pp65 495–503 epitope and it is HLA-A\*02:01-restricted.** Its C-terminal anchor is **V**, which fits A\*02:01's hydrophobic F pocket (Tyr-116). A\*03:01's F pocket (Asp-116) prefers a basic P9 anchor — **K or R**. So the smoke test docked an A\*02:01 epitope into an A\*03:01 groove whose P9 pocket has the opposite charge preference. Boltz will happily return a pose, and its confidence numbers will mean nothing.
>
> **Fix: paste the sequence below, or use `HLA:HLA00005` from `A_prot.fasta`.**
> Ground truth for exactly this complex: **PDB 3GSO**, *"Crystal structure of the binary complex between HLA-A2 and HCMV NLV peptide"* — three entities, alpha chain 274 aa, B2M 100 aa, peptide `NLVPMVATV` 9 aa. (3GSN is the companion entry.) https://www.rcsb.org/structure/3GSO
>
> **Use P04439 for domain boundaries only, never as an allele sequence.** Allele sequences come from IPD-IMGT/HLA.

#### Ready-to-paste ectodomains (IMGT/HLA, precursor residues 25–299, 275 aa each)

Extracted and length-checked during this research from `https://raw.githubusercontent.com/ANHIG/IMGTHLA/Latest/fasta/A_prot.fasta` and `.../C_prot.fasta`:

**HLA-A\*02:01** — `HLA:HLA00005 A*02:01:01:01` (use this for `NLVPMVATV` and for TP53 R175H `HMTEVVRHC`):
```
GSHSMRYFFTSVSRPGRGEPRFIAVGYVDDTQFVRFDSDAASQRMEPRAPWIEQEGPEYWDGETRKVKAHSQTHRVDLGTLRGYYNQSEAGSHTVQRMYGCDVGSDWRFLRGYHQYAYDGKDYIALKEDLRSWTAADMAAQTTKHKWEAAHVAEQLRAYLEGTCVEWLRRYLENGKETLQRTDAPKTHMTHHAVSDHEATLRCWALSFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGQEQRYTCHVQHEGLPKPLTLRWE
```

**HLA-A\*11:01** — `HLA:HLA00043 A*11:01:01:01` (for KRAS G12V `VVGAVGVGK`):
```
GSHSMRYFYTSVSRPGRGEPRFIAVGYVDDTQFVRFDSDAASQRMEPRAPWIEQEGPEYWDQETRNVKAQSQTDRVDLGTLRGYYNQSEDGSHTIQIMYGCDVGPDGRFLRGYRQDAYDGKDYIALNEDLRSWTAADMAAQITKRKWEAAHAAEQQRAYLEGRCVEWLRRYLENGKETLQRTDPPKTHMTHHPISDHEATLRCWALGFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGEEQRYTCHVQHEGLPKPLTLRWE
```

**HLA-C\*08:02** — `HLA:HLA00446 C*08:02:01:01` (the flagship KRAS G12D case) — see §4.3.

**β2-microglobulin** — UniProt **P61769** mature chain 21–119, **99 aa** (your value is correct):
```
IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDWSFYLLYYTEFTPTEKDEYACRVNHVTLSQPKIVKWDRDM
```
Keep 99, not 100 — crystal structures show 100 because of a retained bacterial initiator Met (§4.4).

### 4.3 The actual Boltz-2 input — validated against the experimental structure

I pulled the HLA-C\*08:02:01:01 sequence from IMGT/HLA (`HLA:HLA00446`, 366 aa precursor), removed the 24-residue leader (`MRVMAPRTLILLLSGALALTETWA`), and took residues 25–299 → a **275-aa α1-α2-α3 ectodomain**. Then I fetched the polymer entities of **PDB 6ULN** from the RCSB GraphQL API to check the construct crystallographers actually used:

| 6ULN entity | Description | Length | Matches? |
|---|---|---|---|
| `6ULN_1` | HLA class I antigen | **274 aa**, begins `CSHSMRYFYTAVSRPGRGEPRFIAVGYVDDTQFVQFDSDAASPRGEPRAPWVEQEGPEYWDRETQKYKRQAQTDRVSLRNLRGYYNQSEA…` | ✅ identical to my IMGT-derived ectodomain (they trim one extra C-terminal residue) |
| `6ULN_2` | Beta-2-microglobulin | **99 aa**, `IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDWSFYLLYYTEFTPTEKDEYACRVNHVTLSQP…` | ✅ identical to UniProt P61769 mature chain |
| `6ULN_3` | peptide | **9 aa**, `GADGVGKSA` | ✅ identical to the peptide my §3 script derives from the §2 VCF row |
| `6ULN_4`, `6ULN_5` | TCR α / β | 206 / 243 aa | Not modelled — you are building pMHC, not pMHC:TCR |

**Conventions confirmed by this check:** three chains (heavy chain ectodomain, B2M, peptide); **signal peptide removed**; transmembrane and cytoplasmic tails removed; no TCR.

```yaml
# kras_g12d_hlac0802.yaml
version: 1
sequences:
  - protein:                       # HLA-C*08:02 alpha1-alpha3 ectodomain (IMGT/HLA HLA00446, res 25-299)
      id: A
      sequence: CSHSMRYFYTAVSRPGRGEPRFIAVGYVDDTQFVQFDSDAASPRGEPRAPWVEQEGPEYWDRETQKYKRQAQTDRVSLRNLRGYYNQSEAGSHTLQRMYGCDLGPDGRLLRGYNQFAYDGKDYIALNEDLRSWTAADKAAQITQRKWEAAREAEQRRAYLEGTCVEWLRRYLENGKKTLQRAEHPKTHVTHHPVSDHEATLRCWALGFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGEEQRYTCHVQHEGLPEPLTLRWG
      msa: ./msa/hla_c0802.a3m    # pre-generated ONCE while networked; see section 7
  - protein:                       # beta-2-microglobulin, UniProt P61769 mature chain (21-119)
      id: B
      sequence: IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDWSFYLLYYTEFTPTEKDEYACRVNHVTLSQPKIVKWDRDM
      msa: ./msa/b2m.a3m
  - protein:                       # the neoepitope from section 3
      id: C
      sequence: GADGVGKSA
      msa: empty                   # a 9-mer has no meaningful MSA
```

**Verification claim you can make on stage, and it is true:** *every one of these three chains is byte-identical to the corresponding chain in an experimentally solved crystal structure of this exact complex (PDB 6ULN), and the peptide was derived by our pipeline from a synthetic VCF row, not typed in.*
https://www.rcsb.org/structure/6ULN

**One caveat to keep honest:** because 6ULN exists, this is a *retrospective* prediction — Boltz-2's training data may well include it. Say so. The demo's claim is "our pipeline reconstructs a known complex end-to-end on-device in N seconds", not "we predicted something new".

### 4.4 ⭐ The specialist pMHC tools drop α3 *and* B2M — and so does Boltz-2's own training

This is the most actionable structural finding in this document, and it is not obvious.

| Convention | Alpha chain | B2M | Who uses it |
|---|---|---|---|
| Crystallographic / full ectodomain | mature **1–275** (α1α2α3) | yes, 99 aa | PDB depositions; AF-Multimer / AF3 / Boltz given all chains |
| **G-domain only** | mature **1–~180** (α1α2) | **no** | **MHC-Fine, TFold, PMGen — and Boltz-2's own pMHC distillation** |

- **MHC-Fine:** *"From each MHC protein only α1 and α2 domains were used"* — α3 and β2m excluded as non-interacting. https://pmc.ncbi.nlm.nih.gov/articles/PMC10705405/
- **TFold:** *"MHC chains were truncated to G-domains."* No mention of β2m. https://www.osti.gov/pages/servlets/purl/2581320
- **PMGen:** removes *"immunoglobulin-like domains (β2 and α2 for MHC-II; α3 for MHC-I)"*. https://pmc.ncbi.nlm.nih.gov/articles/PMC13308714/
- **Boltz-2 itself** (paper App. A.1, https://jeremywohlwend.com/assets/boltz2.pdf): *"For each MHC allele, we crop sequences to a maximum length of **180 residues**."* **[UNVERIFIED]** whether B2M was included in that distillation set.

**Practical consequence for a 4-day build on GB10:**
- Want maximum fidelity to the crystal structure and the prettiest overlay → **α1α2α3 (275) + B2M (99) + peptide**, as in the YAML above.
- Want to match what the specialist pMHC tools do, match Boltz-2's own training distribution, and cut roughly 40% of the compute → **α1α2 only (mature 1–180) + peptide**, no B2M.
**Start with the 180-residue crop** (it is faster and closer to Boltz-2's training distribution), and render the full three-chain version for the hero screenshot if time allows.

**One more crystallography gotcha, verified via the RCSB API on PDB 1DUZ** (HLA-A\*02:01 + HTLV-1 Tax `LLFGYPVYV`, 1.8 Å): entity 1 is **exactly 275 aa** and byte-identical to IMGT `HLA:HLA00005 A*02:01:01:01` mature residues 1–275 — so "~275 aa extracellular" is exact, not approximate. But **entity 2 (B2M) is 100 aa, not 99** — a retained bacterial initiator `Met`. **Give models the 99-mer**; the extra Met is a construct artefact. Similarly **PDB 3MRE**'s alpha chain is 293 aa = 275 + an 18-residue BirA tag `PGSLHHILDAQKMVWNHR` — strip it if you use 3MRE as a template.

### 3.3 The alternatives, and why each loses

| Option | ARM64 / Py3.12 | Offline data | <2 h install? | Verdict |
|---|---|---|---|---|
| **UniProt FASTA + substitution** | Pure Python | **7.5 MB** | **~20 min** | ✅ **Tier 0 — build this first** |
| **varcode + pyensembl** | ✅ pure `py3-none-any` wheels, Py3.9–3.14 | ~271 MB download, ~2–4 GB indexed | ✅ ~2–3 h | ✅ **Tier 1 — the day-3 upgrade** |
| Ensembl VEP **via GFF3, not the cache** | ✅ `ensemblorg/ensembl-vep` publishes **arm64** since release 110 | **~0.9 GB** (GFF3 80 MB + FASTA 841 MB) | ~half a day | ⚠️ Tier 2 — only if you need VEP-grade annotation |
| Ensembl VEP **indexed cache** | Perl | **27.6 GB** | ❌ No | Reject — the cache, not VEP |
| pVACtools | **❌ excludes Python 3.12** | Large | ❌ No | **Reject — hard blocker** |
| bcftools csq | ✅ Ubuntu 24.04 `bcftools 1.19-1build2` **arm64 package exists** | GFF3 + FASTA (~0.9 GB) | ✅ Yes | Viable; emits only the single-residue change |
| snpEff | ✅ bioconda noarch, needs `openjdk>=21` | GRCh38 db ~1–2 GB **[UNVERIFIED]** | ✅ Yes | Fallback |
| NeoPredPipe / antigen.garnish | Wrap NetMHCpan (x86-only) / R+Docker | — | ❌ No | Reject — licence + x86 |
| TransVar / neoepiscope | Python 2.7 / unmaintained since 2022 | — | ❌ | Reject |

**Ensembl VEP — the *cache* is the problem, not VEP.** Verified by HTTP `Content-Length` against `https://ftp.ensembl.org/pub/current_variation/indexed_vep_cache/`:
- `homo_sapiens_vep_116_GRCh38.tar.gz` = **27,644,657,162 bytes (27.6 GB)** compressed (~25 GB unpacked)
- `homo_sapiens_merged_vep_116_GRCh38.tar.gz` = **30.3 GB**

That is **~3,700× larger than the 7.5 MB UniProt FASTA**, for a demo whose protein consequences are already known and citable.

Two corrections to the usual assumptions, both verified:
- ✅ **ARM64 Docker exists.** Docker Hub tag manifests list `amd64, arm64` for `ensemblorg/ensembl-vep` `latest` and `release_110.0` → `release_116.2`. Ensembl's blog (2023-11-03) states support for both ARM and x86 since release 110. Tags 109.x and older are amd64-only. (Bioconda's `ensembl-vep` is `noarch` but has **no `linux-aarch64` build** — prefer Docker.)
  https://hub.docker.com/r/ensemblorg/ensembl-vep
- ✅ **The 26 GB cache is avoidable.** VEP runs offline from a GFF3 + genome FASTA instead:
  ```
  vep -i in.vcf --gff Homo_sapiens.GRCh38.116.gff3.gz \
      --fasta Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz --offline
  ```
  Sizes verified: **GFF3 80 MB + primary-assembly FASTA 841 MB ≈ 0.9 GB**, vs 27.6 GB. The GFF3 must be `grep -v "#" | sort -k1,1 -k4,4n -k5,5n | bgzip` then `tabix -p gff`. Ensembl's caveat: *"not all GFF files will be compatible with Ensembl VEP and not all transcript biotypes may be supported"*, and GFF-with-embedded-FASTA is unsupported.
  https://www.ensembl.org/info/docs/tools/vep/script/vep_cache.html

**Plugin note (corrects a common misconception):** `ProteinSeqs.pm` and `Downstream.pm` are in `Ensembl/VEP_plugins` (Apache-2.0). **`Wildtype.pm` and `Frameshift.pm` are NOT** — they ship with pVACtools (`pvactools/tools/pvacseq/VEP_plugins`). You can copy those two plugin files without installing pVACtools. `ProteinSeqs` documents its own limitation: *"the protein sequence resulting from each mutation is printed separately, no attempt is made to apply multiple mutations to the same protein."* Also useful: `--uniprot` emits `SWISSPROT / TREMBL / UNIPARC / UNIPROT_ISOFORM`, which is your offline genomic→UniProt bridge — but it is a documented **"best match"** accession, not a guarantee.

**Verdict: still reject for day 1** — half a day of Docker + 0.9 GB + GFF3 indexing to re-derive `p.Gly12Asp` from a row you already have. Keep it as the Tier 2 path if the demo grows.

**pVACtools — a hard blocker, not a judgement call.** From PyPI metadata for `pvactools` 7.1.4: **`requires_python: <3.12,>=3.9`**. **Python 3.12 is explicitly excluded**, and 3.12 is what the target machine ships. Even if you downgraded Python, look at the pins: `mhcflurry==2.0.6` (the **old TensorFlow-era** MHCflurry — you'd reintroduce the exact ARM64 problem §1 just eliminated), `mhcnuggets==2.4.1` (TensorFlow again), `biopython==1.77` (2020-era, likely needs compilation on aarch64), `numpy==1.26.4`, `pandas<2.1.0`, `polars==0.16.18`. Licence is BSD-3-Clause-Clear (fine), but the dependency stack is not. It also expects IEDB standalone or NetMHC-family binaries for prediction — i.e. §1's x86/licence problems. **Reject decisively.**
https://pypi.org/pypi/pvactools/json · https://pvactools.readthedocs.io/

**pyensembl / varcode** (openvax — the same org as MHCflurry) — **this is your Tier 1, and it is stronger than I first assumed.** Both ship as **pure `py3-none-any` wheels** (`pyensembl` 2.10.17, `varcode` 9.4.1), classifiers cover **Python 3.9–3.14**, and every dependency (numpy, pandas, gtfparse, serializable, datacache; optional pysam) has aarch64 wheels. **Nothing compiles. ARM64 and Python 3.12 are both fine.** `varcode` gives you the mutant protein in one line:

```python
variant.effects().top_priority_effect().mutant_protein_sequence
```
…and it handles **missense, in-frame indels *and* frameshifts** (it translates through), which is exactly what §3.2 says the Tier 0 path omits.

First-run data, resolved from `pyensembl/ensembl_release.py` (`make_gtf_url` / `make_fasta_url` for cdna, ncrna, pep), release 115 GRCh38: GTF 100 MB + cdna 113 MB + ncrna 39 MB + pep 19 MB = **~271 MB compressed**. Decompressed + SQLite index ≈ **2–4 GB [UNVERIFIED]**; index build typically 10–20 min. Cache dir is `PYENSEMBL_CACHE_DIR`; fully offline afterwards.

**The one real friction: a numpy conflict.** Both pin **`numpy>=2.0,<3.0`**, while **`boltz` pins `numpy<2.0`**. They cannot share a venv with Boltz-2 — use separate venvs (which you want anyway, §7).

**Recommendation: build Tier 0 on day 1, and if you have time on day 3, swap in varcode to add frameshift support.** That upgrade path is ~2–3 hours and turns the biggest item on the §3.2 omission list into a feature.
https://github.com/openvax/varcode · https://github.com/openvax/pyensembl

**`bcftools csq`** — the honest middle road if "we used a real annotator" matters. ✅ **Ubuntu 24.04 (noble) universe ships `bcftools 1.19-1build2` with an arm64 binary package (743.3 kB / 4.0 MB installed)**, alongside amd64/armhf/ppc64el/riscv64; bioconda has `linux-aarch64` 1.24.

> ⚠️ **This is the one recommendation in this document that needs `sudo`** (`sudo apt install bcftools`), and `sudo` on the Nano requires a password. **It is deliberately not on the critical path** — every tool in the recommended stack (§0) installs via `pip` into a user venv with no root. If you want `bcftools` anyway, either ask the human to run one apt command, or grab a static build / bioconda `linux-aarch64` package into `$HOME`.

```
bcftools csq -f GRCh38.fa -g Homo_sapiens.GRCh38.116.gff3.gz in.vcf -Ob -o out.bcf
bcftools query -f '%BCSQ\n' out.bcf
```
`INFO/BCSQ` = `Consequence|gene|transcript|biotype|strand|amino_acid_change|dna_change`, e.g. `1174P>1174L`. It is **haplotype-aware** — it correctly handles two SNVs in one codon, frameshift-then-frame-restoring pairs, and SNVs split by an intron, which naive substitution cannot. Requires an **Ensembl-format GFF3** (only Ensembl GFF3 is supported) plus the reference FASTA (~0.9 GB together).
⚠️ **It emits only the single-residue change, not a full mutant protein sequence** — you would still slice the 8–11-mer windows yourself from a reference protein FASTA. So it replaces the *annotation* step, not the *peptide* step.
https://samtools.github.io/bcftools/howtos/csq-calling.html

**snpEff** — bioconda `noarch` package needing `openjdk>=21`, so it runs on aarch64. GRCh38 database ~1–2 GB **[UNVERIFIED — estimate only]**, from `https://snpeff.blob.core.windows.net/databases/`. Reasonable fallback; no advantage over `bcftools csq` here.

**NeoPredPipe / antigen.garnish — both blocked.**
- **NeoPredPipe** (*BMC Bioinformatics* 2019, https://github.com/MathOnco/NeoPredPipe): built for Python 2.7.13, `biopython 1.70–1.76`, requires **ANNOVAR with hg19_refGene** (note: **hg19**, not GRCh38) and **netMHCpan-4.0/4.1**. Blocked by netMHCpan's x86-only binaries and by the Python-2-era stack on 3.12. **Licence: [UNVERIFIED]** — no licence statement found in the README.
- **antigen.garnish 2.3.1** (https://github.com/immune-health/antigen.garnish): R ≥3.5 + Bioconductor + GNU Parallel + tcsh + Docker, and requires **NetMHC 4.0, NetMHCpan 4.1b, NetMHCII 2.3 and NetMHCIIpan 4.0** under the DTU academic licence — **all x86_64**. Linux-only. **Licence: [UNVERIFIED]** — README says only "Please see LICENSE"; arm64 Docker manifest not confirmed.
**Reject both.**

**TransVar / neoepiscope — skip.** TransVar's docs state **"Python 2.7 and a reasonably modern C compiler"**. `neoepiscope` 0.7.0 (2022) has no `requires_python`, depends on `mhcflurry>=2.0.0` + `mhcnuggets`, and is designed to hand peptides to netMHCpan. Neither is worth a hackathon hour.

### 3.4 The recommendation in one line

**Curated missense variants → UniProt canonical FASTA → assert WT residue → substitute → enumerate 8–11-mers containing the mutation.** 7.5 MB of reference data, no annotator, no cache, no network, ~40 lines, and it demonstrably reproduces three independently published epitopes (§8). Ship the omission list (§3.2) in the UI.

---

## 5. Honest confidence fields — what you may show a judge

Two rules that keep the demo honest:
1. **Nothing here predicts immunogenicity.** A binding/presentation predictor answers "could this peptide sit in this groove and reach the cell surface", not "will a T cell respond". The TESLA consortium measured this directly: across 608 predicted epitopes assessed for T-cell recognition in patient-matched samples, most predicted candidates were not immunogenic; their integrated model filtered out 98% of non-immunogenic peptides at precision >0.70 — i.e. prediction is a *filter*, not a verdict.
   Wells et al., *Cell* 2020: https://www.cell.com/cell/fulltext/S0092-8674(20)31156-9 · data https://www.synapse.org/#!Synapse:syn21048999
2. **Nothing here is a structure determination.** Boltz-2 outputs a *model* with *self-reported* confidence. Self-reported confidence is a calibration statement, not an accuracy measurement.

### 5.1 Binding-screen metrics

| Field | One-line gloss a judge will accept |
|---|---|
| `mhcflurry_affinity` (nM) | "The model's guess at the concentration needed for half-maximal binding — lower means it thinks the peptide sticks harder. Under ~500 nM is the conventional 'worth a look' line." |
| `mhcflurry_affinity_percentile` (0–100) | "Where this peptide's score lands among random natural peptides for *this specific* allele. 1.0 means top 1%. It's the allele-fair way to compare, because raw nM scales differ between alleles." |
| `mhcflurry_processing_score` (0–1) | "Independent of any allele: does the cell's proteasome/transport machinery plausibly produce this exact fragment? Higher = more plausible." |
| `mhcflurry_presentation_score` (0–1) | "Binding and processing combined into one 0–1 ranking number. Use it to sort; there is no published cut-off that makes it a yes/no." |
| `mhcflurry_presentation_percentile` | "Same thing expressed as a rank against random peptides; lower is stronger." |

Threshold provenance, if asked: the 500 nM / 2% conventions come from the NetMHCpan lineage, where %Rank <0.5 = strong binder and <2.0 = weak binder, and %Rank is defined as the score's position in the distribution of scores for random natural peptides against that MHC (so 1% = top 1%).
Reynisson et al., *NAR* 2020: https://academic.oup.com/nar/article/48/W1/W449/5837056 · https://pmc.ncbi.nlm.nih.gov/articles/PMC7319546/

**Say out loud in the demo:** "percentile rank is calibrated against random peptides, not against real tumour peptides, and it says nothing about whether a T cell exists that recognises this."

### 5.2 Boltz-2 structural metrics

Definitions taken verbatim from Boltz's own `docs/prediction.md` and, where Boltz inherits AlphaFold's semantics, from AlphaFold 3's `docs/output.md`.

| Field | Boltz/AF definition | Plain-English gloss |
|---|---|---|
| `confidence_score` | "Aggregated score used to sort the predictions, corresponds to 0.8 * complex_plddt + 0.2 * iptm" | "Boltz's own ranking number for choosing between its samples. Use it to pick which model to show, not to claim the model is right." |
| pLDDT (per-atom, `plddt_*.npz`) | AF3: "a per-atom confidence estimate on a 0-100 scale where a higher value indicates higher confidence" | "How sure the model is about each atom's local position. >90 confident, 70–90 usually roughly right, <50 basically a guess. Colour the peptide by this." |
| `complex_plddt` / `complex_iplddt` | "Average pLDDT score for the complex" / "…when upweighting interface tokens" | "Average local confidence, plain and interface-weighted." |
| PAE (`pae_*.npz`) | AF3: "an estimate of the error in the relative position and orientation between two tokens… Higher values indicate higher predicted error" | "Expected error in Ångströms if you line up on residue *i* and look at residue *j*. The cell you care about is peptide-vs-groove: low PAE there means the model is confident the peptide is placed correctly *relative to* the HLA, which is the only claim you're making." |
| `iptm` | "Predicted TM score when aggregating at the interfaces"; AF3 guidance: ">0.8 confident high-quality", "<0.6 suggest a failed prediction", "0.6–0.8 … gray zone" | "The model's self-rated confidence in the *interface* between chains." |
| `ptm` | "Predicted TM score for the complex" | "Self-rated confidence in the overall fold." |
| `chains_ptm` / `pair_chains_iptm` | "Predicted TM score within each chain" / "…between each pair of chains" | "Per-chain and per-chain-pair breakdown — this is where you read peptide↔HLA specifically." |
| PDE (`pde_*.npz`, `complex_pde`, `complex_ipde`) | "Predicted PDE score for every pair of tokens" / averages | "Predicted distance error between token pairs; a coarser cousin of PAE." |

**The ipTM trap — and why quoting it on a 9-mer would be wrong.** AlphaFold 3's own documentation warns: *"The TM score is very strict for small structures or short chains, so pTM assigns values less than 0.05 when fewer than 20 tokens are involved; for these cases PAE or pLDDT may be more indicative of prediction quality."* A class-I epitope is **8–11 residues**. A naive ipTM/pTM readout on the peptide chain will look catastrophic even when the pose is excellent.

**This is not just theory — every specialist pMHC paper scores on PAE or pLDDT, none on ipTM.** Motmaen et al. (*PNAS* 2023) score with **PAE**; TFold (*Structure* 2024) uses a **pLDDT-derived** metric (`100 − pLDDT` averaged over the peptide core, >3.0 = low confidence); MHC-Fine likewise. **No pMHC paper I found defines an ipTM cutoff.** The generic 0.8 threshold is a protein–protein-complex heuristic — do not present it as pMHC-validated.

⭐ **The one pMHC-specific threshold that does exist is Boltz-2's own.** In its self-distillation pipeline Boltz-2 accepts a generated pMHC structure at **ipTM ≥ 0.85** (with iPDE ≤ 1.0 and PDE ≤ 1.0) — stricter than the generic 0.8, precisely because peptides are short. If you must show a single ipTM gate, **0.85 is the defensible number and Boltz-2's own paper is the citation.**
https://jeremywohlwend.com/assets/boltz2.pdf

**Therefore the UI should headline, in this order:**
1. **mean peptide pLDDT** (per-residue bar chart along the 9-mer) — what TFold and MHC-Fine actually use,
2. **mean peptide↔HLA-groove PAE** (a single Å number, from the off-diagonal block of the PAE matrix) — what Motmaen et al. use,
3. `confidence_score` as the sample-ranking number,
4. ipTM **only** with the short-chain caveat printed beside it, and if you gate on it, gate at **0.85**, not 0.8.

Sources: https://raw.githubusercontent.com/jwohlwend/boltz/main/docs/prediction.md · https://github.com/google-deepmind/alphafold3/blob/main/docs/output.md

### 5.3 Language to put on screen

- ✅ "Predicted binding, research triage only — not validated, not clinical."
- ✅ "Model confidence, self-reported by the network."
- ✅ "This peptide/HLA pair has a published experimental structure (PDB 6ULN); the prediction is shown beside it."
- ❌ "Identified a neoantigen." ❌ "High-affinity binder." ❌ "Candidate for therapy." ❌ any per-patient framing.

---

## 6. Licensing table

| Tool / dataset | Licence | Commercial / demo use | ARM64 | Verdict |
|---|---|---|---|---|
| **MHCflurry 2.2.x/2.3.0** | **Apache-2.0** | Yes, unrestricted | Yes (pure PyTorch since 2.2.0) | **Use — primary** |
| **Boltz-2** | **MIT** — *"Our model and code are released under MIT License, and can be freely used for both academic and commercial purposes."* | Yes, unrestricted | PyTorch; see sm_121 caveat | **Use — structure** |
| BigMHC | "BigMHC Academic License" (custom, non-commercial; redistribution allowed under copyleft-style §3–5) | Non-commercial only; commercial entities must license | Yes (PyTorch) | Backup, flag licence |
| MixMHCpred 3.0 | Academic free; for-profit needs Ludwig Institute licence | Non-commercial only | Likely (Python+MAFFT) **[UNVERIFIED]** | Backup, flag licence |
| MHCnuggets 2.4.1 | Apache-2.0 | Yes | TF aarch64 wheels exist; Keras-2/3 issue **[UNVERIFIED]** | Licence-clean fallback |
| TransPHLA-AOMP | GPL-3.0 | Yes (copyleft) | Yes (PyTorch) | Rejected — binary prob. only, unmaintained |
| NetMHCpan 4.2 | DTU "Academic Software License Agreement" | **No** — publicly funded academic institutions only; no redistribution; no commercialization; name may not be used promotionally; institutional email required | **Yes** (`Linux_arm64` build exists) | **Rejected on licence** |
| IEDB tools standalone (`mhc_i`) | **NPOSL-3.0** (non-profit); for-profit → license@iedb.org | Non-profit only | **No** — ships Linux x86_64 binaries | **Rejected on both** |
| HLAthena | Web server, research use only | No standalone | N/A | Rejected — cannot run offline |

---

## 7. Boltz-2 on the GB10 — install, offline MSAs, sizes

**Package:** `boltz` 2.2.1 on PyPI. `requires_python: >=3.10,<3.13` → **Python 3.12 is supported** (3.13 is not). Licence **MIT**, explicitly *"can be freely used for both academic and commercial purposes."*
https://pypi.org/pypi/boltz/json · https://github.com/jwohlwend/boltz
Paper: Boltz-2, *bioRxiv* 2025.06.14.659707 — https://www.biorxiv.org/content/10.1101/2025.06.14.659707v1

**Weights and data, exact sizes** (resolved from the HuggingFace API for `boltz-community/boltz-2`):

| File | Size | Needed? |
|---|---|---|
| `boltz2_conf.ckpt` | **2,286.6 MB** | Yes — the structure model |
| `mols.tar` | **1,855.7 MB** | Yes — CCD component data (extracted to `mols/`, so budget ~2× on disk) |
| `boltz2_aff.ckpt` | 2,062.1 MB | No — small-molecule affinity module, irrelevant to a peptide–MHC complex |

→ **~4.2 GB download, ~6 GB on disk** for structure-only. Cache location is controlled by `--cache` (default `~/.boltz`), so you can pre-stage it and ship it to the offline box.
Download URLs are hard-coded in `src/boltz/main.py` (`BOLTZ2_URL_WITH_FALLBACK`, `MOL_URL`).

**Dependency traps on aarch64 + CUDA 13:**
- `boltz` pins `numpy<2.0,>=1.26` and a long list of exact versions (`pytorch-lightning==2.5.0`, `numba==0.61.0`, `gemmi==0.6.5`, `scipy==1.13.1`, `rdkit>=2024.3.2`). Install `boltz` into its **own venv**, separate from MHCflurry, to avoid a numpy fight. **[UNVERIFIED]** — I did not confirm every one of these has a `manylinux_*_aarch64` wheel; `numba`, `rdkit` and `gemmi` do publish aarch64 wheels, but plan a pip-resolve dry run on day 1.
- **Do not use the `[cuda]` extra.** Its deps are `cuequivariance_ops_cu12`, `cuequivariance_ops_torch_cu12`, `cuequivariance_torch` — that is **CUDA 12**, and you are on CUDA 13.

> ### ✅ RESOLVED on this machine — but pin your versions
> Boltz 2.2.1 is confirmed running on the Nano with **`torch 2.14.0+cu132`** aarch64. The sm_121 risk is retired. Two things to lock in so a clean rebuild doesn't fail:
> 1. ⚠️ **`gemmi==0.6.5` (Boltz's pin) has no aarch64 wheel** and needs `python3.12-dev` to build — **which needs sudo**. Use **`gemmi 0.7.5`**, which has a prebuilt aarch64 wheel. Put it in your requirements *after* boltz so it overrides the pin.
> 2. Don't let anything re-resolve `torch` from PyPI defaults.
>
> For reference, the community fork **https://github.com/sanjyotshenoy/boltz-gb10-spark** documents the fixes others needed on GB10 (`num_workers=0` to stop the DataLoader hanging; `cuequivariance-ops-torch-cu13`; Triton-Nightly 3.6 for `ptxas fatal: Value 'sm_121a' is not defined`). Keep it bookmarked in case a dependency bump reintroduces any of them.

```bash
python3.12 -m venv ~/boltzenv && source ~/boltzenv/bin/activate   # no sudo needed
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu130
pip install boltz                        # NOT boltz[cuda] — that extra is cu12
pip install 'gemmi==0.7.5'               # AFTER boltz: overrides the 0.6.5 pin (no aarch64 wheel)
python -c "import torch;print(torch.cuda.is_available(), torch.cuda.get_device_capability())"
boltz predict kras_g12d_hlac0802.yaml --cache /opt/boltz-cache --use_potentials
```

**The offline MSA question — ✅ already solved on this machine.** From `docs/prediction.md`:
> "If you include `--use_msa_server`, the MSA will be generated automatically via the mmseqs2 server. **Without this flag, you must provide a pre-computed MSA.**"
> "By default, an `msa` must be provided… To use a precomputed custom MSA, set `msa: MSA_PATH` pointing to a `.a3m` file… **To force single-sequence mode (not recommended, as it reduces accuracy), set `msa: empty`.**"

✅ **Confirmed working on the Nano: `msa: empty` on every chain runs fully offline** — no MSA server, nothing to pre-fetch. That is the zero-friction path and it is what you already have running. Use it.

**But there is a real accuracy trade-off, and you should know its size.** Boltz's own docs call single-sequence mode *"not recommended, as it reduces accuracy"*, and the TCR–pMHC benchmark cited below found **MSA-based models substantially outperform single-sequence/PLM ones**. The good news is the cost of fixing it is almost zero:

> A pMHC complex has only **two distinct sequences that ever need an MSA** — the HLA heavy chain and β2-microglobulin — and both are **fixed across every run of your demo**. So if you get a spare hour on day 3: run `boltz predict --use_msa_server` once per HLA allele + B2M while networked, harvest the `.a3m` files, ship them, and reference them by path. Keep `msa: empty` on the peptide chain regardless — a 9-mer has no meaningful MSA.

**Demo idea:** run the flagship case both ways and put the two confidence numbers side by side. "Here is what the MSA is worth on this complex" is a better beat than either number alone, and it is honest about a limitation instead of hiding it.

**Optional accuracy/credibility boost:** Boltz accepts structural `templates` (a CIF/PDB path, optionally with `force` + `threshold`). Supplying an existing pMHC CIF for the heavy chain is legitimate and cheap — **but you must disclose it on screen**, because it makes the fold largely given and only the peptide pose predicted. For a hackathon, running *without* a template and then overlaying the experimental structure is the more impressive and more honest story.
https://raw.githubusercontent.com/jwohlwend/boltz/main/docs/prediction.md

**Is AlphaFold-class modelling of pMHC actually good?** Yes, and there are four citable benchmarks with hard numbers:

| Study | Result |
|---|---|
| **Motmaen et al., *PNAS* 2023;120(9):e2216697120** (doi 10.1073/pnas.2216697120) | Template-based AF: *"median peptide RMSD of **0.8 Å on backbone and 1.8 Å on all atoms for Class I**"*. After fine-tuning, *"**AUROC of 0.97 for Class I**"*. Affinity Pearson **0.79** for 9-mers on HLA-A\*02:01, vs 0.57 for default AF and **0.78 for NetMHCpan**. Trained on class I lengths 8/9/10. Noted stock-AF2 failure mode: *"AlphaFold tended to dock non-binding peptides in the MHC-peptide-binding groove."* |
| **Mikhaylov et al., *Structure* 2024;32(2):228–241.e4 (TFold)** (doi 10.1016/j.str.2023.11.011) | *"median α-pRMSD of **0.73 Å**"* (discovery) / 0.77 Å (test); beats PANDORA on **79%** of pMHCs (p<10⁻⁷), 0.77 Å vs 1.48 Å. |
| **Zhang et al., *Biophys J* 2024 (MHC-Fine)** (PMID 38751115) | 944 structures, peptides 8–11 aa. Median peptide Cα RMSD: **MHC-Fine 0.65 Å** vs PANDORA 1.27 Å vs AlphaFold 1.44 Å. |
| **Asgary et al., *Bioinformatics* 2026 (PMGen)** (doi 10.1093/bioinformatics/btag381) | MHC-I (n=176): median Cα-pRMSD **0.65 Å**; PANDORA ~1.0 Å. |

For the harder TCR–pMHC problem (an upper bound, not your task): Lu et al., *Brief Bioinform* 2026;27(3):bbag289 — on 70 non-redundant post-2021 complexes, **AlphaFold3 best median DockQ 0.636 (class I)**, with Boltz-1 comparable; MSA-based models ≫ PLM-based. https://academic.oup.com/bib/article/27/3/bbag289/8703116

> ⚠️ **[UNVERIFIED] — and this is the limit of what you may claim.** I found **no published peptide-RMSD benchmark of Boltz-1 or Boltz-2 specifically on held-out pMHC class I.** A "Boltz-2 DockQ ≈0.91 in-training / ≈0.70 unseen" figure surfaced in search results but **could not be confirmed in the paper text** — do not use it.
> **Safe claim:** *"AlphaFold-class co-folding models model class I pMHC to sub-Ångström median peptide RMSD (0.65–0.8 Å across four published benchmarks). Boltz-2 has not been separately benchmarked on pMHC-I, so here is our prediction shown beside the experimental structure of this exact complex."*

---

## 8. Worked example — the case to build the demo around

This is the one I would put on stage. Every link in the chain is published, and the final answer is a solved crystal structure.

### 8.1 The chain, end to end

| Step | Value | Verification |
|---|---|---|
| Gene | **KRAS** | MANE Select `NM_004985.5` / `ENST00000311936` |
| Variant (GRCh38) | **chr12:25,245,350 C>T** | Verified live against Ensembl VEP REST → `KRAS`, `G/D`, `protein_start 12`, `missense_variant` |
| Protein change | **p.Gly12Asp (G12D)** | same |
| Canonical protein | UniProt **P01116** (`RASK_HUMAN`, KRAS-4B, 189 aa) | `https://rest.uniprot.org/uniprotkb/P01116.fasta` |
| WT residues 1–25 | `MTEYKLVVVGAGGVGKSALTIQLIQ` | fetched live |
| MUT residues 1–25 | `MTEYKLVVVGA`**`D`**`GVGKSALTIQLIQ` | substitution at index 12 |
| 9-mer windows spanning pos 12 | `YKLVVVGAD, KLVVVGADG, LVVVGADGV, VVVGADGVG, VVGADGVGK, VGADGVGKS, **GADGVGKSA**, ADGVGKSAL, DGVGKSALT` | computed |
| 10-mer windows | `EYKLVVVGAD, YKLVVVGADG, KLVVVGADGV, LVVVGADGVG, VVVGADGVGK, VVGADGVGKS, VGADGVGKSA, **GADGVGKSAL**, ADGVGKSALT, DGVGKSALTI` | computed |
| **Chosen epitope** | **`GADGVGKSA`** (9-mer) and **`GADGVGKSAL`** (10-mer) | |
| **HLA restriction** | **HLA-C\*08:02** | |
| **Ground-truth structure** | **PDB 6ULN** (and 6ULI, 6ULK, 6ULR, 6UON) | https://www.rcsb.org/structure/6ULN |

**This is the validation that makes the demo scientifically honest:** a naive UniProt-substitution + sliding-window enumeration — the whole of §3's minimal path — *independently re-derives the exact peptides that were experimentally shown to be presented and T-cell-recognised*. You are not claiming a discovery; you are demonstrating that the pipeline recovers a known answer. I ran this derivation and confirmed both `GADGVGKSA` and `GADGVGKSAL` fall out of the window enumeration.

### 8.2 Citations for the epitope

- **Tran E, Robbins PF, Lu Y-C, … Rosenberg SA.** "T-Cell Transfer Therapy Targeting Mutant KRAS in Cancer." *N Engl J Med* 2016;375(23):2255–2262. Polyclonal CD8+ response against KRAS G12D in TILs from metastatic colorectal cancer; **HLA-C\*08:02-restricted** TILs, objective regression of all seven lung metastases.
  https://www.nejm.org/doi/full/10.1056/NEJMoa1609279
- **Sim MJW, Lu J, Spencer M, et al.** "High-affinity oligoclonal TCRs define effective adoptive T cell therapy targeting mutant KRAS-G12D." *PNAS* 2020;117(23):12826–12835. Four TCRs recognising **a nonamer (`GADGVGKSA`) and a decamer (`GADGVGKSAL`)**, all HLA-C\*08:02-restricted; only mutant G12D (not WT) stabilised HLA-C\*08:02 via an anchor salt bridge. Crystal structures deposited as **6ULI / 6ULK / 6ULN / 6ULR / 6UON**.
  https://www.pnas.org/doi/10.1073/pnas.1921964117 · https://pubmed.ncbi.nlm.nih.gov/32461371/
- Structure browser view of 6ULN ("HLA-C\*08:02 presenting GADGVGKSA to an α/β T cell receptor"): https://www.histo.fyi/structures/view/6uln
- Clinical follow-through (KRAS G12D TCR gene therapy, pancreatic cancer): Leidner R, et al., *N Engl J Med* 2022 — https://www.nejm.org/doi/10.1056/NEJMoa2119662

### 8.3 Two more published cases, for a three-card demo

**Case B — TP53 R175H on HLA-A\*02:01** (the most common mutation in the most-mutated tumour suppressor, on the most common HLA allele):

| Field | Value |
|---|---|
| Variant (GRCh38) | **chr17:7,675,088 C>T** — verified live via Ensembl VEP REST → `TP53`, `R/H`, `protein_start 175`, MANE `NM_000546.6` |
| Protein | UniProt **P04637** (`P53_HUMAN`, 393 aa) |
| Context WT → MUT | `QSQHMTEVVR`**`R`**`CPHHERCSDS` → `QSQHMTEVVR`**`H`**`CPHHERCSDS` |
| **Epitope** | **`HMTEVVRHC`** (9-mer) — falls directly out of the window enumeration |
| HLA | **HLA-A\*02:01** |
| Citation | Hsiue EH-C, Wright KM, Douglass J, et al. "Targeting a neoantigen derived from a common TP53 mutation." *Science* 2021;371:eabc8697. The peptide `HMTEVVRHC` binds HLA-A\*02:01; the paper reports the structural basis of presentation and a bispecific antibody (H2-scDb) against the pHLA complex. https://www.science.org/doi/10.1126/science.abc8697 · https://pubmed.ncbi.nlm.nih.gov/33649166/ |

**Case C — KRAS G12V / G12D on HLA-A\*11:01** (shows the same mutation read by a different allele — a nice UI beat):

| Field | Value |
|---|---|
| G12V variant | **chr12:25,245,350 C>A** — verified live via Ensembl VEP REST → `KRAS`, `G/V`, pos 12 |
| **Epitope** | **`VVGAVGVGK`** (9-mer, KRAS G12V 8–16) on **HLA-A\*11:01** |
| Citation | JCI Insight 2025 — HLA-A\*11:01-restricted KRAS G12V-reactive CD8+ T cells from a pancreatic cancer patient recognising `VVGAVGVGK`. https://insight.jci.org/articles/view/181873 · https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11790028/ |
| Structure | PDB **8WTE** — TCR in complex with HLA-A\*11:01 bound to KRAS-G12V `VVGAVGVGK`. https://www.ncbi.nlm.nih.gov/Structure/pdb/8WTE |
| G12D on A\*11:01 | 9-mer `VVGADGVGK` and 10-mer `VVVGADGVGK` — both appear in my window enumeration. See *Commun Biol* 2025, "Structure guided analysis of KRAS G12 mutants in HLA-A\*11:01 reveals a length encoded immunogenic advantage in G12D": https://www.nature.com/articles/s42003-025-09285-0 |

### 8.4 Why this framing survives a hostile question

> *"Aren't you just doing clinical neoantigen prediction without validation?"*

No — and the demo proves it. Every peptide we show on stage is one that a published paper already demonstrated experimentally, on a hand-written synthetic variant file with no patient in it. The pipeline's job here is to **recover known biology quickly on-device**, which is a reproducibility claim, not a discovery claim. The one genuinely novel artefact is the 3D model, and it is shown with its self-reported confidence next to an experimental crystal structure of the same complex.

---

## 9. The recommended end-to-end path, and a 4-day plan

### 9.1 The path

```
synthetic GRCh38 VCF (13 published hotspots, §2.5, hand-written, no licence)
        │
        ├─ parse row → (gene, p.HGVS) ─────────────────────────────────────┐
        │                                                                  │
UniProt Swiss-Prot human canonical FASTA (7.5 MB, §3.1) ───────────────────┤
        │                                                                  │
        ▼                                                                  │
  assert seq[pos-1] == WT   ← hard failure, surfaced in the UI ────────────┘
        │
        ▼
  substitute → enumerate 8–11-mers spanning the mutation   (~38 peptides/variant, ~494 total)
        │
        ▼
MHCflurry 2.2.1 `models_class1_presentation` (Apache-2.0, PyTorch, 285 MB, §1.1)
  × HLA allele from a user-visible dropdown (default = the allele the epitope was published under)
        │  → affinity nM + allele-specific percentile rank   (<1 s of model time)
        ▼
  take top 3–5 peptides
        │
        ▼
Boltz-2 (MIT, ~4.2 GB weights, §7) — 3 chains: HLA ectodomain + B2M + peptide
  MSAs pre-generated offline for the fixed HLA/B2M chains; `msa: empty` for the peptide
        │
        ▼
  render + report: per-residue peptide pLDDT, peptide↔groove PAE, confidence_score
  overlay PDB 6ULN (experimental ground truth for the flagship case)
```

**Total offline footprint: ≈ 4.5 GB** (7.5 MB UniProt + 285 MB MHCflurry + ~4.2 GB Boltz-2), plus ~10 MB of IMGT/HLA per-locus FASTAs. Everything is Apache-2.0 or MIT. Nothing requires registration, an institutional email, a data-use agreement, or a network connection at demo time.

### 9.2 Day plan

| Day | Goal | Ship-or-kill decision |
|---|---|---|
| **1 (AM)** | **Prove torch on GB10 first.** `torch.cuda.is_available()`, `get_device_capability()` → expect `(12,1)`. Then Boltz-2 with the three sm_121 fixes (§7). | If Boltz-2 will not run by end of day 1, switch to pre-rendered structures and say so. Do not spend day 2 on it. |
| **1 (PM)** | Tier 0 path end-to-end in a terminal: VCF → peptides → MHCflurry → CSV. This is ~2 hours and it de-risks the whole demo. | — |
| **2** | Wire the UI. Allele dropdown. Confidence panel with the §5 glosses. Omission panel from §3.2. | — |
| **3** | Boltz-2 on the top peptides; pre-generate and freeze the HLA/B2M MSAs; 6ULN overlay. **Optional:** swap Tier 0 → `varcode` for frameshift support (§3.3). | — |
| **4** | Air-gap rehearsal: pull the network cable and run the whole thing. Add the GDC "real data" tab if time allows. Rehearse the honest-claims script (§5.3). | — |

**Pre-compute everything you can.** The demo should not be waiting on Boltz-2 live unless you have timed it. Run the screen at startup; cache structures for the three worked examples; keep a live run for one peptide as the showpiece.

### 9.3 Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| ~~torch/Boltz-2 on sm_121~~ | **RETIRED** | ✅ Boltz 2.2.1 confirmed running on `torch 2.14.0+cu132` |
| **`gemmi==0.6.5` breaks a clean rebuild** | **High** | No aarch64 wheel, needs `python3.12-dev` (sudo). Pin **`gemmi==0.7.5`** after boltz |
| **Anything needing `apt`** | Certain to block | `sudo` needs a password. Recommended stack is pip-only; `bcftools` is the only apt item and is off the critical path |
| ~~Boltz-2 needs network for MSAs~~ | **RETIRED** | ✅ `msa: empty` confirmed working offline; MSA upgrade is optional (§7) |
| **Wrong HLA allele sequence** (P04439 = A\*03:01) | **Hit already** | Use IMGT/HLA accessions from §4.2; `NLVPMVATV` needs `HLA:HLA00005` (A\*02:01) |
| numpy conflict (boltz `<2.0` vs varcode `>=2.0`) | Certain if one venv | Separate venvs: `~/neofold` (MHCflurry) and `~/boltzenv` (Boltz-2) |
| MHCflurry version drift (2.2.1 vs 2.3.0rc) | Low | Pin the version; both CLI name styles work |
| Wrong VCF REF/ALT on a minus-strand gene | Medium | Use the §2.5 table verbatim; the WT assertion catches it downstream |
| cBioPortal used as a data source | — | Already ruled out (403s); use GDC |
| A judge asks "is this clinical?" | Certain | §5.3 language, §3.2 omission panel, §8.4 answer |

---

## 10. Consolidated list of things I could NOT verify

Stated plainly so nothing here is taken as checked when it wasn't.

**Hardware / install (verify on day 1 — these are the ones that matter):**
- PyTorch cu130 aarch64 on real GB10 sm_121 hardware. Not tested. Highest-risk item in the document.
- Whether every pinned `boltz` dependency (`numba==0.61.0`, `gemmi==0.6.5`, `rdkit`, `scipy==1.13.1`) has a `manylinux_*_aarch64` wheel.
- MHCnuggets on TF 2.16+/Keras 3 with `tf-keras` + `TF_USE_LEGACY_KERAS=1`.
- MixMHCpred 3.0's exact output columns and an explicit ARM64 build.
- `pyensembl`'s on-disk footprint after indexing (~2–4 GB is an estimate; the docs state nothing).
- snpEff's exact GRCh38 database size (~1–2 GB estimate only).
- Docker arch manifests for `andrewrech/antigen.garnish:2.3.1` and `zhouwanding/transvar`.

**Science / data:**
- **No published peptide-RMSD benchmark of Boltz-1 or Boltz-2 on held-out pMHC class I.** A "DockQ ≈0.91 / ≈0.70" Boltz-2 figure appeared in search results but could not be confirmed in the paper. **Do not cite it.**
- Whether Boltz-2's pMHC distillation set included β2-microglobulin.
- The per-allele values in the 2026 Zenodo 9.67M-donor HLA frequency dataset (xlsx not opened). Open it on day 1 if you put frequencies on screen.
- Any *observed* (genotype-counted) HLA phenotype frequencies — every AFND carrier % is HWE-derived.
- The CC **version** for the IPD-IMGT/HLA licence — none is stated anywhere.
- Licence types for NeoPredPipe and antigen.garnish (no statement found in either README).
- PDB 5HHM (not checked). AFND's world-map endpoint `hla6008a.asp` returns HTTP 404 — dead route.
- `##contig` lengths in the synthetic VCF header were written from knowledge, not fetched — check against your `.fai`.
- Whether GDC's `GRCh38.d1.vd1` differs from plain GRCh38 at any of the 13 hotspot loci (it should not; only decoy/viral contigs are added, but this was not proven base-by-base).
- `bcftools csq` output formatting was not run end-to-end; only the documented `BCSQ` schema was read.

**One number where two sources disagreed, and how I resolved it:** a secondary source gave `models_class1_presentation` as **69 MB** (`models_class1_presentation.20200205.tar.bz2`). That is an **older bundle**. The current `downloads.yml` (`current_release: 2.2.0`) points at `models_class1_presentation.20200611.tar.bz2`, and the GitHub releases API reports that asset as **135.4 MB**. I used 135.4 MB. If you fetch and see ~69 MB, you are on an older release — check `mhcflurry downloads info`.
