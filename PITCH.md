# NeoFold Edge — pitch and demo script

**Final:** Saturday 26 September 2026, Student Union Ballroom
**Format:** 3–4 minute live demo + judge questions

---

## The strategic choice

**Open with Rosie.** It is a true story, it is six months old, it takes thirty seconds, and it does three jobs at once: it explains what a neoantigen vaccine *is* without jargon, it proves the demand is real, and it sets up the edge argument — because the one thing in that story you cannot do for a human patient is put the genome in someone else's cloud.

Then: almost every team will show something that *looks* impressive. Very few will be able to say **how often their thing is wrong**. That is our differentiator, and the rest of the pitch should lean on it.

We have three measured numbers nobody can wave away:

| | |
|---|---|
| **AUC 0.78 / 0.76** | on 2,555 peptides with experimental T-cell assay outcomes |
| **1.41 Å** | median structure error on 9 crystals deposited *after* the model's training cutoff |
| **8.8 s → 64 s** | screen 1,890 candidates, then fold one, entirely offline on the Nano |

And four things we got **wrong and fixed** — of twelve we found and wrote down. Say them out loud. A judge who catches you hiding one is fatal; a judge who hears you volunteer them is convinced.

---

## The 4-minute script

### 0:00 — Hook · Rosie (30 s)

*(Screen: the app, already loaded, network badge visible. Say this without slides.)*

> "Last December a dog in Australia named Rosie got an injection her owner designed himself.
>
> Rosie had a tennis-ball-sized tumour on her leg and chemo wasn't shrinking it. Her owner is a **machine learning engineer with no biology background at all.** He paid to have her tumour sequenced, used ChatGPT and AlphaFold to work out which mutations mattered, and — with biologists at a university — built her a personalised cancer vaccine. By March her biggest tumour was down about **75%**.
>
> That's remarkable. It's also completely unrepeatable, because it needed a genomics centre, an RNA institute, months of expert time, and a cloud service you can't legally send a *human* patient's genome to.
>
> **We built the analysis step of that story into one box that never connects to the internet.**"

### 0:30 — Why it must be local (15 s)

> "A genome isn't a file, it's an identity — and it identifies your siblings and your children too. The moment it leaves the hospital it stops being a computation and becomes a regulated disclosure: data use certification, access committee, signing official. **Weeks.**
>
> Running it here doesn't satisfy that process faster. It deletes the step. Everything you're about to see ran with the network dead."

*(Point at the "No external calls (0)" badge.)*

### 0:45 — The funnel, live (40 s)

*(Click **Run triage**. It takes ~9 s — talk through it.)*

> "That's a synthetic tumour variant file — 50 mutations. It expands to 1,890 candidate peptides, and the screen scores every one of them against the patient's HLA type, plus the germline version of each peptide."

*(Results land.)*

> "Thirteen get cut immediately because they're **not neoantigens at all** — they occur verbatim in the normal human proteome. One of them is a KIT mutation our own screen ranked highly. It contains the DFG motif that's conserved across every protein kinase, so it looks like ERK2. A T-cell against it would be autoreactive.
>
> Twenty-two survive as predicted-presented. Each row says why, in English."

### 1:25 — The science moment (60 s)

*(Scroll to the 3D viewer, rotate it.)*

> "The top candidate is KRAS G12D — a real, published epitope. This is the peptide sitting in the patient's HLA molecule, predicted locally in **64 seconds** on the Nano.
>
> Here's the part that's checkable." *(Point at the contact panel.)* "HLA-C\*08:02 has a charged pocket at peptide position 3. The G12D mutation puts an aspartate exactly there. In the crystal structure it forms a 2.7 Å salt bridge to Arg156 — our prediction gets 2.5 Å.
>
> The normal protein has **glycine** there. No side chain. That contact cannot form — not weakly, at all."

*(Switch to the wild-type tab.)*

> "And here's the honest part. The structure model gives the normal peptide **the same confidence score** as the tumour one — 0.987 against 0.991. So we don't rank on confidence. We rank on the binding screen, and we measure one contact that was specified in advance from a crystal structure."

### 2:25 — The evidence (35 s)

*(Click the **Does the screen work?** tab.)*

> "This is the panel I'd want to see from anyone claiming a tool like this.
>
> Two independent benchmarks. 2,555 peptides that were actually tested in a laboratory. 90 of them provoked a real T-cell response.
>
> Our screen reaches **AUC 0.78 and 0.76**, and puts a true responder in the top 25 at **16% and 32%** — about **five times** the base rate on both.
>
> For scale: our *predicted* score matches the *experimentally measured* binding affinity in that dataset. Which tells you the ceiling here is the biology, not the predictor."

*(Point at the red curve dipping below the diagonal, then at the red bar.)*

> "We've left two things on screen that **failed**. That red ROC curve crosses *below* the diagonal — the mutant-versus-normal differential is worse than random. And down here is every triage rule we considered, measured: the one we shipped first scores **0.96×**, inside the shaded region. Worse than chance. It's an annotation now, not a gate."

### 3:00 — The one that lands (20 s)

*(Click the **Is the structure right?** tab.)*

> "One more, because it's the finding I'd want to be asked about. Nine crystal structures deposited **after** the model's training cutoff — held out, nothing memorised. Median error **1.41 Å**.
>
> Now look at the shape of that cloud." *(Point.)* "Every prediction sits inside **0.011** of confidence while the real error spans a **full Ångström**. Correlation minus 0.23. The worst prediction in that set scores *higher* than the best one.
>
> That's why nothing in this pipeline ranks on confidence."

### 3:20 — Scale (20 s)

*(Click the **Throughput** tab.)*

> "One candidate takes 64 seconds. Batched, the Nano does **100 an hour**, because the model loads once instead of per job — that's measured, not projected.
>
> These are independent jobs, so more Nanos is a work queue, not a rewrite. We only had one, so the multi-node bars are labelled projections."

### 3:40 — Close (20 s)

> "We are not claiming to make a vaccine. We assemble a construct for a researcher to review, and we'll tell you that BioNTech **terminated** a randomised trial of exactly this modality last month.
>
> What we're claiming is narrower and testable: a private AI workstation that turns a genome into a small, ranked, **explained** shortlist — and that knows, and tells you, how often it's wrong."

---

## Demo choreography

| When | Action | Fallback if it fails |
|---|---|---|
| Before | Start app at `?run=1`, wait 25 s for warm-up | — |
| Before | `sudo nvidia-smi -lgc 0,2450` on the Nano | — |
| 0:45 | Click **Run triage** | Results are cached — re-click |
| 1:25 | Rotate the 3D structure | It's a static file; cannot fail |
| 1:50 | Switch to wild-type tab | Static file |
| 2:25 | **Does the screen work?** tab | Static JSON |
| 3:00 | **Is the structure right?** tab | Static JSON |
| 3:20 | **Throughput** tab | Static JSON |

The app takes deep links, so a view can be loaded rather than clicked to:
`?run=1` runs triage on load, `?tab=pane-holdout` opens an evidence tab,
`?structure=kras_g12d_9mer_wt_model_0` selects a structure. Worth pre-opening
tabs in a second window as a fallback.

**Do not** run a live Boltz prediction on stage. It takes 64 s of silence and the machine has a power fault. The structures are precomputed; say so if asked — *"this was predicted on this machine this morning, in 64 seconds."*

---

## The four things we got wrong (volunteer these)

*There are twelve in [docs/SCIENCE.md](docs/SCIENCE.md) §3. These are the four to say out loud.*


1. **We shipped a filter that was worse than random.** A 2× mutant-vs-normal threshold, invented rather than cited. Measured at 0.96× enrichment on 1,947 pairs. It's now an annotation, because the differential mostly detects *anchor* mutations — and anchor mutations are the ones T-cells are *least* likely to see.
2. **Our accuracy claim was 3× optimistic.** Both structures we validated against predate the model's training cutoff. On 9 held-out ones it's 1.41 Å, not 0.42 Å.
3. **We labelled a normal human peptide as a tumour target.** Caught by the self-similarity filter we added afterwards.
4. **Our language model asserted three things the evidence didn't support** — including that a confidence score "supports reliability", which we'd already disproved five times. There's now a claim checker, and those three phrases are regression tests.

---

## Judge questions

**"Does this make a vaccine?"**
No. It produces a ranked, explained shortlist for a researcher. We also assemble a construct — amino acids only, never nucleotides — and the honest context is that BioNTech terminated a randomised Phase 2 of this modality in August 2026 on futility, and KEYNOTE-942 was two-sided p = 0.053 with a confidence interval crossing 1.0.

**"Isn't Boltz just AlphaFold?"**
Same family of problem. Boltz-2 is MIT-licensed with open weights, which is why it can run on this box at all — AlphaFold 3's weights are non-commercial and not approved for clinical use.

**"How do you know the HLA type?"**
We don't, and you can't get it from a VCF. We take it as input. Real pipelines type it from sequencing reads; that's out of scope here and we say so.

**"What's your false positive rate?"**
At the top 25 we're right about 16–32% of the time against a base rate of 2.7–6.1%. So most of our top candidates are still wrong — we're five times better than chance, not correct.

**"Why not just use the cloud?"**
Not cost — moving a whole-exome pair costs about five dollars. It's governance: local compute removes a data-use agreement and an institutional certification step rather than merely satisfying one. Also, note that the machine has no internet during this demo.

**"Rosie's owner used the cloud and it worked fine."**
For a dog, yes — and that's the point. Animal genomes aren't controlled-access human data. The moment you run the same workflow on a person, ChatGPT and AlphaFold Server become an external processor holding an identifiable genome, and you need a data use certification, an access committee and a signing official before you upload anything. That's the step we delete.

**"Are you claiming AI cured that dog?"**
No, and neither should anyone else. One dog, not a controlled study, mast cell tumours behave unpredictably, and she got the vaccine alongside a checkpoint inhibitor — so you can't cleanly attribute the response. What the case proves is that the *workflow* is now within reach of someone outside the field. That's what deserves better tooling.

**"Isn't 1.41 Å just memorisation?"**
That number is specifically the held-out figure. Everything deposited after the model's June 2023 training cutoff. Our memorised-set number is 0.42 Å, and we quote the worse one.

**"Your MD says the contact is stable — doesn't that support the salt bridge?"**
No, and we say so in the tool's own output. Generalised-Born implicit solvent over-stabilises salt bridges by 3–4 kcal/mol, and the documented failure is specifically in hydrogens on charged nitrogens — Arg156's guanidinium is exactly the atom type at fault. At 310 K that's a ~130-fold population over-weighting. The contact evidence stands on the crystal comparison and on glycine having no side chain, not on the dynamics.

**"Your three MD replicates agree closely — isn't that reassuring?"**
It's the opposite. Knapp *et al.* 2018 show that sub-10 ns agreement is the signature of undersampling — the run is too short to explore anywhere else — and that 100 ns is the state of the art for this system class. We're 100× below that floor. The MD can reject an implausible pose; it cannot support a stability claim.

**"What aren't you modelling?"**
RNA expression of the tumour — worth 11–13 precision points in published work, and the single most serious omission. Also clonality, peptide-MHC stability, TAP transport. We have the list ranked by measured effect size.

---

## What NOT to say

- ❌ "The normal protein is invisible" — it's a weak binder at 1.055 %rank
- ❌ "Sub-Ångström accuracy" — that's the training-set number
- ❌ "The model is confident, so it's right" — we disproved this five times
- ❌ "49× stronger" without saying it's the 9-mer; the 10-mer is 22.6×
- ❌ Anything with the words *cure*, *treat*, *patient outcome*
