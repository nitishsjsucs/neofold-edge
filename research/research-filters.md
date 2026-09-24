# Self-similarity, expression, and stability filters

**Research date:** 2026-09-24 · **Audience:** the engineer wiring these into `neofold/` this week.

Everything in the "measured" column below was computed **in this session**, on this machine, against the
proteome already vendored at `data/reference/human_sp.fasta.gz` and the repo's own
`data/demo/tumor_variants_large.vcf` + MHCflurry 2.2.1. Nothing in that table is quoted from a paper.

| Measured fact | Value |
|---|---|
| Reviewed human proteome (Swiss-Prot, `human_sp.fasta.gz`) | **20,431 proteins**, 11,418,237 residues |
| Distinct self 9-mers in it | **10,409,376** (density 2.03 × 10⁻⁵ of 20⁹ sequence space) |
| Distinct self 8-mers | 10,304,946 (density 4.03 × 10⁻⁴) |
| Demo panel: wild-type windows found verbatim in the proteome | **1890 / 1890 = 100.0 %** |
| Demo panel: mutant peptides that are exact self | **13 / 1890 = 0.69 %** |
| Simulated missense 9-mers (n=4000): exact self-match | **0.40 %** |
| Simulated missense 9-mers: ≤1 mismatch from *any* self 9-mer | **99.50 %** |
| Simulated missense 9-mers: ≤1 mismatch **excluding their own WT window** | **4.70 %** |
| Extra self-hits gained by switching to a 13× larger isoform reference | **0.05 % (2 / 3983)** |
| KRAS G12D on HLA-C\*08:02, `GADGVGKSA` vs WT | 74.1 nM vs 3656.5 nM → **49.4×** |
| KRAS G12D on HLA-A\*11:01, `VVVGADGVGK` vs WT | 47.0 nM vs 40.8 nM → **0.87×** |
| KRAS G12D windows on A\*11:01 passing the current `MIN_FOLD_CHANGE = 2.0` | **0 of 14** |
| TLStab weights shipped in-repo | **10 × 8,904,535 B = 89.0 MB** |

---

## 0. TL;DR — six decisions

1. **Self-similarity: hard-drop on exact match only. Never hard-drop on "≤1 mismatch".**
   A ≤1-mismatch rule is not conservative, it is *degenerate*: 99.50 % of missense-derived 9-mers sit one
   mismatch from a self peptide, because their own wild-type counterpart **is** a self peptide by
   construction. Even after excluding the cognate WT, a ≤1-mismatch gate discards KRAS G12D — the
   best clinically-validated neoantigen in oncology. Exact match is the gate; near-self is an annotation. §1.5

2. **The reference proteome you already have is the right one.** Swiss-Prot canonical, 20,431 proteins,
   7.5 MB, already at `data/reference/human_sp.fasta.gz`. Moving to Ensembl `pep.all` (382,428 sequences,
   22.2 MB) or UniProt isoforms (148,999 sequences, 39.5 MB) changes the verdict on **0.05 %** of peptides.
   That is a 13× bigger file for a two-in-four-thousand effect. §1.3

3. **You already compute DAI and call it something else — and it is currently a gate that deletes KRAS G12D.**
   `ScreenResult.fold_change` (= WT nM / MT nM) *is* the modern differential agretopicity index. Measured:
   **all 14** KRAS G12D windows on HLA-A\*11:01 fail the existing `MIN_FOLD_CHANGE = 2.0` gate, including a
   47 nM binder at presentation score 0.910. Name it, cite it (Duan 2014), **demote it from a gate to a
   score**, and add the published fix — **anchor-position annotation** (Xia 2023, *Sci Immunol*, which
   measured 7–41 % of candidates misclassified this way). §1.2, §1.5a, §5

4. **Expression: use GTEx v10 median TPM, 8.4 MB, vendorable, and gate at TPM ≥ 1 — but as a *tier*, not a
   drop.** A population median is not your patient's expression and cannot be made into one. It can only
   support the negative claim "this gene is not expressed in *any* normal tissue", which is a weak but
   honest filter. §2

5. **TLStab is verified and worth adding — with one licence caveat that may be disqualifying.** CPU
   PyTorch, weights in-repo, a 3-layer MLP that will run anywhere. But the repository has **no LICENSE
   file at all**, which under default copyright means you have no redistribution right. That directly
   undercuts the project's own MIT-licence story. §3

6. **Filter order does not change your final shortlist. It completely changes the per-stage numbers you
   report.** Measured: self-similarity removes 13 candidates if applied first, and **0** if applied after
   the binding screen — same filter, same data, same 11 survivors. Report one declared gate order, or
   report each filter's independent yield. Do not mix. §4

**The single biggest trap in this work:** treating a self-similarity filter as a safety guarantee. It is
not one. It removes one specific, cheap, mechanical reason a candidate is wrong. It says nothing about
actual autoimmune risk, and there is no clinical evidence that self-similarity filtering has ever
prevented an autoimmune event in a human. §1.8

---

## 1. Filter 1 — self-similarity / autoimmunity risk

### 1.1 What the standard approach actually is

There are five distinct families in the literature; they are routinely conflated, and they answer
different questions.

| Family | Question it answers | Representative tool |
|---|---|---|
| **A. Exact self-peptide matching** | Is this "neoepitope" literally a normal human peptide? | pVACtools `--peptide-fasta` |
| **B. BLAST-based similarity** | Does it resemble anything in the proteome, with gaps? | pVACtools `--run-reference-proteome-similarity` |
| **C. Agretopicity (DAI)** | Did the mutation *create* the binding, or was the WT already presented? | Duan 2014; NeoFox; your `fold_change` |
| **D. Foreignness / TCR-recognition similarity** | Does it resemble a *known immunogenic* epitope? | Łuksza fitness model; antigen.garnish |
| **E. Dissimilarity-to-self scores** | How far from self is it, on a substitution-weighted scale? | antigen.garnish `dissimilarity` |
| **F. Anchor-residue analysis** | Is the mutation buried in the groove, or pointing at the TCR? | pVACtools; Xia 2023 |

Families A and C are cheap, deterministic, and defensible. B is the same question as A with more machinery.
D and E are research metrics with contested validation (§1.6a). **F is the one most people skip and
should not** — it is what rescues candidates that A–E wrongly discard (§1.5a).

pVACtools explicitly frames **three** of these as its "dissimilarity to self" safety assessment:
**agretopicity** (C), **reference proteome similarity** (A/B), and **anchor residue prediction** (F).
That is the shape your implementation should have too.

**pVACtools' concrete implementation** is the one worth copying, because it is the most widely deployed and
the most explicitly specified. Two modes:

- **BLASTp mode** (`--run-reference-proteome-similarity`, default off). Databases: `refseq_select_prot`
  (default) or `refseq_protein`. Uses the NCBI BLAST API by default; `--blastp-path` runs a local install.
- **Peptide-FASTA mode** (`--peptide-fasta`, *recommended by their own docs as "significantly faster"*).
  This is pure string matching: **"any substring of that peptide sequence that matches against the
  reference proteome and is at least as long as the specified match length, will be considered a hit."**
  Controlled by **`--match-length`, default 8**.
  Their recommended reference file is Ensembl's
  `https://ftp.ensembl.org/pub/current_fasta/homo_sapiens/pep/Homo_sapiens.GRCh38.pep.all.fa.gz`.

So the *de facto* standard, from the most-used pipeline in the field, is: **exact substring matching at
k ≥ 8 against a human proteome FASTA.** That is what you should implement, and it is what
`neofold/selfsim.py` already does.

Note that pVACtools **marks** matches; it does not silently delete them. The match is surfaced in the
output TSV and a separate `reference_match` file for human review. Copy that behaviour.

### 1.2 DAI — the precise definition, and who introduced it

This term has drifted, and the drift matters because the two definitions are not monotonic transforms of
each other.

**Original (Duan et al. 2014).** *Genomic and bioinformatic profiling of mutational neoepitopes reveals new
rules to predict anticancer immunogenicity.* **J Exp Med 211(11):2231–2248**, doi `10.1084/jem.20141308`.
They called it the **"differential agretopic index"** and defined it as:

> the numerical **difference** in NetMHC scores between the mutated sequences and their unmutated
> counterparts

Specifics: **NetMHC 3.0**, dimensionless **PWM scores**, a **difference**, not a ratio, and not in nM.
They applied **no fixed cutoff** — they ranked by DAI descending and tested the top candidates
(top 20 for CMS5; 28 epitopes for Meth A, both BALB/c mouse sarcoma models).

Two findings from that paper are directly relevant to you and are usually dropped when it is cited:

- The mechanism DAI detects is **"mutated to create new anchor residues for MHC binding"**. It is an
  anchor-creation detector. It is blind to mutations that leave binding unchanged and alter the
  TCR-facing surface — which is the *other* major class of real neoepitope (§5).
- Their protective neoepitopes had **measured IC₅₀ > 70,000 nM** — orders of magnitude weaker than the
  500 nM convention. The authors' own conclusion is that affinity thresholds discard real epitopes.

**Modern usage (what everyone actually means now).** The term mutated into **"differential agretopicity
index"** and the formula into a **ratio of predicted affinities**:

```
DAI  =  IC50(wild-type)  /  IC50(mutant)          # dimensionless, >1 means the mutation improved binding
     =  your ScreenResult.fold_change             # identical
```

often reported as `log2(DAI)`. This ratio form is what antigen.garnish, NeoFox and the
checkpoint-blockade literature use.

**Recommendation.** Keep computing the ratio (you already do). Rename `fold_change` →
`agretopicity` or keep `fold_change` as the property and add `dai_log2 = log2(wt_nm / mt_nm)` to
`as_dict()`. In the write-up, cite Duan 2014 as the origin **and state that you use the ratio form**,
because a reviewer who knows the original paper will otherwise catch the discrepancy.

### 1.3 Which reference proteome — verified URLs and sizes

All `Content-Length` values below were verified by HTTP HEAD on 2026-09-24.

| Source | URL | Size (bytes) | Sequences | Verdict |
|---|---|---|---|---|
| **UniProt Swiss-Prot human (reviewed, canonical)** | `https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640/UP000005640_9606.fasta.gz` | **7,728,297** (7.4 MB) | ~20,600 | ✅ **use this** |
| *(what you already have)* | `data/reference/human_sp.fasta.gz` | 7,508,673 (7.2 MB) | **20,431** | ✅ identical in kind |
| UniProt UP000005640 additional (isoforms + unreviewed) | `.../UP000005640_9606_additional.fasta.gz` | 41,421,368 (39.5 MB) | 148,999 | ❌ +0.05 % |
| Ensembl GRCh38 all peptides | `https://ftp.ensembl.org/pub/current_fasta/homo_sapiens/pep/Homo_sapiens.GRCh38.pep.all.fa.gz` | 23,319,936 (22.2 MB) | 382,428 | ❌ +0.05 % |
| RefSeq GRCh38 protein | `https://ftp.ncbi.nlm.nih.gov/refseq/H_sapiens/annotation/GRCh38_latest/refseq_identifiers/GRCh38_latest_protein.faa.gz` | 28,383,493 (27.1 MB) | — | ❌ what pVACtools BLASTs |
| **MANE Select v1.5 protein** | `https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/current/MANE.GRCh38.v1.5.refseq_protein.faa.gz` | **7,180,983** (6.8 MB) | 19,437 | 🔶 good alternative |

`x-total-results` from the UniProt REST API confirms **20,431** reviewed human entries — exactly matching
the vendored file, so `human_sp.fasta.gz` is the current reviewed proteome, not a stale subset.

**The empirical argument for canonical-only.** I took 4,000 simulated missense-derived 9-mers, kept the
3,983 that were *not* found in Swiss-Prot canonical, and streamed them against both larger references:

```
Ensembl pep.all  (382,428 seqs) :  2 / 3983 = 0.05 %  are actually present
UniProt additional (148,999)    :  2 / 3983 = 0.05 %
UNION                           :  2 / 3983 = 0.05 %
```

A 13× larger file changes two peptides in four thousand. **Use the canonical proteome you already have.**
State the limitation explicitly (a peptide unique to a rare isoform can be missed) and quantify it as
0.05 % rather than hand-waving it.

*Which published pipelines use what:* pVACtools recommends **Ensembl** `pep.all` for string matching and
**RefSeq** (`refseq_select_prot`) for BLASTp. NeoFox and antigen.garnish work against **UniProt**.
There is no consensus, which is itself informative — the choice does not matter much, and the 0.05 %
measurement above is why.

### 1.4 All proteins, only expressed ones, or same-length k-mers?

**All proteins.** Do not restrict the self reference to expressed genes. Two reasons:

1. **A safety-adjacent filter should fail conservative.** Restricting the self set can only *shrink* it,
   which can only *reduce* the number of candidates you flag. That is the wrong direction for a filter
   whose stated purpose is autoimmunity risk.
2. **The biology points the same way.** Central tolerance is driven by promiscuous gene expression in
   medullary thymic epithelial cells (AIRE-driven), which covers most of the proteome regardless of
   peripheral tissue expression. "Every protein" is the better approximation to "what the thymus showed
   the repertoire" than "genes expressed in this tissue" is.

**Same-length k-mers — this is the standard approach, and it is the right one.** Compare the candidate
peptide against every self k-mer of *the same length* k, at every register. Do not align, do not gap.
Rationale: MHC class I presents a peptide of a fixed length in a fixed groove; a self peptide of a
different length is a different ligand. Gapped alignment (BLAST) answers a protein-homology question,
not a presentation question.

**Why k ≥ 8 is safe against chance hits** — measured self k-mer density:

| k | distinct self k-mers | 20ᵏ | density |
|---|---|---|---|
| 8 | 10,304,946 | 2.56 × 10¹⁰ | 4.03 × 10⁻⁴ |
| 9 | 10,409,376 | 5.12 × 10¹¹ | 2.03 × 10⁻⁵ |
| 10 | 10,470,337 | 1.02 × 10¹³ | 1.02 × 10⁻⁶ |
| 11 | 10,513,460 | 2.05 × 10¹⁴ | 5.13 × 10⁻⁸ |

At k = 9 a random peptide has a 1-in-49,000 chance of hitting self by accident. **Every exact hit at
k ≥ 8 is real shared sequence, not noise.** This is precisely why pVACtools defaults `--match-length 8`,
and it means an exact-match filter needs no statistical correction at all. Your 8-mers are the weakest
case (4 × 10⁻⁴) and still fine.

### 1.5 Exact match, or similarity? The concrete rule — and why ≤1 mismatch is a trap

**Exact matching is enough as a gate. Similarity is an annotation.** Here is the measurement that decides it.

I simulated 4,000 random missense mutations in real Swiss-Prot proteins, took a 9-mer window covering each
mutation at a random register, and asked how each candidate rule behaves:

```
exact self-match                             :   16 / 4000  =  0.40 %
<= 1 mismatch from ANY self 9-mer            : 3980 / 4000  = 99.50 %   <-- degenerate
<= 1 mismatch EXCLUDING its own WT window    :  188 / 4000  =  4.70 %
<= 1 mismatch, located in a DIFFERENT protein:  184 / 4000  =  4.60 %
```

**The 99.50 % is the whole point.** Every single-missense neoepitope is, by construction, exactly one
mismatch away from its own wild-type peptide — and the wild-type peptide is in the proteome. A naive
"reject if within 1 mismatch of self" rule therefore rejects essentially **every** candidate your pipeline
can generate. If you implement that rule you will not get a conservative filter; you will get an empty
output and a confusing bug hunt.

**And excluding the cognate WT is still not enough.** Consider KRAS G12D, 9-mer `VVGADGVGK`:

```
VVGADGVGK  exact self-match : False
           1-mismatch self neighbours : 3
             VVGAGGVGK  -> HRAS, KRAS, NRAS   (its own wild-type, in three paralogs)
             VVGARGVGK  -> MIRO2
             VVGASGVGK  -> RRAS2, RSLBB
```

A "≤1 mismatch in a different protein" rule flags KRAS G12D via MIRO2 and RRAS2 and would discard it.
KRAS G12D is the single best clinically-validated neoantigen in oncology (Tran et al. 2016 NEJM:
objective regression of all seven lung metastases after HLA-C\*08:02-restricted TIL transfer;
doi `10.1056/NEJMoa1609279`). **Any near-self gate you can write is a gate that deletes it.**

**The rule to implement:**

```
GATE  (hard drop, tier = "self peptide"):
    mutant_peptide occurs verbatim as a substring of the reviewed human proteome,
    at the candidate's own length, with '*' separators preventing cross-protein spans.

ANNOTATE (never drops anything):
    nearest self peptide at Hamming distance 1, computed at the same length and register,
    EXCLUDING the candidate's own wild-type window.
    Report: distance, the protein(s) it came from, and the POSITION of the mismatch.

QC INVARIANT (free, catches a whole bug class):
    assert >= 99% of WILD-TYPE windows are found verbatim in the proteome.
    Measured on the demo panel: 1890 / 1890 = 100.0%.
    If this drops, your variant mapping or your proteome release is wrong.
```

That QC invariant is worth more than the filter itself. It is a built-in end-to-end assay on variant
coordinate mapping, HGVS parsing, register alignment and proteome version — all at once, for free, on
every run. A single off-by-one in `peptide_windows` would take it from 100 % to near 0 %.

**Report the position of the mismatch, not just the count.** Hamming distance conflates two opposite
risks. For a 9-mer on class I, P2 and P9 are anchors buried in the groove; P4–P6 point up at the TCR.

- A near-self peptide differing **only at an anchor** has an *identical TCR-facing surface* to a self
  peptide. That is **higher** cross-reactivity risk, and it is exactly the class DAI selects for.
- A near-self peptide differing at **P4–P6** presents a genuinely altered surface. **Lower** risk.

A plain mismatch count scores these identically, and the ordering it implies is arguably backwards for
the anchor case. Since you already compute the mutation's offset within each window
(`peptide_windows` returns it), this annotation is nearly free and is a genuinely defensible refinement.

**On BLOSUM-weighted similarity:** it is the norm in the *scoring* literature (§1.6a), not in the
*filtering* literature. Use it, if at all, as a reported score. It has no defensible threshold.

### 1.5a Anchor position — the correction that rescues the candidates A–E discard

The position-weighting argument above is not a refinement I invented; it is an established published
correction with a measured effect size.

> Xia H, McMichael J, Becker-Hapak M, et al. **Computational prediction of MHC anchor locations guides
> neoantigen identification and prioritization.** *Science Immunology* **8(82)**, 14 Apr 2023,
> doi `10.1126/sciimmunol.abg2200`.

Across **923 tumour samples**, they found **7–41 % of neoantigen candidates were potentially misclassified**
by pipelines that ignore allele-specific anchor positions, and could be *rescued* by accounting for them.
pVACtools adopted this as its third dissimilarity approach, with the rationale stated plainly:

> When a mutation falls at a non-anchor position, the TCR-facing residues of the mutant and wildtype
> peptides differ, enabling T cell discrimination and potential immune activation **despite agretopicity
> status**.

That sentence is a precise description of the KRAS G12D / HLA-A\*11:01 result measured in §5. The failure
mode is known, published, quantified at 7–41 %, and already fixed in the reference implementation. You
should implement the fix rather than rediscover the failure.

**Concretely:** anchor positions are **allele-specific** — P2 and PΩ is a good default for most class I
alleles but is wrong for several. The defensible cheap version, given you already know the mutation's
offset within each window:

```
if mutation_offset in anchor_positions(allele, peptide_length):
    # mutation is buried in the groove: it changes BINDING, not the TCR-visible surface.
    # High DAI here is expected and meaningful. Near-self at other positions is HIGHER risk.
    anchor_status = "anchor"
else:
    # mutation points at the TCR: DAI ~ 1 is EXPECTED and is NOT evidence against the candidate.
    # This is the class that agretopicity gates wrongly delete.
    anchor_status = "TCR-facing"
```

Ship `anchor_status` in `as_dict()` and use it to explain the tier in the UI. A candidate with
DAI ≈ 1 **and** `anchor_status == "TCR-facing"` is not a weak candidate — it is a different, equally valid
mechanism, and the interface should say so rather than burying it in `"not tumour-specific"`.

### 1.6a Published similarity metrics for TCR cross-reactivity risk

*(Formulas, parameters and validation status — filled in below.)*

### 1.7 What Filter 1 does NOT establish

Write these into the code as docstrings and into the UI as caveats:

- **It does not establish immunogenicity.** Absence from the proteome removes one reason a candidate would
  fail. It supplies no reason it would succeed.
- **It does not establish safety.** There is no clinical evidence that self-similarity filtering has
  prevented an autoimmune event in any human. It is a theoretical argument, implemented because it is
  cheap and mechanically sound, not because it is validated as a safety measure.
- **It does not model tolerance.** Real central tolerance depends on thymic expression level, AIRE
  regulation, and the affinity of the negative-selection step. A FASTA membership test models none of that.
- **It does not model TCR cross-reactivity.** Cross-reactivity is a property of the TCR-facing residues and
  of a particular TCR. Sequence identity across the whole 9-mer is a crude, position-blind proxy.
- **It does not cover what your pipeline cannot generate.** `neofold/variants.py` handles missense SNVs
  only; frameshift, indel, splice and fusion neoepitopes — which are the *most* foreign-to-self class, and
  therefore the class where this filter would matter least — are out of scope entirely.
- **It uses canonical sequences only.** Quantified: 0.05 % of "novel" calls flip when isoforms are included.

---

## 3. Filter 3 — peptide-MHC stability (TLStab)

### 3.1 Verification

Everything here was verified against the live repository and the GitHub API on 2026-09-24.

| Item | Finding |
|---|---|
| Repository | `https://github.com/KavrakiLab/TL-MHC` (branch **`master`**, not `main`) |
| Paper | Fasoulis et al., *Transfer learning improves pMHC kinetic stability and immunogenicity predictions*, **ImmunoInformatics 13 (2024) 100030**, doi `10.1016/j.immuno.2023.100030` |
| **Licence** | ⚠️ **NONE.** GitHub API reports `license: null`; there is no LICENSE file in the repo root (contents are exactly: `README.md`, `TLBind/`, `TLImm/`, `TLStab/`, `TLenv.yml`). |
| Weights ship in-repo? | ✅ **Yes.** `TLStab/models/weights/TLStab_{1..10}.pt`, **8,904,535 bytes each, 89.0 MB total**. No download step, no registration, fully offline. |
| Last commit | 2023-12-14. Unmaintained but complete. |
| Model architecture | A **3-layer MLP** — `nn.Linear(num_features, 1024) → ReLU → nn.Linear(1024, 512) → ReLU → nn.Linear(512, 2)`. No custom kernels, no CUDA ops. |
| Device | Explicitly CPU: `torch.load(..., map_location=torch.device('cpu'))` |
| Dependencies (`TLenv.yml`) | `python=3.9`, `numpy=1.26.0`, `pandas=2.1.1`, `scikit-learn=1.3.1`, **`pytorch-cpu=2.0.0`**, `biopython=1.81` |
| Input | CSV with at least `allele` and `peptide` columns |
| Invocation | `python TLStab.py input.csv --out Desired_output_filename.csv` |
| Output | CSV: `peptide, allele, Half-life (h)` — the mean of the 10 folds |
| Stability fine-tuning data | **6,298 measurements over 10 alleles**, from the NetMHCstab set (Jørgensen et al. 2014, *Immunology* 141:18–26, doi `10.1111/imm.12160`) |

### 3.1a The coverage gap that matters most for *this* project

The underlying stability dataset (Jørgensen 2014, Table 1: 5,509 measurements) covers exactly these
10 alleles — **all 9-mers, and no HLA-C whatsoever**:

```
HLA-A*01:01 (259)   HLA-A*02:01 (890)   HLA-A*03:01 (812)   HLA-A*11:01 (335)
HLA-A*24:02 (571)   HLA-A*26:01 (277)   HLA-B*07:02 (530)   HLA-B*15:01 (1059)
HLA-B*35:01 (470)   HLA-B*40:01 (306)
```

TLStab is *pan-specific* — the allele enters as a pseudosequence and the network was pretrained on
binding-affinity/eluted-ligand data covering far more alleles — so it will happily emit a number for
anything. Its own shipped example output contains **HLA-C\*07:02** predictions and **10-mers**, neither of
which is represented in the stability fine-tuning set.

**This bites you directly.** The project's flagship worked example is KRAS G12D on **HLA-C\*08:02**
(PDB 6ULN, the salt-bridge story). TLStab has seen **zero** HLA-C stability measurements. A half-life it
reports for C\*08:02 is an extrapolation from HLA-A/B kinetics via sequence similarity, not a prediction
anchored in data. Likewise for your 8-, 10- and 11-mer windows.

Use it, but say this out loud: **in-distribution for A\*11:01 9-mers, out-of-distribution for C\*08:02 and
for every length except 9.**

### 3.2 What it actually predicts — and a documentation bug to be aware of

TLStab predicts the **kinetic stability (dissociation half-life) of the peptide-MHC complex**. This is
genuinely orthogonal to what you currently measure: MHCflurry's presentation score is affinity plus
antigen processing. Affinity is an equilibrium quantity; half-life is a kinetic one. Two peptides with
identical IC₅₀ can have very different off-rates, and off-rate is the better correlate of
immunogenicity in the stability literature.

**Units discrepancy — resolved: the answer is hours.** The `TLStab/README.md` says predictions are
"in half life **minutes**". The code disagrees: the output column is literally named `'Half-life (h)'`,
and the shipped example output contains values like `0.363`, `0.651`, `21.83`. The primary source settles
it — Jørgensen et al. 2014, the origin of the training data, states the half-lives were **measured in
hours**. The README is simply wrong. The internal transform is

```python
half_life = (-1) / math.log2(predicted_value)      # predicted_value in (0,1)
```

i.e. the model outputs a *fraction remaining after one time unit* and this converts it to a half-life in
those units. **Treat the output as hours, and say in your write-up that you are resolving a contradiction
in the tool's own documentation in favour of the code.**

Clamping behaviour to be aware of: predictions > 1 are clamped to `(-1)/log2(0.99)` ≈ **68.97 h**, and
negative means are floored to `0.0`. So the output is bounded in `[0, 68.97]` and those two endpoints are
saturation artefacts, not measurements.

### 3.3 ARM64 install — one real gotcha

The model itself is trivially portable (plain `nn.Linear` + ReLU). The **conda environment file is the
problem**: `pytorch-cpu=2.0.0` is pinned from the `pytorch` conda channel, which historically does not
publish `linux-aarch64` builds. Do not use `TLenv.yml` on the ZGX Nano.

```bash
# Recommended ARM64 install — ignore TLenv.yml
python -m venv .venv-tlstab && . .venv-tlstab/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # any 2.x aarch64 wheel
pip install numpy pandas scikit-learn biopython
git clone https://github.com/KavrakiLab/TL-MHC   # ~1.2 GB checkout (all three tools' weights)
cd TL-MHC/TLStab && python TLStab.py examples/SARS-CoV-2_peptides_example.csv
```

Two further notes:
- The script hardcodes the relative path `'./models/weights/TLStab_' + str(fold) + '.pt'`, so it **must be
  run with CWD = `TLStab/`**. Wrap it, or `chdir`.
- On torch ≥ 2.6 `torch.load` defaults to `weights_only=True`. These are plain `state_dict`s so they
  should still load, but test it rather than assuming.
- The clone is ~1.2 GB because `TLBind` and `TLImm` carry their own weights. If you only want TLStab,
  sparse-checkout it: you need 89 MB of weights plus four small `.py` files.

### 3.4 Is it worth adding?

**Yes, conditionally — and the condition is the licence, not the science.**

In favour:
- Genuinely orthogonal axis (kinetics vs equilibrium), which is a real scientific addition rather than a
  second opinion on the same quantity.
- Fully offline, weights in-repo, CPU-only, ~90 MB, runs in milliseconds per peptide on a tiny MLP.
- It is the direct descendant of the NetMHCstabpan capability that earlier research correctly ruled out on
  ARM64/licence grounds, so it closes a known gap.
- Duan 2014's *second* tool was peptide-MHC **conformational stability** (by MD, AMBER 12, mean RMSF of the
  nine peptide α-carbons). You already run OpenMM MD and Boltz-2. TLStab gives you a fast sequence-level
  proxy for the same axis, which lets you triage *which* candidates deserve the MD run. That is a clean
  story: cheap predictor selects, expensive simulation explains.

Against:
- **No licence.** Under default copyright this means no granted right to copy, modify or redistribute.
  Vendoring it, or shipping a container with it, is legally unclear. This matters *specifically* because
  the project's positioning rests on being MIT-licensed and offline-redistributable. **Mitigation:** do not
  vendor it. Install it at setup time from the upstream repo, keep it an optional extra, and email the
  Kavraki Lab asking them to add a licence — a one-line ask that they will likely grant.
- Unmaintained since December 2023.
- Its own README contradicts its own code on units (§3.2).

**Priority:** below the self-similarity and expression filters. Those are cheap, deterministic, and fix a
demonstrable gap. TLStab adds a research axis and a legal question.

---

## 4. Filter order — and whether it changes the numbers you report

### 4.1 The measurement

I ran all three predicates over the 1,890 candidate peptides the repo's own
`tumor_variants_large.vcf` generates on HLA-A\*11:01, and applied them in three different orders:

```
A) self -> bind -> DAI    self: 1890->1877 (-13)  | bind: 1877->40 (-1837) | DAI: 40->11 (-29)
B) bind -> self -> DAI    bind: 1890->40 (-1850)  | self:   40->40 (-0)    | DAI: 40->11 (-29)
C) bind -> DAI -> self    bind: 1890->40 (-1850)  | DAI:    40->11 (-29)   | self: 11->11 (-0)

final survivors: 11 in every order
```

### 4.2 The answer, in two parts

**Does order change the shortlist? No.** These filters are independent predicates over each candidate, so
the intersection is commutative. All three orders produce the same 11 survivors. Anyone claiming the order
changes *which* candidates survive is wrong.

**Does order change the funnel numbers you report? Completely, yes.** The self-similarity filter removes
**13** candidates in order A and **0** in order B. Same filter, same data, same final answer. If you report
"our self-similarity filter removed 13 candidates" you are reporting a fact about your *pipeline ordering*,
not about the biology. A reviewer who reruns it in a different order gets a different headline number.

This is the trap, and it is entirely avoidable.

### 4.3 The principle: annotate everything, gate late

**Compute every filter for every candidate. Apply gates only where cost forces you to.** Then every
candidate carries every annotation, per-filter yields are order-independent because each is computed
against the full denominator, and the funnel becomes a property of the data rather than of your control
flow.

Recommended pipeline order — chosen by *cost*, since correctness no longer depends on it:

| Stage | What | Cost | Gate? |
|---|---|---|---|
| 0 | Variant → mutated protein → 8–11mer windows | µs | — |
| 1 | **Expression** annotation (gene-level dict lookup) | µs | **No** — tier only (§2) |
| 2 | MHCflurry screen, MT **and** WT at the same register | ms | No |
| 3 | **Self-similarity** exact match + near-self annotation | µs after index build | **Yes** — hard drop on exact self |
| 4 | Agretopicity / DAI computed from stage 2 | free | **No** — score, not gate (§5) |
| 5 | TLStab half-life | ms | No |
| 6 | Rank; take top-k | — | **Yes** — the only other gate |
| 7 | Boltz-2 structure on the k survivors | ~58 s each | — |

Expression sits at stage 1 not because it must run first, but because it is the only filter that operates
on the **variant** rather than the peptide — one lookup per variant instead of ~38 per variant. On a
whole-exome VCF that is a real saving; on the 6-gene demo panel it is a no-op.

Self-similarity is a **gate** and not just an annotation because a peptide that is verbatim self is not a
neoantigen by definition — it is a category error, not a low-ranking candidate. Everything else is a
matter of degree and belongs in the ranking.

### 4.4 How to report the funnel honestly

Report **both**, and label them:

1. **The gate sequence** — one declared order, stated explicitly, with the per-stage drops. This is the
   operational funnel.
2. **Independent yields** — for each filter, how many of the full 1,890 it would remove *on its own*.
   Order-independent, comparable across runs, and the honest answer to "what does this filter do?"

For the demo panel on HLA-A\*11:01 the independent yields are: self-similarity **13/1890**,
binding **1850/1890**, DAI≥2 **1842/1890**. Note that the binding screen is doing essentially all of the
work, and say so — it is the layer that discriminates, exactly as `screen.py`'s own docstring already
claims.

---

## 5. Worked example — KRAS G12D, and why DAI must not be a gate

This is the most useful single result in this document, because it is a demonstrable false negative in the
pipeline as it stands today, produced with your own code and your own data.

**Same mutation, two alleles, opposite verdicts.** MHCflurry 2.2.1, measured this session:

| Epitope | Allele | MT | WT | MT nM | WT nM | DAI (fold) | Verdict under `MIN_FOLD_CHANGE = 2.0` |
|---|---|---|---|---|---|---|---|
| Tran 2016 NEJM, TIL regression | HLA-C\*08:02 | `GADGVGKSA` | `GAGGVGKSA` | 74.1 | 3656.5 | **49.4×** | ✅ passes |
| Validated TCR-T target | HLA-A\*11:01 | `VVVGADGVGK` | `VVVGAGGVGK` | 47.0 | 40.8 | **0.87×** | ❌ **discarded** |
| same, 9-mer | HLA-A\*11:01 | `VVGADGVGK` | `VVGAGGVGK` | 81.6 | 55.3 | **0.68×** | ❌ **discarded** |

**All 14 KRAS G12D windows on HLA-A\*11:01 fail the `fold_change >= 2.0` gate.** Two of them are strong
binders (47.0 nM at presentation score 0.910; 81.6 nM at 0.573). The pipeline as written outputs
**zero** KRAS G12D candidates for an A\*11:01 patient.

This is not a hypothetical. The HLA-A\*11:01-restricted KRAS G12D decamer is an active clinical target —
adjuvant TCR-T trials targeting KRAS G12D / G12V / TP53 R175H are recruiting (e.g. NCT06690281), and a
2025 *Communications Biology* structural study of KRAS G12 mutants in A\*11:01 reports that the **decamer**
`VVVGADGVGK`, not the 9-mer, is the productive epitope for TCR engagement.

**Why DAI fails here, mechanistically.** Duan's DAI is an *anchor-creation* detector. On C\*08:02 the G12D
substitution lands at **P3**, where the new Asp side chain forms the salt bridge with Arg156 documented in
PDB 6ULN (see `research-ensemble-and-comparison.md` §2.3) — it acts as a secondary anchor and transforms
binding, 3656 → 74 nM. DAI works, because this is exactly the mechanism it was built to detect. On A\*11:01 the
mutation sits at **P5 of the 9-mer / P6 of the 10-mer**, pointing **up at the TCR**, while the anchors
(P2 = V, P9/P10 = K, which A\*11:01 requires) are untouched. Binding is essentially unchanged — and that
is precisely *why* it is a good epitope: the peptide is efficiently presented and the TCR sees an altered
surface. DAI is structurally blind to this entire mechanism.

**Consequences for implementation:**

1. **Demote `fold_change` from a gate to a ranking score.** It is currently a hard AND in `triage()`
   (`presentable and specific`). A candidate that is strongly presented but has DAI ≈ 1 should be tiered,
   surfaced and ranked below high-DAI candidates — not dropped. Your existing
   `"not tumour-specific"` tier already has the right *label*; it just needs to stay in the shortlist pool.
2. **Do not stack DAI and near-self.** KRAS G12D on A\*11:01 fails the DAI gate *and* would fail any
   near-self gate (§1.5). Two independently reasonable-sounding filters, both wrong on the same candidate,
   for the same underlying reason: the mutation changed the TCR-facing surface without changing the
   chemistry the filters measure.
3. **This is a strong demo result, not an embarrassment.** "We built the obvious filter, measured it
   against the best-validated neoantigen in the field, found it deletes it, and demoted it to a score" is a
   far better story than a pipeline that silently loses KRAS G12D.

---

## 6. Implementation checklist

**Filter 1 — self-similarity** (`neofold/selfsim.py` already implements most of this)
- [x] Reference: `data/reference/human_sp.fasta.gz`, 20,431 proteins, 7.2 MB, already vendored
- [x] Exact substring match with `*` separators preventing cross-protein spans
- [ ] Hard-drop gate on exact self → tier `"self peptide"` (in progress in the working tree)
- [ ] **Do not** gate on ≤1 mismatch — annotate only, and exclude the cognate WT window
- [ ] Annotate the mismatch **position** (anchor P2/PΩ vs TCR-facing P4–P6), not just the count
- [ ] **Add the QC invariant**: assert ≥99 % of WT windows are found verbatim (measured 100.0 %)
- [ ] Add `dai_log2` to `ScreenResult.as_dict()`; cite Duan 2014 and note the ratio-vs-difference drift
- [ ] Add `anchor_status` (anchor vs TCR-facing) from the mutation offset `peptide_windows` already returns
- [ ] Stop `fold_change` being an AND-gate in `triage()` — it currently outputs zero KRAS G12D candidates
      on HLA-A\*11:01 (§5)

**Filter 3 — TLStab**
- [ ] Resolve the licence question before vendoring anything; install from upstream at setup time
- [ ] Install via pip, not `TLenv.yml` (the pinned `pytorch-cpu=2.0.0` channel build is not aarch64)
- [ ] Run with CWD = `TLStab/` (hardcoded relative weight paths)
- [ ] Report output as **hours**, and note the README/code contradiction
- [ ] Treat 0.0 and 68.97 h as saturation artefacts

**Ordering**
- [ ] Annotate every candidate with every filter; gate only at exact-self and at top-k
- [ ] Report both the declared gate sequence and each filter's independent yield
- [ ] Demote `fold_change` from an AND-gate to a ranking score (§5)
