# What we can and cannot claim

*The claims, the evidence, the limits, and every error we found in our own work.*

This document exists because the project's central argument is not "our tool is good" — it is **"we know how wrong our tool is."** A system that reports only its successes has not been tested. So the failures are here, in detail, with the mechanism that caused each one.

---

## 1. The claims, with their evidence

| Claim | Evidence | Strength |
|---|---|---|
| The screen ranks candidates better than chance | AUC **0.777** / **0.759**, two independent benchmarks, 2,555 lab-tested peptides | **strong** |
| A top-25 shortlist is 5–6× enriched | precision **16%** / **32%** against base rates of 2.7% / 6.1% | **strong** |
| Structure prediction is accurate on held-out crystals | **1.41 Å** median peptide backbone RMSD, 9 post-cutoff structures, all < 2 Å | **strong** |
| Structure-model confidence cannot rank candidates | 5 independent demonstrations; **r = −0.23** against measured error | **strong** |
| The mutant/germline differential does not validate | **0.592** and **0.412** — the second below random | **strong** |
| The whole pipeline runs offline on one Nano | egress blocked; 8.8 s + 64 s + 4 s | **strong, demonstrated** |
| Batching gives 100 candidates/hour | **measured**, 5 in one process, 1.79× | **strong** |
| A named atomic contact discriminates mutant from germline | pre-registered from 6ULI/6ULN; predicted 2.5 Å vs crystal 2.7 Å; glycine cannot form it | **moderate** — see §2.3 |
| More Nanos scale linearly | — | **projection only. We had one Nano.** |

---

## 2. The claims we do **not** make

### 2.1 We do not claim to find neoantigens

The field's own numbers forbid it. TESLA: 608 expert-nominated candidates, **37 immunogenic**. Bjerregaard: 1,947 pairs, **53 responders**. At our best measured precision — 32% at k=25 — **two thirds of our top candidates are still wrong.**

What we claim is concentration, not identification. That is a measurable claim and we measured it.

### 2.2 We are a binding-triage tool, not a neoantigen prioritisation pipeline

This distinction matters and we lost an argument about it internally. Production pipelines — pVACtools, NeoPredPipe — are mostly *orchestration around* expression and clonality filters; the binding predictor is one module inside them. **We are that one module, plus a structural evidence layer.** Claiming the category invites a challenge we would lose; claiming the module is defensible and still interesting.

### 2.3 We do not claim the MD run corroborates the salt bridge

This one is worth spelling out, because it is the most technically embarrassing constraint in the project and it is a constraint on our own headline.

Our structural claim is a **p3-Asp ↔ Arg156 salt bridge**. Our MD uses **generalised-Born implicit solvent (OBC2)**. Over-stabilising salt bridges is GB's single best-documented failure mode:

- Geney *et al.* (*JCTC* 2006): *"salt bridges are too stable by as much as 3−4 kcal/mol"* — and their fix reduces the radii of **hydrogens bound to charged nitrogens**, i.e. guanidinium groups. **Arg156 is exactly the atom type at fault.** At 310 K, 3 kcal/mol is a ~130× population over-weighting; 4 kcal/mol is ~660×.
- Roe *et al.* (*JPC B* 2007) independently reproduce 3–4 kcal/mol against explicit TIP3P REMD.
- Zhou & Berne (*PNAS* 2002): spurious salt bridges **inverted** the native/non-native free-energy ranking.

Worse, OpenMM's `GBSAOBC2Force` defaults to **`kappa = 0.0`** — zero ionic strength, infinite Debye length, completely unscreened Coulomb attraction between the Asp carboxylate and the Arg156 guanidinium. At physiological 150 mM the Debye length is 7.85 Å.

So the MD result is in the output with this attached, verbatim from `md.py`:

> *"Generalised-Born implicit solvent over-stabilises salt bridges by 3-4 kcal/mol and defaults to zero ionic strength, so this run must NOT be used to corroborate any specific salt-bridge claim."*

The contact evidence stands on the **pre-registered crystal comparison** (2.5 Å predicted vs 2.7 Å observed) and on the fact that **glycine has no side chain**. The MD is a pose-plausibility check and nothing more.

### 2.4 We do not claim the MD run means anything about stability

Measured pMHC-I half-lives are **10³–10⁵ seconds**. We run ~1 ns. That is **1 part in 3.6 × 10¹²**.

And the field floor is far above us:

| Study | System | Length |
|---|---|---|
| Ayres *et al.* 2017 | 73 HLA-A\*02:01 9-mers | **1 µs each** |
| Ayres *et al.* 2019 | 52 peptides on HLA-A2 | **97 × 1 µs** |
| Knapp *et al.* 2014 | TCR/HLA-B\*08:01, 172 variants | 100 ns each, **first 10 ns discarded** |
| Knapp *et al.* 2018 | 827-residue TCRpMHC | 100 × 100 ns |

Knapp 2018 states plainly that *"a 100 ns TCRpMHC simulation is the current state of the art for this type of system."* **We are 100× below the field floor, and Knapp 2014 discarded ten times our entire production run as equilibration.**

**The finding that undercuts our own replicate agreement.** Knapp 2018, verbatim:

> "Short simulations (<10 ns) tend to agree with each other… **However, this is not due to the good sampling quality but rather is due to undersampling and exploration of just the local neighborhood solution space** instead of the global solution space."

Our three replicates agree closely — contact persistence 0.760–0.769 for the mutant. We were briefly pleased about that. **It is the expected signature of undersampling.** The tight range is not a result; it is an artefact of the run being too short to move anywhere.

So `md.py` is written as a one-sided filter. Its pass case claims nothing:

| Verdict | Wording |
|---|---|
| Fail | *"REJECTED by dynamics: the peptide left its predicted pose within the simulated window"* |
| Marginal | *"UNSTABLE in this short run: the pose drifted materially"* |
| Pass | claims nothing |

### 2.5 We do not emit nucleotide sequences

`construct.py` emits amino acids only. Ordering epitopes to avoid creating junctional binders is a real combinatorial problem and we solve it exhaustively. Emitting an orderable nucleotide sequence is a line we do not cross, and the spacer we use is marked `SPACER_IS_PUBLISHED = False`.

### 2.6 We do not claim anything clinical

KEYNOTE-942 (mRNA-4157 + pembrolizumab) reported improved recurrence-free survival at **two-sided p = 0.053**, confidence interval crossing 1.0. BioNTech **terminated** a randomised Phase 2 of this modality on futility in **August 2026**. Any tool in this space that talks about treating patients is overclaiming by orders of magnitude.

---

## 3. Errors we found in our own work

Twelve. Each with the mechanism, because the mechanism is the transferable part.

### 3.1 We shipped a filter that was worse than random

**What:** `DAI ≥ 2` as a hard gate. **Measured enrichment 0.965×** on 1,947 pairs — worse than picking at random *as a standalone gate*. TESLA's reciprocal metric scored **0.412 AUC**, also below random.

**The qualifier matters, and it cuts against us.** Conditional on presentation — inside the 1,370 candidates our shipped rule keeps — a *strict* cut of DAI ≥ 10 lifts precision from 3.58% to **4.90%**. So the honest claim is not "the differential carries no signal"; it is "we used it in the wrong role at the wrong threshold." At n = 204 with 10 responders we are not defending that as a win either. Both halves are in `docs/BENCHMARKS.md` §1.1 and in `benchmarks/screen_validation.json`.

**Why it was wrong:** the threshold was invented, not cited. And the stratification reveals the mechanism: DAI does *better* on anchor mutations (0.660) than TCR-facing ones (0.577), the exact inverse of presentation (0.719 vs 0.801). It is an anchor detector. An anchor residue points down into the HLA groove — **the T-cell never sees it.** A high-DAI candidate is disproportionately likely to be exactly the wrong kind of neoantigen.

**One measurement of ours disagrees with that story.** Within the presented set, anchor mutations reach **4.23%** precision against **3.37%** for TCR-facing — the inverse of what the mechanism predicts. Presentation scoring may already be absorbing the anchor signal, or the cell is too small to read. We flag it rather than resolve it; see `docs/BENCHMARKS.md` §1.1.

**Fix:** demoted to an annotation, displayed with the mutation position beside it so the reader can see which kind it is.

**What makes this the most instructive error:** the reasoning behind DAI is *good*. It is published (Łuksza *et al.*, *Nature* 2017), mechanistically sensible, and widely used. It simply does not survive measurement at our threshold. A plausible mechanism is not evidence.

### 3.2 Our accuracy claim was 3× optimistic

**What:** "0.42 Å median peptide backbone RMSD", from 6ULN (2020) and 3GSO (2009).

**Why it was wrong:** Boltz-2's training cutoff is **2023-06-01**. Both structures predate it by years. That is reconstruction of something the model has likely seen, not blind prediction.

**Fix:** assembled 12 crystals, split on the cutoff, and now quote the held-out number: **1.41 Å**. Our best number is 0.42 Å and it is labelled a training-set result wherever it appears.

### 3.3 We labelled a normal human peptide a tumour target

**What:** `ICDFGLARV`, from KIT D816V, shown in the demo as "KIT D816V — tumour". It had the largest fold change in the whole demo: **112×**, 177.7 nM vs 19,899 nM.

**Why it was wrong:** it occurs **verbatim** in MAPK1/ERK2 (P28482, residues 165–173) and in NLK (Q9UBE8, 280–288). The `DFG` motif is conserved across essentially the entire human kinome. A T-cell raised against it would be autoreactive against every cell expressing a MAP kinase.

**Fix:** `selfsim.py`, searching 20,431 reviewed human proteins; exact match is a hard disqualification. The case is **kept in the demo as a deliberate negative control** — the highest-fold-change candidate in the set, killed by the filter. That is strictly more useful than deleting it, and it is the cleanest available demonstration that fold change is not tumour specificity.

### 3.4 Our near-self metric was vacuous

**What:** a 1-mismatch proteome search to flag candidates resembling self peptides. It flagged everything.

**Why:** **every missense neoepitope is one mismatch from its own germline peptide.** The metric was measuring its own input.

**Fix:** `find_near(peptide, max_mismatches=1, exclude=wild_type)`. The `exclude` argument is the entire metric.

### 3.5 MD "rejected" a validated epitope at 7 Å

**Why:** implicit solvent has no periodic box, so the whole complex tumbles freely, and a naive RMSD measures the tumbling rather than the peptide.

**Fix:** Kabsch superposition of the MHC heavy chain on every frame before measuring the peptide.

**Note:** this is the same bug class as `validate.py`'s superposition requirement — **found twice, independently, in two different modules.** Worth recording as a class rather than an incident.

### 3.6 The TCR appeared 72 Å out of place

**Why:** 6ULN's biological assembly applies **operator 1 to the pMHC chains and operator 2 to the TCR chains.** Comparing a prediction against the asymmetric unit compares it against the wrong thing.

**Fix:** `gemmi.make_assembly`. Result: TCR α 1.42 Å, TCR β 1.50 Å. Frozen in `test_tcr.py`.

### 3.7 We cited the wrong paper for the TCR

**What:** "the patient-derived TCR from Tran *et al.*, *NEJM* 2016."

**Why it was wrong:** 6ULN's receptor is **TCR9d**, from **patient 3995**, characterised in **Sim *et al.*, *PNAS* 2020**. Tran's patient was **4095**. Tran reported the TIL therapy and identified the epitopes `GADGVGKSA` and `GADGVGKSAL`; the TCR structures are Sim's.

**How it was caught:** extracting the CDR3β from our own predicted chain E — `CASSLGQTNYGYTF` — and matching it against Sim 2020 Table 1.

*The full Sim 2020 series, since getting these wrong is easy: 6ULI binary pMHC 9-mer (1.88 Å), 6ULK binary pMHC 10-mer (1.90 Å), 6ULN + TCR9d (2.01 Å), 6ULR + TCR9a (3.20 Å), 6UON + TCR10 (3.50 Å). For a binary reference with no TCR distorting the groove, **6ULI is the better ground truth** and higher resolution than 6ULN. Two traps: 6JTO is HLA-C\*05:01, not C\*08:02; and `VVVGADGVGK` is a different G12D epitope restricted by HLA-A\*11:01.*

### 3.8 The language model asserted three unlicensed claims

**What:** it passed numeric verification and still wrote that the differential showed *"enhanced immunogenic potential"*, that a percentile rank showed *"rarity within the human proteome"*, and that ipTM *"supports the reliability"* of the interaction.

**Why each is wrong:** the first is the DAI error of §3.1 in prose. The second confuses a binding percentile with a proteome search. The third is contradicted by our own five measurements.

**Fix:** `BANNED_CLAIMS`, a phrase list checked after generation. All three phrases are regression tests. The lesson: **numeric verification is not claim verification.** A model can restate every number correctly and still draw a conclusion the numbers do not support.

### 3.9 A test asserted a conclusion our own data refuted

**What:** a test asserting the model "knows recognition is harder", because the pMHC:TCR ipTM (0.947) was lower than peptide-only ipTM (~0.985).

**Why it was wrong:** our **wild-type TCR control** — the same receptor against a peptide it does **not** recognise — showed the same drop. The confidence gap tracks complex size and chain count, not recognition.

**Fix:** the test was **deleted**, not repaired. The observation was real; the conclusion was not licensed by it. This is the single most seductive error in the set, because the number was real and the story was good.

### 3.10 We diagnosed the hardware fault wrong. Twice.

**First:** "cuEquivariance kernels" — a custom CUDA kernel on a brand-new architecture. `--no_kernels` still died.

**Second:** "a teammate's concurrent GPU benchmark." Corrected directly by the user: *"he only ran it once and that was this time that's all, it is definitely not the cause."* One data point, confidently misread as a pattern.

**What it actually was:** the GPU auto-boosts to **2,522 MHz**, and at that clock the transient current draw exceeds the supply. The machine browns out — no Xid, no thermal event, no panic, the log just stops mid-write.

**The fix came from the user's question**, not from my analysis: *"what was the max gpu clock speed you were setting, did you set it higher than 2500?"*

```bash
sudo nvidia-smi -lgc 0,2450        # does NOT survive reboot
```

Result: 12 consecutive predictions, zero reboots.

### 3.11 We conflated two different "foreignness" metrics

**What:** TESLA's *foreignness* (similarity to a pathogen epitope database) is not our *self-similarity* (identity to the human proteome). Treating them as the same quantity briefly let DAI-0.9 candidates through a filter.

**Fix:** reverted. Worth stating because TESLA's foreignness scores 0.5293 — essentially chance — and that is **not** evidence against our filter. Different questions.

### 3.12 Our demo input files had defects

Found by auditing our own data rather than our own code:

| Defect | Impact |
|---|---|
| `tumor_variants.vcf` declares `##reference=GRCh38`; the KIT row carries a **GRCh37** coordinate (chr4:55599321 vs 54733155) | none on results — the pipeline maps via UniProt + HGVSp, so **the genomic coordinates are decorative** — but a free catch for a reviewer |
| 13 synthetic rows in `tumor_variants_large.vcf` have positions **beyond the length of the chromosome they name**, and `N>N` for REF/ALT | any real VCF validator rejects the file |

*Credit where due: all seven proteins in `data/sequences/proteins.fasta` are byte-identical to the current UniProt canonical sequences, and `apply_missense` asserts the reference residue matches — so a wrong isoform fails loudly rather than producing confidently wrong peptides.*

---

## 4. Terminology, used precisely

The field is loose about these words. Being precise is cheap and it is the first thing a domain reviewer checks.

| Term | What it means here |
|---|---|
| **Candidate peptide** | a sequence our pipeline generated. Says nothing about presentation. |
| **Neoepitope** | a mutation-containing peptide predicted to be presented. Still a prediction. |
| **Neoantigen** | a neoepitope that is actually presented **and** recognised by a T-cell. We have never demonstrated one. |
| **Presentation** | displayed on the cell surface by an HLA molecule. What our screen predicts. |
| **Recognition** | a T-cell receptor engages the peptide–HLA surface. Not predicted here. |
| **Immunogenicity** | recognition **plus** a functional response. Measured in a laboratory, never by us. |
| **Agretopicity** | mutant/wild-type affinity ratio. TESLA's convention. |
| **DAI** | wild-type/mutant — the reciprocal. Ours, following Łuksza. Agretopicity < 0.1 ≡ DAI > 10. |
| **Anchor position** | P2 and PΩ, which point into the HLA groove. The T-cell does not see them. |
| **TCR-facing** | the middle of the peptide, which the receptor contacts. |

**One we used wrongly and fixed:** *"tumour-specific"*. A large fold change is **not** tumour specificity — `ICDFGLARV` had a 112× fold change and is a self peptide. Tumour specificity is a statement about where the sequence occurs, which is what `selfsim.py` tests and what fold change cannot.

**On the 50 nM / 500 nM thresholds:** these are real, widely used cutoffs, but the literature is not unanimous and **%rank has largely superseded them** because absolute affinity is not comparable across alleles. We report both, and our measurement shows %rank (0.744 / 0.7624) and presentation (0.777 / 0.7592) are close, with presentation more stable across k.

---

## 5. What we left out, ranked by measured effect size

"What did you leave out" is the first question a competent reviewer asks. Ranked, with the evidence for each ranking:

### 1. Tumour gene/transcript expression — by far the most serious

A peptide from an untranscribed gene **cannot** be presented, whatever its predicted affinity. This is a **logical gate**, not a correlate, and every production pipeline has it. Ours does not: the demo scores KRAS, TP53, BRAF, PIK3CA, EGFR and KIT without ever asking whether the tumour transcribes them. Published work puts it at **11–13 precision points**.

*Note the asymmetry with §3 of [PROBLEM.md](PROBLEM.md): we deliberately reject a **normal**-tissue expression gate, because it deletes cancer-testis antigens. **Tumour** expression is a different quantity and a legitimate gate. GTEx cannot supply it.*

### 2. pMHC complex stability

TESLA measured it at **AUC 0.6855**, and the association is statistically **stronger** than expression (p = 1.4×10⁻⁴ vs p = 0.01). Harndahl *et al.* (*Eur J Immunol* 2012) found stability prediction accounted for **30% of non-immunogenic binders previously written off as "holes in the T-cell repertoire."**

MHCflurry has **no stability axis at all**. NetMHCstabpan exists, is cheap, and is pan-specific.

**And there is a free, citable demonstration that our single-axis ranking misses something real:** Sim 2020 reports thermal melts for our exact peptides — **9-mer 51 ± 1.3 °C vs 10-mer 45 ± 1.8 °C**. Our presentation score ranks the **10-mer first**. The stability measurement **inverts our ranking.**

*(A related trap we avoid: do not call the 9-mer "the dominant epitope". Sim designates neither. The 9-mer has the higher melt and the highest-affinity TCR — TCR9a, K_D 16 ± 8 nM vs TCR10 at 6.7 ± 1.7 µM — **but** its C-terminal Ala is a suboptimal PΩ anchor, and in vivo the **10-mer-specific clone persisted** while TCR9a fell to 0%. Our screen ranks the 10-mer #1 and the 9-mer #2, which is arguably right for the wrong reason.)*

### 3. Clonality / variant allele frequency

McGranahan *et al.* (*Science* 2016): **clonal** neoantigen burden, not total burden, predicts checkpoint-blockade response. Our VCF has no VAF or CCF field at all.

### 4. TAP transport and proteasomal cleavage — the omission we defend rather than concede

MHCflurry's processing predictor is trained on real mass-spec hits, and its authors state its C-terminal preferences *"may reflect TAP binding and/or proteasomal cleavage"*. So NetChop and TAP predictors are **partly redundant** with what we already run. Conceding the two omissions that matter and defending the two that do not is more convincing than conceding all four.

### Also absent

- **HLA typing from reads.** You cannot get an HLA type from a VCF. We take it as input.
- **Multiple HLA alleles.** Patients have six class I alleles, and they compete for peptides. We score one.
- **Class II / CD4 epitopes.** A different prediction problem.
- **Multi-node execution.** We had one Nano.

---

## 6. What a sceptical immunologist would ask

| Question | Our answer |
|---|---|
| *"You've validated nothing — your case is in every model's training set."* | For the original two, correct. That is why there are 9 post-cutoff structures and why we quote **1.41 Å** and not 0.42 Å. |
| *"`ICDFGLARV` is in ERK2. You're showing me a self peptide labelled 'tumour'."* | You are right, and it is now the demo's negative control. §3.3. |
| *"Presentation isn't immunogenicity, and your own citation says you'll be wrong 94% of the time."* | Yes. **68–84% of our top 25 are wrong**, and that number is in the UI. We claim concentration, not identification. |
| *"Your structural panel measures something you could read off the sequence."* | Partly fair — you can tell from the sequence that Asp can salt-bridge and Gly cannot. The structure supplies the **geometry** (2.5 Å vs a crystal's 2.7 Å) and the pose. We do not claim it changes the ranking. |
| *"1 ns of implicit-solvent MD tells you nothing, and it over-stabilises exactly the bond you're claiming."* | Both true, both in §2.3–2.4, both in the tool's own output. |
| *"ipTM 0.947 doesn't mean the model 'knows recognition is harder'."* | Correct. We deleted the test that said so. §3.9. |
| *"You typed in one HLA allele. Patients have six, and they compete."* | A real limitation, listed in §5. |
| *"Your differential is agretopicity, not specificity — and it doesn't validate."* | Correct on both counts, and we measured the second ourselves: 0.592 and 0.412. §3.1. |

---

## 7. What we defend

Not everything here is a concession. These hold up:

- **Validating a screen against 2,555 lab-tested peptides.** Most tools in this space are never measured against experimental outcomes at all.
- **Holding out on the training cutoff.** Almost nobody does this for structure prediction, and it cost us a 3× better-looking number.
- **Pre-registering the contact.** Specified from a crystal structure *before* prediction. A measurement chosen after seeing the answer is not a measurement.
- **Reference-sequence assertion in `apply_missense`.** Wrong isoform fails loudly instead of silently producing confidently wrong peptides.
- **Two guardrails on the language model**, one of which exists because the first was insufficient.
- **The self-proteome filter.** It caught a real error in our own demo.
- **Reporting the failures.** Three metrics at or below chance are in the benchmark tables and in the UI.

---

## Sources

**Benchmarks**
- Wells *et al.*, *Cell* 183:818 (2020) — TESLA.
- Bjerregaard *et al.*, *Front. Immunol.* 8:1566 (2017).

**Screening**
- Łuksza *et al.*, *Nature* 551:517 (2017) — the DAI fitness model.
- O'Donnell *et al.*, *Cell Systems* (2020) — MHCflurry 2.0.
- Harndahl *et al.*, *Eur J Immunol* 42:1405 (2012), PMID 22678897 — stability beats affinity.
- Rasmussen *et al.*, *J Immunol* 197:1517 (2016), PMID 27402703 — NetMHCstabpan; 28,939 half-life measurements across 80 allotypes.
- McGranahan *et al.*, *Science* 351:1463 (2016), PMID 26940869 — clonal neoantigen burden.
- Peters *et al.*, *J Immunol* 171:1741 (2003), PMID 12902473 — TAP transport.

**Structures**
- Tran *et al.*, *NEJM* 375:2255 (2016), PMID 27959684 — the KRAS G12D epitopes.
- Sim *et al.*, *PNAS* 117:12826 (2020), PMID 32461371 — TCR9d and the 6ULI/6ULK/6ULN/6ULR/6UON series. **Correction at PNAS 117:27743, PMID 33077608.**
- PDB 6ULI, 6ULK, 6ULN, 3GSO, and the 12 held-out entries in `benchmarks/holdout_structures.json`.

**Molecular dynamics**
- Onufriev *et al.*, *Proteins* 55:383 (2004), PMID 15048829 — OBC2 / Amber igb=5.
- Geney *et al.*, *JCTC* 2:115 (2006), PMID 26626386 — **salt bridges too stable by 3–4 kcal/mol**.
- Roe *et al.*, *J Phys Chem B* 111:1846 (2007) — independent confirmation.
- Zhou & Berne, *PNAS* 99:12777 (2002), PMID 12242327 — spurious salt bridges invert native ranking.
- Nguyen *et al.*, *JCTC* 9:2020 (2013), PMID 25788871 — GB-Neck2, which exists because of these weaknesses.
- Knapp *et al.*, *PLoS Comput Biol* 10:e1003748 (2014), PMID 25101830.
- Knapp *et al.*, *JCTC* 14:6127 (2018) — **"100 ns is the current state of the art"**, and the undersampling finding.
- Ayres *et al.*, *JCIM* 57:1990 (2017), PMID 28696685; *Front Immunol* 10:966 (2019), PMID 31130956.
- Jandova *et al.*, *JCTC* 17:5944 (2021), PMID 34342983.

**Governance**
- 45 CFR 164.514(b)(2); 78 FR 5566.
- Gymrek *et al.*, *Science* 339:321 (2013), DOI 10.1126/science.1229566.
- NIH Genomic Data Sharing Policy, NOT-OD-14-124.
- GA4GH Framework, *The HUGO Journal* 8:3 (2014).

**Clinical**
- Weber *et al.*, KEYNOTE-942 / mRNA-4157 — two-sided p = 0.053.
- Morgan *et al.*, *J. Immunother.* 36:133 (2013) — MAGE-A3 / titin cardiac fatalities.
