# Scientific audit — NeoFold Edge

**Date:** 2026-09-24
**Method:** every claim in `README.md`, `BUILD-GUIDE.md`, `app/main.py`, `app/static/`, `neofold/` and `tests/`
checked against primary literature, and — where the repo contains the data — **re-computed locally**.
Re-computed numbers are marked **[reproduced]**; numbers I could not reproduce from the repo are marked
**[unverifiable]**.

This document is adversarial on purpose. It is a list of things that are wrong, imprecise, or
overclaimed. It is not a summary of what works.

**Currency.** Audited against working-tree state at commit `1039f4c`. Work landed during the audit and is
already reflected: `neofold/selfsim.py` exists, and the `2×` fold-change threshold has been replaced by
**DAI ≥ 10** with a citation (Rech et al., *Cancer Immunol Res* 2018 / TESLA's agretopicity < 0.1) — so
§C2's recommendation is **already done**; §C1's naming guidance is partly done in `screen.py` but not in the
UI. **Everything in Tier 1 and Tier 2 of the fix list was still open at the time of writing** and I
re-checked each one against the working tree.

---

## 0. Verdict table

| # | Claim (as the project states it) | Verdict | One-line correction |
|---|---|---|---|
| **A. Terminology** |
| A1 | "neoantigen" used for a predicted-binding peptide | **IMPRECISE** | Use **candidate neoepitope** / **predicted binder** until a T-cell response is shown |
| A2 | "neoepitope" used for a predicted-binding peptide | **IMPRECISE** | An epitope is defined by recognition; nothing here shows recognition |
| A3 | presentation ≠ recognition ≠ immunogenicity are distinct steps | **CORRECT** | Keep it; it is one of the project's genuine strengths |
| A4 | "restricted by HLA-C\*08:02" | **CORRECT** | Correct usage — but only for the *published* epitopes, not for your predictions |
| A5 | "tumour-specific" applied to a peptide whose mutant binds better than WT | **WRONG** | That is *differential agretopicity*, not tumour specificity |
| A6 | 50 nM / 500 nM strong/weak binder cut-offs | **IMPRECISE (superseded)** | Real cut-offs; tool authors now advise %rank. On %rank the WT 10-mer is a **weak binder**, so "invisible" is an overclaim **[reproduced]** |
| A7 | wild-type peptide called "normal tissue" | **WRONG** | It is a self peptide / the germline counterpart. `GAGGVGKSA` is in 5 human proteins |
| **B. KRAS G12D case** |
| B1 | `GADGVGKSA` + `GADGVGKSAL` are HLA-C\*08:02-restricted G12D epitopes | **CORRECT** | Tran 2016 + Sim 2020 both support it |
| B2 | "PDB 6ULN is this complex with a patient-derived TCR" | **CORRECT but under-specified** | 6ULN = **TCR9d**, patient **3995**, from **Sim 2020** — not from Tran 2016 |
| B3 | "the patient-derived TCR α/β from Tran *NEJM* 2016" (§6E) | **WRONG** | The chains you folded are TCR9d (Sim 2020). CDR3β `CASSLGQTNYGYTF` **[reproduced]** |
| B4 | p3 Asp salt-bridges Arg156; impossible with WT Gly | **CORRECT but incomplete** | **Arg97** also contacts the same carboxylate; **Tyr99** H-bonds the p3 backbone |
| B5 | "HLA-C\*08:02 prefers Asp at p3 (Rasmussen 2014)" | **CORRECT, wrong emphasis + partly wrong citation** | P3-Asp is a **primary** anchor, not a preference. Elution data = **Di Marco 2017** |
| B6 | "p3" nomenclature | **CORRECT** | `p3` / `P3` / `PΩ` are all standard; be internally consistent |
| B7 | "KRAS 4B residues 10-18/10-19" | **WRONG (harmless here)** | You load P01116 canonical = **4A, 189 aa** **[reproduced]**. Register identical; the label is not |
| B8 | 6ULN crystal p3Asp–Arg156 = 2.73 Å | **CORRECT** **[reproduced]** | — |
| B9 | Boltz prediction reproduces it at "2.52 Å" | **IMPRECISE** | Repo model measures **2.58 Å** **[reproduced]** |
| **C. Screening logic** |
| C1 | MT-vs-WT differential is a real criterion | **CORRECT** | It is the differential agretopicity index (Duan 2014); say so, and say which direction you use |
| C2 | 2× fold-change threshold | **ARBITRARY (but conservative)** | Uncited. pVACtools ships this filter **off** (default 0); its documented floor is 1× |
| C3 | `presentation_score >= 0.10` | **WRONG (uncited)** | MHCflurry's own docs: *"there is no universal presentation-score threshold"* |
| C4 | `processing_score` reported without flanks | **IMPRECISE (missed, not broken)** | Correct model is auto-selected, but you *have* the flanks; costs ~3.3% PPV and the column is mislabelled |
| C5 | "35× stronger" for the 10-mer (§6B) | **WRONG (arithmetic)** | Correct value is **22.6×**; the guide compared a 10-mer to a 9-mer **[reproduced]** |
| C6 | Omitted: expression, clonality, TAP, stability | **SERIOUS** | **Gene expression** is the most damaging omission by a wide margin; TAP/cleavage the least |
| **D. Structure claims** |
| D1 | peptide backbone RMSD after MHC superposition | **CORRECT metric, overclaimed result** | Field standard; but PANDORA's median is 0.70 Å, so 0.509 Å is normal, not exceptional |
| D2 | per-chain CA RMSD for the TCR complex | **NON-STANDARD** | Use **DockQ**/CAPRI + CDR-loop RMSD; whole-chain RMSD is diluted by the easy framework |
| D3 | "the model knows recognition is harder" (ipTM 0.88 < 0.99) | **WRONG** | Your own WT ternary run scores the same **[reproduced]** |
| D4 | "0.486 Å" (README headline) | **[unverifiable]** | Repo reproduces **0.509 Å** and **0.560 Å**; tests pin 0.56 |
| D5 | "deviation highest at termini, lowest in the middle" | **WRONG** | Minimum is at **p2–p3**, rising monotonically to p9 **[reproduced]** |
| **E. MD** |
| E1 | ~1 ns is meaningful | **NO** | 100× below the field floor; replicate agreement at 1 ns is a known *undersampling* signature |
| E2 | "contact persistence" | **INVENTED NAME, FLAWED DEFINITION** | It is Q/fnat referenced to your own predicted pose, so a rigid wrong pose scores 1.0 |
| E3 | OBC2 implicit solvent under a salt-bridge claim | **WRONG TOOL FOR THIS CLAIM** | GB over-stabilises salt bridges by **3–4 kcal/mol**, at zero ionic strength by default |
| E4 | 10 ps restrained equilibration | **YES, laughably short** | Field uses 500 ps restrained heating; Knapp discards 10 ns |
| E5 | replicates are comparable | **WRONG (design flaw)** | Trajectories are **0.64–1.00 ns**, unequal across replicates **[reproduced]** |
| **Data provenance** |
| P1 | KIT D816V peptide `ICDFGLARV` shown as "tumour" | **WRONG — fatal for that panel** | It is an **exact self peptide** in ERK2/MAPK1 and NLK **[reproduced]** |
| P2 | demo VCF declares `##reference=GRCh38` | **WRONG** | The KIT row is a **GRCh37** coordinate |
| P3 | synthetic passenger rows | **WRONG** | 13 rows have positions **beyond the chromosome length** **[reproduced]** |

---

## A. Terminology

### A1–A2. neoantigen / neoepitope / candidate peptide

There is **no** formal consensus nomenclature — I checked, and the commonly-cited claim that
"a neoantigen with validated immunogenicity is a neoepitope, one with uncertain immunogenicity is a
neopeptide" is **not** in the source usually credited for it (Zhou WJ et al., *Database* 2019;2019:baz128,
PMID 31819989 — I read it; it makes no such distinction and uses the terms interchangeably).

So do not claim a definition the field has not agreed. The *defensible* usage, and the one that will
survive a reviewer:

- **neoantigen** — the mutant **protein/antigen** as a whole; the property belongs to the gene product
  (Schumacher TN & Schreiber RD, *Science* 2015;348:69–74, DOI 10.1126/science.aaa4971).
- **neoepitope** — the specific MHC-bound **peptide determinant that a T cell recognises**. "Epitope" is
  defined *by recognition*. Calling something an epitope asserts a T cell has seen it.
- **candidate peptide / predicted binder** — everything your pipeline outputs.

**Verdict: IMPRECISE.** A peptide that has only been *predicted to bind* is a **candidate peptide** or, at
most, a **predicted neoepitope**. It is not a neoantigen and it is not a neoepitope. The base rate makes
this more than pedantry: the TESLA consortium found **37 of 608** predicted neoantigens were immunogenic
(Wells DK et al., *Cell* 2020;183:818–834.e13, DOI 10.1016/j.cell.2020.09.015) — so calling a prediction a
"neoantigen" is wrong roughly 94% of the time.

`neofold/selfsim.py` already gets this right in its docstring (`is this "neoepitope" actually a normal
human peptide?` — scare quotes included). The UI does not.

### A3. presentation vs recognition vs immunogenicity — **CORRECT**

These are genuinely distinct, sequential requirements, and the project is right to separate them:

1. **Processing & presentation** — proteasomal cleavage → TAP transport → MHC-I loading → surface display.
   Measured by immunopeptidomics; predicted by MHCflurry/NetMHCpan.
2. **Recognition** — a TCR in *this patient's* repertoire engages that pMHC. Requires a T cell to exist
   and to have escaped thymic deletion.
3. **Immunogenicity** — recognition actually produces a functional, expanded T-cell response in vivo.

Each step loses most candidates. Keep this framing — it is one of the strongest honest things in the
project. TESLA (above) is the citation to use, and the project already uses it.

### A4. "HLA restriction" — **CORRECT usage**

"Peptide X is restricted by HLA-C\*08:02" is the standard formulation, from Zinkernagel RM & Doherty PC,
*Nature* 1974;248:701–702 (DOI 10.1038/248701a0) — the H-2/MHC restriction discovery. Strictly, **restriction
is a property of the T cell / the response**, not of the peptide: a *T-cell response* is restricted by an
allele, meaning that T cell only sees the peptide when presented by that allele.

**Caveat the project must observe:** "HLA-C\*08:02-restricted" is a statement about a *demonstrated T-cell
response*. It is correct for `GADGVGKSA` and `GADGVGKSAL` because Tran 2016 and Sim 2020 demonstrated
restricted TCRs. It is **not** correct for anything your pipeline predicts. A predicted binder is
"**predicted to be presented by** HLA-C\*08:02", never "restricted by" it.

### A5. "tumour-specific" — **WRONG as applied**

The field's meaning of **tumour-specific** is *absent from the normal genome/proteome* — i.e. the sequence
does not exist in healthy tissue. That is the property that distinguishes a true neoantigen from a
tumour-**associated** antigen (an over-expressed but normal self protein, e.g. NY-ESO-1, gp100).

What the project measures is **mutant binds ≥2× better than wild-type at the same register**. That is a
different quantity, and the field already has a name for it: the **differential agretopicity index (DAI)**
(Duan F et al., *J Exp Med* 2014;211:2231–2248, DOI 10.1084/jem.20141308). Agretopicity is about *binding
to MHC*; specificity is about *sequence novelty*.

They come apart, and your own repo contains the counter-example:

> `ICDFGLARV` (KIT D816V) has a **112× fold change** over its wild-type counterpart **[reproduced]** —
> and it is an **exact self peptide**, present verbatim in MAPK1/ERK2 (P28482, residues 165–173) and NLK
> (Q9UBE8, residues 280–288) **[reproduced]**.

Maximum "fold change", zero tumour specificity. Rename the tier: **`not tumour-specific` → `no
mutant/WT differential`**, and `investigate`'s reason string should say "differential agretopicity", not
"tumour-specific". The newly-added `neofold/selfsim.py` is the thing that actually tests tumour
specificity — wire it into the tier name.

### A6. 50 nM / 500 nM — real cut-offs, but superseded by %rank (and the literature is not unanimous)

**Origin.** The affinity bands trace to Sette A et al., *J Immunol* 1994;153:5586–5592 (PMID 7527444), which
established that IC50 ≤ 500 nM is broadly necessary for class-I immunogenicity, with ≤50 nM enriching
strongly for epitopes. They were adopted as the NetMHC reporting convention.

**The mechanism that undermines them.** Alleles differ enormously in the *size and affinity* of their
binding repertoires. Paul S, Weiskopf D, Angelo MA, Sidney J, Peters B, Sette A, *J Immunol*
2013;191(12):5831–5839, DOI 10.4049/jimmunol.1302101, PMID 24190657, measured it: the fraction of peptides
predicted to bind ranged from **0.07% for HLA-B\*51:01 to 10.40% for HLA-A\*02:06**, and the geometric mean
affinity of each allele's **top 1%** ranged from **14 nM (A\*68:01) to 1,110 nM (B\*51:01)**. For B\*51:01,
a flat 500 nM gate discards essentially the allele's entire true repertoire.

> **Do not cite Paul 2013 as support for switching to %rank — it argues the opposite**, and a reviewer will
> catch it. Verbatim: *"if a single criterion for alleles has to be chosen, it is preferable to use absolute
> binding affinity, rather than a relative percentile… 500 nM is a reasonably good 'universal' threshold…
> more effective allele-specific thresholds can be derived."* Cite it for the **mechanism** (repertoire-size
> variation), then cite the tool authors for the **recommendation**.

**The recommendation to cite instead.** NetMHCpan-4.1 (Reynisson B, Alvarez B, Paul S, Peters B, Nielsen M,
*Nucleic Acids Res* 2020;48(W1):W449–W454, DOI 10.1093/nar/gkaa379, PMID 32406916) defines
**%rank < 0.5 strong binder, < 2.0 weak binder** and states *"We advise to select candidate binders based
on %Rank rather than Score… This measure is not affected by inherent bias of certain molecules towards
higher or lower mean predicted affinities."* Same advice from Jurtz V et al., *J Immunol*
2017;199(9):3360–3368, DOI 10.4049/jimmunol.1700893, PMID 28978689, and from IEDB
(*"currently recommends using the percentile rank as the metric for ranking binding predictions"*).

> **Also do not attribute this to MHCflurry.** The word "percentile" does not appear in the MHCflurry 2.0
> paper. The recommendation is from the NetMHC lineage and IEDB.

**This matters acutely for HLA-C\*08:02 specifically — and it damages a headline claim.** Both percentile
columns are available and the project uses neither. `affinity_percentile` requires one keyword
(`include_affinity_percentile=True`); `presentation_percentile` is returned unconditionally.
`neofold/screen.py::_predict` keeps only `affinity`, `presentation_score`, `processing_score`
**[reproduced]**:

| peptide | affinity (nM) | **affinity_percentile** | NetMHCpan-convention call | presentation_percentile |
|---|---|---|---|---|
| `GADGVGKSAL` (mut) | 38.9 | **0.051** | strong binder | 0.047 |
| `GADGVGKSA` (mut) | 74.1 | **0.188** | strong binder | 0.676 |
| **`GAGGVGKSAL` (WT)** | **876.9** | **1.055** | **WEAK BINDER** | 2.504 |
| `GAGGVGKSA` (WT) | 3656.5 | **2.254** | non-binder (just) | 9.494 |
| `ICDFGLARV` | 177.7 | 0.426 | strong binder | 0.762 |
| `ICDFGLARD` | 19899.1 | 5.699 | non-binder | 46.225 |

**Read the third row.** On the nM scale the wild-type 10-mer `GAGGVGKSAL` is 876.9 nM — comfortably past
your 500 nM gate, and the guide calls the normal protein **"invisible"**. On the allele-normalised scale it
is **1.055%** — inside NetMHCpan's **weak-binder** band. HLA-C\*08:02 has a low-affinity repertoire (HLA-C is
expressed ~10× lower than HLA-A/B and its motifs are less well sampled), so 877 nM is within its top ~1% of
peptides.

So **"the normal version of that protein is invisible" is an overclaim** for the 10-mer. The 9-mer survives
the argument (2.25%, just outside the weak band); the 10-mer — your **rank-1 candidate** — does not. Reword
to *"the wild-type peptide is predicted to bind 20–50× more weakly"* and drop "invisible".

**One caveat on `presentation_percentile` before you switch to it:** unlike `affinity_percentile`, it is
computed by a **single global transform with no allele argument** — it is allele-*independent*, so it does
not solve the cross-allele comparability problem that motivates percentile ranks in the first place. It is
also entirely **undocumented** in MHCflurry's docs. If you want the allele-fair number, use
`affinity_percentile`.

### A7. "normal tissue" — **sloppy, and in one place wrong**

`app/main.py:129` labels the wild-type structure **"KRAS wild-type — normal tissue"**. Two problems:

1. A **peptide** is not a tissue. The correct terms are **wild-type / germline counterpart** or **self
   peptide**.
2. It implies tissue-level provenance the pipeline never establishes — you never look at expression,
   so you do not know which normal tissues present it, or whether any do.

And the specific peptide is shared far more widely than "KRAS": `GAGGVGKSA` occurs verbatim in **NRAS
(P01111), HRAS (P01112), KRAS (P01116), RIT1 (Q92963) and RIT2 (Q99578)** **[reproduced]**. Label it
**"KRAS wild-type (germline counterpart)"**.

---

## B. The KRAS G12D case

### B1. The two epitopes — **CORRECT**

- Tran E, Robbins PF, Lu Y-C, et al. *T-Cell Transfer Therapy Targeting Mutant KRAS in Cancer.*
  **N Engl J Med** 2016;375(23):2255–2262. DOI 10.1056/NEJMoa1609279. PMID 27959684. Verbatim:
  "Three of the four T-cell receptors were preferentially reactive against the KRAS G12D peptide
  GADGVGKSA (consisting of 9 amino acids [9mer]), whereas one T-cell receptor was reactive only against
  the KRAS G12D peptide GADGVGKSAL (consisting of 10 amino acids [10mer])". HLA-C\*08:02-restricted TIL.
- Sim MJW, Lu J, Spencer M, et al. *High-affinity oligoclonal TCRs define effective adoptive T cell
  therapy targeting mutant KRAS-G12D.* **PNAS** 2020;117(23):12826–12835. DOI 10.1073/pnas.1921964117.
  PMID 32461371. "All five TCRs are HLA-C\*08:02–restricted."
  **There is a correction:** PNAS 2020;117(44):27743–27744, PMID 33077608 — check it before quoting any
  figure-level number.

**Do not call the 9-mer "the dominant epitope."** Sim 2020 designates neither. The evidence is mixed: the
9-mer has a higher pMHC melting temperature (51 ± 1.3 °C vs 45 ± 1.8 °C) and the highest-affinity TCR
(TCR9a, K_D 16 ± 8 nM vs TCR10 at 6.7 ± 1.7 µM), **but** the 9-mer's C-terminal Ala is a *suboptimal* PΩ
anchor — Sim 2020 notes Ala at PΩ is "absent from nonamer or decamer peptides previously eluted from
HLA-C\*08:02", and A18L improved stabilisation ~20×. In vivo, the **10-mer-specific clone persisted**
(Tran 2016: the highest persisting reactive clone recognised the 10-mer); TCR9a fell to 0%.

Your screen ranks the 10-mer #1 and the 9-mer #2 **[reproduced]**, which is arguably the *right* answer for
the wrong reason — do not present the ordering as validated.

### B2–B3. PDB 6ULN — **correct structure, wrong attribution**

**[reproduced]** from `results/reference/6ULN.cif`: P 1 21 1, **2.01 Å**; chain A = HLA-C\*08:02 heavy chain
(residues 2–274), B = β2m (99), **C = `GADGVGKSA` (9-mer)**, D = TCR α (189), E = TCR β (240). So "6ULN is
this complex with a patient-derived TCR" is **CORRECT**.

But **§6E's "the patient-derived TCR α/β from Tran *NEJM* 2016" is WRONG.** I extracted the CDR3β from the
project's own predicted chain E: **`CASSLGQTNYGYTF`** **[reproduced]** — that is **TCR9d**, from **patient
3995**, characterised in **Sim 2020** (Table 1). Tran 2016 described patient **4095**. TCR9a is a *different*
structure, **PDB 6ULR** (3.2 Å).

The full Sim 2020 series, for correct citation:

| PDB | Contents | Peptide | Res. |
|---|---|---|---|
| **6ULI** | binary pMHC | 9-mer `GADGVGKSA` | 1.88 Å |
| **6ULK** | binary pMHC | 10-mer `GADGVGKSAL` | 1.90 Å |
| **6ULN** | + **TCR9d** | 9-mer | 2.01 Å |
| **6ULR** | + **TCR9a** | 9-mer | 3.20 Å |
| **6UON** | + **TCR10** | 10-mer | 3.50 Å |

**Two traps to avoid:** (a) a separate series by Bai P et al. — **6JTN is HLA-C\*08:02** with the 10-mer, but
**6JTO is HLA-C\*05:01**, not C\*08:02 (differs at positions 77 S→N, 80 N→K); (b) `VVVGADGVGK` (KRAS 7–16) is
a *different* G12D epitope restricted by **HLA-A\*11:01** (PDB 7OW6, 7PB2) — do not conflate.

**Also worth noting for the pitch:** if you want a *binary* pMHC reference (no TCR distorting the groove),
**6ULI is the better ground truth** than 6ULN, and at 1.88 Å it is higher resolution.

### B4. The salt bridge — **CORRECT but incomplete**

Sim 2020, verbatim: "The most contacts between the HLA-C\*08:02 peptide-binding groove and peptide side
chains were at peptide p3, where the negatively charged Asp formed a salt bridge with the positively
charged **Arg-156** on the α2-helix … Critically, p3 Asp is the result of the KRAS-G12D mutation and the
salt bridge cannot be formed with the WT Gly."

So the claim is right, and the "chemically impossible with Gly" framing is Sim's own. Measured distances
across the series (Arg156 NE–Asp3 OD): 6ULI 2.63 Å, 6ULK 2.79 Å, **6ULN 2.73 Å**, 6ULR 2.63 Å. My local
re-measurement of 6ULN with `neofold/contacts.py` gives **2.73 Å** **[reproduced]** — exact match.

**What the project omits, and a structural reviewer will not:**

| Heavy-chain residue | Contact to peptide p3 | Distance |
|---|---|---|
| **Arg97** | NH1 → Asp3 OD1/OD2 — a *second* charge interaction | 3.35–3.71 Å |
| **Tyr99** | OH → p3 **backbone** amide N (H-bond) | 2.74–3.01 Å |
| Tyr159 | vdW packing against the Asp3 side chain | 3.2–3.6 Å |
| Lys66 | → p3 backbone carbonyl O (9-mers) | ~3.5–3.9 Å |

"Salt bridge with Arg156" is fine. "**The** salt bridge, as the sole interaction at p3" is not. Suggested
wording: *"a bidentate salt bridge to Arg156, plus a second charge interaction with Arg97, with Tyr99
hydrogen-bonding the p3 backbone."* Note **Arg97 is also Arg in the wild-type complex** — so the "the
mutation creates the contact" story is about Arg156 **and** Arg97; mentioning only one understates it.

**Arg156 is genuinely present in C\*08:02** — confirmed independently from the project's own stored
ectodomain, where residue 156 = **R**, against HLA-A\*02:01 residue 156 = **L** **[reproduced]**. Position 156
is a classic micropolymorphic α2-helix position (cf. HLA-B\*44:02 Asp156 vs B\*44:03 Leu156; Macdonald WA
et al., *J Exp Med* 2003;198:679–691, PMID 12939341) and contacts peptide P3 in the majority of class-I
structures. It is *also* Arg in HLA-C\*05:01, which is why C\*05:01 presents the same 10-mer — worth a line,
because it means the "Arg156 is why this works" story is not unique to C\*08:02.

### B5. The P3-Asp motif — right paper, wrong emphasis, and a second source you are missing

**Rasmussen M, Harndahl M, Stryhn A, et al.** *Uncovering the peptide-binding specificities of HLA-C: a
general strategy to determine the specificity of any MHC class I molecule.* **J Immunol**
2014;193(10):4790–4802. DOI 10.4049/jimmunol.1401689. PMID 25311805. — **the citation is real and correct.**

But it says something *stronger* than the project claims. Table II classifies, for C\*08:02, **P3 = D as a
PRIMARY anchor** and P9 = F/I/L/M as primary, with **P2 = A/S demoted to auxiliary**. Verbatim: "the
concurrent presence of the strong Asp anchor residue in P3 seems to lessen the importance of P2, making
P2 an auxiliary anchor in these latter molecules"; and "HLA-C\*04:01, -C\*05:01, and -C\*08:02 share a strong
preference for Asp". So "prefers Asp at p3" **understates it** — say **"P3-Asp is a primary anchor for
HLA-C\*08:02"**. That is a stronger and still fully citable claim.

**Citation mismatch to fix.** Sim 2020's own support for the *eluted-ligand* P3 D/E observation is **not**
Rasmussen — it is **Di Marco M, Schuster H, Backert L, et al.** *Unveiling the Peptide Motifs of HLA-C and
HLA-G from Naturally Presented Peptides and Generation of Binding Prediction Matrices.* **J Immunol**
2017;199(8):2639–2651. DOI 10.4049/jimmunol.1700938. PMID 28904123. The two are different methods
(Rasmussen = positional-scanning combinatorial libraries + dissociation assay; Di Marco = mass-spec
elution of naturally presented ligands). `app/main.py:247` currently cites only Rasmussen — **add Di Marco
2017** if you are going to say anything about what is *naturally presented*.

### B6. "p3" nomenclature — **CORRECT**

Both `p3` (lower-case, Sim 2020's own convention) and `P3` (upper-case, Rasmussen/Rammensee convention) are
standard; `PΩ` denotes the C-terminal anchor regardless of peptide length. Position 1 is the N-terminal
residue of the **peptide**, never the protein. The project uses `p3` consistently in prose and
`peptide_position=3` in code, and `contacts.py::_residue_at` correctly counts positionally from the
N-terminus rather than trusting author numbering — that is the right call.

**Minor:** be internally consistent. `BUILD-GUIDE.md` §6A writes "P1 0.55 Å, P9 0.52 Å" (upper-case) while
everything else uses lower-case `p3`. Pick one.

### B7. "KRAS 4B residues 10-18/10-19" — **WRONG label, correct register**

The arithmetic is right **[reproduced]**:

```
M  T  E  Y  K  L  V  V  V  G  A  G  G  V  G  K  S  A  L
1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19
                          ^G12 -> D, i.e. peptide position 12-10+1 = 3
10-18 WT GAGGVGKSA  -> G12D -> GADGVGKSA   (9-mer,  G12 at p3)
10-19 WT GAGGVGKSAL -> G12D -> GADGVGKSAL  (10-mer, G12 at p3)
```
Independently corroborated by Sim 2020's own superscript notation (**¹⁰**GADGVGKSA), its reference to
"Leu-19", and its "A18L" mutant.

**But the "4B" label is wrong about your own data.** `data/sequences/proteins.fasta` ships P01116 at
**189 aa**, byte-identical to the UniProt canonical **[reproduced]** — and UniProt's canonical P01116 is
**isoform 2A = KRAS4A**. KRAS4B is **P01116-2, 188 aa**. The two are identical through residue 150 and first
differ at **residue 151** **[reproduced]**, so the epitope register is unaffected — but:

- `tests/test_variants.py:14` comments "KRAS-4B residues 1-23 (UniProt P01116)" — **factually wrong**.
- `BUILD-GUIDE.md` §5 cites MANE `NM_004985.5`, which encodes **KRAS4B (188 aa)** — so the guide cites a
  4B transcript while the code loads a 4A protein. Harmless for G12; a **silent off-by-one-to-39 landmine**
  for any variant past residue 150.

**Fix:** say "KRAS residues 10–18/10–19 (identical in isoforms 4A and 4B)", and either ship P01116-2 or
drop the MANE reference.

### B8–B9. Measured contact distances

**[reproduced]** with the project's own `neofold/contacts.py`:

| Structure | p3 residue | Arg156 distance | Salt bridge |
|---|---|---|---|
| Crystal 6ULN | ASP3 | **2.73 Å** | yes — matches BUILD-GUIDE ✓ |
| `kras_g12d_9mer_mut_model_0` | ASP3 | **2.58 Å** | yes — BUILD-GUIDE says **2.52 Å** ✗ |
| `kras_g12d_9mer_wt_model_0` | GLY3 | — | chemically impossible ✓ |
| `kit_d816v_mut_model_0` | ASP3 | 2.54 Å | yes |
| `kit_d816v_wt_model_0` | ASP3 | 2.49 Å | yes |

The 2.52 vs 2.58 Å discrepancy is trivial in magnitude but it means **a number in the guide is not the
number the repo produces**. Either it came from a different model file or it was transcribed wrong. Fix it
before a judge runs your own test suite.

**The deeper problem with the contact panel** is in §F6 below: on this evidence the measurement carries no
information that the peptide sequence did not already carry.

---

## C. The screening logic

### C1. Is the mutant-vs-wild-type differential a real criterion? — **YES, it is real and well-established**

It has a name, an originating paper and a validation cohort:

- **Duan F, Duitama J, Al Seesi S, et al.** *Genomic and bioinformatic profiling of mutational neoepitopes
  reveals new rules to predict anticancer immunogenicity.* **J Exp Med** 2014;211(11):2231–2248.
  DOI 10.1084/jem.20141308. PMID 25245761. Introduced the **differential agretopicity index (DAI)**.
  Verbatim: *"the NetMHC scores of the unmutated counterparts of the predicted mutated epitopes were taken
  into consideration by **subtracting them from** the corresponding NetMHC scores of the mutated epitopes."*
  So the original DAI is a **difference of NetMHC log-space scores, and Duan applied no threshold at all** —
  epitopes were *ranked* by it.
- **Ghorani E, Rosenthal R, McGranahan N, et al.** *Differential binding affinity of mutated peptides for
  MHC class I is a predictor of survival in advanced lung cancer and melanoma.* **Ann Oncol**
  2018;29(2):271–279. PMC5834109. DAI-high neoantigen burden predicted survival.
- **Łuksza M, Riaz N, Makarov V, et al.** *A neoantigen fitness model predicts tumour response to checkpoint
  blockade immunotherapy.* **Nature** 2017;551(7681):517–520. DOI 10.1038/nature24473. PMID 29132144.
  Neoantigen quality = **A × R**, where **amplitude A is the ratio of predicted wild-type to mutant
  dissociation constants (Kd_WT / Kd_MT)** and R is TCR cross-reactivity. **This is exactly your
  `fold_change`.** Cite it — it gives your metric a name and a Nature paper instead of looking home-made.

**Three different conventions are in circulation, and you must state which you use.** Duan = a **difference
of scores**; Łuksza's amplitude = **Kd_WT / Kd_MT** (your direction, higher = better); TESLA's agretopicity =
**MT/WT** (the **inverse** of yours, lower = better). `fold_change = wt_affinity_nm / affinity_nm` matches
**Łuksza's amplitude**. A reviewer comparing your column to a TESLA agretopicity column will read it upside
down unless you say so.

**The counter-example that should worry you most.** Duan's own Table 5 lists the validated, tumour-protective
epitopes their method found — and they are mostly *weak* binders with unfavourable ratios. `Dhx8.1` has
mutant/wild-type IC50 of **2192 / 1653 nM** and scored strongly in ELISpot; its WT/MT ratio is **0.75**,
i.e. *below 1*. **Your pipeline applies a 500 nM gate AND a ≥2× gate, so it would have discarded the founding
paper's own validated epitopes.** That is the single most precise attack on the two-gate design, and the
honest answer is that both gates are tuned for precision at the cost of recall — which is a defensible
choice for GPU triage, but you should say it out loud rather than be shown it.

**And the criticism you must be ready for: DAI does not validate well on held-out data.**
Nibeyro G, Baronetto V, Folco JI, et al., *Front Immunol* 2023;14:1094236. DOI 10.3389/fimmu.2023.1094236.
PMID 37564650 — across 199 tumour-specific neoantigens and 16 metrics, **DAI reached AUC 0.59 (anchor) /
0.56 (non-anchor), and "no significant difference was found between immunogenic and non-immunogenic TSNs
according to DAI values (P = 0.25)."** Binding-affinity-derived metrics generally scored AUC 0.52–0.60.

*Fair caveat to state alongside it:* that benchmark required every peptide to have **experimentally
validated binding and presentation** for inclusion. So it shows these metrics fail to separate immunogenic
from non-immunogenic peptides **among peptides already known to be presented** — not that the filter is
useless upstream, which is where you apply it. Quoting it with that caveat is more credible than avoiding it.

### C2. Is 2× defensible or arbitrary? — **arbitrary, uncited, but erring in the safe direction**

**`MIN_FOLD_CHANGE = 2.0` has no citation anywhere in the repo.** Here is what pipelines actually do:

| Pipeline | WT/MT parameter | Default |
|---|---|---|
| **pVACtools** (Hundal J et al.) | `--minimum-fold-change` — "Minimum fold change between mutant binding score and wild-type score" | **0 — filters nothing by default** |
| pVACtools, documented meaningful value | — | **1** ("a value of 1 requires better binding to the mutant than wild-type peptide") |
| pVACtools binding threshold | `-b/--binding-threshold` | **500 nM** |
| pVACtools percentile gates | `--binding-percentile-threshold`, `--presentation-percentile-threshold` | **2.0**, with `--percentile-threshold-strategy` defaulting to **conservative** (must pass BOTH nM and percentile) |

So: **2× is stricter than any published default.** The reference implementation ships the filter **off**, and
the value its own documentation calls meaningful is **1** (merely "better than wild-type"). Your 2× is
therefore *conservative*, not reckless — but it is still a magic number, and "we used 2×" invites "why not
1× or 5×?" with no answer.

**The full landscape of what anyone actually uses:**

| Source | Differential criterion |
|---|---|
| Duan 2014 (originator) | **no threshold** — rank by DAI |
| pVACtools | default **0** (off); docs call **1** "a sensible option" |
| NeoPredPipe (Schenck RO et al., *BMC Bioinformatics* 2019) | **no WT comparison at all** — reports %rank only (SB < 0.5, WB < 2) |
| MuPeXI (Bjerregaard AM et al., *Cancer Immunol Immunother* 2017;66(9):1123–1130, PMID 28429069) | priority score using binding, expression and **similarity to normal peptides** (AUC 0.63) |
| Łuksza 2017 | amplitude used **continuously**, not thresholded |
| **TESLA (Wells 2020)** | empirical cut at **agretopicity < 0.1, i.e. mutant binds ≥ 10× better** |

**So 2× is nobody's published cut.** It sits in the gap between "off" and TESLA's empirically derived 10×.

**Two defensible responses, pick one:**
1. **Honest arbitrariness + sensitivity analysis:** "pVACtools ships this off, TESLA's empirical cut is 10×,
   and we chose 2× as a loose sanity check. Here is the shortlist at 1×, 2×, 5× and 10×." You have 38
   candidates; this costs seconds and converts a magic number into a *finding*.
2. **Adopt a cited value:** use **1×** (pVACtools' documented floor) as the gate and report the amplitude
   continuously, as Łuksza does — then you have a Nature citation for the metric and a reference
   implementation's default for the threshold.

**Also worth noting:** pVACtools' default strategy requires a candidate to pass **both** an nM and a
percentile threshold. You gate on nM and `presentation_score` and **no percentile at all** (§A6) — so on this
axis you are *less* stringent than the reference pipeline, not more.

### C3. What the MHCflurry columns actually mean — and where you are reading them wrong

**Citation:** O'Donnell TJ, Rubinsteyn A, Laserson U. *MHCflurry 2.0: Improved Pan-Allele Prediction of
MHC Class I-Presented Peptides by Incorporating Antigen Processing.* **Cell Systems** 2020;11(1):42–48.e7.
DOI 10.1016/j.cels.2020.06.010. PMID 32711842.
**There is an erratum you do not cite:** *Cell Systems* 2020;11(4):418–419, DOI 10.1016/j.cels.2020.09.001,
PMID 33091335.

| Column | What it actually is | How the project treats it |
|---|---|---|
| `affinity` | Predicted IC50 (nM). **Not a pure affinity model** — trained on 219,357 affinity measurements **plus 470,586 MS hits, where each MS hit is assigned a censored "<50 nM" label.** So it is a hybrid of measured binding and presentation evidence. | Used as if it were a measurable IC50 |
| `affinity_percentile` | **Per-allele** rank vs a calibrated background (100,000 random peptides per length). Background is **uniform amino-acid composition**, not proteome-derived — so it is **not interchangeable with NetMHCpan percentiles**, which use natural peptides | **Never requested** (`include_affinity_percentile=False` by default) |
| `processing_score` | **Allele-independent**, 0–1. Trained as an MS-hit-vs-decoy discriminator at **1:100** hit:decoy ratio. **It is not a proteasomal cleavage predictor.** The authors hedge: *"may reflect TAP binding and/or proteasomal cleavage"* | Reported in the UI without saying which variant produced it |
| `presentation_score` | `LogisticRegression.predict_proba()` over exactly **two** features: `affinity_score` (= `1 − log(IC50)/log(50000)`, clipped) and `processing_score`. **Not a calibrated probability** — fit on hits vs decoys at artificial ratios with no `class_weight`, so it reflects training class balance, not any real prior of presentation | Used as the **primary ranking key** and gated at a hard 0.10 |
| `presentation_percentile` | `100 − percent_rank_transform(presentation_score)`, via a **single global, allele-independent** transform. Undocumented in MHCflurry's docs | **Discarded** |

**`MIN_PRESENTATION = 0.10` has no source and contradicts the tool's own documentation.** MHCflurry's docs
state plainly: *"Presentation scores are useful for ranking candidates, but there is no universal
presentation-score threshold."* The constant appears in `neofold/screen.py:164` with a comment but **no
citation anywhere in the repo**. Either derive it (e.g. calibrate against a set of known C\*08:02 ligands)
or drop the gate and rank on percentile.

**Flanks: not a bug, but a missed improvement — I over-called this initially and the correction matters.**
`_predict` calls `predict(peptides=..., alleles=...)` with `n_flanks`/`c_flanks` left as `None`. MHCflurry
handles that **correctly**: `class1_presentation_predictor.py` tests `if n_flanks is None:` and swaps in
`processing_predictor_without_flanks` together with matching logistic-regression weights. So the numbers are
internally consistent, not corrupted.

The real points are:

1. **You have the flanks and are not using them.** `Candidate` already carries `start`, and `build_candidates`
   has the full protein. Supplying 15 residues either side is a few lines. The paper quantifies the gain:
   *"The use of flanking sequences made a small but consistent difference, further improving PPV by a mean
   3.3% (1.8 – 4.8)."*
2. **The effect on your own numbers is large.** **[reproduced]** for `GADGVGKSA` with real KRAS flanks
   (`MTEYKLVVV` / `LTIQLIQNH`): `processing_score` **0.0399 → 0.1144** (2.9×), `presentation_score`
   0.570 → 0.603. For the wild-type `GAGGVGKSA`: 0.00248 → 0.0351 (14×). The mutant/WT *processing* contrast
   changes materially, so this is not cosmetic.
3. **A footgun to avoid when you fix it:** the guard tests `is None`, **not** emptiness. Passing
   **empty-string** flanks runs the *with_flanks* model on empty context — that *is* silent degradation.
   Pass real flanks or pass `None`, never `""`.

**Ranking key.** `score()` sorts by `presentation_score` descending. Given the above — an uncalibrated
two-feature logistic regression — the more defensible key is `affinity_percentile` (allele-normalised), with
`presentation_score` shown as a secondary annotation.

**Two repo inconsistencies to fix while you are in here:**
- **Allele count:** `BUILD-GUIDE.md` says 14,884, `research/research-screen-and-data.md` says 20,246, the
  Cell Systems paper says 14,993. My installed build reports **14,884** **[reproduced]**. Source one number
  to the installed model version and delete the others.
- **Citation error:** `research/research-scaling-and-pitch.md:771` attributes a quotation to *"Buckley PR
  et al., Front Immunol 2023, DOI 10.3389/fimmu.2023.1094236."* That DOI is **Nibeyro G et al.**
  (PMID 37564650). The quoted sentence is verbatim from Nibeyro. Fix the author.

### C6. Which omission a reviewer would consider most serious

Ranked. The first is not close.

**1. Gene/transcript expression — by far the most serious.** A peptide from an unexpressed gene cannot be
presented, whatever its predicted affinity. Every production pipeline gates on it, and the project gates on
nothing. This is also the cheapest fix conceptually (accept an optional expression TPM column in the VCF and
show it as a column, even if the demo data has to supply it synthetically) and the most obvious gap to a
clinician: your demo scores KRAS, TP53, BRAF, PIK3CA, EGFR and KIT without ever asking whether the tumour
transcribes them.

**2. pMHC complex stability.** Harndahl M, Rasmussen M, Roder G, et al., *Eur J Immunol* 2012;42(6):1405–1416,
DOI 10.1002/eji.201141774, PMID 22678897 — *"immunogenic peptides tend to be more stably bound to MHC-I
molecules compared with nonimmunogenic peptides"*, and stability prediction accounted for **30% of
non-immunogenic binders previously written off as "holes in the T-cell repertoire."** TESLA independently
confirms it, and note the p-values: **stability p = 1.4×10⁻⁴ is a *stronger* association than expression
p = 0.01**. I still rank expression first because it is a **logical gate** (no transcript, no peptide) rather
than a correlate — but if you only have appetite for one addition, the statistics favour stability.

MHCflurry supplies **no stability axis at all**; `NetMHCstabpan` (Rasmussen M et al., *J Immunol*
2016;197(4):1517–1526, PMID 27402703) exists, is cheap and is pan-specific. And Sim 2020 already reports
thermal melts for your exact peptides — **9-mer 51 ± 1.3 °C vs 10-mer 45 ± 1.8 °C** — a stability signal that
**inverts your presentation-score ranking** (which puts the 10-mer first). That is a free, citable
demonstration that your single-axis ranking is missing something real.

**3. Clonality / variant allele frequency.** A subclonal neoantigen is present in only part of the tumour.
McGranahan N, Furness AJS, Rosenthal R, et al., *Science* 2016;351(6280):1463–1469,
DOI 10.1126/science.aaf1490, PMID 26940869 — **clonal** neoantigen burden, not total burden, predicts
checkpoint-blockade response and sensitivity. Your VCF has no VAF/CCF field at all.

**4. TAP transport and proteasomal cleavage beyond MHCflurry's AP score.** Genuinely lower priority, and the
omission you can most easily defend: MHCflurry's processing predictor is trained on real MS hits and its
authors state its C-terminal preferences *"may reflect TAP binding and/or proteasomal cleavage"*, so NetChop
and TAP predictors are partly redundant with it. (The TAP reference is Peters B, Bulik S, Tampé R,
van Endert PM, Holzhütter HG, *J Immunol* 2003;171(4):1741–1749, PMID 12902473 — but I could not verify a
figure for how much TAP adds on top of binding prediction, so do not quote one.) **Say this explicitly
rather than listing it as a gap** — conceding the two that matter and defending the two that do not is more
convincing than conceding all four.

**The honest framing for the pitch:** you are a **binding**-prediction triage tool, not a neoantigen
prioritisation pipeline. Real pipelines (pVACtools, NeoPredPipe) are mostly *orchestration around* expression
and clonality filters; the binding predictor is one module. Claiming the category is what will get you
challenged; claiming the module is defensible and still interesting.

### C-extra. Structural problems in the screening code itself

- **One allele per run.** `run_triage(..., allele: str)` takes a single allele **[reproduced]**. A patient has
  **up to six** class I alleles, and a peptide presented by any one of them matters. Worse, alleles *compete*
  for peptides. A single-allele demo is fine; the funnel diagram implying patient-level triage is not.
- **`fold_change` silently becomes `nan`.** When a WT counterpart is missing from the dedup dict,
  `wt_affinity_nm` is `nan`, `fold_change` is `nan`, and `nan >= 2.0` is `False` — so the candidate is
  labelled **"not tumour-specific"**, which is a positive claim derived from missing data. It should be a
  distinct "WT not scored" tier.
- **`ensemble_spread` consistency bands** (`<1.0` high, `<2.5` medium) and **`_verdict` MD thresholds**
  (`>5.0 Å` or `<0.3` rejected; `>3.0 Å` or `<0.6` unstable) are **uncited round numbers**. The docstrings
  admit this ("conventions… NOT validated decision rules") — good — but they are still five magic constants
  driving user-facing verdicts.
- **`SALT_BRIDGE_CUTOFF_A = 4.0` is well chosen** — it matches the Barlow DJ & Thornton JM convention
  (*J Mol Biol* 1983;168(4):867–885), ≤4 Å between charged-group heavy atoms. Keep it. Minor: including
  **HIS** ND1/NE2 as a charged group on both sides is loose, since histidine is only cationic when protonated.

---

## D. Structure claims

### D1. Peptide backbone RMSD after MHC superposition — **CORRECT metric, but you are grading yourself on a generous curve**

The method is the field convention. The superposition target is right, and `validate.py`'s docstring
("given the groove, did we put the peptide in the right place?") is the right framing:

- **Mikhaylov V, Brambley CA, Keller GLJ, et al.** *Accurate modeling of peptide-MHC structures with
  AlphaFold.* **Structure** 2024;32(2):228–241.e4. DOI 10.1016/j.str.2023.11.011. PMID 38113889.
  Superimpose on **MHC chains only**, then measure the peptide. Primary metric **Cα-pRMSD**.
- **Marzella DF, Parizi FM, van Tilborg D, et al. (PANDORA)** *Front Immunol* 2022;13:878762.
  DOI 10.3389/fimmu.2022.878762. PMID 35619705. Superpose **G-domains (residues 1–180)**, then L-RMSD over
  peptide atoms, backbone = Cα, N, C, O — **identical to your `BACKBONE = ("N","CA","C","O")`**.
- **Motmaen A, Dauparas J, Baek M, et al.** *PNAS* 2023;120(9):e2216697120. DOI 10.1073/pnas.2216697120.
  PMID 36802421. Class I median **0.8 Å backbone / 1.8 Å all-atom**.

**What "good" means — and it is stricter than the project implies.** Mikhaylov et al. define explicit
bands: **sub-angstrom < 1.0 Å; good 1.0–1.5 Å; poor 1.5–2.5 Å; unacceptable ≥ 2.5 Å**. PANDORA maps onto
CAPRI-like bands (high < 1 Å, medium < 2 Å, acceptable < 5 Å) and reports **median backbone L-RMSD 0.70 Å
across 835 pMHC-I complexes / 78 MHC types, 96.6% below 2 Å**.

**So the honest framing of 0.509 Å is not "remarkable" — it is normal.** PANDORA (2022, CPU, seconds per
model) achieves a 0.70 Å median across 835 complexes. Your 0.509 Å on **one** complex is inside the
existing state of the art, not beyond it. The defensible claim is about **where** it runs (offline, on a
Nano, in 58 s, from a VCF row) — which is genuinely novel — not about the RMSD being exceptional. Any slide
that implies "sub-Ångström = breakthrough accuracy" will be shot down by anyone who knows PANDORA.

**The small-N dilution problem, which the project should pre-empt.** A 9-mer backbone RMSD averages 36
atoms, and P2/PΩ are anchored in the B and F pockets and essentially template-determined. The residues a
TCR actually reads (P4–P8) are the hard part. PMGen (bioRxiv 2025, DOI 10.1101/2025.11.14.688404) reports
that restricting modelling to validated anchors cut average peptide-core RMSD by **1.46 Å**; PANDORA
reports class-II binding-core L-RMSD 0.42 Å vs whole-peptide 0.88 Å — a **2× gap** between core and full
peptide. For class I, per-residue or central-bulge RMSD is generally **not** reported. **You already
compute `per_residue_ca_deviation_a`. Report it.** Doing so is *more* rigorous than the field standard.

### D2. TCR complex scored by "CA RMSD per chain" — **NON-STANDARD and weak**

Superposing on the MHC is legitimate (Bradley does it in TCRdock). Stopping at **whole-chain Cα RMSD is
not**. The field uses **DockQ / CAPRI**, plus CDR-loop RMSD:

- **DockQ** — Basu S & Wallner B, *PLoS ONE* 2016;11(8):e0161879. DOI 10.1371/journal.pone.0161879.
  `DockQ = (fnat + 1/(1+(L-RMS/8.5)²) + 1/(1+(i-RMS/1.5)²)) / 3`.
  Bands **confirmed exactly**: incorrect < 0.23; acceptable 0.23–0.49; medium 0.49–0.80; high ≥ 0.80.
- **CAPRI** — Méndez R, Leplae R, De Maria L, Wodak SJ, *Proteins* 2003;52(1):51–67. DOI 10.1002/prot.10393.
  Incorrect: fnat < 0.1 **or** (L-RMSD > 10 Å **and** I-RMSD > 4 Å). High: fnat ≥ 0.5 **and**
  (L-RMSD ≤ 1 Å **or** I-RMSD ≤ 1 Å). Interface defined at a 10 Å contact cutoff.
- **TCRmodel2** — Yin R, Ribeiro-Filho HV, Lin V, et al., *Nucleic Acids Res* 2023;51(W1):W569–W576.
  DOI 10.1093/nar/gkad356. Scores TCR-pMHC by CAPRI criteria; reports confidence–DockQ correlation r = 0.75.
- **TCRdock** — Bradley P, *eLife* 2023;12:e82813. DOI 10.7554/eLife.82813. Superimposes on **MHC**, then
  Cα RMSD over **CDR loops with CDR3 up-weighted 3×**; high quality ≲ 2 Å.
- **Benchmark for context** — Lu J, Zhu X, Hu X, et al., *Brief Bioinform* 2026;27(3):bbag289.
  DOI 10.1093/bib/bbag289. AlphaFold3 median DockQ **0.636 (class I)**; Boltz-1 closest open model.

**Why per-chain Cα RMSD is weak, specifically for you:** a TCR V-domain Ig fold is predicted near-perfectly
by any AF-class model. Averaging ~110 easy framework residues against ~10 hard CDR3 residues means your
1.42 Å / 1.50 Å is dominated by the part that was never in question, and **says nothing about whether the
predicted contacts are the native contacts**. CAPRI's "incorrect" class is defined by fnat < 0.1 precisely
because a correctly folded TCR docked with the wrong polarity can still give a respectable whole-chain RMSD.

**Concrete fix:** report **DockQ (with fnat, I-RMSD, L-RMSD broken out)** for the TCR:pMHC interface, plus
CDR-loop RMSD with CDR3 separated. Keep per-chain Cα as supplementary. `results/tcr/` has everything needed;
DockQ is a pip install.

**Latent fragility in the scoring code.** Both `validate.py::_rmsd` and `tests/test_tcr.py::_rmsd` pair atoms
**by list index** with `n = min(len(a), len(b))` and no sequence alignment. It happens to be valid here —
I verified chains B/C/D/E are exact sequence matches between the 6ULN assembly and the prediction
**[reproduced]** — but chain A is **not**: the crystal starts at seqid 2 (SER) while the prediction starts
at 1 (CYS), so any index-paired comparison of chain A is silently off by one. Add an assertion that the
sequences match before computing RMSD, or this will produce a confidently wrong number the first time a
crystal has a disordered loop.

### D3. "The model knows recognition is harder" — **WRONG, and your own data disproves it**

ipTM is a **self-assessment of the model's own inter-chain alignment error**, not a measure of biological
difficulty. Definition from Evans R, O'Neill M, Pritzel A, et al., *Protein complex prediction with
AlphaFold-Multimer*, bioRxiv 2021/2022, DOI 10.1101/2021.10.04.463034. DeepMind's own bands: > 0.8
confident, 0.6–0.8 grey zone, < 0.6 likely failed — **both of your numbers are in the "confident" band**.

**The killer is in `results/tcr/` already.** You ran the wild-type ternary complex too **[reproduced]**:

| | TCR9d + **G12D** peptide | TCR9d + **wild-type** peptide |
|---|---|---|
| global ipTM | 0.9468 | **0.9489 (higher)** |
| TCRα ↔ peptide `pair_chains_iptm` | 0.8795 | 0.8669 |
| TCRβ ↔ peptide | 0.8790 | 0.8638 |
| HLA ↔ peptide | 0.9959 | 0.9963 |

TCR9d is a **G12D-specific** TCR — it does not recognise the wild-type peptide. Boltz gives the
non-recognised pair **the same ~0.87 interface ipTM and a marginally higher global ipTM**. So the ~0.88 is
not the model "knowing recognition is hard"; it is a **generic property of that interface's size and
flexibility**, invariant to whether recognition actually occurs. This is the same result as your
wrong-allele control, one level up — and it is arguably a **better** slide, because it is a negative control
on the *recognition* step rather than the presentation step.

Four further confounds, any one fatal:

1. **Different d₀, different scale.** In Boltz (`confidence_utils.py`), `d0 = 1.24·(N_res−15)^(1/3) − 1.8` is
   computed once from the **total padded token count of the whole complex** and reused for `iptm` and every
   `pair_chains_iptm` entry. A 383-residue pMHC run and an 812-residue ternary run use **different d₀**, so
   the two numbers are not on a common scale.
2. **Non-contacting pairs drag ipTM down mechanically.** Global ipTM averages over all inter-chain residue
   pairs, including TCRα↔β2m and TCRβ↔β2m, which never touch. See **Dunbrack RL Jr**, *Rēs ipSAE loquuntur:
   What's wrong with AlphaFold's ipTM score and how to fix it*, bioRxiv 2025, DOI 10.1101/2025.02.10.637595,
   PMID 39990437 — inserting GGGS linkers alone drops ipTM from ~0.8 to ~0.59 with **no change to the modelled
   interface**. Also **Varga JK, Ovchinnikov S, Schueler-Furman O**, *Bioinformatics* 2025;41(3):btaf107,
   DOI 10.1093/bioinformatics/btaf107 (actifpTM), same diagnosis independently.
3. **Training-data density.** The PDB holds thousands of pMHC-I structures and only a few hundred TCR:pMHC
   complexes. Lower confidence on the rarer modality follows from data density alone.
4. **ipTM is poorly calibrated against real accuracy on interfaces like this.** Yin R & Pierce BG,
   *Protein Sci* 2024;33(1):e4865, DOI 10.1002/pro.4865, PMID 38073135: on 427 antibody-antigen complexes,
   ipTM–DockQ Pearson **r ≈ 0.53** (≈25% of variance). Lu et al. 2026 found **CDR3 pLDDT correlates with
   DockQ better than ipTM does** (r = 0.710/0.719 vs DockQ) for TCR-pMHC specifically.

**And the Boltz-2 authors demonstrate ipTM's emptiness in their own paper.** Passaro S, Corso G, Wohlwend J,
et al., *Boltz-2: Towards Accurate and Efficient Binding Affinity Prediction*, bioRxiv 2025,
DOI 10.1101/2025.06.14.659707, PMID 40667369: on the OpenFE/FEP+ subset, **Boltz-2 ipTM vs affinity gives
Pearson R = −0.07, Kendall τ = −0.05**; on MF-PCBA virtual screening ipTM gets **AUROC 0.566**, worse than
Chemgauss4 docking. These are protein–ligand benchmarks, so quote them carefully — but this is the model's
own authors showing ipTM carries no affinity signal. **It is a far stronger citation for your §6 argument
than the n=1 wrong-allele control**, and you should use it.

**One more thing to correct:** Boltz's `confidence_score = 0.8 × complex_plddt + 0.2 × iptm` — **not**
AlphaFold 3's `0.8 × ipTM + 0.2 × pTM`. Boltz's headline confidence is **80% a global per-residue score**.
Do not describe it as an interface quality number.

### D4–D5. Two numbers in the guide that the repo does not produce

**[reproduced]** by running `neofold/validate.py` against `results/reference/6ULN.cif`:

| Model file | MHC CA RMSD | Peptide backbone RMSD | Peptide CA RMSD |
|---|---|---|---|
| `results/kras_g12d_c0802_model_0.cif` | 0.970 Å | **0.560 Å** | 0.464 Å |
| `results/shortlist/kras_g12d_9mer_mut_model_0.cif` | 0.878 Å | **0.509 Å** | 0.412 Å |

- **`README.md` headlines 0.486 Å.** That number is **[unverifiable]** — no artefact in the repo produces it,
  and `tests/test_structure_analysis.py:34` pins **0.56**. Three different values (0.486 / 0.509 / 0.560)
  circulate for one measurement. Pick the one a judge can reproduce from the repo — **0.509 Å** — and say
  which model file and which MSA setting it came from.
- **`BUILD-GUIDE.md` §6A: "Per-residue deviation is highest at the peptide termini (P1 0.55 Å, P9 0.52 Å)
  and lowest in the middle."** This is **WRONG**. The actual per-residue Cα deviations **[reproduced]** are
  `[0.51, 0.24, 0.30, 0.47, 0.40, 0.43, 0.46, 0.55, 0.67]` (single-seq) and
  `[0.46, 0.18, 0.27, 0.33, 0.42, 0.42, 0.37, 0.48, 0.62]` (shortlist model). The minimum is at **p2–p3**
  (0.18–0.30 Å), not the middle, and deviation rises roughly monotonically to **p9 (0.62–0.67 Å)** — which
  is *higher* than the quoted 0.52. The stated pattern and both quoted numbers are wrong.

  The real pattern is the *expected* one and a better story: **p2 and p3 are the anchors** (p2 in the B
  pocket, p3 the Asp in the D pocket) and are pinned tightest; error accumulates toward the C-terminus.
  Say that instead.

### D6. MSA-free mode and the training-leakage question

Boltz's own documentation says forcing single-sequence mode is **"not recommended, as it reduces accuracy"**.
Magnitude, from **Peng C, Ni W, Liu Q, Hu G, Zheng W**, *A comprehensive benchmarking of AlphaFold3*,
*Brief Bioinform* 2025;26(6):bbaf616, DOI 10.1093/bib/bbaf616: on 150 monomers, with MSA TM = 0.817 vs
**single-sequence TM = 0.413**, with only 26% of targets reaching TM ≥ 0.5. Roughly a halving.

**But this cuts in the project's favour, and the project should say so.** Motmaen et al. (PNAS 2023) got
their **best** pMHC results from **single-sequence input plus pMHC templates**, and Bradley's TCRdock
**deliberately dropped MSAs** for templates. Single-sequence is a published, validated choice for *this
system class* — the HLA fold is rigid and heavily represented, so the MSA buys little. Your own measurement
agrees: 0.560 Å single-sequence vs 0.486 Å with MSA is a **13% difference on an already-sub-Ångström number**.
That is a genuinely interesting finding and it justifies the offline architecture. Frame it that way.

**The question you cannot answer with RMSD, and a judge will ask:** 6ULN was released 2020-05-27 and is
near-certainly in Boltz-2's training set. The guide admits this once (§5, §6A) — good — but the README does
not. **What is the maximum sequence identity between your target and anything in the training set?** For a
pMHC where the HLA is identical and the peptide is 9 residues, the answer is ~100%. The honest headline is
**"reconstructs a known complex"**, never "predicts". Your `a0201_msa_gen_model_0` and the 3GSO case do not
escape this either — 3GSO is older still.

---

## E. The MD check

### E1. Is 1 ns meaningful for anything here? — **Essentially no. Be blunt in the pitch.**

**Timescale.** Measured pMHC-I complex half-lives sit at **10³–10⁵ s**. Rasmussen M, Fenoy E, Harndahl M,
et al., *J Immunol* 2016;197(4):1517–1526, DOI 10.4049/jimmunol.1600582, PMID 27402703, is built on
**28,939 half-life measurements across 80 HLA-I allotypes**, with a **2-hour** training threshold and
"peptides forming stable pMHC-I complexes (t½ > 1h) were found for most HLA-I allotypes". See also
Harndahl M, Rasmussen M, Roder G, et al., *Eur J Immunol* 2012;42(6):1405–1416, DOI 10.1002/eji.201141774,
PMID 22678897 — **stability is a better immunogenicity predictor than affinity**, which is itself a
criticism of the screen (§C). 1 ns against a 1-hour half-life is **1 part in 3.6 × 10¹²**. The project's
"~10⁻¹³ of the relevant timescale" is the right order of magnitude — keep it.

**What the field actually runs:**

| Study | System | Length |
|---|---|---|
| Ayres CM, Riley TP, Corcelli SA, Baker BM, *JCIM* 2017;57(8):1990–1998, PMID 28696685 | 73 HLA-A*02:01 9-mers | **1 µs each** |
| Ayres CM, Abualrous ET, Bailey A, et al., *Front Immunol* 2019;10:966, PMID 31130956 | 52 peptides on HLA-A2 | **97 × 1 µs** |
| Knapp B, Dunbar J, Deane CM, *PLoS Comput Biol* 2014;10(8):e1003748, PMID 25101830 | LC13 TCR/HLA-B*08:01, 172 APLs | **100 ns each, first 10 ns discarded** |
| Knapp B, Ospina-Forero L, Deane CM, *JCTC* 2018;14(12):6127–6138, DOI 10.1021/acs.jctc.8b00391 | 827-residue TCRpMHC | 100 × **100 ns** |

Knapp 2018: **"a 100 ns TCRpMHC simulation is the current state of the art for this type of system."** You
are **100× below the field floor**. Knapp 2014 discarded **10× your entire production run** as equilibration.

**The single most damaging finding, and it undercuts your headline directly.** Knapp 2018, verbatim:

> "Short simulations (<10 ns) tend to agree with each other. For example, two simulations of 10 ns differ
> on average by only 0.61 Å... **However, this is not due to the good sampling quality but rather is due to
> undersampling and exploration of just the local neighborhood solution space** (e.g., side-chain
> conformations) **instead of the global solution space**."

Your n=3 replicates agreeing (contact persistence 0.760–0.769 for the mutant) is the **expected signature of
undersampling**, not evidence of stability. The tight mutant range is not a result; it is an artefact of
the run being too short to move.

**Can it work as a negative filter?** Only far above your budget. **Jandova Z, Vargiu AV, Bonvin AMJJ**,
*JCTC* 2021;17(9):5944–5954, DOI 10.1021/acs.jctc.1c00336, PMID 34342983, is the best case for the idea —
native docking models were more stable in RMSD and fraction of native contacts, and a classifier reached
**0.85 accuracy** — but states the requirement plainly: **"Reasonably modest simulation lengths of the order
of 50–100 ns are sufficient."** That is the **lower bound**, 50–100× your run. At 1 ns a pose can only fail
if it is grossly broken, which 500 steps of minimisation already catches. **It is a clash check wearing a
dynamics costume.**

### E2. "Contact persistence" — **you invented the name, and the definition has a logic error**

**The name.** There is **no** established "contact persistence" metric in the pMHC or protein–protein
interface literature. The conventional metrics are:

- **Q, fraction of native contacts** — Best RB, Hummer G, Eaton WA, *Native contacts determine protein
  folding mechanisms in atomistic simulations*, **PNAS** 2013;110(44):17874–17879.
  DOI 10.1073/pnas.1311599110. PMID 24128758:
  `Q(X) = (1/|S|) Σ_(i,j)∈S  1 / (1 + exp[β(r_ij(X) − λ·r_ij⁰)])`
  with **β = 5 Å⁻¹, λ = 1.8**, and native set S = heavy-atom pairs with **|i−j| > 3** and native distance
  **< 4.5 Å**.
- **fnat** — CAPRI, where two residues are in contact if any atoms are within **5 Å** (Méndez et al. 2005,
  *Proteins* 60:150–169).

**Your 4.5 Å heavy-atom cutoff is exactly conventional** — that part is fine, and `CONTACT_CUTOFF_NM = 0.45`
matches Best–Hummer–Eaton precisely. Three problems with the rest:

**(a) The reference set is the predicted pose, not a native structure — this is the serious one.** Q and
fnat are both defined against an **experimentally determined** reference. `md.py` computes `ref_contacts`
from the simulation's own starting frame. The metric therefore measures **drift from your own model**, and
**a completely wrong pose that happens to be rigid scores 1.0**. Presenting a high value as support for the
pose inverts the logic of both source metrics. Call it what it is: **pose drift**, or compute genuine
**Q against 6ULN** — which you can, because you have the crystal.

**(b) The reference frame is not even the Boltz pose.** In `run_md`, `ref` is captured **after**
minimisation → 2,500 steps of restrained equilibration → a 2,000-step throughput probe — i.e. ~18 ps of
dynamics past the predicted structure, including **8 ps of completely unrestrained relaxation**. So the
largest, fastest relaxation away from the Boltz pose happens *before* measurement starts and is excluded.
The chart label **"peptide RMSD from starting pose"** (`app/static/charts.js`) is therefore **wrong** — it is
RMSD from the post-equilibration pose. This systematically under-reports drift, in the direction that
flatters the result.

**(c) Hard cutoff, no switching function.** Best–Hummer–Eaton use the sigmoid specifically to avoid
**contact flickering**: a pair oscillating around 4.5 Å flips 0↔1 every frame, so the mean depends on the
frame-saving interval and thermal noise rather than on structure. `_contacts()` uses a bare `d < 0.45`. No
sensitivity analysis over the 4.0–5.0 Å range is reported.

**Fix:** rename to **Q (fraction of native contacts)**, define S against **6ULN**, use the Best–Hummer–Eaton
switching function, and report the cutoff sensitivity.

### E3. OBC2 implicit solvent — **the worst possible solvent model for a salt-bridge claim**

Your headline structural claim is a **p3-Asp ↔ Arg156 salt bridge**. Over-stabilising exactly that
interaction is GB's best-documented failure mode.

`implicit/obc2.xml` implements **Onufriev A, Bashford D, Case DA**, *Proteins* 2004;55(2):383–394,
DOI 10.1002/prot.20033, PMID 15048829 (= Amber `igb=5`). The relevant errors:

- **Geney R, Layten M, Gomperts R, Hornak V, Simmerling C**, *Investigation of Salt Bridge Stability in a
  Generalized Born Solvent Model*, **JCTC** 2006;2(1):115–127. DOI 10.1021/ct050183l. PMID 26626386.
  Verbatim: **"salt bridges are too stable by as much as 3−4 kcal/mol"**. Their fix reduces the intrinsic GB
  radii of **hydrogens bound to charged nitrogens** — i.e. the error is specifically in
  **guanidinium/ammonium groups. Arg156 is exactly the atom type at fault.** At 310 K, 3 kcal/mol is a
  **~130×** population over-weighting; 4 kcal/mol is **~660×**.
- **Roe DR, Okur A, Wickstrom L, Hornak V, Simmerling C**, *J Phys Chem B* 2007;111(7):1846–1857.
  Independently finds salt bridges too stable by 3–4 kcal/mol vs explicit TIP3P REMD.
- **Zhou R, Berne BJ**, *PNAS* 2002;99(20):12777–12782. DOI 10.1073/pnas.142430099. PMID 12242327.
  **"An overly strong salt-bridge effect between charged residues... is found to be responsible"** for the
  native structure ceasing to be the free-energy minimum. Implicit solvent **inverted** the native/non-native
  ranking because of spurious salt bridges.
- **Nguyen H, Roe DR, Simmerling C**, *JCTC* 2013;9(4):2020–2034. DOI 10.1021/ct3010485. PMID 25788871 —
  GB-Neck2 (`implicit/gbn2.xml`) exists because of these weaknesses. **You are using the older OBC2.**

**Zero ionic strength makes it worse, and it is a one-line omission.** OpenMM's `GBSAOBC2Force` defaults to
**`kappa = 0.0`** — zero salt, infinite Debye length, **completely unscreened** Coulomb attraction between
the Asp carboxylate and the Arg156 guanidinium. At physiological 150 mM the Debye length is 7.85 Å, so real
screening is partial but **not zero**. `implicitSolventKappa` is supported on this code path. Not setting it
compounds the 3–4 kcal/mol over-stabilisation instead of partly offsetting it.

**No explicit water, and pMHC grooves are water-mediated.** **Petrone PM, García AE**, *MHC-peptide binding
is assisted by bound water molecules*, **J Mol Biol** 2004;338(2):419–435. DOI 10.1016/j.jmb.2004.02.039.
PMID 15066441 — explicit MD of HLA-A2 found **14 waters bound longer than 1 ns** in the interface, forming
**"hydrogen bond bridges between MHC and peptide and filling empty spaces in the groove"**, concluding water
is an **"active mediator"**. See also **Smith KJ, Reid SW, Harlos K, et al.**, *Immunity* 1996;4(3):215–228,
PMID 8624812. GB-OBC2 has **zero** discrete waters, so the vacated space is filled by direct protein–protein
contacts — **which your metric then counts as persistent contacts.** The missing water and the inflated
contact count are the same artefact.

**The 1.8 nm cutoff is below OpenMM's own recommendation.** The OpenMM user guide: *"If you choose to use a
nonbonded cutoff with implicit solvent, it is usually best to set the cutoff distance larger than is typical
with explicit solvent. **A cutoff of 2 nm gives good results in most cases.**"* The mechanism matters: in
`GBSAOBC2Force` the Born-radius integral is a `ParticlePairNoExclusions` computed value and is therefore
**subject to the cutoff** — atoms beyond 1.8 nm contribute nothing to burial, so buried atoms are assigned
radii that are too small, i.e. treated as too solvent-exposed. At 6,088 atoms, `NoCutoff` is affordable.

**Bottom line: an Asp–Arg salt bridge observed in GB-OBC2 at zero ionic strength carries no independent
evidential weight.** The good news is that **you do not need the MD for this claim at all** — the salt bridge
is in the crystal structure at 2.73 Å and in the Boltz model at 2.58 Å **[reproduced]**. Cite those and drop
the MD from the salt-bridge argument entirely.

### E4. 10 ps restrained equilibration — **yes, laughably short**

| Study | Equilibration |
|---|---|
| Knapp 2018 (JCTC) | minimisation, then **500 ps** warming 0→310 K with position restraints |
| Ayres/Baker (JCIM 2017, Front Immunol 2019) | minimisation; heating with restraints **gradually relaxed 25 → 0 kcal/mol/Å² in NPT**; then **50 ps NVT** |
| Knapp 2014 | **first 10 ns of every 100 ns trajectory discarded** as relaxation |

**10 ps is 50× shorter than Knapp's restrained heating alone, 5× shorter than the Baker lab's final NVT step
alone, and 1000× shorter than Knapp 2014's discarded window.** Three specifics:

1. **A single flat 5 kcal/mol/Å² restraint with no ramp**, removed instantaneously. Both reference protocols
   *gradually release* restraints. The start of your production run **is** the relaxation transient — and
   you count it as data (well, you exclude it via the probe, which is its own problem: see E2b).
2. **Heavy-atom restraints for 10 ps relax essentially nothing but hydrogens** and the fastest side-chain
   librations. Backbone strain from the prediction and interface packing error are still present.
3. **500 minimisation steps is an arbitrary cap.** OpenMM's `minimizeEnergy()` defaults to
   `maxIterations=0` = iterate to convergence. For ~6,000 atoms with freshly added hydrogens and
   PDBFixer-modelled side chains, 500 will terminate on the iteration limit, not the gradient tolerance.
   Running to convergence costs seconds. There is no reason for the cap.

**Braun E, Gilmer J, Mayes HB, et al.**, *Best Practices for Foundations in Molecular Simulations*,
**Living J Comput Mol Sci** 2019;1(1):5957. DOI 10.33011/livecoms.1.1.5957. PMID 31788666 — the warning maps
onto this protocol almost word for word: *"It's easy to run several short MD simulations where (for example)
the composition of the system is varied, and conclude that any observed differences are a result of
variations in composition. But... even simulations started from the same structure but slightly different
initial positions or velocities will diverge over time."* That is **precisely** the mutant-vs-WT contact
persistence comparison.

**n=3 is below the published minimum.** Knapp, Ospina-Forero & Deane, *JCTC* 2018, based on **310,000 ns**:
**"a good rule of thumb is to perform a minimum of five to 10 replicas."** Their measured replicate-group
disagreement: 1 replica → 11.5% of total (19.7% with upper SD); 5 → 5.0%; 10 → 3.6%; 25 → 2.2%. Their
conclusion — a 20% effect from a single 100 ns run gives "no strong reason to believe that this
increase/decrease is true" — applies a fortiori at 1 ns.

### E5. Unequal trajectory lengths — **a design flaw that invalidates the comparison as stated**

`run_md` is **time-budgeted, not length-budgeted** (`total_steps = int(steps_per_s * remaining)`). The
consequence, from `results/md/*.json` **[reproduced]**:

| Run | production_ns | final peptide RMSD (Å) | contact persistence |
|---|---|---|---|
| mut r1 | **0.9967** | 1.41 | 0.765 |
| mut r2 | **0.6451** | 1.19 | 0.760 |
| mut r3 | **0.6430** | 2.13 | 0.769 |
| wt r1 | **0.9804** | 2.07 | 0.601 |
| wt r2 | **0.6425** | 3.38 | 0.697 |
| wt r3 | **0.6461** | 1.99 | 0.711 |

**"Final peptide RMSD" at 1.00 ns and at 0.64 ns are different quantities.** RMSD grows with time, so
comparing them across replicates — and reporting a mean and a range over them — is not valid. Contact
persistence is a mean over frames and is similarly length-dependent (and is biased high by construction,
since early frames are near-identical to the reference by definition).

**The "separates" claim is weaker than it looks.** `app/main.py` uses a min/max disjointness test:
mutant min 0.760 > wild-type max 0.711. With n=3 vs n=3, complete separation in a pre-specified direction has
an exact permutation p = 1/C(6,3) = **1/20 = 0.05** — borderline at best, on **one** peptide pair, with
unequal trajectory lengths, in a solvent model that over-stabilises the very interaction that distinguishes
them. The BUILD-GUIDE already says "suggestive, not a validated discriminator" — good — but the UI's
`separates: true` boolean does not carry that caveat, and the word "separates" will be read as a result.

**Minimum fix:** make the run **step-budgeted** so all replicates are the same length, and report the
per-replicate values (you already store them) rather than a mean over unequal runs.

### E6. Remaining protocol flags

- **`hydrogenMass = 4.0 amu`** is above AMBER's conventional ceiling of **3.024 amu**. The reason for that
  ceiling: at 4.0 amu a methyl carbon retains **3.04 amu — lighter than each of its three 4.0 amu
  hydrogens**, a mass inversion AMBER's documentation explicitly warns against. OpenMM's guide does show
  `4*amu`, so this is not off-label for OpenMM, but it is outside what **Hopkins CW, Le Grand S, Walker RC,
  Roitberg AE**, *JCTC* 2015;11(4):1864–1874, DOI 10.1021/ct5010406, PMID 26574392 validated. Reduce to
  3.0 amu or report it.
- **Friction 2/ps is 5× too low.** **Feig M**, *Kinetics from Implicit Solvent Simulations of Biomolecules
  as a Function of Viscosity*, *JCTC* 2007;3(5):1734–1748. DOI 10.1021/ct7000705. PMID 26627618: implicit
  solvent kinetics match explicit solvent and experiment at **~10 ps⁻¹**; lower friction accelerates
  sampling (local exploration by **4–5×**, barrier crossing by ~2×). Two consequences: (i) your "~1 ns" is
  an uncalibrated quantity, not 1 ns of physical time; (ii) fast local exploration **plus** GB-over-stabilised
  electrostatics means the Asp–Arg pair finds and locks the salt bridge quickly and stays — the speed-up and
  the artefact reinforce each other.
- **Good choice worth keeping:** you use `LangevinMiddleIntegrator`, which implements the LFMiddle
  discretisation and gives better configurational sampling than `LangevinIntegrator` at long timesteps.
  That is the right call at 4 fs.
- **HMR + `HBonds` is correct**, not a flaw — OpenMM's `hydrogenMass` transfers mass from the bonded heavy
  atom, conserving total mass, exactly as AMBER's `HMassRepartition` does.

### E7. The literature citation you repeat three times — **real, but you are quoting the worst half of it**

`neofold/md.py:7`, `app/main.py:472` and `BUILD-GUIDE.md` §6C all cite "the largest published study
(2,883 HLA-A2 peptides, 200 ns each) improved discrimination only from AUC 0.80 to 0.81."

**The study is real and your description is accurate as far as it goes:**
**Weber JK, Morrone JA, Kang S-g, Zhang L, Lang L, Chowell D, Krishna C, Huynh T, Parthasarathy P, Luan B,
Alban TJ, Cornell WD, Chan TA.** *Unsupervised and supervised AI on molecular dynamics simulations reveals
complex characteristics of HLA-A2-peptide immunogenicity.* **Brief Bioinform** 2024;25(1):bbad504.
DOI 10.1093/bib/bbad504. 2,883 complexes (1,038 immunogenic / 1,845 non-immunogenic), HLA-A*02:01,
**≥200 ns each, CHARMM36m + TIP3P explicit**, **first 30 ns discarded**. ✓ All verified.

**But the 0.80 → 0.81 comparison is the random split.** On the **debiased** split the same paper reports
**MD-graph AUC 0.80 vs sequence-only 0.61** — a **19-point gain** — and on 100-peptide subsets 0.69 vs 0.61.
`research/research-md-openmm.md:967` records this correctly; the three places that face a judge do not.

You are **under-claiming in a way that is still a misquotation**, and it is the kind a domain judge will
catch and then wonder what else was quoted selectively. State both splits: *"on a random split MD added
+0.01 AUC; on a debiased split it added +0.19 — and either way it took 200 ns per peptide in explicit
solvent, 200× our budget."* That is more honest **and** a better argument for why your 1 ns cannot claim
anything.

---

## Data provenance — three concrete defects in the demo inputs

### P1. The KIT D816V demo peptide is an exact self peptide — **fatal for that panel**

`app/main.py:135` labels `ICDFGLARV` **"KIT D816V — tumour"**. **[reproduced]** by direct search of the
reviewed human proteome (`data/reference/human_sp.fasta.gz`, 20,431 proteins):

| Peptide | Occurs verbatim in |
|---|---|
| **`ICDFGLARV`** (KIT D816V "mutant") | **MAPK1/ERK2 (P28482), residues 165–173** and **NLK (Q9UBE8), residues 280–288** |
| `GAGGVGKSA` (KRAS WT) | NRAS (P01111), HRAS (P01112), KRAS (P01116), RIT1 (Q92963), RIT2 (Q99578) |
| `GADGVGKSA` (KRAS G12D) | *no exact match*; nearest is `GAPGVGKSA` in RRAD (P55042), 1 mismatch |

`ICDFGLARV` is **not a neoantigen**. The DFG kinase motif is conserved across the kinome, so a KIT
kinase-domain peptide is shared with other kinases — ERK2 and NLK are ubiquitously expressed. T cells
against it are subject to central tolerance, and any therapeutic targeting it would be autoreactive. It
also has the largest fold change in the whole demo (**112×**, 177.7 nM vs 19,899 nM **[reproduced]**),
which makes it the perfect illustration of why fold change is not tumour specificity (§A5).

Your own new `neofold/selfsim.py` catches this correctly — but `PAIRS` in `app/main.py` and the structure
panel do not consult it. **Either wire `selfsim` into the structure panel, or drop the KIT case.** Leaving a
self peptide labelled "tumour" in a demo about tumour-specific antigens is the single most damaging thing
in the repo, and an immunologist will spot it in seconds.

*(Turning it into a deliberate negative control — "here is a high-fold-change candidate our self-filter
kills" — would be strictly better than removing it.)*

### P2. The demo VCF mixes genome builds

`data/demo/tumor_variants.vcf` declares `##reference=GRCh38`. Seven of eight rows are GRCh38 coordinates.
The KIT row is not:

| Variant | In file | GRCh38 | GRCh37 |
|---|---|---|---|
| KRAS G12D | chr12:25245350 C>T | 25245350 ✓ | 25398284 |
| TP53 R175H | chr17:7675088 C>T | 7675088 ✓ | 7578406 |
| BRAF V600E | chr7:140753336 A>T | 140753336 ✓ | 140453136 |
| PIK3CA H1047R | chr3:179234297 A>G | 179234297 ✓ | 178952085 |
| EGFR L858R | chr7:55191822 T>G | 55191822 ✓ | 55259515 |
| **KIT D816V** | **chr4:55599321 A>T** | **54733155** | **55599321 ← this is GRCh37** |

It does not change any result (the pipeline maps via `UNIPROT` + `HGVSP`, not coordinates) — which is
itself worth noting, because it means **the genomic coordinates are decorative**. But an incorrect
coordinate in a file that declares its build is a cheap, free thing for a judge to catch.

### P3. Thirteen synthetic rows have impossible coordinates

**[reproduced]** — in `tumor_variants_large.vcf`, 13 `synthetic_passenger` rows carry positions **beyond the
length of the chromosome they name**: e.g. `chr12:158380468` (chr12 is 133,275,309 bp), `chr17:195402784`
(chr17 is 83,257,441 bp), `chr4:194230199` (chr4 is 190,214,555 bp). They also use `N>N` for REF/ALT. Any
real VCF validator rejects the file. Harmless to your pipeline, trivially fixable, and exactly the kind of
detail that makes a reviewer distrust the rest.

### P4. Reference sequences are clean — **credit where due**

All seven proteins in `data/sequences/proteins.fasta` are **byte-identical to the current UniProt canonical
sequences** **[reproduced]** (P01116, P04637, P15056, P42336, P00533, P10721, P61769). The `apply_missense`
reference check is genuinely valuable and I could not break it. KIT numbering is correct: P10721 residue 816
is Asp, and residues 808–816 = `ICDFGLARD` **[reproduced]**, so the D816V register is right.

---

## F. What a sceptical immunologist would say

The eight most damaging criticisms, each with a citation and the best *honest* response. These are ordered
by how hard they are to answer, not by how likely they are to be asked.

### F1. "You have validated nothing. Your one case is in every model's training set."

**The charge.** 6ULN was released 2020-05-27 and is near-certainly in Boltz-2's training data. The KRAS
G12D/HLA-C\*08:02 epitopes have been in IEDB since 2016 and MHCflurry 2.0 trains on IEDB plus mass-spec
(O'Donnell TJ et al., *Cell Systems* 2020;11(1):42–48.e7, PMID 32711842). So "MHCflurry ranks both published
epitopes #1 and #2 of 38" is **circular**: the model was trained on the answer. Likewise the 0.509 Å RMSD.

**Best honest response.** "It is retrospective and we say so. It is a *system* test — VCF row to ranked
peptide to 3D structure to measured contact, offline, in under a minute — not an accuracy claim. The
accuracy claim we *can* make is narrow: we reconstruct a known complex to 0.5 Å on-device. For a real
accuracy claim you would need a temporal holdout against structures released after the training cutoff, and
we have not done that." **The README does not currently carry this caveat — only the BUILD-GUIDE does. Fix
that.**

### F2. "`ICDFGLARV` is in ERK2. You are showing me a self peptide labelled 'tumour'."

**The charge.** **[reproduced]** — the KIT D816V demo peptide occurs verbatim in MAPK1/ERK2 (P28482) and NLK
(Q9UBE8). It is not a neoantigen; T cells against it are centrally tolerised and a therapeutic targeting it
would be autoreactive. It also carries the demo's largest fold change (112×).

**Best honest response.** There is no good defence of shipping it as-is. The *good* move is to pre-empt:
**turn it into the demo's punchline.** "Here is a candidate with 112× differential agretopicity and a
textbook salt bridge — and our self-proteome filter kills it, because the DFG kinase motif is shared across
the kinome. This is why fold change is not tumour specificity." That converts your worst bug into your best
slide. `neofold/selfsim.py` already does the work; the structure panel just does not consult it.

### F3. "Presentation is not immunogenicity, and your own citation says you will be wrong 94% of the time."

**The charge.** Wells DK, van Buuren MM, Dang KK, et al. (Tumor Neoantigen Selection Alliance),
*Key Parameters of Tumor Epitope Immunogenicity Revealed Through a Consortium Approach Improve Neoantigen
Prediction*, **Cell** 2020;183(3):818–834.e13, DOI 10.1016/j.cell.2020.09.015, PMID 33038342. Verbatim:
*"608 peptides selected from among the top-ranked peptides from all groups… were tested for immunogenicity
by pMHC multimer-based assays and **37 (6%)** of those were found to be immunogenic."* **Your 37/608 is
correct.** Worse for the field: *"no team included more than 20 of the 37 immunogenic peptides in their top
100."*

**And TESLA names the features you omit.** Immunogenic pMHC had significantly stronger measured binding
affinity (p = 4×10⁻⁶), **higher tumour abundance (p = 0.01)**, **higher binding stability (p = 1.4×10⁻⁴)**,
and were **less** hydrophobic (p = 0.04). Their threshold set, verbatim: *"binding affinity less than
**34 nM**, tumor abundance greater than **33 TPM**, and binding stability greater than **1.4 h**"*, which
*"filtered out 93% of non-immunogenic peptides while maintaining 55% of immunogenic peptides."* Even then,
of the 286 peptides with all five features measured, **29 passed → 12 immunogenic / 17 not → PPV 0.41.**
Their closing summary: immunogenic epitopes *"have strong MHC binding affinity and long half-life, are
expressed highly, and have either **low agretopicity** or high foreignness"* — with the empirical cut at
**agretopicity < 0.1 (mutant ≥ 10× better than wild-type)**.

⚠️ **Use these numbers carefully:** TESLA's analyses used **measured** affinity and **measured** stability,
not predicted values. Quoting "34 nM" as a prediction threshold would be a misreading.

**Best honest response.** "We agree, and we never claim immunogenicity. We output a ranked hypothesis list
and we separate presentation from recognition from immunogenicity explicitly in the UI. TESLA also tells us
exactly what we are missing: of their five discriminating features we cover one and a half — affinity, and
mutation position only implicitly. We have no expression, no stability, and our agretopicity gate is 2×
against their empirical 10×." **This is the project's strongest ground — lean on it, and let TESLA write
your roadmap slide.**

### F4. "Your structural panel measures something you could read off the sequence."

**The charge, and it is the sharpest one available.** The "pre-registered contact" is: does peptide position 3
carry an Asp that reaches Arg156? **[reproduced]** across all four predicted structures, *every* peptide with
Asp at p3 formed the salt bridge (2.49–2.58 Å) and the one with Gly did not — because Gly has no side chain.
Boltz will build this contact for any p3-Asp peptide. So the measurement's output is a deterministic function
of `peptide[2] == 'D'`, and the 58 s of GPU structure prediction adds no information to it.

**Best honest response.** "Correct — for *this* contact, the chemistry is decidable from the sequence, and
that is precisely why we trust it: the wild-type failure is chemical, not predictive. The structure is a
communication and inspection layer, not a discriminator, and we say that in the UI. What the structure would
buy you is contacts that are *not* sequence-decidable — bulge conformation, p4–p8 side-chain orientation,
TCR-facing surface — and we do not currently measure any of those." Then measure one.

### F5. "One nanosecond of implicit-solvent MD tells you nothing, and it over-stabilises the exact bond you are claiming."

**The charge.** Two independent hits. (a) Knapp B, Ospina-Forero L, Deane CM, *JCTC* 2018;14(12):6127–6138,
DOI 10.1021/acs.jctc.8b00391 — *"a 100 ns TCRpMHC simulation is the current state of the art"*, and short runs
agree with each other **because of undersampling**, not convergence. (b) Geney R, Layten M, Gomperts R,
Hornak V, Simmerling C, *JCTC* 2006;2(1):115–127, DOI 10.1021/ct050183l, PMID 26626386 — GB makes salt
bridges **"too stable by as much as 3−4 kcal/mol"**, with the error localised to **hydrogens on charged
nitrogens**, i.e. exactly Arg156's guanidinium. OpenMM's GB default is **zero ionic strength**, so there is
no Debye screening either.

**Best honest response.** "We agree it cannot support a stability claim and the UI says so. But you have
found something worse than we stated: the solvent model specifically inflates the interaction our headline
depends on. The right fix is that the salt-bridge claim should not rest on MD at all — it rests on the
crystal structure at 2.73 Å and the prediction at 2.58 Å. We will cut MD out of that argument." **Do that.**

### F6. "ipTM 0.88 does not mean the model 'knows recognition is harder'."

**The charge.** ipTM is a self-assessment with a d₀ that depends on total complex size, so a 383-residue and
an 812-residue run are not on the same scale (Dunbrack RL Jr, bioRxiv 2025, DOI 10.1101/2025.02.10.637595,
PMID 39990437). And **your own wild-type ternary run refutes it [reproduced]**: TCR9d against the
non-recognised wild-type peptide scores TCR↔peptide ipTM 0.867/0.864 versus 0.880/0.879 for the cognate
G12D peptide, with a *higher* global ipTM (0.9489 vs 0.9468).

**Best honest response.** "You are right, and we have the control that proves it — we just drew the wrong
conclusion from it. The honest reading is the opposite of what we wrote: the ~0.88 is a property of the
interface, invariant to whether recognition actually occurs. That is a third independent demonstration that
Boltz confidence does not discriminate, this time at the recognition step." **Delete the claim, keep the
data, flip the conclusion. `tests/test_tcr.py::test_tcr_interfaces_are_less_confident_than_the_pmhc_core`
currently enshrines the wrong reading in a test.**

### F7. "You typed in one HLA allele. Patients have six, and they compete."

**The charge.** `run_triage(..., allele: str)` scores a single allele **[reproduced]**. A real patient has up
to six class I allotypes; a peptide presented by any one of them is a candidate, and peptides compete for
loading across them. HLA-C\*08:02 is also uncommon — the Tran 2016 result applies only to patients carrying
it, which is a small minority.

**Best honest response.** "It is a demo limitation, not an architectural one — the screen loops over
alleles trivially and MHCflurry supports 14,884 of them. What we have not modelled is inter-allele
competition, which nobody models well either. But we should stop drawing a patient-level funnel diagram off
a single-allele run."

### F8. "Your differential is agretopicity, not specificity — and it does not validate."

**The charge.** Two parts. (a) Terminology: "tumour-specific" means absent from the normal proteome, not
"binds better than wild-type" (§A5). (b) Evidence: Nibeyro G et al., *Front Immunol* 2023;14:1094236,
PMID 37564650 found **DAI AUC 0.56–0.59** with **no significant separation of immunogenic from
non-immunogenic peptides (P = 0.25)**.

**Best honest response.** "The terminology is wrong and we will fix it — it is differential agretopicity,
and we now have a self-proteome filter that tests actual specificity. On the evidence: that benchmark
conditions on peptides already known to be presented, so it shows DAI does not separate immunogenicity among
presented peptides, which is not the job we are using it for. We use it to avoid spending GPU time on
candidates whose wild-type binds just as well. That is a triage heuristic, and we should label it as one
rather than as the 'personalization signal'." (`neofold/screen.py:39` currently calls it exactly that.)

### Honourable mentions — smaller, but each is a free hit

- **"Which number is it?"** — 0.486 / 0.509 / 0.560 Å all circulate for one measurement (§D4).
- **"Your per-residue pattern is backwards."** — the guide says deviation is lowest in the middle; it is
  lowest at p2–p3 **[reproduced]** (§D5).
- **"Your 35× is a 22.6×."** — the guide compares a 10-mer mutant to a 9-mer wild-type (§below).
- **"Your VCF says GRCh38 and one row is GRCh37, and thirteen rows are off the end of the chromosome."** (§P2–P3)
- **"6ULN is TCR9d from Sim 2020, not a Tran 2016 TCR."** (§B3)
- **"You quoted the worse half of your own MD citation."** — 0.80→0.81 is the random split; the debiased
  split is 0.61→0.80 (§E7).

---

## G. The arithmetic error in BUILD-GUIDE §6B

Worth its own section because it is the one number on the "scientific heart of the demo" slide that is wrong.

The guide's neoantigen-specificity table reads:

| | Mutant (G12D) | Wild-type | Fold change |
|---|---|---|---|
| `GADGVGKSA` vs `GAGGVGKSA` | 74.1 nM | 3,656 nM | **49× stronger** |
| `GADGVGKSAL` vs **`AGGVGKSAL`** | 38.9 nM | **1,355 nM** | **35× stronger** |

**Row 1 is correct** — 3656.5 / 74.1 = 49.4 **[reproduced]**.

**Row 2 is wrong.** `GADGVGKSAL` is a **10-mer** spanning KRAS 10–19; its wild-type counterpart at the same
register is **`GAGGVGKSAL`** (10-mer, **876.9 nM**), giving **22.6×**. `AGGVGKSAL` is a **9-mer** — it is the
wild-type counterpart of a *different* candidate (`ADGVGKSAL`, which ranks 4th and is *deprioritised* with a
fold change of **0.4**). Two rows of the results table were crossed.

**[reproduced]** by running the project's own pipeline:

```
rank peptide      wt                  nM       wtnM    fold    pres   tier
   1 GADGVGKSAL   GAGGVGKSAL        38.9      876.9    22.6   0.950  investigate
   2 GADGVGKSA    GAGGVGKSA         74.1     3656.5    49.4   0.570  investigate
   3 VGADGVGKSAL  VGAGGVGKSAL      230.0      904.2     3.9   0.341  investigate
   4 ADGVGKSAL    AGGVGKSAL       3265.0     1355.4     0.4   0.136  deprioritised
```

The code in `neofold/variants.py::build_candidates` is **correct** — it takes
`reference[start-1 : start-1+len(pep)]`, which yields the same-register, same-length wild-type. Only the
hand-written guide table is wrong. Fix it to **22.6×**, which is still a strong number.

---

## H. Reproduction log

Everything marked **[reproduced]** was re-computed on 2026-09-24 from the repo as committed:

| Check | Command / source |
|---|---|
| Reference sequences vs UniProt | `rest.uniprot.org/uniprotkb/{acc}.fasta`, diffed against `data/sequences/proteins.fasta` — all 7 byte-identical |
| KRAS isoform | P01116 = 189 aa (**4A**); P01116-2 = 188 aa (**4B**); first divergence residue **151** |
| KRAS/KIT registers | computed from the stored FASTA |
| VCF coordinates | compared against GRCh38/GRCh37 positions and GRCh38 chromosome lengths |
| Screen ranking, fold changes | `neofold.screen.PeptideScreen.score()` on the 38 KRAS windows, `HLA-C*08:02` |
| MHCflurry columns | `Class1PresentationPredictor.predict(..., include_affinity_percentile=True)`, with and without real KRAS flanks |
| Salt-bridge distances | `neofold.contacts.measure_salt_bridge()` on 6ULN and all four shortlist models |
| Peptide RMSD | `neofold.validate.peptide_rmsd_vs_reference()` against `results/reference/6ULN.cif` |
| TCR clonotype | CDR3β extracted from `results/tcr/kras_tcr_ternary_model_0.cif` → `CASSLGQTNYGYTF` = TCR9d |
| WT ternary confidence | `results/tcr/confidence_kras_tcr_ternary_wt_model_0.json` |
| MD replicate lengths | `results/md/*.json` |
| Self-proteome search | `neofold.selfsim.SelfProteome` + independent direct search of `data/reference/human_sp.fasta.gz` (20,431 proteins) |

**Things I could not verify and am not asserting:**
- The **0.486 Å** MSA-run RMSD and the **0.748 Å** MSA MHC RMSD — no artefact in the repo produces them.
- The **2.52 Å** predicted salt-bridge distance in BUILD-GUIDE §6D — the repo model gives **2.58 Å**.
- **TAP quantification** — Peters B, Bulik S, Tampé R, van Endert PM, Holzhütter HG, *J Immunol*
  2003;171(4):1741–1749, PMID 12902473 is the right citation for TAP prediction, but I could not retrieve
  the sentence quantifying how much TAP adds on top of binding prediction. Do not quote a figure for it.
- **Neopepsee** and **antigen.garnish** WT/MT thresholds — not verified; not asserted anywhere above.
- **Łuksza 2017's typeset amplitude formula** — the semantics (Kd_WT/Kd_MT) are confirmed from multiple
  secondary descriptions, but PMC served a CAPTCHA, so do not quote a formula on this audit's authority.
- The **Sim 2020 correction** (*PNAS* 2020;117(44):27743–27744, PMID 33077608) is PDF-only and I could not
  read it. **Check it before quoting any figure-level number from Sim 2020.**

---

## I. Fix list, in priority order

Tiered by what a judge can catch and how much damage it does.

### Tier 1 — factually wrong, and cheap to fix. Do these first.

| # | Fix | Where |
|---|---|---|
| 1 | **Remove or repurpose the KIT D816V case.** `ICDFGLARV` is an exact self peptide (ERK2, NLK). Best move: keep it, wire `selfsim` into the structure panel, and relabel it as a deliberate negative control | `app/main.py` `PAIRS`, `NO_CONTACT_REASON`, structure panel |
| 2 | **Fix the 35× → 22.6×.** The guide compares a 10-mer mutant to a 9-mer wild-type | `BUILD-GUIDE.md` §6B |
| 3 | **Fix the per-residue claim.** Deviation is lowest at p2–p3, not "in the middle", and p9 is 0.62–0.67 Å, not 0.52 Å | `BUILD-GUIDE.md` §6A |
| 4 | **Fix the TCR attribution.** 6ULN's TCR is **TCR9d, patient 3995, Sim PNAS 2020** — not "the patient-derived TCR from Tran NEJM 2016" | `BUILD-GUIDE.md` §6E |
| 5 | **Pick one RMSD number.** 0.486 / 0.509 / 0.560 all circulate. Use the one the repo reproduces (**0.509 Å**) and name the model file | `README.md`, `BUILD-GUIDE.md` §6A, tests |
| 6 | **Fix "KRAS 4B".** You load P01116 canonical = **4A**. Say "residues 10–18/10–19, identical in 4A and 4B" | `tests/test_variants.py:14`, `BUILD-GUIDE.md` §5 |
| 7 | **Fix the KIT VCF coordinate** (GRCh37 in a GRCh38 file) and the 13 out-of-range synthetic rows | `data/demo/*.vcf` |
| 8 | **Fix the salt-bridge distance** 2.52 → **2.58 Å** | `BUILD-GUIDE.md` §6D |
| 9 | **Fix the Nibeyro/Buckley author attribution** and the three conflicting allele counts (14,884 / 20,246 / 14,993) | `research/`, `BUILD-GUIDE.md` |

### Tier 2 — overclaims to re-word. No code changes needed.

| # | Re-word | From → To |
|---|---|---|
| 10 | **Delete "the model knows recognition is harder."** Your own WT ternary run refutes it. Flip it into a third negative control | `BUILD-GUIDE.md` §6E, `tests/test_tcr.py` |
| 11 | **"tumour-specific" → "differential agretopicity"** everywhere it describes a fold change. Reserve "tumour-specific" for what `selfsim` tests | `screen.py` tier names + reasons, UI, charts |
| 12 | **Drop "the normal protein is invisible."** By allele-normalised percentile the WT 10-mer is a **weak binder** (1.055%) | `BUILD-GUIDE.md` §6B |
| 13 | **"neoantigen"/"neoepitope" → "candidate peptide"** for anything only predicted | UI, `README.md`, pitch |
| 14 | **"KRAS wild-type — normal tissue" → "KRAS wild-type (germline counterpart)"** | `app/main.py:129` |
| 15 | **Soften the structure verdicts.** "decisive" is too strong for both the contact and the screen; and the contact is sequence-decidable (§F4) | `app/main.py` `/api/compare` |
| 16 | **Quote both halves of the MD citation** — 0.80→0.81 random split *and* 0.61→0.80 debiased | `md.py`, `app/main.py`, `BUILD-GUIDE.md` |
| 17 | **Move the training-data caveat into the README.** Currently only the BUILD-GUIDE admits 6ULN is retrospective | `README.md` |
| 18 | **Say "predicted to be presented by", not "restricted by"**, for anything you predict | UI, docs |

### Tier 3 — methodology. Worth doing if there is time; worth *saying* either way.

| # | Change | Rationale |
|---|---|---|
| 19 | **Use `affinity_percentile`** (one keyword) alongside nM, and report the NetMHCpan-convention call | §A6 — the single highest-value technical change |
| 20 | **Supply flanks to MHCflurry.** You have them; costs ~3.3% PPV to omit. Never pass `""` | §C3 |
| 21 | **Cite the 2× threshold or run the sensitivity analysis** at 1×/2×/5×/10× | §C2 — pVACtools ships it off, TESLA's cut is 10× |
| 22 | **Make MD step-budgeted, not time-budgeted**, so replicates are comparable; report per-replicate values | §E5 |
| 23 | **Rename "contact persistence" → Q / fnat**, reference it to **6ULN** rather than your own pose, add the switching function | §E2 |
| 24 | **Cut MD out of the salt-bridge argument entirely.** GB over-stabilises salt bridges by 3–4 kcal/mol at zero ionic strength; the crystal and the prediction already make the point | §E3 |
| 25 | **Report DockQ** (with fnat) for the TCR interface, and per-residue peptide RMSD for the pMHC | §D1, §D2 |
| 26 | **Add an expression column**, even if the demo supplies it synthetically | §C6 — the most serious omission |
| 27 | Fix `hydrogenMass` 4.0 → 3.0 amu; friction 2 → 10 /ps; cutoff 1.8 → 2.0 nm or `NoCutoff`; minimise to convergence | §E3, §E6 |
| 28 | **Assert sequence identity before index-paired RMSD.** It is valid today by luck, and chain A is already off by one | `validate.py`, `tests/test_tcr.py` |
| 29 | Make a missing wild-type a distinct tier, not silently "not tumour-specific" (`nan >= 2.0` is `False`) | `screen.py` |
| 30 | Loop over all six class I alleles, or stop drawing a patient-level funnel from a single-allele run | `pipeline.py`, UI |

### What is genuinely good, and should be defended loudly

Not everything here is a criticism, and the project should not throw away its real strengths under
questioning:

- **The wrong-allele negative control** and the refusal to rank on Boltz confidence. This is the best thing
  in the project. Strengthen it with the Boltz-2 authors' own data: **ipTM vs affinity Pearson R = −0.07**
  (§D3).
- **The pre-registered contact discipline** — specifying the measurement in advance from a crystal structure,
  and refusing to measure anything for KIT because the mutation is at p9. That is real methodological
  hygiene, rare at a hackathon.
- **The pre-registered ensemble-spread negative result.** Testing your own proposed feature and publishing
  that it fails is a genuine credibility asset.
- **`apply_missense`'s reference check.** I tried to break it and could not; all seven sequences are
  byte-identical to UniProt.
- **The `UNSUPPORTED` list.** Explicitly naming frameshifts, indels, splice and fusion neoantigens as
  out of scope is exactly right.
- **`neofold/selfsim.py`**, including the subtlety that a neoepitope is by construction one mismatch from its
  own wild-type, so the WT must be excluded from the near-self search. That is a detail most pipelines get
  wrong. Now make the UI use it.
