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
| KRAS G12D windows on A\*11:01 passing the live `MIN_DAI = 10.0` gate | **0 of 14** |
| Demo-panel binders whose mutation is at an **anchor**, passing `DAI ≥ 10` | **3 / 4 = 75 %** |
| Demo-panel binders whose mutation is **TCR-facing**, passing `DAI ≥ 10` | **1 / 36 = 3 %** |
| Demo-panel binders discarded by the `DAI ≥ 10` gate | **36 / 40** (incl. BRAF V600E, KRAS G12V/D/A, KIT D816V) |
| Self-similarity yield: applied first vs after the binding screen | **13 vs 0** — same 11 survivors |
| GTEx **v11** median-TPM file (current release, 2026-01-15) | **10,129,906 B**, 74,628 genes × 68 cols |
| NY-ESO-1 (`CTAG1B`) max median TPM across GTEx v11 | **0.065** — *fails* a TPM ≥ 1 inclusion filter |
| `SSX2` / `MAGEA1` / `TTN` max median TPM | 0.141 / 10.93 / 351.3 |
| TLStab weights shipped in-repo | **10 × 8,904,535 B = 89.0 MB** |
| TLStab stability fine-tuning data | 6,298 points, **10 HLA-A/B alleles, 9-mers only, no HLA-C** |

---

## 0. TL;DR — seven decisions

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
   **all 14** KRAS G12D windows on HLA-A\*11:01 fail the live `MIN_DAI = 10.0` gate, including a
   47 nM binder at presentation score 0.910. Name it, cite it (Duan 2014), **demote it from a gate to a
   score**, and add the published fix — **anchor-position annotation** (Xia 2023, *Sci Immunol*, which
   measured 7–41 % of candidates misclassified this way). §1.2, §1.5a, §5

4. **Expression: do NOT build the filter you were planning. Build its inverse.** A GTEx `TPM ≥ 1`
   inclusion gate **deletes NY-ESO-1** (CTAG1B, measured max median **0.065 TPM**) and SSX2. Silence in
   normal tissue is a cancer-testis *signature*, not a defect — so a normal-tissue atlas used as an
   inclusion gate selects **against** tumour specificity. Used in the safety direction it works
   beautifully: TTN at 351 TPM flags the exact off-target that killed patients in the MAGE-A3 TCR trial.
   Vendor **GTEx v11** (10,129,906 B — v10 and v8 are superseded), drop its 14 LCM columns, and never
   gate on it. §2

5. **TLStab is verified and worth adding — with one licence caveat that may be disqualifying.** CPU
   PyTorch, weights in-repo, a 3-layer MLP that will run anywhere. But the repository has **no LICENSE
   file at all**, which under default copyright means you have no redistribution right. That directly
   undercuts the project's own MIT-licence story. §3

6. **Filter order does not change your final shortlist. It completely changes the per-stage numbers you
   report.** Measured: self-similarity removes 13 candidates if applied first, and **0** if applied after
   the binding screen — same filter, same data, same 11 survivors. Report one declared gate order, or
   report each filter's independent yield. Do not mix. §4

7. **The similarity *scores* do not earn a gate — but be precise about which are disproven and which are
   merely untested.** Łuksza *foreignness* scores **AUC 0.516 — indistinguishable from random** on the
   largest independent benchmark, and the NeoFox self-similarity kernel **failed to replicate** (p = 0.24)
   at 9× the original sample size by a superset of its own authors. Richman *dissimilarity*, by contrast,
   was **never independently tested at all** — not by TESLA, not by that benchmark. "Unvalidated" is a
   weaker and more defensible claim than "disproven"; do not conflate them. And note the direction they
   were all validated *for*: **immunogenicity enrichment, never toxicity**. §1.6a

**The single biggest trap in this work:** treating a self-similarity filter as a safety guarantee. It is
not one. It removes one specific, cheap, mechanical reason a candidate is wrong. There is **no clinical
evidence** that self-similarity filtering has ever prevented an autoimmune event in a human; no trial has
run the counterfactual; and the sequence similarity of the MAGE-A3/titin pair that killed two patients is
**lower** than that of a randomly chosen peptide to its own nearest human neighbour — so no threshold
could have caught it without deleting every candidate. The filter that the leading clinical platform
actually deploys for autoimmunity risk is an **expression filter over wild-type genes in critical
organs** (§2.2), not a sequence filter. §1.6a, §1.7

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

#### Implementation note — index the proteome as packed integers, not seed lists

Measured against the in-progress `neofold/selfsim.py` on this machine:

| Approach | Memory | Build | Exact lookup | Full 1-mismatch scan |
|---|---|---|---|---|
| `blob.find()` + half-seed dict (current) | **547 MB RSS** for k=9 alone | 1.7 s | **4.1 ms** | 1.1 ms |
| **Packed uint64 + `np.searchsorted`** | **83 MB per length** | 2.8 s | **5–44 µs** | **0.6–0.7 ms** |

Both return identical answers (`VVGADGVGK` → not self, 3 one-mismatch neighbours:
`VVGAGGVGK`, `VVGARGVGK`, `VVGASGVGK`).

The trick: 20 amino acids fit in 5 bits, so a k-mer up to k=12 packs into a `uint64`. Encode the whole
proteome once with a vectorised shift-or, `np.unique` to sort-and-dedupe, then every query is a binary
search. The `*` protein separators encode as an invalid code and are masked out, which preserves the
"no peptide spans two proteins" guarantee.

```python
AA = "ACDEFGHIKLMNPQRSTVWY"
CODE = np.full(256, 255, dtype=np.uint8)
for i, a in enumerate(AA): CODE[ord(a)] = i

arr = CODE[np.frombuffer(blob.encode(), dtype=np.uint8)]
def pack(k):
    n = len(arr) - k + 1
    out = np.zeros(n, dtype=np.uint64); bad = np.zeros(n, dtype=bool)
    for j in range(k):
        s = arr[j:j+n]
        out = (out << np.uint64(5)) | s.astype(np.uint64)
        bad |= (s == 255)          # '*' separator -> drop this window
    return np.unique(out[~bad])    # sorted + deduped; searchsorted from here
```

Distinct k-mer counts and index sizes: k=8 → 10,304,716 (82.4 MB); k=9 → 10,409,122 (83.3 MB);
k=10 → 10,470,058 (83.8 MB); k=11 → 10,513,156 (84.1 MB). Build lazily per length; you rarely need all four.

The 4.1 ms exact lookup in the current implementation is `str.find` scanning 11.4 MB linearly. At 1,890
candidates that is ~8 s per run for the gate alone — tolerable now, but it scales with the VCF, and the
packed index removes it for free. The 547 MB figure is the bigger concern: the half-length seed is a
**4-mer**, which partitions 11.4 M positions into only 160 K buckets, so the index is really 11.4 M Python
ints in lists. That will not coexist comfortably with MHCflurry and Boltz-2 on the same box.

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

**Measured on your own demo panel.** `Candidate.mut_offset` already gives the mutation's position within
each window, so this cross-tabulation cost nothing. Of the 1,890 candidates on HLA-A\*11:01, 40 are
predicted binders (presentation ≥ 0.10 and ≤ 500 nM). Classifying each by whether the mutation sits at an
anchor (P2 or PΩ) or faces the TCR:

*(Measured against the **live** `MIN_DAI = 10.0` in `neofold/screen.py`. The earlier `MIN_FOLD_CHANGE = 2.0`
gave 4/4 anchor and 7/36 TCR-facing; raising the bar to 10 makes the asymmetry worse, not better.)*

| Binders, by mutation position | n | pass `DAI ≥ 10` | **discarded by the gate** |
|---|---|---|---|
| **anchor** (P2 / PΩ) | 4 | **3 (75 %)** | 1 |
| **TCR-facing** | 36 | **1 (3 %)** | **35** |

**The DAI gate is, empirically, an "anchor mutations only" filter.** It keeps three of four anchor-mutation
binders and rejects **35 of 36** TCR-facing ones. That is not a side effect — it is exactly what Duan
designed DAI to detect, working as specified, being used for the wrong job. Overall it leaves
**4 of 40 predicted binders** standing.

The discarded binders are a roll-call of the canonical actionable drivers:

```
KRAS G12V    VVVGAVGVGK   P6    35.8 nM  pres=0.959  DAI=1.14   DISCARDED
BRAF L733W   SASEPSWNR    P7    62.5 nM  pres=0.943  DAI=0.77   DISCARDED
KRAS G12V    VVGAVGVGK    P5    42.8 nM  pres=0.912  DAI=1.29   DISCARDED
KRAS G12D    VVVGADGVGK   P6    47.0 nM  pres=0.910  DAI=0.87   DISCARDED
EGFR L122Y   AVYSNYDANK   P3    31.3 nM  pres=0.867  DAI=1.12   DISCARDED
KRAS G12A    VVVGAAGVGK   P6    37.5 nM  pres=0.865  DAI=1.09   DISCARDED
BRAF V600E   KIGDFGLATEK  P10   52.9 nM  pres=0.857  DAI=1.05   DISCARDED
KIT  D816V   VIKNDSNYVVK  P1   121.2 nM  pres=0.852  DAI=8.67   DISCARDED  <- misses by 1.33
```

That last row is worth staring at: `KIT D816V` at DAI 8.67 is discarded and an otherwise identical
candidate at 10.01 is kept. Whatever the literature says about where the empirical DAI distribution sits,
a hard cut through a continuous, noisy, allele-dependent quantity manufactures exactly this kind of
arbitrary boundary. That is an argument for ranking, not for a better threshold.

**Losing BRAF V600E and EGFR L858R** — at 53 nM / 0.857 and 48 nM / 0.850 — is not a defensible outcome
for a neoantigen prioritisation tool.

**⚠ One contrary data point, stated honestly.** TESLA evaluated *mutational position* as one of five
candidate features and reported that *"neither peptide hydrophobicity nor mutational position was found to
be important for optimal filtering"* — its optimal filter used only affinity, abundance and stability.
That is a real tension with Xia 2023 and with the table above, and you should not pretend otherwise.

The reconciliation that survives both results: **anchor position is not useful as a *presentation* filter
(TESLA's question), but it is useful for deciding whether a low agretopicity value means anything
(Xia's question).** The two papers tested different things. And TESLA supports the same bottom line from
the other direction — verbatim, submissions that prioritised *"agretopicity … without accounting for
presentation, either had no difference in performance or performed worse."* Both point to:
**presentation first, agretopicity as a score, anchor status as the annotation that explains a low score.**
Neither supports agretopicity as a gate.

⚠️ **Do not quote the 88 % (35/36 TCR-facing) as a population rate.** `tumor_variants_large.vcf` is a curated
hotspot-driver panel and is heavily enriched for exactly this class. The honest population figure is
Xia 2023's **7–41 % across 923 tumour samples**. Report the 88 % as what it is: the effect on *this*
demo panel, where it happens to be severe because hotspot drivers are disproportionately TCR-facing.

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

**Where to get allele-specific anchor data, offline.** Two options, both redistributable:
- `https://github.com/griffithlab/anchor_huiming_etal_2023` — **MIT licensed**, with a `Datasets/` folder
  holding the normalized anchor scores from the paper (also in its supplementary materials). Note the
  README's caveat: per-allele/per-length weight *tables* are produced by running their workflow; the
  repo ships normalized scores plus the seed dataset rather than a finished lookup table.
- The `pvactools` pip package bundles the per-allele/per-length anchor weights it uses for pVACview's
  anchor heatmap. Extracting that table is the fastest path to a vendored lookup.

**Start with the P2/PΩ default.** It is right for HLA-A\*11:01 and most class I alleles, it needs no
extra data, and it already produces the result in the table above. Upgrade to allele-specific weights
only if you have time; the finding does not depend on it.

Ship `anchor_status` in `as_dict()` and use it to explain the tier in the UI. A candidate with
DAI ≈ 1 **and** `anchor_status == "TCR-facing"` is not a weak candidate — it is a different, equally valid
mechanism, and the interface should say so rather than burying it in `"not tumour-specific"`.

### 1.6a Published similarity metrics for TCR cross-reactivity risk — and how well they hold up

**Short answer: they exist, they are cheap to implement, and the independent evidence for them is weak.
Compute them as annotations. Do not gate on them, and do not present them as safety controls.**

#### The formulas, precisely

**Łuksza 2017 "foreignness" / recognition probability R** (*Nature* 551:517–520, doi `10.1038/nature24473`):

```
S    = SUM over IEDB epitopes e of  exp[ -k * (a - |s,e|) ]
R(s) = S / (1 + S)                      # the "1" is the unbound state

a = 26.0          k = 4.86936           # code values; the paper rounds k to 4.87
|s,e| = BLOSUM62 local alignment score, gap-open 11, gap-extend 1
```

Three things a literal reading of the paper will not reproduce:
- **The alignment is effectively gapless.** BLAST HSPs containing `-` are discarded *before* rescoring; the
  surviving ungapped segments are then re-scored with a *gapped* aligner. Paper says "gapless", code says
  11/1 — both are true, in that order.
- **Quality is `A × R × w`, not `A × R`.** The reference code multiplies by a binary hydrophobicity weight
  `w` that zeroes out neoantigens whose wild-type residue at an anchor position (2 or 9) is not hydrophobic.
- **`k = 4.86936` makes R a near-step function.** One BLOSUM unit changes R by ~e^4.87 ≈ **130×**.
  R is ~0 below score 25 and ~1 above 27. Score fidelity is load-bearing; there is no useful gradient.

**Richman 2019 "dissimilarity" D** (*Cell Systems* 9:375–382.e4, doi `10.1016/j.cels.2019.08.009`) reuses
the same partition function and **inverts** it:

```
S    = SUM over self-proteome BLAST hits h of  exp[ -k * (a - |s,h|) ]
D(s) = 1 - S / (1 + S)

k = 4.86936       a = 32     <-- NOT 26; re-derived from mean self-alignment scores
reference = Ensembl GRCh38 release 90   <-- NOT UniProt
threshold "high dissimilarity" = D > 0.75   (a "natural break", explicitly not optimised)
no BLAST hits at all -> D = 1
```

**Bjerregaard 2017 / NeoFox `Selfsimilarity_conserved_binder`** (*Front Immunol* 8:1566,
doi `10.3389/fimmu.2017.01566`) is a different quantity entirely — it compares the mutant peptide to
**its own wild-type**, not to the proteome:

```
K1(x,y)    = BLOSUM62-2(x,y) ^ beta            beta = 0.11387
K2_k(u,v)  = PRODUCT over positions of K1
K3(f,g)    = SUM over all k, all length-k substrings of f and g, of K2_k
K_hat3     = K3(f,g) / sqrt( K3(f,f) * K3(g,g) )        in (0, 1]
```

⚠ **`BLOSUM62-2` is the odds-ratio matrix `Q(x,y)/(p(x)p(y))`, not standard BLOSUM62.** All entries are
strictly positive, which is what makes the fractional exponent defined. Loading Biopython's integer
BLOSUM62 and raising it to a fractional power produces garbage — this is the most common reimplementation
bug. `beta` was fitted by cross-validation on **HLA class II binding-affinity regression**, and traces to
a **2012 arXiv preprint that was never peer reviewed** (arXiv:1205.6031).

#### The validation record — read this before you build any of it

| Finding | Source |
|---|---|
| **Foreignness score alone: AUC 0.516 — "performs similarly to random predictions"** across three evaluation sets, 3,033 neo-epitope–HLA pairs. Verbatim, verified against the full text. | Wan et al. 2024, *NAR Cancer* 6:zcae002, doi `10.1093/narcan/zcae002` |
| Even where foreignness *was* retained as a model feature, it *"only accounts for **1.7 % of feature importances** … ranking at the **bottom five least important features**, along with the amino acids cysteine, histidine, asparagine and tryptophan"* | ibid. |
| **TESLA never tested dissimilarity-to-self-proteome at all.** Its foreignness result rests on **12 immunogenic vs 17 non-immunogenic** pMHC, with foreignness *pooled* with agretopicity into one "recognition" variable rather than shown independently significant | Wells et al. 2020, *Cell* 183:818–834.e13, doi `10.1016/j.cell.2020.09.015` |
| TESLA, verbatim: *"submissions that explicitly prioritized peptide foreignness…, agretopicity…, or both…, **without accounting for presentation, either had no difference in performance or performed worse**"* | ibid. |
| Bjerregaard's own conclusion: *"self-similarity in general is a **relatively poor predictor** for peptide immunogenicity"* — AUC 0.65 on a post-hoc subgroup of ~25 positives, where NetMHCpan EL %Rank scored **0.72** on the same data | Bjerregaard 2017 |
| **Failed to replicate** on 467 positives (9× the original) by a superset of the original authors: `SelfSim p = 0.24`, not significant overall or within either subgroup | Borch et al. 2024, *Front Immunol* 15:1360281, doi `10.3389/fimmu.2024.1360281` |
| Dissimilarity is **not monotonic**: thymic *positive* selection is self-driven, so maximally dissimilar peptides have **no available TCRs**. The true relationship is an inverted U | Koncz et al. 2021, *PNAS* 118:e2100542118, doi `10.1073/pnas.2100542118` |
| 12 common self-similarity measures show *"remarkably low consistency"* with each other; BLOSUM-based scores partly measure **HLA restriction**, because anchor residues dominate the sum | Koncz et al. 2024, *PNAS* 121:e2309674121, doi `10.1073/pnas.2309674121` |
| Neither Łuksza model has been externally validated by an unaffiliated group; the 2022 parameters were fitted on the same lab's earlier cohort | — |

**Two practical traps if you build these anyway:**

- **The reference set is not stable.** Łuksza's 2017 IEDB set has 2,558 epitopes (28 of them *Homo sapiens*,
  so "foreignness" is not strictly non-self). The 2022 set shipped with `NeoantigenEditing` has 4,103, of
  which **973 (23.7 %) are SARS-CoV-2** — an artifact of when it was downloaded. R shifts by **four to five
  orders of magnitude** between the two. **Pin and version your reference set** or the numbers are
  meaningless across runs.
- **antigen.garnish's licence is restrictive**, despite the paper calling it open source — it forbids
  distribution for commercial purposes and requires distribution through the original authors.
  **Reimplement from the formulas above rather than vendoring it.** The formulas are short and published.

#### Is there any evidence that self-similarity filtering prevents autoimmunity in humans?

**No. None. This is the honest answer and it should be in the write-up.**

- **No trial has ever run the counterfactual.** There is no unfiltered comparator arm anywhere in the
  literature, and no trial was designed or powered to test a self-similarity safety hypothesis.
- **None of the landmark vaccine trials used a sequence self-similarity filter** — not Ott 2017 (NeoVax),
  not Hu 2021, not Rojas 2023 (autogene cevumeran). No autoimmunity attributable to self-cross-reactive
  neoepitopes was reported in any of them.
- **The one large randomised dataset bounds the problem.** In KEYNOTE-942 (Weber et al. 2024, *Lancet*
  403:632–644, doi `10.1016/S0140-6736(23)02268-7`), immune-mediated adverse events occurred in
  **36 % (37/107)** of the vaccine + pembrolizumab arm versus **36 % (18/50)** on pembrolizumab alone.
  Adding ~34 personalised neoantigens produced no detectable increase.
- **What the leading clinical platform actually does.** The Genentech IMCODE001 protocol (NCT03815058)
  calls the risk "**Theoretically**", and the mitigation it deploys is *"a database that provides
  comprehensive information about expression levels of respective wild-type genes in healthy tissues…
  Mutations occurring in proteins with a possible higher auto-immunity risk in critical organs are
  filtered out."* **That is an expression filter over wild-type genes in critical organs — not a
  sequence-similarity filter.** It is precisely the design recommended in §2.2.

#### The MAGE-A3 / titin case — why sequence similarity could not have caught it

The canonical cross-reactivity disaster: an affinity-enhanced HLA-A\*01 MAGE-A3 TCR killed the first two
patients by cardiogenic shock (Linette et al. 2013, *Blood* 122:863–871, doi `10.1182/blood-2013-03-490565`),
via titin (Cameron et al. 2013, *Sci Transl Med* 5:197ra103, doi `10.1126/scitranslmed.3006034`).

```
MAGE-A3 : E V D P I G H L Y
Titin   : E S D P I V A Q Y      5/9 identity, BLOSUM62 ungapped score = 20
```

Scored against all ~11.25 M human 9-mers, **titin ranks ~1,003rd** — a thousand human peptides score
*better*. And the decisive number: for random composition-matched 9-mers, **every one** has a best
self-match scoring **≥ 29 (median 34)**. The MAGE-A3/titin pair scored **20** — *less* similar than an
arbitrary peptide is to its own nearest human neighbour. **A threshold loose enough to flag titin flags
100 % of all peptides.**

This converges exactly with the measurement in §1.5: across 20,000 simulated single-substitution
neoepitopes, the BLOSUM62 score against their own wild-type has **minimum 28, median 40**. Every SNV
neoepitope is more self-similar to a real self peptide than MAGE-A3 was to titin. **Sensitivity and
false-negative cost are the same dial, and it has no usable setting.**

*(Two honest qualifications. First, CrossDome (Fonseca et al. 2023, *Front Immunol* 14:1142573,
doi `10.3389/fimmu.2023.1142573`) does rank titin 27th of ~36,000 — improving to 6th with TCR-contact
weighting — by restricting to the HLA-matched **measured immunopeptidome** rather than the raw proteome.
So the failure is specific to unweighted proteome-wide BLOSUM scanning, which is exactly what neoantigen
pipelines do. Second, the other fatal case cuts the other way: the MAGE-A12 cross-reactivity that caused
two neurological deaths (Morgan et al. 2013, *J Immunother* 36:133–151, doi `10.1097/CJI.0b013e3182829903`)
sits at **rank 3** in a proteome scan and was trivially findable — that was an **expression-atlas failure**,
not a sequence-similarity failure.)*

#### The distinction that actually justifies "annotate, don't gate"

This is stronger ground than "the metrics are weak", and it is the framing to use:

> Every one of these metrics was validated for **immunogenicity enrichment** — "prefer dissimilar/foreign,
> they are more immunogenic". **None was validated for toxicity** — "exclude similar, they are dangerous".
> Those are different claims, and because both are computed from the *same BLOSUM alignment*, the slippage
> between them is invisible in the code. Only the first has any human correlative support.

And note what the field's own best-developed model does with near-self information. Łuksza 2022
(*Nature* 606:389–395, doi `10.1038/s41586-022-04735-9`) defines quality as

```
quality = ( w * logC + (1-w) * logA ) * R        w = 0.22402192838740312
logC = a distance between the mutant peptide and ITS OWN WILD-TYPE,
       from a 20x20 substitution matrix fitted to measured TCR activation data,
       with per-position weights (heaviest at P5-P7, lightest at the termini)
```

`logC` is precisely a near-self measure — and it enters as a **graded, weighted, positive contributor to a
continuous score**, never as a gate. "Near-self is informative" is defensible. "Near-self should gate" is
not. That is exactly the position recommended here, stated in the field's own vocabulary.

*(Note the position weights: P5–P7 heaviest, termini lightest. That is the same anchor-vs-TCR-facing
insight as §1.5a, arrived at independently from TCR activation measurements rather than from structure.)*

#### What to actually build

1. **Keep the exact-match gate from §1.5.** It is not a similarity metric; it is a category check, and it
   needs no validation literature because it is definitional.
2. **Compute R and D as annotations if you want them**, reimplemented from the formulas above (not
   vendored), with the reference set pinned and versioned in `PROVENANCE.txt`. Justify them on
   **immunogenicity-enrichment** grounds — where the correlative human data actually are — and never as a
   safety control. If you cite their status, be precise: *foreignness* has been tested and performs at
   chance; *dissimilarity* has never been independently tested. Those are different sentences.
3. **If you want a real safety filter, build the two things with actual support:** wild-type gene
   expression in critical normal tissues (§2.2 — what the clinical platforms actually deploy), and, if you
   ever extend it, similarity to the **measured** benign immunopeptidome (HLA Ligand Atlas, Marcu et al.
   2021, *JITC* 9:e002071, doi `10.1136/jitc-2020-002071`) with TCR-contact-position weighting.
4. **Do not implement the Bjerregaard/NeoFox kernel.** It failed to replicate at 9× the original sample
   size, its hyperparameter comes from an unrelated class-II regression, its threshold was a median split
   on the discovery set, and its numerical range on SNV data is a near-constant ~[0.87, 1.00].

### 1.7 What Filter 1 does NOT establish

Write these into the code as docstrings and into the UI as caveats:

- **It does not establish immunogenicity.** Absence from the proteome removes one reason a candidate would
  fail. It supplies no reason it would succeed.
- **It does not establish safety, and the evidence gap is total.** No trial has ever run the
  counterfactual — there is no unfiltered comparator arm anywhere in the literature. None of the landmark
  vaccine trials (Ott 2017, Hu 2021, Rojas 2023) used a sequence self-similarity filter at all. In the
  randomised KEYNOTE-942, immune-mediated AEs were **36 % with the vaccine vs 36 % without**. The leading
  clinical platform's own protocol calls the risk "*Theoretically*" and mitigates it with a **wild-type
  expression filter over critical organs, not a sequence filter**. Self-similarity filtering is
  implemented here because it is cheap and mechanically sound, **not** because it is validated. §1.6a
- **It would not have caught the disasters it is invoked to prevent.** The MAGE-A3/titin pair scores
  **below** what an arbitrary 9-mer scores against its own nearest human neighbour (20 vs median 34), and
  titin ranks only ~1,003rd of 11.25 M human 9-mers. Any threshold that flags it flags everything. §1.6a
- **It does not model tolerance.** Real central tolerance depends on thymic expression level, AIRE
  regulation, and the affinity of the negative-selection step. A FASTA membership test models none of that.
- **It does not model TCR cross-reactivity.** Cross-reactivity is a property of the TCR-facing residues and
  of a particular TCR. Sequence identity across the whole 9-mer is a crude, position-blind proxy.
- **It does not cover what your pipeline cannot generate.** `neofold/variants.py` handles missense SNVs
  only; frameshift, indel, splice and fusion neoepitopes — which are the *most* foreign-to-self class, and
  therefore the class where this filter would matter least — are out of scope entirely.
- **It uses canonical sequences only.** Quantified: 0.05 % of "novel" calls flip when isoforms are included.

---

## 2. Filter 2 — gene expression

### 2.1 How published pipelines actually do it

The reference implementation is again pVACseq, and it filters on **two** things, not one:

| Flag | Default | What it tests |
|---|---|---|
| `--expn-val` | **1.0** | Gene *and* transcript expression cutoff |
| `--trna-vaf` | **0.25** | Tumour **RNA** variant allele fraction |
| `--tdna-vaf` | 0.25 | Tumour DNA VAF |
| `--normal-vaf` | 0.02 | Normal VAF (germline exclusion) |

**Three things about that `1.0` that are not in the docs.**

1. **It is unit-agnostic by construction.** The help string names no unit; the value is compared against
   whatever the upstream annotator wrote. VAtools' `vcf-expression-annotator` emits kallisto → `tpm`,
   StringTie → `TPM`, Cufflinks → `FPKM`. The pVACseq FAQ still says "FPKM" — legacy Cufflinks-era
   wording. A modern kallisto-fed run therefore filters at **1 TPM while its own FAQ says FPKM**.
   "The pVACtools threshold is TPM ≥ 1" is a thing people say; the tool never says it.
2. **`NA` passes the filter.** The filter short-circuits on unannotated fields, so a missing expression
   value is silently *kept*, not dropped. In pipelines that never populate the transcript field, the
   transcript half of the filter is a permanent no-op and the effective rule is gene-level only.
   If you copy this design, copy it deliberately rather than by accident.
3. **The stronger filter is `--trna-vaf`, not `--expn-val`.** Gene-level expression asks "is this gene
   on?". RNA VAF asks "is the *mutant allele* actually transcribed?" — the question that matters, since a
   gene can be well expressed while the mutant allele is silenced or lost. **We can do neither.**

**On "TPM ≥ 1" — there is no canonical derivation, and it is not even GTEx's number.**

- **Wagner, Kin & Lynch 2012** (*Theory Biosci* 131:281–285, doi `10.1007/s12064-012-0162-3`) defines the
  TPM *unit*. It proposes no detection threshold.
- **GTEx's own pipeline uses TPM ≥ 0.1**, not 1 — and pairs it with a read-count criterion
  (`tpm_threshold=0.1`, `count_threshold=6`, each in ≥20 % of samples) precisely because TPM alone is
  unreliable at low abundance. Ten-fold lower than the pipeline convention.
- **HPA is the closest citable source for "≥ 1"**, and is explicit that it is a chosen convention: a
  cutoff of **1 nTPM** as the limit of detection. Note that is *nTPM* (TMM-normalised), not raw TPM.
- The entire published justification in the neoantigen literature traces to a parenthetical illustration
  in Hundal et al. 2016 — *"is the gene expressed at a reasonably high level (for example, FPKM > 1)"* —
  an example that hardened into a default.

**Cite HPA if you need a citation, and say plainly that it is convention.** Anyone claiming TPM ≥ 1 is
derived is overclaiming.

**Cross-tool reality check.** Four tools converge on the number "1" while meaning four different quantities:

| Tool | Cutoff | Units | Level |
|---|---|---|---|
| pVACseq | `--expn-val` 1.0 | undefined (annotator-dependent) | gene + transcript |
| nextNEOpi (standard / relaxed) | 1 / 2 | gene TPM | gene |
| TSNAD v2 | `> 1` hardcoded | FPKM | gene |
| antigen.garnish | `min_counts = 1` | estimated read counts | transcript |
| **Vaxrank / isovar** | `min-alt-rna-reads = 3` | **raw reads at the variant** | **allele-specific** |
| MuPeXI | none — `tanh(expr+0.1)` weight | — | transcript |
| NeoPredPipe, NeoFox | none (annotation only) | — | gene |
| ScanNeo, INTEGRATE-Neo | none — calls variants *from* RNA | implicit | — |

**Vaxrank's design note is the load-bearing critique**, and it applies directly to what you are
considering: it uses raw read counts rather than a normalised measure *"since these scoring criteria are
not meant to be compared between patient samples"*, because bulk abundance *"would potentially
overestimate how much of a mutant protein is being made"* — all the reads at a locus can be wild-type.
**Bulk TPM cannot see allele-specific expression.** A population median sees it even less.

*(Correction worth noting if you read NeoFox's docs: its expression fallback imputes from **TCGA** medians
for the tumour entity, not from GTEx. It provides no normal-tissue baseline at all.)*

**What the clinical trials actually did.** None of the landmark personalised-vaccine trials applied a
numeric TPM gate — they had patient RNA-seq and used it per-variant, qualitatively:
Ott 2017 (*Nature* 547:217–221, doi `10.1038/nature22991`) used TPM to rank and display, not to gate;
Keskin 2019 (*Nature* 565:234–239, doi `10.1038/s41586-018-0792-9`) states expression was "confirmed by
tumour RNA-seq"; Sahin 2017 (*Nature* 547:222–226, doi `10.1038/nature23003`) used RPKM and
"expressed non-synonymous mutations"; Hu 2021 (*Nat Med* 27:515–525, doi `10.1038/s41591-020-01206-4`)
has numeric thresholds only for *sample QC*. **Not one of them used a population median for anything.**
That is the fact most relevant to your situation, and it should be stated in the write-up.

### 2.2 The fallback — and the reframe that makes it defensible

**State this plainly and never soften it: a population median is not your patient's expression.** A GTEx
median TPM is the middle of a distribution over a few hundred *post-mortem normal* donors. It carries no
information about whether this patient's tumour transcribes this allele. Invisible to it: intra-tumour
heterogeneity, allele-specific expression, loss of the wild-type allele, copy-number effects, and the
transcriptional rewiring that is the defining feature of the tissue you actually care about.

| Source | The question it can answer | The question it cannot |
|---|---|---|
| **GTEx median TPM** | "Is this gene expressed in *normal* tissue X?" | Anything about the tumour |
| **HPA consensus nTPM** | Same, with a different normalisation | Same |
| **TCGA tumour-type medians** | "Is this gene expressed in this *tumour type*, typically?" | Anything about *this* tumour |

**The reframe — and the measurement that forces it.** I tested a GTEx `max median TPM ≥ 1` inclusion
filter against the canonical cancer-testis antigens, directly on the v11 file:

```
CTAG1B (NY-ESO-1)   max median TPM = 0.0648    passes TPM>=1 ?  FALSE
SSX2                max median TPM = 0.1407    passes TPM>=1 ?  FALSE
MAGEA1              max median TPM = 10.93     passes           TRUE
TTN                 max median TPM = 351.3     passes           TRUE
```

**NY-ESO-1 — arguably the most clinically validated tumour antigen in immunotherapy — fails a GTEx
TPM ≥ 1 filter.** So does SSX2.

This is not a badly chosen threshold; **the direction of use is wrong**. Silence in normal tissue is the
*defining property* of a good tumour antigen, not a disqualifier. A normal-tissue expression atlas used as
an inclusion gate selects **against** tumour specificity. It is the same failure shape as the DAI gate in
§1.5a — a filter that is correct on its own terms, used for a job it cannot do.

It is also barely selective in that direction: `max ≥ 1` retains **93.5 %** of protein-coding genes
(17,949 / 19,192). It removes 6.5 %, and that 6.5 % is enriched for exactly the genes you want.

**So invert it. GTEx answers the safety question far better than the expression question**, and that
direction validates cleanly against real clinical toxicities:

```
TTN      351.3 TPM  (64.4 in Heart_Left_Ventricle)  -- the MAGE-A3 TCR cardiac deaths
CEACAM5  243.7 TPM  Colon_Transverse                -- severe colitis
ERBB2    131.1 TPM  Nerve_Tibial                    -- fatal HER2 CAR-T lung toxicity
MSLN      86.3 TPM  Lung
MLANA     10.7 TPM  Skin                            -- vitiligo / uveitis
MAGEA3     0.00 TPM Heart                           -- target itself was clean
```

Every gene implicated in a real clinical toxicity lights up. And MAGEA3 correctly reads as silent — the
MAGE-A3 TCR deaths were **off-target cross-reactivity to TTN**, which GTEx flags loudly. This is what
population medians are actually good for, and it pairs naturally with the self-similarity filter in §1.

**Build the safety direction. Do not build the inclusion gate.**

**This is not a novel idea — it is what the leading clinical platform actually does.** The Genentech
IMCODE001 protocol (NCT03815058) describes its autoimmunity risk mitigation as *"a database that provides
comprehensive information about expression levels of respective wild-type genes in healthy tissues…
Mutations occurring in proteins with a possible higher auto-immunity risk in critical organs are filtered
out."* A wild-type expression filter over critical organs — not a sequence-similarity filter. If you build
this, you are matching clinical practice, and you can say so. (The same protocol calls the underlying
cross-reactivity risk "**Theoretically**" — see §1.6a for why that hedge is well earned.)

### 2.3 Data sources — verified URLs and sizes

All `Content-Length` values verified by HTTP HEAD on 2026-09-24.

| File | URL | Size (bytes) | Verdict |
|---|---|---|---|
| **GTEx v11 gene median TPM** | `https://storage.googleapis.com/adult-gtex/bulk-gex/v11/rna-seq/GTEx_Analysis_2025-08-22_v11_RNASeQCv2.4.3_gene_median_tpm.gct.gz` | **10,129,906** (9.7 MB) | ✅ **use this — it is current** |
| GTEx v10 gene median TPM | `.../bulk-gex/v10/rna-seq/GTEx_Analysis_v10_RNASeQCv2.4.2_gene_median_tpm.gct.gz` | 8,846,936 (8.4 MB) | ❌ superseded |
| GTEx v8 gene median TPM | `.../bulk-gex/v8/rna-seq/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct.gz` | 6,952,331 (6.6 MB) | ❌ superseded |
| HPA consensus tissue RNA | `https://www.proteinatlas.org/download/tsv/rna_tissue_consensus.tsv.zip` | **5,293,680** (5.0 MB) | ⚠️ **not independent** — see below |
| **MANE Select v1.5 summary** (ID mapping) | `https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/current/MANE.GRCh38.v1.5.summary.txt.gz` | **1,115,288** (1.1 MB) | ✅ **the mapping spine** |
| HGNC complete set (alias/prev symbols) | `https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt` | 16,940,274 (16.2 MB) | 🔶 only if you must resolve aliases |

**Release drift matters here.** Verified by downloading each:

| Release | Genes × tissue cols | GENCODE | `_PAR_Y` rows | Bytes |
|---|---|---|---|---|
| v8 | 56,200 × 54 | v26 | 44 | 6,952,331 |
| v10 | 59,033 × 68 | v39 | 45 | 8,846,936 |
| **v11** | **74,628 × 68** | **v47** | **0** | **10,129,906** |

v11 was published 2026-01-15. I confirmed the header independently: `74628  68`, first columns
`Name` (versioned ENSG), `Description` (HGNC symbol), then tissues starting `Adipose_Subcutaneous`.

Three traps in that table:

- ⚠️ **The 68 columns are 54 bulk tissues + 14 laser-capture-microdissection pilot columns.** Some LCM
  "medians" are over **2 samples** (`Liver - Portal Tract`), 3 (`Pancreas - Islets`), 8, 9…
  **Drop the 14 LCM columns.** A median of two donors is not a population baseline. That returns you to
  v8's 54 comparable bulk tissues.
- ⚠️ **Column naming changed between every release.** v8 → v10 changed the whole convention
  (`Adipose - Visceral (Omentum)` → `Adipose_Visceral_Omentum`). v10 → v11 changed exactly one column,
  a typo fix (`..._Lymphode_Aggregate` → `..._Lymphoid_Aggregate`). Anything keyed on that string breaks
  **silently**.
- ⚠️ **HPA consensus is partly derived from GTEx**, by HPA's own methods: the consensus nTPM is the
  **maximum** of the HPA and GTEx values. Using both is not two independent sources — it is
  double-counting, and HPA is the more permissive by construction. On the 19,697 shared genes the two
  disagree on "max ≥ 1" for **731 genes (3.7 %)**, and 609 of those are HPA-yes/GTEx-no. On the
  cancer-testis genes that matter most the discrepancy is ~100× (HPA calls CTAG1B 7.6 nTPM where GTEx
  says 0.065). Use HPA as a cross-check and say which one you reported.

There is **no smaller GTEx artifact**: the median file is the smallest in the bucket by an order of
magnitude, there is no transcript-level median file, and there is no plain-TSV alternative — GCT only.

**Licensing — one correction worth making loudly:**

| Source | Licence | Vendorable into a public MIT repo? |
|---|---|---|
| **HPA** | **CC BY 4.0** (it was CC BY-SA 3.0 only up to v21) | ✅ attribution only — **no share-alike**, contrary to what is widely assumed |
| HGNC | **CC0** | ✅ unconditionally |
| MANE / NCBI | US Gov public domain | ✅ |
| UniProt | CC BY 4.0 | ✅ |
| TCGA open-access | No restrictions; acknowledgment sentence expected | ✅ |
| **GTEx** | ⚠️ **No explicit licence.** NIH GDS policy, no DUA, no LICENSE file in the bucket | Yes in practice, but you are relying on "no stated restriction" rather than an affirmative grant |

GTEx is the **weakest** licence position of the set — mildly ironic, since it is the one everyone vendors.
Note also that HPA's CC BY does **not** launder the GTEx content inside it; their licence page explicitly
carves out third-party data.

**Recommendation:** vendor a **derived** table rather than the raw `.gct.gz`, and ship a `PROVENANCE.txt`
with the upstream URL, sha256 and licence for each. Protein-coding rows × 54 bulk tissues at 2 d.p. gzips
to about **2.0 MB** — 5× smaller than upstream, and it drops the 14 statistically worthless LCM columns,
which is a correctness win as well as a size win. Suggested vendored set, ~4 MB total:

```
gtex_v11_pc_54tissue_median_tpm.tsv.gz   ~2.0 MB   normal-tissue SAFETY filter
mane_v1.5_idmap.tsv.gz                   ~0.4 MB   identifier anchor
hpa_consensus_max_ntpm.tsv.gz            ~0.2 MB   cross-check only
PROVENANCE.txt                                     URLs + sha256 + licences
```

Attribution to include: GTEx (*Science* 369:1318–1330, doi `10.1126/science.aaz1776`) and
HPA (Uhlén et al. 2015, *Science* 347, doi `10.1126/science.1260419`). HGNC is CC0 and needs none.

**On TCGA tumour-type medians: no vendorable table exists.** Everything published is a per-sample matrix —
UCSC Xena PANCAN EB++ is 331 MB, the GDC TSV of the same data is 1.88 GB, Xena TOIL is 1.32 GB,
cBioPortal across 32 studies is 1.71 GB (and ships only z-scores, no medians). If you want tumour medians,
**derive them once offline and vendor the ~2 MB result** — legally fine, since a per-tumour-type median is
far more aggregated than the matrices already redistributed publicly. If you do: the tumour-type key in
Xena's phenotype file is `_primary_disease`, and you must **filter to `Primary Tumor`** first, or
`Solid Tissue Normal` and `Metastatic` samples will contaminate the medians.

### 2.4 Gene identifiers — and the pitfalls

**Key on unversioned Ensembl gene ID (`ENSG…`), with HGNC symbol as a fallback.** Use the MANE summary as
the mapping spine — it is 1.1 MB, has **19,437 rows**, and ties every field together:

```
#NCBI_GeneID  Ensembl_Gene        HGNC_ID  symbol  RefSeq_nuc  RefSeq_prot  Ensembl_nuc  Ensembl_prot  MANE_status …
GeneID:1      ENSG00000121410.14  HGNC:5   A1BG    NM_130786.4 NP_570602.2  ENST00000263100.8  ENSP00000263100.2  MANE Select
```

The pitfalls, with measured magnitudes rather than warnings:

- **Version suffixes are not cosmetic.** Among genes shared between releases, the suffix changed for
  **41.4 % (22,832 / 55,216)** from v8 → v10 and **21.0 % (11,880 / 56,474)** from v10 → v11. A versioned
  exact-string join silently drops two-fifths of your genes — not an error, a **silent partial join**.
  **Strip at the first `.` before joining.**
- **Stable IDs still get retired.** Stripping the version is necessary but not sufficient: WASH7P was
  `ENSG00000227232` in v8/v10 and is `ENSG00000310526` in v11. 2,514 v10 genes vanish in v11; 18,154 are new.
- **`_PAR_Y` duplicates.** v8 has 44, v10 has 45, **v11 has 0** (GENCODE v47 dropped them). In v10 they look
  like `ENSG00000182378.15_PAR_Y`; a naive `split('.')[0]` maps them onto the X copy and creates exactly
  **45 silent duplicate keys** (59,033 rows → 58,988 unique). Preserve the suffix as part of the key or drop
  those rows. If you pin v11, this problem does not exist.
- **Do not key on symbols.** In GTEx v11, **33,835 of 74,628 rows (45 %) have an ENSG in the symbol column**
  — no symbol at all. Plus 231 duplicated symbols and 732 rows named `Y_RNA`.
- **Alias symbols are the real hazard.** Measured on the 45,083 approved HGNC records: approved symbol → ENSG
  has **0 ambiguities** and ENSG → approved symbol has **3**. But **alias/previous symbols → ENSG has 1,466
  ambiguities**, and — decisively — **580 alias/previous symbols collide with a *different* gene's approved
  symbol.** `AMN`, `CAD`, `CCR9`, `ADAM23` and `ADCY3` are each simultaneously one gene's approved symbol and
  another gene's alias. **An alias lookup that runs before, or merges with, approved-symbol lookup will
  confidently return the wrong gene 580 different ways.**
- **The Excel corruption class.** `SEPT2` → `2-Sep`, `MARCH1` → `1-Mar`. HGNC renamed the worst offenders in
  2020 (`SEPTIN2`, `MARCHF1`, `MTARC1`), so you must handle both the corrupted forms and the pre/post-2020
  spellings. If any input ever touched a spreadsheet, assume this has happened — and note it is
  *unrecoverable* without the prev_symbol table.
- **Your own VCF already sidesteps most of this.** `tumor_variants_large.vcf` carries
  `GENE=KRAS;UNIPROT=P01116`, and `neofold/variants.py` keys on the **UniProt accession** — the cleanest
  identifier you have. Map UniProt → ENSG once via MANE and cache it.

**Do not panic at the headline join rate.** ENSG → HGNC looks alarming (v8 72.9 %, v10 69.6 %, **v11 54.1 %**)
but the decline is entirely GENCODE v47 adding ~18k unnamed non-coding loci. Restricted to protein-coding:

```
HGNC protein-coding genes with an ENSG : 19,254
  covered by GTEx v11 : 19,192  (99.7%)
  covered by HPA      : 19,215  (99.8%)
```

The unmapped 45 % is non-coding and pseudogene — irrelevant for neoantigens. Do not let that number drive a
design decision.

**Resolution order to implement:**

```
1. UniProt accession (what variants.py already uses)  ->  ENSG  via MANE summary
2. unversioned ENSG (strip /\.\d+$/, handle _PAR_Y)   ->  GTEx row        ~99.7% of protein-coding
3. retired-ID remap via a vendored ENSG-history table  (e.g. WASH7P)
4. APPROVED HGNC symbol -> ENSG                        (0 ambiguity)
5. alias / previous symbol -> ONLY IF THE HIT IS UNIQUE; a non-unique hit
   must resolve to UNMAPPED, never to a best guess       (580 collisions)
6. otherwise: expression = UNKNOWN
```

**Unmapped policy — and it differs by direction, deliberately.**

- **Expression (inclusion) direction: FAIL OPEN.** Annotate `expression_unknown` and let the candidate
  through to human review. Failing closed would delete candidates for *bookkeeping* reasons and record it as
  a biological finding. The asymmetry is the point: a silent identifier mismatch that quietly removes
  candidates while the pipeline reports success is unauditable, whereas an extra flagged candidate is caught
  by the binding screen and by review. **Fail-closed on a join failure makes your filter's stringency a
  secret function of your annotation version.**
- **Safety (off-tumour risk) direction: FAIL CLOSED.** If you cannot resolve the gene, you cannot assert the
  gene is *not* highly expressed in heart. Flag it `risk_unknown` and require review before it is promoted.

Log the unmapped rate either way; above a few percent, your mapping is broken, not the biology.

### 2.5 The rule to implement

```
ANNOTATE every candidate with:
    gtex_top_tissues  = the 3 normal tissues with the highest median TPM   <-- the PRIMARY use
    gtex_max_tpm      = max median TPM across the 54 BULK tissues (LCM columns dropped)
    gtex_tissue_tpm   = median TPM in the tumour's tissue of origin, if known
    expression_source = "GTEx v11 population median across normal donors -
                         NOT this patient's tumour RNA-seq"

FLAG (the defensible direction - off-tumour safety):
    gtex_max_tpm >= 100 in any normal tissue  -> "on-target/off-tumour risk: {tissue} @ {tpm} TPM"
    gene unresolvable                          -> "risk_unknown" (FAIL CLOSED, needs review)

TIER (weak, advisory only - never a hard drop):
    gtex_max_tpm < 1 in every bulk tissue      -> "not detected in normal tissue"
        !! DO NOT deprioritise on this alone. NY-ESO-1 (CTAG1B) sits at 0.065 TPM.
           Low normal-tissue expression is a cancer-testis SIGNATURE, not a defect.
    gene unresolvable                          -> "expression_unknown" (FAIL OPEN)

NO GATE. Expression never removes a candidate from the funnel in this pipeline,
because we do not have the measurement that would justify removing one.
```

On the 6-gene demo panel (BRAF, EGFR, KIT, KRAS, PIK3CA, TP53) this filter is a **no-op** — every one is a
well-expressed driver. Say that out loud rather than showing a filter that appears to do nothing: its value
appears on a genome-wide VCF, and on the demo it exists to demonstrate the annotation and the honesty
statement, not to cut the funnel.

### 2.6 What Filter 2 does NOT establish

- **It is not the patient's expression, and no amount of processing makes it so.** This is the single
  sentence that must appear in the UI next to the number.
- **It does not establish that the mutant allele is transcribed.** That needs tumour RNA-seq variant
  read support (`--trna-vaf`), which is a strictly stronger and different measurement.
- **It does not establish that the protein is made, degraded by the proteasome, transported by TAP, or
  loaded onto MHC.** mRNA abundance is several causal steps upstream of presentation.
- **A low GTEx value is not evidence of tumour silence.** For cancer-testis antigens it is evidence of the
  *opposite* of what a naive filter would conclude — measured: NY-ESO-1 at 0.065 TPM.
- **A median hides the tail.** A gene with median 0 can be highly expressed in a minority of donors — and
  that minority is a patient. This matters most in the *safety* direction, where the tail is the risk.
- **GTEx donors are post-mortem**, with known tissue-specific RNA degradation and stress-response artefacts.
- **Bulk medians hide cell-type structure.** A gene that is off in bulk pancreas can be on in islets.
- **Normal-tissue medians say nothing about tumour-specific splicing, fusions or retained introns** — the
  neoepitope sources your pipeline does not model anyway (`neofold/variants.py` is missense-only).

**The two sentences to put in the UI, verbatim:**

> ✅ Defensible: *"Candidate is in a gene with median TPM ≥ X in normal tissue T (GTEx v11), indicating
> on-target/off-tumour risk."*
> ❌ Not defensible: *"Candidate is expressed in this patient's tumour."*

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
- **TESLA put binding stability in its three-feature presentation filter, with a threshold.** This is the
  strongest external justification available for adding it, and it is far better evidence than anything
  supporting the similarity metrics in §1.6a. Wells et al. 2020 (*Cell* 183:818–834.e13,
  doi `10.1016/j.cell.2020.09.015`) found the optimal filter over 608 assayed peptides was:

  ```
  MHC binding affinity  <  34 nM
  tumour abundance      >  33 TPM
  pMHC binding stability > 1.4 h        <-- this is what TLStab predicts
  ```

  which removed **93 % of non-immunogenic peptides while keeping 55 % of immunogenic ones**
  (p = 3.7 × 10⁻⁸). Adding the recognition features took it to 98 % filtered at precision > 0.70.
  **Use `> 1.4 h` as your stability threshold and cite TESLA for it** — with the §3.1a caveat that
  TLStab is out-of-distribution for HLA-C and for non-9-mers.
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
| 1 | **Expression / off-tumour-risk** annotation (gene-level dict lookup) | µs | **Never** — flag only (§2) |
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

| Epitope | Allele | MT | WT | MT nM | WT nM | DAI (fold) | Verdict under `MIN_DAI = 10.0` |
|---|---|---|---|---|---|---|---|
| Tran 2016 NEJM, TIL regression | HLA-C\*08:02 | `GADGVGKSA` | `GAGGVGKSA` | 74.1 | 3656.5 | **49.4×** | ✅ passes |
| Validated TCR-T target | HLA-A\*11:01 | `VVVGADGVGK` | `VVVGAGGVGK` | 47.0 | 40.8 | **0.87×** | ❌ **discarded** |
| same, 9-mer | HLA-A\*11:01 | `VVGADGVGK` | `VVGAGGVGK` | 81.6 | 55.3 | **0.68×** | ❌ **discarded** |

**All 14 KRAS G12D windows on HLA-A\*11:01 fail the `DAI >= 10` gate** — and they also failed the earlier
`fold_change >= 2.0` gate, so this is not an artefact of the threshold change. Two of them are strong
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
- [ ] Replace the half-seed dict with a packed-`uint64` + `np.searchsorted` index — measured 547 MB → 83 MB
      and 4.1 ms → 5–44 µs per exact lookup, identical answers (§1.5)
- [ ] Add `dai_log2` to `ScreenResult.as_dict()`; cite Duan 2014 and note the ratio-vs-difference drift
- [ ] Add `anchor_status` (anchor vs TCR-facing) from the mutation offset `peptide_windows` already returns
- [ ] Stop `fold_change` being an AND-gate in `triage()` — it currently outputs zero KRAS G12D candidates
      on HLA-A\*11:01 (§5)

**Filter 2 — expression**
- [ ] Vendor **GTEx v11** (not v10/v8), derived to protein-coding × **54 bulk tissues** — drop the 14 LCM columns
- [ ] Vendor `MANE.GRCh38.v1.5.summary.txt.gz` as the identifier spine; join UniProt → ENSG
- [ ] Strip ENSG version at the first `.`; handle/drop `_PAR_Y` (v11 has none)
- [ ] Never resolve a non-unique alias symbol — 580 collide with another gene's approved symbol
- [ ] **Build the off-tumour safety flag, not the inclusion gate** (NY-ESO-1 = 0.065 TPM)
- [ ] Fail **open** on unmapped for expression; fail **closed** on unmapped for safety
- [ ] Ship `PROVENANCE.txt` with URL + sha256 + licence (GTEx has *no* explicit licence; HPA is CC BY 4.0)

**Filter 3 — TLStab**
- [ ] Resolve the licence question before vendoring anything; install from upstream at setup time
- [ ] Install via pip, not `TLenv.yml` (the pinned `pytorch-cpu=2.0.0` channel build is not aarch64)
- [ ] Run with CWD = `TLStab/` (hardcoded relative weight paths)
- [ ] Report output as **hours**, and note the README/code contradiction
- [ ] Treat 0.0 and 68.97 h as saturation artefacts
- [ ] Use TESLA's **> 1.4 h** threshold and cite Wells 2020; flag HLA-C and non-9-mers as out-of-distribution

**Similarity scores (§1.6a) — optional, and only as annotations**
- [ ] Do **not** implement the Bjerregaard/NeoFox kernel (failed to replicate, p = 0.24 at 9× sample size)
- [ ] If you implement Łuksza R or Richman D: reimplement from the formulas, do **not** vendor
      antigen.garnish (restrictive licence); pin and version the IEDB / proteome reference in `PROVENANCE.txt`
- [ ] Never describe any of these as a safety control — justify on immunogenicity-enrichment grounds only

**Ordering**
- [ ] Annotate every candidate with every filter; gate only at exact-self and at top-k
- [ ] Report both the declared gate sequence and each filter's independent yield
- [ ] Demote `fold_change` / `MIN_DAI` from an AND-gate to a ranking score (§5)

---

## 7. What in this document is NOT verified

Everything in the ground-truth table at the top was computed in this session and can be re-run. The
literature claims were checked against primary sources — code, data files, or full text — wherever
possible. These specific points were **not** independently verified and should not be restated as fact:

- **Sahin 2017 (*Nature* 547:222–226) adverse-event profile and epitope-selection pipeline.** Paywalled and
  not in Europe PMC. The claim "no autoimmunity reported" rests on secondary sources for this trial only.
- **The circularity argument against Richman's AUC 0.85** — that the Chowell 2015 validation set's negative
  class is largely self peptides, so a dissimilarity-to-self metric is partly scoring the label — is an
  analytical reading, **not a published rebuttal**. No paper makes this criticism of Richman specifically.
- **The IEDB Calis 2013 exact weight vector and amino-acid scale** were not retrieved; pull them from the
  distributed source at `tools.iedb.org/immunogenicity/` if you implement it.
- **What the NeoFox correction (doi `10.1093/bioinformatics/btad763`) actually corrects** is unknown.
- **PRIME's packaging and ARM64 status** were not directly confirmed (README 404s on both branches).
- **NetTCR-2.2** has no peer-reviewed version found; Expitope could not be verified at all.
- **The 2,552 (paper) vs 2,558 (shipped file) IEDB epitope-count discrepancy** in Łuksza 2017 is unexplained.
- **The 54-bulk-vs-14-LCM GTEx column split and the HGNC ambiguity counts** in §2.3–2.4 were measured, but by
  a separate agent in this session rather than re-derived here; the GTEx v11 file size, dimensions and the
  NY-ESO-1 / SSX2 / MAGEA1 / TTN values **were** re-verified directly.

One process note: `neofold/selfsim.py`, `data/reference/`, and the `MIN_DAI` change in `neofold/screen.py`
appeared in the working tree **during** this research session, from a parallel session, and have since been
committed. The measurements in §1.5b and §1.5a were taken against that live code. If it has moved again,
re-run the scripts rather than trusting the numbers here.
