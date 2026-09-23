# Multi-seed ensemble spread & the tumour-vs-normal panel

**Research date:** 2026-09-23 · **Demo date:** 2026-09-26 · **Audience:** the engineer implementing this in 2 days.

**Ground-truth inputs (measured by us, treated as fact throughout):**

| Fact | Value |
|---|---|
| Boltz-2 wall clock, 383-residue pMHC-I, `--recycling_steps 3 --diffusion_samples 1 --sampling_steps 200` | **58 s** on one HP ZGX Nano GPU |
| Peptide backbone RMSD vs PDB 6ULN, single-sequence | **0.56 Å** |
| Peptide backbone RMSD vs PDB 6ULN, with MSA | **0.486 Å** |
| Negative control: NLVPMVATV on HLA-A\*02:01 (correct) | ipTM **0.987** |
| Negative control: NLVPMVATV on HLA-A\*03:01 (wrong allele) | ipTM **0.988** ← *higher* |
| MHCflurry 2.2.0, KRAS G12D on HLA-C\*08:02 | both published epitopes ranked **#1 and #2 of 38** |
| MHCflurry 2.2.0, mutant vs wild-type affinity | **74 nM vs 3656 nM = 49×** |

---

## 0. TL;DR — the four decisions

1. **Do not build a multi-seed ensemble as a confidence signal.** Verified from the Boltz source: `--seed` and `--diffusion_samples` vary *the same single random quantity* — the diffusion noise. `--seed` is strictly the more expensive way to get the same draws. And a 2026 preprint states outright that in Boltz-2 "increasing the number of diffusion samples does not produce conformational diversity," because "the trunk and pair representations are deterministic functions of the input MSA." Ensemble spread is a **reproducibility** measurement, not an uncertainty measurement. Build it as a **25-minute pre-registered negative result** (§1.4) instead of as a product feature — that is worth far more on stage.

2. **The tumour-vs-normal 3D panel is salvageable, and better than you think** — but not for the reason in the original pitch. For KRAS G12D on HLA-C\*08:02 there is a *specific, crystallographically observed, prespecified* contact: the mutant p3 Asp forms a **salt bridge with Arg156** of HLA-C\*08:02 (PDB 6ULN, 2.01 Å). Wild-type KRAS has **Gly** at p3 — no side chain, so the contact is **impossible by chemistry, not by prediction**. That is a legitimate structural claim you can measure as one distance. See §2.3.

3. **Skip NetMHCstabpan — but `TLStab` is a real stretch goal.** NetMHCstabpan has no aarch64 binary, needs a second x86-only DTU package, won't ship to a gmail address, and is trade-secret/non-redistributable — which would undercut your own MIT-licence argument. But **TLStab** (Kavraki Lab, *Immunoinformatics* 2024) predicts half-life directly, is CPU PyTorch, ships weights in the git repo, and installs on ARM64 in under an hour. It adds a genuinely orthogonal axis — MHCflurry's presentation score is affinity + processing, **not** stability. Rank it below items 1 and 2. §3.

4. **Funnel: 1,000 → 38,000 → ~760 → ~50 → 5 → 1**, with **exactly one Boltz fold run live** (58 s) and four precomputed. Arithmetic in §4.

**The single biggest scientific-honesty trap in these two additions:** presenting ensemble spread as if it were uncertainty about *whether the peptide binds*. It is not. It is uncertainty about *where the atoms land given that the model has already decided the peptide is in the groove*. Those are different questions, and your own negative control proves the model gets the first one wrong while being tight on the second.

---

## 1. Does multi-seed ensemble spread measure anything useful?

### 1.1 What `--seed` and `--diffusion_samples` actually vary — verified from source

I read the Boltz source rather than the docs, because the docs do not document `--seed` at all.

**`--seed`** exists and is plumbed as:

```python
# src/boltz/main.py:919
@click.option("--seed", type=int,
    help="Seed to use for random number generator. Default is None (no seeding).",
    default=None)
# src/boltz/main.py:1101
if seed is not None:
    seed_everything(seed)
```
<https://github.com/jwohlwend/boltz/blob/main/src/boltz/main.py>

`seed_everything` is PyTorch Lightning's global RNG setter (torch, numpy, python `random`).

**`--diffusion_samples N`** is passed through to the model's `forward` and becomes `multiplicity` in the structure module:

```python
# src/boltz/model/models/boltz2.py — forward()
structure_module.sample(
    s_trunk=s.float(),
    s_inputs=s_inputs.float(),
    ...
    multiplicity=diffusion_samples,
)
```

and inside the diffusion module the trunk representations are simply **broadcast**:

```python
# src/boltz/model/modules/diffusionv2.py:129-136
s_trunk.repeat_interleave(multiplicity, 0),
s_inputs.repeat_interleave(multiplicity, 0),
...
# :345  — the ONLY source of between-sample difference
atom_coords = init_sigma * torch.randn(shape, device=self.device)
# :377
eps = sqrt(noise_var) * torch.randn(shape, device=self.device)
```

**Three consequences, and they are load-bearing:**

| | |
|---|---|
| **(a) All N diffusion samples share one identical trunk.** | The MSA module, the Pairformer and all recycling run **once**. `s_trunk` and `z_trunk` are `repeat_interleave`d, not recomputed. Every sample is conditioned on the *same* learned belief about the complex. |
| **(b) The featurizer RNG is hard-coded to 42, so `--seed` does not change it.** | `src/boltz/data/module/inferencev2.py:271-273` reads literally `seed = 42; random = np.random.default_rng(seed)`. That generator is what drives MSA subsampling, conformer choice and template selection. **`--seed` cannot reach it.** So changing `--seed` does *not* change the input features, and therefore does not change the trunk. |
| **(c) Therefore `--seed S` ≡ `--diffusion_samples`, at N× the cost.** | Both vary exactly one thing: the torch global RNG feeding `torch.randn` in the diffusion trajectory. `--diffusion_samples 5` costs one trunk + 5 diffusion trajectories. Five `--seed` runs cost **five trunks + five diffusion trajectories** for statistically identical draws. Multi-seed is **strictly dominated**. |

> ⚠️ **This is where the AlphaFold intuition breaks.** In ColabFold/AF2, multi-seed genuinely works, because `num_seeds` is normally combined with **MSA subsampling and inference-time dropout** — both of which perturb the *trunk*. See the EBI course material: enabling dropout "means dropout layers in the model remain active during predictions, further increasing variability" (<https://www.ebi.ac.uk/training/online/courses/alphafold/advanced-modeling-and-applications-of-predicted-protein-structures/customising-alphafold-structure-predictions/>). **Boltz-2 at inference has neither.** Do not carry the AF2 multi-seed folklore across. If you cite AF2 multi-seed papers (AFsample2, SPEACH_AF) to justify your Boltz ensemble, a judge who knows the codebase will take you apart.

**The one lever that *does* increase diversity** is `--step_scale` (Boltz-2 default **1.5**), documented as: *"The step size is related to the temperature at which the diffusion process samples the distribution. The lower the higher the diversity among samples."* (<https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md>). Lowering it to ~1.0 will widen the ensemble — but that is **turning up the sampling temperature**, not discovering uncertainty. Widening a distribution by fiat tells you nothing about the model's belief. Do not use `--step_scale` to manufacture a spread signal.

### 1.2 Is diffusion-sample spread a meaningful uncertainty estimate?

**Short answer: weakly informative at best, and the specific published finding for Boltz-2 is that it is near-zero.**

The directly on-point source is a 2026 bioRxiv preprint, *Steering Conformational Sampling in Boltz-2 via Pair Representation Scaling* (<https://www.biorxiv.org/content/10.64898/2026.01.23.701250v1.full.pdf>). Its entire premise is that Boltz-2 mode-collapses:

> "increasing the number of diffusion samples does not produce conformational diversity"

> "the trunk and pair representations are deterministic functions of the input MSA"

Their fix is to perturb the **pair representation** — i.e. they had to reach *into the trunk* because sampling the diffusion could not get them diversity. That is a published, independent confirmation of the architectural reading in §1.1.

> ⚠️ **Uncertainty flag:** this is a preprint (Jan 2026), not peer-reviewed, and I extracted those quotes via automated PDF read. **Verify both sentences against the PDF before putting them on a slide.** The architectural claim, however, is independently verified by me from the source code above, which is the stronger evidence anyway.

The same picture holds for AF2 generally — *Assessing AF2's ability to predict structural ensembles of proteins*, **Structure** 2024 (<https://www.cell.com/structure/fulltext/S0969-2126(24)00370-8>): AlphaFold ensembles "typically represent a single conformational state with minimal structural heterogeneity," which is why a whole cottage industry of pipelines (AFsample2 <https://www.nature.com/articles/s42003-025-07791-9>, SPEACH_AF <https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1010483>) exists to force diversity.

**On calibration of the confidence heads themselves:** Mikhaylov & Levine, *Accurate modeling of peptide-MHC structures with AlphaFold* (bioRxiv 2023.03.06.531396, <https://www.biorxiv.org/content/10.1101/2023.03.06.531396v1.full>) report for class I a **Spearman correlation of only 0.55 (discovery) / 0.42 (test) between pLDDT and Cα-peptide RMSD**. So even the *first* moment of the confidence signal is a weak-to-moderate predictor of *geometric* accuracy. A second moment (a standard deviation) estimated from N=5 of that same weak signal is not a foundation to build a claim on.

Useful calibration context for the same paper: their class I median Cα-peptide RMSD was **0.77 Å** (all-atom 1.77 Å). **Your measured 0.56 Å / 0.486 Å is better than the published median** — that is a real, citable, defensible claim and you should make it.

### 1.3 Would ensemble spread have caught the A\*02:01 / A\*03:01 error?

**Decisive answer: almost certainly not — and here is the mechanism, stated so you can defend it.**

Reason it through in three steps:

1. **The two runs have different inputs** (different HLA α-chain sequence), so they *do* have different trunks. So this is not trivially ruled out — the question is fair.
2. **But the failure is a trunk failure, and the spread does not sample the trunk.** Your ipTM of 0.988 on the wrong allele is the *confidence head*, which reads the trunk, asserting that the interface is well-defined. The diffusion samples are all drawn conditioned on that same confident trunk. Asking the samples to disagree is asking the denoiser to contradict the belief it was handed.
3. **Empirically, Boltz-2 mode-collapses** (§1.2). If N samples land on one mode regardless, the spread is ≈0 in *both* arms and carries no signal at all.

There is a real counter-argument, and you should be able to state it: the model has **no PDB precedent** for NLVPMVATV in an A\*03:01 groove, so it is extrapolating, and the learned score function may be flatter there, which *would* show up as spread. This is a genuine open question. **I cannot resolve it from the literature. You can resolve it in 25 minutes.**

**Root cause of the whole problem, and the sentence to say on stage:** Boltz-2's structure module is trained on the PDB — a database of complexes that *did* assemble. It has never been shown a peptide-MHC pair that fails to form. It has no representational capacity for "this does not bind"; its only output vocabulary is "here is the complex." This is not a Boltz bug, it is a property of the entire co-folding model class:

Motmaen et al., **PNAS** 120 (2023), PMID 36802421. Verbatim from the preprint (<https://www.biorxiv.org/content/10.1101/2022.07.12.499365v1.full>):

> "AlphaFold tended to dock non-binding peptides in the MHC peptide-binding groove"

> "both the PAE, calculated between MHC and peptide, and the per-residue accuracy estimate pLDDT, provided **some** discrimination of binders from non-binders"

Their fine-tuned model reached **AUROC 0.97 (class I), 0.96 (class II)**.

That paper is your single most valuable citation in this project. **Your negative control independently reproduced a published finding, on different hardware, with a different model.** Frame it that way. And note their conclusion: they bolted a *trained classifier* onto the PAE, i.e. they decided raw confidence could not be rescued and a **separate discriminative model** was required. That is exactly your architecture, with MHCflurry playing the classifier's role. **You arrived at the published answer independently.** That is a genuinely good thing to be able to say.

> 🚨 **Honesty correction — read this before you write the slide.** The paper says confidence gives **"some discrimination"**, not *none*. So the strictly correct claim is that ipTM/PAE are **weak and unreliable** discriminators, not that they carry zero signal. And **your negative control is n=1.** A sharp judge will say: *"You tested one pair. One inverted pair doesn't prove the metric is useless."* They are right, and you need the answer ready:
>
> *"Agreed — one pair isn't a benchmark. What it is, is an existence proof that the ordering can invert, which is enough to disqualify ipTM as a decision rule. The published result is that this signal is weak — 'some discrimination', considerably worse than NetMHCpan. We then raised it to four pairs with a 2×2 allele swap; here's that result."*
>
> **Do not say "Boltz confidence is meaningless" or "ipTM has zero discriminative power."** Say "weak, unreliable, and not something we're willing to make a clinical-adjacent decision on." The overclaim is both false and unnecessary — the true version is already damning enough.

> ⚠️ **Uncertainty flag:** the three quotes above are verbatim from the **2022 bioRxiv preprint**. PNAS and PMC both blocked automated fetching, so I could not diff the preprint against the published version. Cite the PNAS DOI but **verify these sentences survived into the published text** via <https://www.ipd.uw.edu/publication-pdfs/280/3955569e5b33623b7e651e7430aa61a3/motmaen-et-al-2023-peptide-binding-specificity-prediction-using-fine-tuned-protein-structure-prediction-networks.pdf>. Separately, the widely-quoted per-allele numbers (Pearson r = 0.57 default AF / 0.79 fine-tuned / 0.78 NetMHCpan for 9-mers on HLA-A\*02:01) come from a secondary summary (<https://www.fredhutch.org/en/news/spotlight/2023/05/phs-motmaen-pnas.html>), **not** from text I read directly — do not put those three numbers on a slide unverified.

### 1.4 The experiment that settles it — run this, it is 25 minutes

Do **not** ship the ensemble as a feature. Ship it as a **pre-registered negative result**. Write down the prediction *before* you run it; a judge who sees a pre-registered prediction that came true will trust everything else you say.

**Design: a 2×2 allele swap.** This is much stronger than your current n=1, because it controls for peptide identity and allele identity independently — neither arm can be explained by "that peptide is just weird" or "that allele is just weird."

| Arm | Peptide | Allele | Expected |
|---|---|---|---|
| A | NLVPMVATV (CMV pp65 495–503) | HLA-A\*02:01 | correct |
| B | NLVPMVATV | HLA-A\*03:01 | **wrong** (V at PΩ into a basic F pocket) |
| C | KLGGALQAK (CMV IE-1 184–192) | HLA-A\*03:01 | correct (K at PΩ) |
| D | KLGGALQAK | HLA-A\*02:01 | **wrong** (K at PΩ into a hydrophobic F pocket) |

Both peptides are canonical, tetramer-validated CMV epitopes — KLGGALQAK is sold as an HLA-A\*03:01 IE1 184–192 tetramer (e.g. <https://www.mblintl.com/products/ts-m100-2/>), NLVPMVATV as the HLA-A\*02:01 pp65 tetramer. **Same virus, two alleles, swapped.** That framing is clean enough to put on a slide in one line, and it forecloses "you picked a weird peptide."

Run each with `--diffusion_samples 10 --sampling_steps 200 --recycling_steps 3`, single-sequence, one fixed `--seed 42`.

**Pre-register this decision rule, in writing, before running:**

> Ensemble spread is a usable binder/non-binder signal **only if** mean pairwise peptide backbone RMSD separates the two wrong arms from the two correct arms **with no overlap**, and the gap exceeds **2× the pooled within-arm standard deviation**. Anything less is noise and we will report it as a negative result.

**My prediction, on record: no separation.** All four arms will show mean pairwise peptide RMSD well under ~1.0 Å, and the wrong arms will not be reliably wider.

**Cost:** ≈ 4 arms × (58 s + ~9 extra diffusion trajectories). Because the trunk runs once per invocation, `t(N) ≈ t_trunk + N · t_diff`. Measure `t(1)` and `t(5)` once and solve the two-equation system for `t_trunk` and `t_diff` before committing to N=10 — that is a 5-minute calibration that de-risks the whole plan. Budget **20–30 minutes total**; if `t(10)` turns out worse than ~5 min/arm, drop to N=5 and say so.

**Either outcome is a good slide.** If there is no separation, you have a 2×2 controlled experiment showing your own tool's limit and justifying MHCflurry. If there *is* separation — you have a genuinely novel finding and should lead with it.

### 1.5 Metrics: formulas and which to defend

**Superpose on the MHC, never on the peptide.** This is the single most important implementation detail here. Align every sample *j* onto sample *i* using the **Cα atoms of the heavy-chain α1/α2 platform, residues 1–180**, then measure the peptide without further alignment. If you superpose on the peptide you measure only its internal conformational wobble and discard where it sits in the groove — which is the thing you care about.

**(a) Mean pairwise peptide backbone RMSD — the single number. Most defensible.**

For peptide backbone atoms *a* ∈ {N, Cα, C, O}, after MHC superposition of sample *j* onto sample *i*:

```
RMSD_pep(i,j) = sqrt( (1/N_atoms) · Σ_a ‖ x_a^(i) − x_a^(j) ‖² )

S = ( 2 / (N(N−1)) ) · Σ_{i<j} RMSD_pep(i,j)          [Å]
```

Report `S` with N and a bootstrap 95% CI. Defensible because it is a plain geometric measurement with no interpretive layer.

**(b) Per-position RMSF — the one to display. Most informative.**

After MHC superposition onto the ensemble mean, for each peptide position *p*:

```
x̄_p = (1/N) · Σ_i x_p^(i)                              (Cα, or side-chain centroid)

RMSF_p = sqrt( (1/N) · Σ_i ‖ x_p^(i) − x̄_p ‖² )        [Å]
```

This is the best display metric because it **localises**. If the ensemble story were ever going to be real, it would show up as tight P2/PΩ anchors for a binder and loose anchors for a non-binder. Plotting RMSF per position lets the audience see *whether that happened* rather than taking a scalar on faith. It is also the honest way to show a null result — a flat profile in all four arms is visually unambiguous.

**(c) ipTM standard deviation across samples — report, do not lean on.** Least defensible, for two reasons:

- It is the second moment of a first moment that your own negative control just falsified. A standard deviation of a broken signal is not a repaired signal.
- **The estimator is terrible at your N.** The standard error of a sample SD is approximately `σ / sqrt(2(N−1))`, which at N=5 is **≈ 0.35 σ** — a 35% relative error on the quantity itself. You cannot distinguish σ=0.004 from σ=0.008 with five samples. If you quote σ_ipTM, quote N and the CI beside it, or a judge with a statistics background will ask and you will not have an answer.

**Recommended display.** One figure, two stacked rows:

- **Top:** all N peptide backbone traces overlaid in the groove (groove as a pale grey surface, traces as thin semi-transparent tubes). Visually this is an "ensemble ribbon" — if it collapses to one line, the audience sees the collapse immediately, which *is* the finding.
- **Bottom:** an RMSF bar strip, positions 1–9 on the x-axis, Å on the y-axis, with **P2 and PΩ shaded**.
- **One number printed:** `S = 0.__ Å (N=10)`.

**Label it "sampling spread", never "confidence" or "uncertainty".** Caption to use verbatim:

> **Sampling spread across 10 diffusion samples.** All samples share one identical trunk representation, so this measures how reproducibly the model places the peptide — not whether the peptide binds.

---

## 2. The tumour-vs-normal comparison, designed to survive a hostile judge

### 2.1 The trap, stated plainly

Your negative control guarantees that Boltz will return a confident, plausible, well-packed structure for the **wild-type** peptide too. A panel captioned "mutant binds, wild-type doesn't — look at the structures" is **false**, and it is the easiest thing in your whole demo for a knowledgeable judge to break. They will break it in one sentence: *"What was the ipTM on the wild-type?"* If your answer is "also 0.98" and your slide implied otherwise, the entire pitch loses credibility retroactively — including the parts that are true.

### 2.2 The fix: three sources, three distinct jobs, never conflated

| Source | Job in the panel | What it may claim |
|---|---|---|
| **MHCflurry 2.2.0** | **Evidence.** All quantitative claims about binding. | 74 nM vs 3656 nM (49×); percentile ranks; WT is a non-binder |
| **Boltz-2 structure** | **Location and mechanism.** Where in the groove, which pocket, which contact. | The predicted pose reproduces the crystal contact; the anchor sits in the D pocket |
| **Published crystallography + pocket chemistry** | **Explanation.** Why the numbers are what they are. | HLA-C\*08:02 prefers Asp at p3; the p3 Asp–Arg156 salt bridge exists |

**Say this out loud on stage.** "The structure tells you *where*. The binding predictor tells you *whether*. We keep those separate on purpose, and here's the experiment that shows why." That sentence pre-empts the attack and converts your weakness into evidence of competence.

**The strongest single move available to you: put the ipTM equality *on the slide*.** Display `Boltz ipTM — WT 0.98 / MUT 0.98 — identical` in the panel, with the label "the structure model cannot tell these apart." A judge who arrived intending to attack you on exactly this now finds you already said it, with numbers. This is the highest-leverage 20 characters in the entire deck.

### 2.3 The one structural measurement that *is* legitimate

**You got lucky with your system, and you should exploit it.** KRAS G12D on HLA-C\*08:02 is not an arbitrary neoantigen — it is one of the best-characterised neoantigens in existence, and the mechanism is published at 2.01 Å.

**The chain of evidence:**

1. **HLA-C\*08:02 has a strong Asp anchor at p3.** Rasmussen et al., *J Immunol* 193(10):4790–4802 (2014), doi:10.4049/jimmunol.1401689 (<https://pmc.ncbi.nlm.nih.gov/articles/PMC4226424/>): *"HLA-C\*04:01, -C\*05:01, and -C\*08:02 share a strong preference for Asp"*, with P2 only an auxiliary Ala/Ser preference (*"HLA-C\*05:01 and HLA-C\*08:02 show auxiliary preference for Ala and Ser in position 2"*) and a shared *"Tyr9, Ala24, Tyr99 motif"*. ⚠️ The Asp quote as extracted does not itself name the position — the surrounding text and a secondary summary place it at **p3** ("the strong Asp anchor residue in P3"). **Open the paper's motif figure and confirm p3 before you put it on a slide.** Everything downstream depends on this one position, and it is a 5-minute check.

2. **KRAS G12D puts Asp exactly at peptide position 3.** KRAS residues 10–18 = G-A-**G**-G-V-G-K-S-A; with G12D this becomes **GADGVGKSA** — the mutated residue is the third. (Same for the 10-mer GADGVGKSAL, residues 10–19. The other published epitope VVGADGVGKS, residues 8–17, puts it at p5 instead — see the warning below.)

3. **The crystal structure shows the contact.** PDB **6ULN** (2.01 Å; HLA-C\*08:02 / β2m / GADGVGKSA / TCR α+β; chains 274 + 99 + 9 + 206 + 243), from Sim et al., *PNAS* 117:12826–12835 (2020), doi:10.1073/pnas.1921964117 (<https://www.rcsb.org/structure/6ULN>). The reported mechanism: the G12D neoantigens *form a salt bridge between the mutant p3 Asp and HLA-C Arg156 on the α2 helix of HLA-C\*08:02*.

4. **Arg156 is a D-pocket residue**, i.e. exactly the pocket a p3 side chain occupies. histo.fyi's pocket assignment for 6ULN lists pocket D as **Arg156, Tyr159, Leu160, Tyr99** (<https://www.histo.fyi/structures/view/6uln>). The pocket chemistry, the elution motif and the crystal contact all agree.

5. **Wild-type KRAS has Gly at p3.** Glycine has no side chain. The salt bridge is not "weaker" in the wild type — it is **geometrically impossible**. This asymmetry comes from chemistry, not from a model, and it cannot be faked or argued away.

**So the one number you may measure from the predicted structure:**

```
d_saltbridge = min over { Asp(p3) OD1, OD2 } × { Arg156 NH1, NH2, NE }  of  ‖ · ‖     [Å]
```

Conventional salt-bridge cutoff: **≤ 4.0 Å** between the charged groups (Barlow & Thornton, *J Mol Biol* 168:867 (1983)). Report your predicted `d` next to the 6ULN crystal value.

**Why this specific measurement is defensible when the others are not:** you are asking a **validation** question — *does the prediction reproduce a contact that was independently observed in a crystal structure?* — not an **inference** question — *does the structure tell me this binds?* The contact was specified in advance by the literature. You are not fishing the structure for a feature that flatters your story.

> ⚠️ **Two warnings you must respect.**
>
> **(i) Say which peptide.** Confirm which peptide your 74 nM / 3656 nM pair refers to. For **GADGVGKSA / GADGVGKSAL** the mutation is at **p3** and the anchor story above is correct. For **VVGADGVGKS** it is at **p5** — a central, TCR-facing position — and the anchor story is **wrong**. Do not let the two get swapped between the slide and the script. Note also that the crystal structure you validated against (6ULN) contains the **9-mer GADGVGKSA**, while Tran et al. (*NEJM* 375:2255, 2016) reported the 10-mer GADGVGKSAL and VVGADGVGKS from TILs.
>
> **(ii) This does not generalise, and you must say so.** This panel works because a crystal structure of this exact complex exists. For an arbitrary patient neoantigen it does not. Label the panel **"validated exemplar"** and, if asked, answer: *"For a novel mutation we would have the affinity numbers and the pocket-motif reasoning, but not the crystallographic confirmation. That is the honest limit of the structural half of this pipeline."*

### 2.4 What NOT to measure — the over-interpretation list

Do not compute, display, or mention any of the following as evidence of binding.

> ⚠️ **How I reached this list:** it is a **deduction** from Motmaen's verified finding, not a set of papers that each individually tested SASA or BSA on predicted pMHC structures. The deduction: *if the model docks non-binding peptides into the groove, then every feature derived from "peptide sits in groove" is contaminated by the model's prior and cannot discriminate.* I consider that sound and I'd defend it on stage — but if a judge asks "is there a paper showing BSA specifically fails?", the honest answer is *"not one I can cite; this follows from the docking behaviour Motmaen documented."*

| Feature | Why it fails here |
|---|---|
| **Anchor SASA / burial depth** | Motmaen: AF-class models "dock non-binding peptides in the MHC peptide-binding groove." A non-binder's *predicted* anchor is buried too. The burial is the model's prior, not the biology. |
| **Buried surface area of the interface** | Same failure, same reason. Both peptides will show a large, similar BSA because both were placed in the groove. |
| **Distance of anchor side chains to B/F pocket floors** (generically) | Same. The exception is §2.3, where the target contact was **prespecified from a crystal structure** rather than discovered post hoc. |
| **Groove occupancy / peptide bulge** | Mikhaylov & Levine note *"the challenge lies in modeling the peptide middle"* — the central bulge is the *least* reliably predicted part. Never build a claim on it. |
| **Per-residue pLDDT differences between WT and MUT** | Same confidence head your negative control just caught inverting. Too weak to carry a claim. |

**Also: do not claim structure-based scoring beats sequence-based scoring.** The literature currently says the opposite — Motmaen et al. found raw AlphaFold confidence gave only *"some discrimination"* of binders from non-binders and had to fine-tune a classifier to approach NetMHCpan. Your pipeline does not beat MHCflurry at ranking; it *uses* MHCflurry at ranking and adds structure for mechanism and for a visual a clinician can read. That is a defensible architecture. Claiming more is the fastest way to lose the room.

### 2.5 Panel layout and literal caption text

**Layout — one slide, three regions.**

```
┌──────────────────────────┬──────────────────────────┐
│  NORMAL (wild-type)      │  TUMOUR (KRAS G12D)      │
│  GA G GVGKSA             │  GA D GVGKSA             │
│  HLA-C*08:02 groove      │  HLA-C*08:02 groove      │
│  p3 Gly — no side chain  │  p3 Asp — sticks, red    │
│  Arg156 shown, grey      │  Arg156 shown, blue      │
│                          │  dashed line + "X.X Å"   │
├──────────────────────────┴──────────────────────────┤
│  EVIDENCE  (MHCflurry 2.2.0 — this is the data)     │
│                                                      │
│  Affinity    3656 nM  ▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏▏  74 nM       │
│                        (log scale, 500 nM line)      │
│  %ile rank   __.__               __.__               │
│                          49× stronger                │
│                                                      │
│  Boltz ipTM     0.98   ═══ identical ═══   0.98      │
│  "the structure model cannot tell these apart"       │
└──────────────────────────────────────────────────────┘
```

Both structures in the **same orientation**, same groove rendering, same zoom. The only visual difference should be the p3 side chain and the dashed salt-bridge line. Any additional visual asymmetry is you putting a thumb on the scale.

**Caption — use this text verbatim:**

> **Same groove, one atom of difference.** KRAS G12D places an aspartate at peptide position 3. HLA-C\*08:02 has a strong Asp preference at p3 (Rasmussen et al., *J Immunol* 2014), and the 2.01 Å structure of this exact complex shows the mutant p3 Asp forming a salt bridge to Arg156 in the D pocket (PDB 6ULN; Sim et al., *PNAS* 2020). Wild-type KRAS has glycine there — no side chain, so that contact cannot form.
>
> **The structures are not the evidence.** Boltz-2 returns a confident pose for both peptides — ipTM 0.98 either way — because it is trained only on complexes that were solved, and has never been shown one that fails to assemble. The binding evidence is MHCflurry's: **74 nM for the mutant, 3656 nM for the wild type, a 49-fold difference.** The structure shows you *where* and *why*; the predictor tells you *whether*.

**Spoken line to go with it (~15 s):** *"One atom. Glycine to aspartate. The groove wants an aspartate right there, and the crystal structure shows the salt bridge it makes. Our structure model is happy to fold both of these — it'll give you 0.98 confidence on a peptide that doesn't bind, and we tested that. So the binding call comes from MHCflurry: 74 nanomolar versus 3656. The structure is the explanation, not the evidence."*

---

## 3. Peptide-MHC *stability* predictors

**Verdict: NetMHCstabpan is out. But there is a real, citable, peer-reviewed alternative that installs in under an hour on ARM64 — `TLStab`. Treat it as a stretch goal ranked *below* §1.4 and §2.5.**

### 3.1 NetMHCstabpan — obtainable, but not runnable on your box

Rasmussen et al., *"Pan-specific prediction of peptide-MHC-I complex stability; a correlate of T cell immunogenicity"*, **J Immunol** 197(4):1517 (2016). Service: <https://services.healthtech.dtu.dk/services/NetMHCstabpan-1.0/>. Version 1.0, unchanged since 2015. Outputs half-life in hours plus a %-Rank against 200,000 random natural peptides, for 8–14mers.

**Licence — exact wording**, from the DTU academic licence form:

- *"If you are not a member of a publicly funded Academic and/or Education and/or Research Institution you must obtain a commercial license"*
- *"Any use of the software which results in any form of commercialization is not allowed under this license."*
- Redistribution explicitly banned: *"not give the program to third parties or grant licenses on software, which include the Software, alone or integrated into other software, to third parties"*
- Single-site: *"The License is only granted for personal and internal use in research only at one Site"*
- *"The software code shall be treated as trade secrets and confidential information."*

**Four blockers, each independently sufficient:**

1. **No aarch64 build exists.** DTU ships exactly three: `1.0cstatic`/Linux, `1.0b`/Linux, `1.0a`/Darwin — all x86. The tcsh wrapper resolves its binary directory as `` `uname -s`_`uname -m` ``, which on the GB10 evaluates to `Linux_aarch64`, and the package contains only `Linux_x86_64/`. It prints *"no binaries found for Linux_aarch64"* and exits. **This is not a guess — it is the wrapper's control flow.**
2. **It needs a second DTU package.** The readme: *"NetMHCstabpan 1.0 depends on the **NetMHCpan-2.8** sofware for combined predictions."* NetMHCpan 2.8a is also x86-only. Second licence request, second download, plus a separate ~42 MB `data.tar.gz`.
3. **Your email will be rejected.** The download form states the software *"will not ship to private or commercial addresses e.g. hotmail.com, gmail.com etc."* — it requires an institutional address. (Turnaround itself is instant and automated, so my earlier assumption about human review was wrong; the blocker is the *address*, not the wait.)
4. **The emulation path costs you the licensing argument.** Even if you got `1.0cstatic` running under `qemu-x86_64-static`, bolting an academic-only, non-redistributable, trade-secret-encumbered binary into a pipeline whose pitch is *"Boltz is MIT — code and weights, academic and commercial"* **actively undercuts your own strongest slide.** A judge who noticed would be right to.

> **Also note:** pVACtools' `--netmhc-stab` flag calls the **DTU web server**, not a local binary. It is useless on an offline box. Do not let that flag's existence mislead you into thinking the capability is local.

### 3.2 Recommended: `TLStab`, from TL-MHC

Fasoulis, Rigo, Antunes, Paliouras & Kavraki, *"Transfer learning improves pMHC kinetic stability and immunogenicity predictions"*, **Immunoinformatics** 13:100030 (2024), doi:10.1016/j.immuno.2023.100030, PMC10994007 — <https://www.sciencedirect.com/science/article/pii/S2667119023000101>. Code: <https://github.com/KavrakiLab/TL-MHC>.

| | |
|---|---|
| **Output** | Half-life directly. Output CSV header is literally `peptide,allele,Half-life (h)`. |
| **Runtime** | Pure **CPU PyTorch**, 10-fold ensemble averaged. Deps: torch, numpy, pandas, scikit-learn, biopython. **ARM64-clean.** |
| **Offline** | Weights are committed as **plain git blobs** (`TLStab/models/weights/TLStab_{1..10}.pt`, ~89 MB total, no git-LFS). One `git clone --depth 1` on a networked machine and you are fully offline. |
| **Usage** | `python TLStab.py input.csv --out out.csv`, input CSV with `allele` and `peptide` columns — i.e. the same shape you already feed MHCflurry. |
| **Provenance** | Explicitly built and benchmarked against NetMHCstabpan on the same stability data. It is the *legitimate* citable substitute, not a workaround. |
| **Budget** | Under an hour. |

**Two caveats you must respect:**

> ⚠️ **(i) There is no LICENSE file in the repo** and the GitHub API reports no licence — which legally defaults to **all rights reserved**. Fine for a hackathon demo and research use; cite Fasoulis et al. 2024. Do **not** claim it is open-source, and do not put it in the same sentence as your MIT-licence argument.
>
> ⚠️ **(ii) The repo's own README contradicts its code** on units — `TLStab/README.md` says "half life minutes" while the code and shipped example output say **hours**. The code is right. If you display a half-life number, sanity-check it against a known epitope before it goes on a slide.

### 3.3 What you already have, and why it is not stability

MHCflurry 2.x gives four columns (<https://openvax.github.io/mhcflurry/commandline_tutorial.html>): `mhcflurry_affinity` (*"Predicted nM affinity; lower is stronger"*), `mhcflurry_affinity_percentile`, `mhcflurry_processing_score`, `mhcflurry_presentation_score`. **None of them is stability.** Per O'Donnell et al., *Cell Systems* 11(1):42 (2020):

> "The PS model is a two-input logistic regression model that integrates a BA prediction... with an AP prediction"

— three learned parameters over affinity and antigen processing. So the presentation score is *not* a proxy for half-life, and TLStab genuinely adds an **orthogonal axis** rather than a third correlated column. That is the honest justification for adding it, and it is a good one.

### 3.4 Bonus finding: NetMHCpan 4.2e *does* ship a native ARM64 build

Not needed for this demo, but worth knowing for later: **NetMHCpan 4.2e offers an official `Linux_arm64` package** (<https://services.healthtech.dtu.dk/services/NetMHCpan-4.2/9-Downloads.php>) — so DTU's *affinity/EL* predictor runs natively on the GB10 with no emulation. Same academic-only licence and same institutional-email requirement, and it gives no stability. Mention only if a judge pushes on "why not NetMHCpan?"

### 3.5 Priority call

**Do §1.4 and §2.5 first.** They are what the pitch stands on. If both are done with time to spare on Friday, add TLStab as a fourth column in the evidence panel — it is an hour and it strengthens the honest half of your argument. If you run out of time, the answer in Q12 below is already a strong one.

---

## 4. The funnel — real arithmetic

### 4.1 Where "38" comes from, and why it is the number to lead with

Your MHCflurry run ranked the two published KRAS epitopes **#1 and #2 of 38**. That 38 is not arbitrary — it is the complete set of mutation-containing peptides for one missense SNV across class I lengths:

```
lengths 8, 9, 10, 11  →  8 + 9 + 10 + 11 = 38 registers containing the mutated residue
```

(For a length-L window, exactly L placements of the window contain a given position.) This is the pVACtools-standard length set. **Use 38 as your per-mutation multiplier** — it is exact, derived, and you already validated it.

### 4.2 The funnel

```
  1,000 somatic missense SNVs                                  [patient variant file]
      × 38 mutant peptides per SNV (len 8–11)
  = 38,000 candidate peptides
      × 1 HLA allele (demo)  /  × 6 alleles (A,B,C ×2 — the real-world number)
  = 38,000  /  228,000 peptide–allele predictions
      ↓ MHCflurry: keep percentile rank < 2                    [seconds, CPU]
  ≈   760 peptide–allele hits          ← see the warning below
      ↓ tumour-specificity filter: MUT rank < 2 AND WT rank > 2 AND affinity ratio ≥ 10×
      ↓ collapse to best peptide per mutation
  ≈    50 mutations                    ← ORDER OF MAGNITUDE. Measure on your data.
      ↓ rank by (percentile, WT/MUT ratio, expression if available); take top 5
  =     5 structures                                            [Boltz-2, 58 s each]
      ↓ manual/structural review
  =     1 shortlisted candidate
```

> 🚨 **Boundary — a sharp judge will catch this one.** *"Percentile rank < 2" retains 2% by construction.* It is a percentile. 2% of 38,000 = 760 is arithmetic, not selectivity. **Never present the 38,000 → 760 step as your pipeline being discriminating.** The step that is genuinely selective — and that is genuinely *yours* — is the next one: requiring the **wild-type counterpart to be a non-binder**. That is the differential filter, it is what "personalised" actually means mechanically, and it is exactly the filter your KRAS panel illustrates. **Make that the hero step of the funnel animation, not the rank cut.**
>
> The ~760 → ~50 collapse is an **order-of-magnitude estimate**, not measured. Run it on your actual 1,000-mutation file and quote the real number. If it comes out 23 or 140, say 23 or 140.

### 4.3 Timing, and what runs live

**Boltz stage:**
```
  5 structures × 58 s               = 290 s  =  4 min 50 s   ← longer than the entire demo
  5 structures × 58 s × 5 samples   ≈ 12–15 min               ← if you add diffusion samples
```
**Therefore: exactly one Boltz fold runs live. Four are precomputed.** There is no arithmetic that makes five live folds fit in four minutes, and pretending otherwise on stage is a lie that a stopwatch exposes.

**MHCflurry stage — measure this today.** MHCflurry throughput is not reliably documented (the widely circulated ">7,000 predictions/sec" figure is from **v1.2.0** and could not be verified at source — see `research-scaling-and-pitch.md` §5.3). Do not cite it. Instead:

```
  t_mhcflurry = 38,000 / R          where R = measured peptide-allele predictions/sec
```

Time `mhcflurry-predict` on 38,000 peptides on the Nano's 20 cores. Then:
- **If t < 30 s** → run the full 38,000 live. This is your "real compute on stage" moment and it is nearly free.
- **If t > 30 s** → run a **250-mutation slice** live (9,500 peptides), show the wall clock, and state plainly that the full 1,000 was precomputed with the same command.

### 4.4 Recommended 4-minute choreography

| Time | What | Live? |
|---|---|---|
| 0:00–0:30 | Problem; show the 1,000-mutation patient file | file on disk |
| 0:30–1:00 | **MHCflurry on 38,000 peptides, visible wall clock** | **LIVE** |
| 1:00–1:30 | Funnel collapses on screen; land on 5. **Linger on the WT-must-not-bind step.** | animation |
| 1:30–2:40 | **Launch Boltz on candidate #1, visible 58 s timer.** Fill the wait with §2.5 — the tumour-vs-normal evidence panel does real narrative work while the GPU runs. | **LIVE (58 s)** |
| 2:40–3:20 | Fold lands. Show it. Then the other 4, labelled *"precomputed — same command, same box."* | mixed |
| 3:20–4:00 | **Close on the negative control**: A\*02:01 0.987 vs A\*03:01 0.988, and the §1.4 ensemble null result. | slide |

**Total live GPU: 58 s. Total precompute needed: 4 × 58 s ≈ 4 min, plus the §1.4 arms.**

**Close on the negative control.** Ending a hackathon pitch on *"here is the experiment we ran that shows our own tool's limit, and here is why the architecture accounts for it"* is memorable, nearly unattackable, and separates you from every other team, all of whom will close on a triumph slide.

---

## 5. Judge questions — with honest answers and boundaries

**Q1. "You ran five diffusion samples. Isn't that just the same model five times?"**
Effectively yes, and we say so. All five share one identical trunk representation — we verified that in the Boltz source; the trunk is computed once and `repeat_interleave`d across samples. The only thing that varies is the diffusion noise. We call it *sampling spread*, not uncertainty.
🚫 **Do not claim** the ensemble is an epistemic uncertainty estimate or a Bayesian posterior.

**Q2. "Then why run it at all?"**
To test whether it would have caught our negative control. We pre-registered the prediction that it would not, ran a 2×2 allele swap, and [report result]. It is a negative result and we are reporting it as one.
🚫 **Do not claim** it is a product feature if the answer came back null.

**Q3. "Why not use different random seeds instead of diffusion samples?"**
Because they are the same thing at higher cost. `--seed` sets the global torch RNG; the featurizer RNG that drives MSA subsampling is hard-coded to 42 in `inferencev2.py` and `--seed` cannot reach it. So different seeds re-run the identical deterministic trunk and redraw the same diffusion noise — N× the compute for statistically identical samples.
🚫 **Do not** cite AlphaFold multi-seed papers as support — AF2 multi-seed works because it is paired with MSA subsampling and inference dropout, neither of which Boltz-2 does at inference.

**Q4. "Your ipTM was higher for the wrong allele. Doesn't that invalidate the structure half of your pipeline?"**
It invalidates using structure *confidence* as a binding signal — which is why we don't. It does not invalidate the *geometry*: our peptide backbone RMSD against PDB 6ULN is 0.56 Å single-sequence and 0.486 Å with MSA, against a published class-I median of 0.77 Å. The structure is accurate. It just isn't discriminative. Those are different properties, and Motmaen et al. found the same thing in PNAS in 2023.

**Q5. "You tested one peptide pair. One inverted result doesn't prove the metric is broken."**
Agreed, and we don't claim it's broken — we claim it's weak and unreliable, which is also what the literature says: Motmaen et al. found raw AlphaFold confidence gave only *"some discrimination"* of binders from non-binders, and had to fine-tune a separate classifier onto the PAE to approach NetMHCpan. Our single pair is an existence proof that the ordering can invert, which is enough to disqualify it as a decision rule. We then took it to four pairs with a 2×2 allele swap — same two CMV epitopes, both alleles, each on its correct and its wrong partner.
🚫 **Do not say** "Boltz confidence is meaningless" or "ipTM has zero discriminative power." Neither is true, and the true version is damning enough.

**Q6. "Isn't the wild-type structure in your comparison panel also confident? Aren't you showing me a picture of something that doesn't happen?"**
Yes, and it's on the slide — ipTM 0.98 for both, labelled. The binding evidence is MHCflurry's 49× affinity difference. The structure shows the mechanism: HLA-C\*08:02 prefers aspartate at p3, and the 2.01 Å crystal structure of this complex shows the p3 Asp–Arg156 salt bridge. Wild-type KRAS has glycine there and physically cannot make it.
🚫 **Do not claim** the wild-type structure "looks worse" or that the model "rejected" it.

**Q7. "You measured a salt-bridge distance from a predicted structure. Isn't that circular?"**
It would be if we'd gone looking for a feature that matched our story. We didn't — the contact was specified in advance by a published crystal structure of this exact complex, and we're asking whether our prediction reproduces it. That's validation, not inference. We deliberately do *not* report anchor burial, buried surface area, or groove occupancy, because those are the ones that would be circular: a model that docks every peptide into the groove will show good burial for a non-binder too.

**Q8. "Does this generalise beyond KRAS G12D?"**
The affinity half does. The crystallographic half does not — that panel works because a 2.01 Å structure of this complex exists. For a novel patient mutation we'd have the MHCflurry numbers and the pocket-motif reasoning, but no crystallographic confirmation. We label that panel a validated exemplar for exactly this reason.
🚫 **Do not** present the KRAS panel as typical pipeline output.

**Q9. "If MHCflurry does the discriminating, what is the structure prediction actually for?"**
Three things, none of which is ranking. Mechanism — it shows *why* a peptide binds, at an atomic contact a clinician can look at. Downstream capability — TCR modelling and structure-based design need a structure and a sequence score cannot provide one. And falsifiability — we can check the predicted pose against a crystal structure, which is how we caught that confidence doesn't discriminate.
🚫 **Do not claim** structure-based scoring outperforms NetMHCpan/MHCflurry for ranking. The published evidence says the opposite.

**Q10. "Your funnel says 38,000 peptides down to 760. That's a 2% cut — but you filtered on 2nd percentile rank. Isn't that just arithmetic?"**
Correct, and that step is arithmetic, not selectivity — a percentile cut retains its percentile by construction. The selective step is the next one: we require the mutant to bind *and* the wild-type counterpart not to. That differential filter is what makes this personalised rather than a lookup, and it's what the tumour-vs-normal panel illustrates.

**Q11. "How much of this demo actually ran on stage?"**
The MHCflurry screen over [38,000 / 9,500] peptides, and one Boltz fold in 58 seconds — both live, both timed in front of you. Four folds were precomputed, with the same command on the same box; five at 58 seconds is 4 minutes 50, which doesn't fit in a 4-minute slot. We'd rather tell you which 58 seconds were real than imply all of it was.

**Q12. "How do you know 58 seconds is representative and not a warm-cache best case?"**
[Answer from your own measurements — state whether the 58 s includes model load, and report n runs and the spread. If you have not measured this, measure it before Saturday; it is a 5-minute job and it is the one number your whole hardware argument rests on.]

**Q13. "You have no stability predictor. Doesn't affinity alone overcall?"**
*If you shipped TLStab:* We do — TLStab from the Kavraki Lab, published in Immunoinformatics in 2024, which predicts half-life directly. We chose it over NetMHCstabpan because NetMHCstabpan ships no ARM64 binary and is trade-secret-licensed and non-redistributable, which doesn't fit an offline ARM box or the open-licensing argument we're making about Boltz.
*If you didn't:* We don't, and it's a real gap. NetMHCstabpan is the standard but it has no aarch64 build and its wrapper hard-fails on this hardware. We were careful not to substitute MHCflurry's presentation score for it — that's a three-parameter regression over affinity and antigen processing, not stability, and conflating them would be exactly the kind of thing we've tried not to do.
🚫 **Do not claim** MHCflurry's presentation score is a stability or half-life measurement.

---

## 6. Sources

**Boltz — primary source code (verified directly, strongest evidence in this document)**
- `src/boltz/main.py` — `--seed` definition (L919), `seed_everything` (L1101), `--diffusion_samples` (L865) — <https://github.com/jwohlwend/boltz/blob/main/src/boltz/main.py>
- `src/boltz/model/modules/diffusionv2.py` — `repeat_interleave` of trunk (L129-136), `torch.randn` noise (L345, L377) — <https://github.com/jwohlwend/boltz/blob/main/src/boltz/model/modules/diffusionv2.py>
- `src/boltz/model/models/boltz2.py` — trunk computed once, `multiplicity=diffusion_samples` — <https://github.com/jwohlwend/boltz/blob/main/src/boltz/model/models/boltz2.py>
- `src/boltz/data/module/inferencev2.py` L271-273 — **featurizer RNG hard-coded to `seed = 42`** — <https://github.com/jwohlwend/boltz/blob/main/src/boltz/data/module/inferencev2.py>
- CLI docs (`--step_scale`, all defaults) — <https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md>

**Boltz-2 papers**
- Boltz-2: Towards Accurate and Efficient Binding Affinity Prediction — <https://www.biorxiv.org/content/10.1101/2025.06.14.659707v1> · *the affinity module is small-molecule/protein only; do not expect it to score peptides*
- Steering Conformational Sampling in Boltz-2 via Pair Representation Scaling (preprint, 2026) — <https://www.biorxiv.org/content/10.64898/2026.01.23.701250v1.full.pdf> · ⚠️ verify quotes

**Confidence does not discriminate binders (the key citation)**
- Motmaen et al., *PNAS* 120 (2023), PMID 36802421 — <https://www.pnas.org/doi/10.1073/pnas.2216697120> · PDF: <https://www.ipd.uw.edu/publication-pdfs/280/3955569e5b33623b7e651e7430aa61a3/motmaen-et-al-2023-peptide-binding-specificity-prediction-using-fine-tuned-protein-structure-prediction-networks.pdf> · ⚠️ **verify quotes before slide use**
- Plain-language summary — <https://www.fredhutch.org/en/news/spotlight/2023/05/phs-motmaen-pnas.html>

**pMHC structure prediction accuracy**
- Mikhaylov & Levine, Accurate modeling of peptide-MHC structures with AlphaFold — <https://www.biorxiv.org/content/10.1101/2023.03.06.531396v1.full> (published *Structure* 2023, <https://www.sciencedirect.com/science/article/pii/S0969212623004136>) · class I median Cα-peptide RMSD 0.77 Å; pLDDT↔RMSD Spearman 0.55/0.42

**Ensemble spread / AF2 conformational diversity**
- Assessing AF2's ability to predict structural ensembles, *Structure* 2024 — <https://www.cell.com/structure/fulltext/S0969-2126(24)00370-8>
- AFsample2 — <https://www.nature.com/articles/s42003-025-07791-9> · SPEACH_AF — <https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1010483>
- EBI: customising AlphaFold predictions (num_seed, dropout, MSA subsampling) — <https://www.ebi.ac.uk/training/online/courses/alphafold/advanced-modeling-and-applications-of-predicted-protein-structures/customising-alphafold-structure-predictions/>

**KRAS G12D / HLA-C\*08:02**
- PDB **6ULN**, 2.01 Å — <https://www.rcsb.org/structure/6ULN>
- Sim et al., *PNAS* 117:12826 (2020), doi:10.1073/pnas.1921964117 — p3 Asp–Arg156 salt bridge — <https://www.pnas.org/doi/10.1073/pnas.1921964117>
- 6ULN pocket assignments and 5 Å contact lists — <https://www.histo.fyi/structures/view/6uln>
- Rasmussen et al., *J Immunol* 193:4790 (2014), doi:10.4049/jimmunol.1401689 — HLA-C\*08:02 p3 Asp preference — <https://pmc.ncbi.nlm.nih.gov/articles/PMC4226424/>
- Tran et al., *NEJM* 375:2255 (2016) — KRAS G12D TIL epitopes GADGVGKSAL, VVGADGVGKS
- Barlow & Thornton, *J Mol Biol* 168:867 (1983) — salt bridge ≤ 4 Å convention

**Binding / stability predictors**
- MHCflurry CLI docs (output columns, offline models) — <https://openvax.github.io/mhcflurry/commandline_tutorial.html> · repo (Apache-2.0, PyTorch) — <https://github.com/openvax/mhcflurry>
- O'Donnell et al., *Cell Systems* 11(1):42 (2020), doi:10.1016/j.cels.2020.06.010 — <https://www.cell.com/cell-systems/fulltext/S2405-4712(20)30239-8>
- **TLStab / TL-MHC** — Fasoulis et al., *Immunoinformatics* 13:100030 (2024), doi:10.1016/j.immuno.2023.100030, PMC10994007 — <https://www.sciencedirect.com/science/article/pii/S2667119023000101> · code <https://github.com/KavrakiLab/TL-MHC>
- NetMHCstabpan 1.0 — <https://services.healthtech.dtu.dk/services/NetMHCstabpan-1.0/> · downloads (3 x86 builds only) <https://services.healthtech.dtu.dk/services/NetMHCstabpan-1.0/9-Downloads.php> · Rasmussen et al., *J Immunol* 197:1517 (2016)
- NetMHCpan 4.2 downloads (**includes `Linux_arm64`**) — <https://services.healthtech.dtu.dk/services/NetMHCpan-4.2/9-Downloads.php>
- Other ARM64-feasible options, for reference: BigMHC (academic, redistribution permitted) <https://github.com/KarchinLab/bigmhc> · MixMHCpred 3.0 (free non-commercial) <https://github.com/GfellerLab/MixMHCpred> · TransPHLA (GPL-3.0) <https://github.com/a96123155/TransPHLA-AOMP> · ⚠️ MHCnuggets depends on TensorFlow/Keras — aarch64 wheels are a known problem on Grace stacks

---

## 7. Uncertainty register

| Claim | Confidence | How to settle it |
|---|---|---|
| `--seed` and `--diffusion_samples` vary only diffusion noise | **High** — read from source | Already verified; re-check against your installed Boltz version |
| Featurizer RNG hard-coded to 42, unreachable by `--seed` | **High** — read from source | `grep -n "seed = 42" $(python -c "import boltz,os;print(os.path.dirname(boltz.__file__))")/data/module/inferencev2.py` |
| Ensemble spread will not separate correct from wrong allele | **Medium-high** — mechanistic + one preprint | **Run §1.4. 25 minutes.** |
| Boltz-2 mode-collapses across diffusion samples | **Medium** — one unreviewed preprint | Falls out of §1.4 for free |
| Motmaen exact quotes and r values | **Medium** — from summaries, PNAS/PMC blocked fetch | Open the UW IPD PDF and verify |
| ~760 → ~50 funnel collapse | **Low** — order of magnitude only | Run your own 1,000-mutation file and quote the real number |
| MHCflurry throughput | **Unknown — do not cite any published figure** | Time it on the Nano today |
| NetMHCstabpan has no aarch64 build; wrapper hard-fails on `Linux_aarch64` | **High** — from the wrapper's own `uname`-based path logic + DTU's 3-build download list | Settled. Licence quotes are verbatim from the DTU form |
| TLStab installs and runs on ARM64 in <1 h | **Medium-high** — pure CPU PyTorch, weights in-repo | `git clone --depth 1` and run one peptide; 15 min to find out |
| TLStab outputs hours, not minutes | **Medium** — code and example output say hours, its README says minutes | Sanity-check one known epitope before displaying a number |
| 58 s is steady-state, not warm-cache | **Unknown** | Measure n≥5 runs; state whether model load is included |
