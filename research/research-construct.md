# Polyepitope construct assembly: published, citable design parameters

**Research date:** 2026-09-25 · **Audience:** the engineer adding a construct-assembly step after
`rank_for_structure()` in `neofold/screen.py`.

**Scope discipline.** This document exists so that a construct-assembly step can be implemented as
**deterministic assembly of a research artifact for expert review**. Every parameter below is traced to a
primary source. Where a parameter is *proprietary and unpublished*, it says so and says what to do
instead. Nothing here supports a therapeutic, manufacturing, or efficacy claim — see §5, which is the
most important section in the file.

---

## 0. TL;DR — ten decisions

1. **Copy the BioNTech pentatope, not a minimal-epitope string.** Published architecture: **27-mer
   stretches, mutation at position 14, five per RNA molecule, joined by non-immunogenic 10-mer
   glycine/serine linkers, flanked N-terminally by an MHC-class-I signal peptide (sec) and
   C-terminally by the MHC class I trafficking domain (MITD)**. Sahin et al. *Nature* 2017; construct
   spelled out in Vormehr et al. *J Immunol Res* 2015. The linked format itself is validated: the
   pentatope RNA was **more immunogenic than an equal-amount mixture of the same epitopes as separate
   RNAs** (Kreiter et al. *Nature* 2015;520:692–696). **But the exact 10-mer linker string is not
   published** — the patent's example is `GGSGGGGSG` (9 aa), and `GGSGGGGSGG` could not be confirmed
   anywhere. §1.1, §7.1

2. **Do not assemble minimal 9-mers.** The long-peptide length is not cosmetic: exact 8–10-mers in
   adjuvant induce a *vanishing* CTL response because they load directly onto MHC-I of non-professional
   APCs, whereas ≥25-mers must be taken up and processed by professional APCs. Bijker et al.
   *J Immunol* 2007;179:5033–5040. §3.0

3. **Order first, linker only where a junction needs one — and then use the published G/S linker.**
   This is the corrected recommendation. For long stretches in native flanking context, the best
   *experimental* evidence says linkers add nothing: AAY helped 9-mers but **not** 20-mers (Li et al.
   *Genome Med* 2021), and a direct linker-vs-no-linker test with immunopeptidomic readout found the
   **no-linker** cassette recovered **more** neoepitope–HLA pairs, with G/S linkers causing a
   **translation drop-off after ~20 antigens** (Gurung et al. *Nat Biotechnol* 2024). Junction-free
   orderings are usually abundant (Lee et al. 2010), so most junctions will not need anything. §2.1a

4. **Never default to AAY. No primary paper ever established it.** Its citation chain runs through a
   review with no AAY data, and two models rank it below optimised spacers — one ranks it **below no
   spacer at all** on neo-epitope creation (Schubert & Kohlbacher *Genome Med* 2016: 4.31 vs 3.37), and
   JessEV found it **costs 85–95 % of achievable effective immunogenicity** (Dorigatti & Schubert 2020).
   And **GPGPG is contraindicated near a class I junction**: G and P C-flanks specifically inhibit the
   adjacent epitope (Bergmann et al. *J Immunol* 1996). §2.1b, §2.2

5. **Junctional epitopes are real, and there is one decisive primary experiment — cite it.** Livingston
   et al. *J Immunol* 2002;168:5499–5506: the epitope arrangement *created* a high-affinity class II
   junctional epitope (Gag171/Pol335), it raised its own ELISPOT response, the four intended responses
   were lost, and **GPGPG insertion restored all four**. Separately, Cornet et al. *Vaccine* 2006: of
   **all six** orderings of three epitopes, **only one** gave a trispecific response. §2.3

6. **Implement ordering as pvacvector's algorithm, not as our own invention.** Directed graph over
   peptides; an edge A→B exists iff no junction k-mer of A|B is a well-binder; simulated annealing for a
   Hamiltonian path; on failure escalate spacer → clip (≤3 aa default, never into the binding core) →
   exclude peptides (default ≤2). Its junction test is **`left[-(k−1):] + spacer + right[:k−1]`**, so every
   k-mer spans the junction; thresholds **500 nM *or* percentile < 2.0, failing on either**; class I k =
   8–11. **At n=5 we can enumerate all 120 orderings exactly** and skip the annealing. Hoang, Kiwala
   et al. 2026 (pVACtools v6); Hundal et al. *Cancer Immunol Res* 2020;8:409–420. §2.4, §2.5

7. **sec/MITD: the real sequences ARE published — use them.** The BNT122 phase 1 Methods (*Nat Med*
   2025, PMC11750724, open access) print **sec = `MRVMAPRTLILLLSGALALTETWAGS`** (26 aa) and
   **MITD = `IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA`** (55 aa), citing Kreiter et al.
   *J Immunol* 2008;180:309–318 for the design. They cross-check **exactly** against the independent
   patent base counts (78 bp and 168 bp incl. stop). The **linker length** is likewise confirmed twice
   (30 bp = 10 aa) but **its sequence is still unpublished**. §3.1

8. **mRNA elements: publish what is public, refuse to fake what is not.** Citable: Holtkamp 2006 (2×
   β-globin 3′ UTR, 120-nt poly(A), free 3′ terminus), von Niessen 2019 (AES 136 nt – mtRNR1 142 nt),
   the named vector `pST1-Sp-MITD-2hBgUTR-A120` (Kreiter 2015 Methods), the segmented poly(A)
   `A30–GCATATGACT–A70` and its rationale (**EP 3 167 059 B1** — it is a *plasmid-stability* fix, not a
   translation one), and the **β-S-ARCA(D1)** cap (Kuhn 2010). Proprietary: the cancer-vaccine UTRs as
   nucleotides, the clinical LPX process, and every codon table. Autogene cevumeran is
   **nucleoside-*un*modified uridine mRNA** — its Methods literally list "ATP, CTP, **UTP**, GTP". It is
   not m1Ψ, and that is deliberate. §4

9. **Emit a construct record, not a manufacturing file.** Amino-acid construct + linker provenance +
   junction-screen report + every honesty caveat in §5, machine-readable. No "order this" affordance,
   no GMP language, no dose.

10. **The single blunt caveat that must be on the artifact:** in August 2026 BioNTech **terminated** the
   randomised Phase 2 of autogene cevumeran in resected ctDNA+ colorectal cancer after the futility
   boundary was crossed, with a **numerical overall-survival imbalance between arms**. The modality is
   not established. §6.4

---

## 1. Real clinical constructs

### 1.0 Master table

| Parameter | **BioNTech IVAC MUTANOME** (Sahin 2017) | **BNT122 / autogene cevumeran** | **Moderna mRNA-4157 / V940 (intismeran autogene)** | **NeoVax** (Ott 2017) | **NEO-PV-01** |
|---|---|---|---|---|---|
| Modality | Unmodified-uridine mRNA, intranodal | Unmodified-uridine mRNA–lipoplex (RNA-LPX), IV | Nucleoside-modified mRNA in LNP, IM | Synthetic long peptides, SC | Synthetic long peptides, SC |
| Neoepitopes / patient | **10** | **up to 20** | **up to 34** (range 9–34; 91 % got 34) | **up to 20** | **up to 20** |
| Molecules per dose | **2 RNAs × 5 epitopes** ("pentatope") | **2 mRNA strands × up to 10 epitopes** | **1** single concatemeric mRNA | up to **4 peptide pools** | up to **4 peptide pools** |
| Epitope stretch length | **27 aa**, mutation at **position 14** | 15-mers used for read-out; stretch length not stated in the paper | not published ("optimised concatemeric") | **15–30 aa** (protocol: 17–26 aa) | **~14–35 aa** |
| Joined by | **non-immunogenic 10-mer glycine/serine linkers** | **"short glycine- and serine-rich linkers"** | **not published**; patent family claims protease-cleavable spacers (GFLG, KVSR, TVGLR, PMGLP, PMGAP) | n/a — separate peptides | n/a — separate peptides |
| Flanking / trafficking | **sec** (MHC-I signal peptide) N-term + **MITD** C-term | **sec `MRVMAPRTLILLLSGALALTETWAGS` (26 aa) + MITD `IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA` (55 aa)** — sequences published | not published; patent family mentions sec/MITD, LAMP-1, Ii, ubiquitin | n/a | n/a |
| Adjuvant / vehicle | naked RNA, intranodal | DOTMA/DOPE lipoplex, ~400 nm | LNP: SM-102, PEG2000-DMG, DSPC, cholesterol | **poly-ICLC 0.5 mg/pool** | poly-ICLC |
| Dose | escalating, intranodal | **25 µg × 9 IV** (PDAC); 15–100 µg in Ph1 | **1 mg IM × ≤9**, alternating limbs | **0.3 mg/peptide**, 4 pools | 4 sites × 1.5 mL |
| n | 13 | 16 (PDAC); 213 (solid-tumour Ph1) | 107 vaccinated (KEYNOTE-942) | 6 | 34 (Ph1b) / 114 (NSCLC Ph2) |

### 1.1 BioNTech IVAC MUTANOME — the published layout (epitope geometry)

> "Ten selected mutations per patient were engineered into two synthetic RNAs, each encoding **five
> linker-connected 27-mer peptides with the mutation in position 14** (pentatope RNAs)."

> "Mutated sequences (Mut1–5) encoding **27 amino acids with the mutation in the center** are separated
> by **nonimmunogenic 10 mer glycine/serine linkers**." … "flanked by **a signal peptide and the MHC
> class I trafficking domain (MITD**, transmembrane, and cytoplasmic domain of MHC class I) to ensure
> optimal antigen presentation."

- **Primary:** Sahin U, Derhovanessian E, Miller M, et al. *Personalized RNA mutanome vaccines mobilize
  poly-specific therapeutic immunity against cancer.* **Nature** 2017;547:222–226.
  doi:10.1038/nature23003 · PMID 28678784 · NCT02035956.
- **Construct detail (open access, use this one for the architecture):** Vormehr M, Schrörs B, Boegel S,
  Löwer M, Türeci Ö, Sahin U. *Mutanome Engineered RNA Immunotherapy: Towards Patient-Centered Tumor
  Vaccination.* **J Immunol Res** 2015;2015:595363. doi:10.1155/2015/595363 · PMC4710911.
- **Patent-level linker language:** BioNTech, *Individualized vaccines for cancer*, US 10,738,355 B2 —
  linkers are "enriched in glycine and/or serine", "at least 50 % … at least 95 % of the amino acids of
  the linker are glycine and/or serine", example **`GGSGGGGSG`**; "poly(A)-tail consisting of **120
  nucleotides**"; 5′-cap analog.

**Verification of the ~27-mer claim: confirmed.** 27 aa with the mutation at position 14 means 13
wild-type residues either side — enough to contain every 9-, 10- and 11-mer register through the
mutation, which is exactly why the length is chosen. It is **not** a minimal 9-mer design.

**Numbers, for the record:** 13 patients, stage III/IV melanoma; up to 20 doses; T-cell responses
against **60 %** of vaccine neoepitopes, every patient responding to ≥3 mutations; 8/13 tumour-free at
23 months; 5 had relapsed *before* neoepitope vaccination started; 2 objective responses, 1 complete
response after sequential vaccine + anti-PD-1.

### 1.2 BNT122 / autogene cevumeran — the best construct-level source in the literature

- **Architecture (open access, quote it):** "up to **two 5′-capped single-stranded uridine-based mRNA
  molecules** (together encoding **up to 20 neoantigens** per patient)"; "Neoantigens are flanked by an
  **N-terminal SEC and an HLA class I trafficking domain (MITD**, transmembrane and cytoplasmic domain
  of HLA class I)"; joined by "**short glycine- and serine-rich linkers**"; "encapsulated in a lipoplex
  formulation (RNA–LPX)". — *Autogene cevumeran with or without atezolizumab in advanced solid tumors:
  a phase 1 trial.* **Nat Med** 2025 · PMC11750724. Dose levels 15–100 µg IV.
  **This paper's Methods are the single best construct-level source in the literature**, and they give
  more than the figure legend does: two synthetic DNA fragments each coding ≤10 neoantigen targets,
  *"connected by **30 bp** non-immunogenic glycine and serine linkers"* (= **10 aa**, independently
  confirming Vormehr 2015's "10 mer"), cloned into a starting vector containing **sec**
  (`MRVMAPRTLILLLSGALALTETWAGS`) and **MITD**
  (`IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA`); IVT with T7 polymerase in the presence of
  *"ATP, CTP, **UTP**, GTP and **β-S-ARCA(D1)** cap analog"*. The clinical liposome step is *"an adopted
  proprietary protocol"*. See §3.1 and §4.
  Note also: the construct-level statements are consistent across the whole BNT122 series — the 3-year
  PDAC follow-up calls it *"backbone-optimized uridine mRNA–lipoplex nanoparticles"* (Sethna 2025), and
  the adjuvant TNBC report describes *"two strings of **immunostimulatory, non-nucleoside-modified uridine
  mRNA**"* with **27-mers centred on the changed residue**, and frameshifts encoded from the changed
  residue to the next stop (*Nature* 2026;651:1088–1096, PMC13017525).
- **PDAC trial:** Rojas LA, Sethna Z, Soares KC, et al. *Personalized RNA neoantigen vaccines stimulate
  T cells in pancreatic cancer.* **Nature** 2023;618:144–150. doi:10.1038/s41586-023-06063-y ·
  PMC10171177. "**two uridine-based mRNA strands**", "each strand encoded **up to 10 MHCI and MHCII
  neoepitopes**", "up to 20 MHCI and MHCII restricted neoantigens", **nine 25 µg intravenous doses**,
  lipoplex ~400 nm of **DOTMA + DOPE**.

The PDAC paper does **not** state the epitope stretch length. It gives 15-mers for ELISpot read-out and
8–14-mers as the minimal predicted neopeptides — those are assay reagents, not the construct. Do not
cite them as the construct's stretch length.

### 1.3 Moderna mRNA-4157 / V940 (intismeran autogene)

- **Primary:** Weber JS, Carlino MS, Khattak A, et al. *Individualised neoantigen therapy mRNA-4157
  (V940) plus pembrolizumab versus pembrolizumab monotherapy in resected melanoma (KEYNOTE-942): a
  randomised, phase 2b study.* **Lancet** 2024;403:632–644.
  doi:10.1016/S0140-6736(23)02268-7 · NCT03897881.
- Construct, verbatim: "mRNA-4157 is an mRNA-based individualised neoantigen therapy encoding **up to 34
  neoantigens** in a lipid nanoparticle formulation"; "The top amino acid candidates were incorporated
  into an **optimised concatemeric mRNA-4157 sequence (long, continuous mRNA molecule)**".
- **The 34 figure is verified**, and so is its spread: "**91 % of patients received mRNA-4157 with 34
  neoantigens (range 9–34 neoantigens)**".
- Dosing: **1 mg IM, alternating limbs, maximum nine doses**, synchronised to 3-weekly pembrolizumab 200 mg.
- LNP: SM-102, PEG2000-DMG, DSPC, cholesterol (same four lipids as mRNA-1273).
- **Linkers, UTRs, codon strategy and the selection algorithm are all proprietary.** The paper says
  "proprietary, automated in-house bioinformatics system" and puts the algorithm in an appendix figure.
  Do not invent a Moderna linker.
- **Patent family (citable, but it is a patent, not a validated product spec):** ModernaTx,
  *Concatemeric peptide epitope RNAs*, US 2022/0152178 A1 (priority 2015-07-30; Ciaramella, Huang,
  Valiante, Zaks). Claims **2–100 epitopes of 9–30 aa** (also "25–35 aa with a centrally located SNP",
  and "**31 amino acids** with a centrally located SNP and 15 flanking amino acids each side"), joined by
  **cleavage-sensitive sites**: `GFLG` (SEQ ID 1), `KVSR` (SEQ ID 2), `TVGLR` (SEQ ID 3), `PMGLP`
  (SEQ ID 4), `PMGAP` (SEQ ID 5) — cathepsin B/S-sensitive. And explicitly: "the mRNA encoding the
  peptide epitopes is arranged such that the peptide epitopes are **ordered to minimize
  pseudo-epitopes**."

### 1.4 NeoVax (Ott et al. 2017) — the peptide-pool comparator

- **Primary:** Ott PA, Hu Z, Keskin DB, et al. *An immunogenic personal neoantigen vaccine for patients
  with melanoma.* **Nature** 2017;547:217–221. doi:10.1038/nature22991.
- **up to 20 long peptides per patient**, **15–30 aa** (trial protocol: 30 candidate peptides of 17–26
  aa selected and prioritised, maximum 20 formulated), in **≤4 pools** (3–4 peptides per pool),
  **0.3 mg of each peptide + 0.5 mg poly-ICLC per pool in 1 mL**, SC on **days 1, 4, 8, 15, 22** then
  **weeks 12 and 20**. 6 patients.
- **The immunogenicity split is the single most useful number in this paper for us:** across 97 unique
  neoantigens, vaccine-induced **CD4+ T cells targeted 58 (60 %)** and **CD8+ T cells only 15 (16 %)**.
  A long-peptide/long-stretch construct is predominantly a CD4 vaccine. The follow-up (Hu et al.
  *Nat Med* 2021, PMC8273876) reports the same shape: CD8 responses against **15/117 IMP (13 %)**,
  CD4 against **69/124 IMP (56 %)**.
- Outcome: 4/6 recurrence-free at 25 months; 2 progressors regressed on subsequent anti-PD-1.

### 1.5 NEO-PV-01

- **up to 20 synthesised peptides of ~14–35 aa**, formulated in **up to 4 pools** with poly-ICLC;
  vaccination begins at **week 12** (five priming immunisations over three weeks, boosts at weeks 19
  and 23), on a nivolumab backbone.
- Ott PA, et al. *A Phase Ib Trial of Personalized Neoantigen Therapy Plus Anti-PD-1 in Patients with
  Advanced Melanoma, Non-small Cell Lung Cancer, or Bladder Cancer.* **Cell** 2020;183:347–362.e24.
- NSCLC first-line: *Cancer Cell* 2022;40:1010–1026 (S1535-6108(22)00359-2).

---

## 2. Linkers, and the junctional-epitope problem

### 2.0 What the clinical products actually use

Only one linker family is used by a clinical personalised-vaccine construct whose architecture is
published: **glycine/serine-rich**. IVAC MUTANOME: "nonimmunogenic 10 mer glycine/serine linkers".
Autogene cevumeran: "short glycine- and serine-rich linkers". BioNTech's patent example:
**`GGSGGGGSG`** (9 aa) with the claim that ≥50–95 % of linker residues are G and/or S.

`(G4S)n` — `GGGGSGGGGS` — is the standard flexible-linker idiom, inherited from single-chain antibody
engineering (**Huston JS, et al. *PNAS* 1988;85:5879–5883**, PMID 3045807 · PMC281868), and is used in
academic MITD constructs as "(G4S)2". Note what Huston 1988 actually is: a **15-amino-acid linker in an
anti-digoxin single-chain Fv**, with **zero** antigen-processing or junctional-epitope content. (Even the
exact `(GGGGS)3` string is conventional attribution — the primary source states "a 15-amino acid linker".)

**None of the three candidate strings is confirmed as the clinical linker.** What is published is the
*description* — "nonimmunogenic 10 mer glycine/serine linkers" (Vormehr 2015) — and a *patent example*,
`GGSGGGGSG` (9 aa, US 10,738,355 B2). `GGSGGGGSGG` circulates widely and traces to no primary source.

### 2.1 Linker table, graded by evidence quality

| Linker | Claimed role | Class | Primary citation | Verdict |
|---|---|---|---|---|
| **None** (direct fusion, native flanks) | no foreign residues; shortest construct | I + II | Li et al. *Genome Med* 2021;13:56 · Gurung et al. *Nat Biotechnol* 2024;42:1107–1117 | **Strongest modern evidence for long stretches.** See §2.1a. `"None"` is also the *first* entry in pvacvector's default spacer list. |
| **G/S 10-mer** (`GGSGGGGSG`, `GGGGSGGGGS`) | flexible, non-immunogenic separator | I + II | Huston et al. *PNAS* 1988;85:5879–5883 (origin: scFv engineering) · used in the clinical RNA products (Vormehr 2015; Rojas 2023) | **Use this when a linker is needed** — on *provenance*, not mechanism. Huston 1988 is antibody engineering with no antigen-processing data; the G/S *choice* is separately defensible because G and P are poor MHC anchors and poor proteasome substrates (Bergmann 1996). |
| **GPGPG** | destroys junctional class II epitopes | **II only** | **Livingston et al. *J Immunol* 2002;168(11):5499–5506** (PMID 12023344) | **The best-evidenced linker in the field** — see §2.3. But Bergmann 1996 shows G and P C-flanks *actively inhibit* the adjacent class I epitope, so **GPGPG is contraindicated near a class I junction.** Our pipeline screens class I. |
| **AAY** | "proteasome cleavage site" | nominally I | **none** — see §2.1b | **Convention, sustained by mis-citation.** Scores *worse than no spacer* on neo-immunogenicity (Schubert & Kohlbacher 2016) and costs 85–95 % of achievable effective immunogenicity (Dorigatti & Schubert 2020). **Do not default to it.** |
| **Oligo-alanine (`AAA`)** | spaces an insert from disruptive neighbours | I | **Del Val et al. *Cell* 1991;66:1145–1153** | Real primary evidence, and the actual basis for the "AA" in AAY. |
| **KK / RR / RK** | dibasic endopeptidase/cathepsin site | II | **Schneider et al. *J Immunol* 2000;165(1):20–23** · **Zhu et al. *J Immunol* 2005;175(4):2252–2260** | **Mechanism well-evidenced** (inserting a dibasic motif converts cryptic class II determinants into presented ones), but neither paper tested a polyepitope construct or KK *between* two epitopes. The common "KK for B-cell epitopes" usage has **no primary support**. |
| **Furin sites (`RVKR`, `REKR`)** | TAP-independent secretory-pathway cleavage | I | **Lu et al. *J Immunol* 2004;172(7):4575–4582** | **Clean positive/negative control pair**: furin-*sensitive* linkers released all epitopes; furin-*resistant* linkers released none. Aurisicchio 2014 found furin/REKR **beat AAY**. But Li 2021: "furin cleavage sites are not required for robust neoantigen presentation." |
| **`GFLG`, `KVSR`, `TVGLR`, `PMGLP`, `PMGAP`** | cathepsin B/S-cleavable | I + II | ModernaTx US 2022/0152178 A1 | Citable as *claimed in a patent*, not as validated. |
| **`HH`, `HHH`, `HHHH`, `HHC`, `HHL`, `HHAA`, `HHHD`, `HHHC`, `AAL`, `GGS`** | junction-breaking candidates | — | **none exists** | These are pvacvector's `--spacers` defaults. **No primary citation exists for any of them** — the pVACtools docs give none. Engineering conventions; the unstated rationale is presumably that His is a poor MHC anchor. Citable only as "pvacvector's default candidate set". |
| **`EAAAK`** | rigid α-helical separator | — | Arai et al. *Protein Eng* 2001;14:529–532 | **A GFP FRET experiment.** No immunological or antigen-processing data whatsoever. Its ubiquity in in-silico vaccine papers is unsupported extrapolation. |

**The class I / class II split is half-supported, and it is the AAY half that fails.** GPGPG-for-class-II
rests on Livingston 2002, a real causal experiment. "G and P are bad for class I" rests on Bergmann 1996.
So *avoiding GPGPG at class I junctions* is well-founded. *Using AAY at class I junctions* is not.

**The unresolved tension in the G/S linker — state it, do not paper over it.** Bergmann 1996 supports two
*opposite* readings of glycine in a class I context, and both are correct:

| Glycine is… | Consequence | Direction |
|---|---|---|
| a poor MHC anchor residue | a G-rich junction is **unlikely to create a new binder** | **good** — this is what our junction screen measures |
| a poor proteasomal C-flank ("G and P specifically inhibited recognition of the adjacent amino-terminal epitope") | a G-rich linker may **impair liberation of the epitope upstream of it** | **bad** — and our junction screen cannot see this at all |

So a G/S linker optimises the thing we can measure and may degrade the thing we cannot. The clinical
products accept that trade (and Kreiter 2015 shows the linked pentatope still outperformed separate RNAs),
but **our screen is blind to the second column**, and the artifact must say so. MHCflurry's
`processing_score` is a weak proxy at best — it is a presentation-pathway model, not the PCM/NetChop
cleavage model that the Schubert/Kohlbacher line uses for exactly this purpose. This is the strongest
argument in the document for the **no-linker default** (§2.1a): direct fusion keeps the epitope's *native*
C-flank, which is the context in which it was predicted in the first place.

### 2.1a The finding that should change our default: for long stretches, no linker

Three independent lines of primary evidence say linkers are unnecessary — or harmful — when epitopes are
delivered as **long peptides in native flanking context**, which is exactly our case (27-mers).

1. **Li L, Zhang X, … Gillanders WE.** *Optimized polyepitope neoantigen DNA vaccines elicit
   neoantigen-specific immune responses in preclinical models and in clinical translation.*
   **Genome Med** 2021;13:56. PMID 33879241 · PMC8059244.
   They set out to test whether spacers help, using **AAY** (cited to Velders 2001). Result: AAY
   increased surface presentation for **9-mer** constructs but **not** for the **20-mer** construct.
   Verbatim: *"we found that epitopes flanked by natural sequences can be processed and presented
   effectively and **adding a linker does not further enhance antigen presentation**"*; also **"furin
   cleavage sites are not required for robust neoantigen presentation."** They use pVACvector for
   ordering instead.
2. **Gurung HR, … Rose CM.** *Systematic discovery of neoepitope-HLA pairs for neoantigens shared among
   patients and tumor types.* **Nat Biotechnol** 2024;42:1107–1117. PMID 37857725 · PMC11251992.
   **A direct linker-vs-no-linker head-to-head with immunopeptidomic (HLA-IP + MS) readout.** 47
   neoantigens as ~25-aa segments, concatenated either **directly** or with **short G/S linkers**, across
   15 monoallelic HLA lines. Findings: Ribo-Seq showed consistent translation across the no-linker
   cassette, but **a substantial decrease in translation after ~20 neoantigen sequences in the
   linker-containing cassette**; six extra neoepitope–HLA pairs were recovered from the no-linker
   cassette in that region; overall the **no-linker cassette yielded more neoepitope–HLA pairs**; and for
   epitopes seen in both, presentation went **up for some and down for others — no consistent benefit**.
3. **NeoDesign** (Yu W, et al. **Bioinformatics** 2024;40(10):btae585, PMID 39331572 · PMC11471261) is
   built on this premise: linkers lengthen the mRNA (faster degradation) and their repetitive sequences
   can form hairpins that impede translation. **62 of its 100 designs contain zero linkers**, against
   "10 to 20 linkers per sequence" for pVACvector.
4. Clinical-stage precedent for native-context, linker-free cassettes: Gritstone's GRANITE/SLATE
   (Palmer CD, et al. **Nat Med** 2022;28:1619–1629).

**But note the countervailing clinical fact**: the BioNTech pentatope *does* use a 10-mer G/S linker, and
**Kreiter et al. *Nature* 2015;520:692–696** (PMID 25901682 · PMC4838069) showed the pentatope RNA was
**more immunogenic than an equal-amount mixture of the same epitopes delivered as separate RNAs** — i.e.
the linked format itself is validated, with that linker in it.

**Resolution for us (§7.2):** follow the VaccineCAD / NeoDesign / pvacvector policy — **order first with
no linker; insert the published G/S 10-mer only at junctions that reordering cannot clean.** That is
simultaneously the evidence-aligned position and consistent with clinical provenance, and it is literally
what pvacvector's `"None"`-first spacer list does.

### 2.1b AAY's citation chain, traced — and where it breaks

Worth recording because it is a cautionary example of exactly the failure mode this document exists to
avoid.

- **The paper everyone cites for AAY** is Velders MP, … Kast WM. *Defined flanking spacers and enhanced
  proteolysis is essential for eradication of established tumors by an epitope string DNA vaccine.*
  **J Immunol** 2001;166(9):5366–5373 (PMID 11313372). What it actually shows: spacered construct
  protected **100 %** of mice vs **50 %** unspacered; ubiquitin fusion was additionally needed to
  eradicate 7-day tumours. It compares **"defined spacers" against "no spacers" — not AAY against other
  spacers.**
- **The real mechanistic basis** is two earlier papers: Del Val et al. **Cell** 1991;66:1145–1153
  (oligo-alanine rescues a poorly processed insert), and **Bergmann CC, Yao Q, Ho CK, Buckwold SL.
  *Flanking residues alter antigenicity and immunogenicity of multi-unit CTL epitopes.* J Immunol
  1996;157(8):3242–3249** (PMID 8871618) — a genuine single-residue head-to-head: aromatic (Y), basic
  (K) and small aliphatic (A) C-flanks supported efficient CTL recognition, while **acidic and
  helix-breaking residues (G, P) specifically inhibited recognition of the adjacent N-terminal epitope**,
  with precursor ratios varying **up to 50-fold** with molecular context. Also Livingston BD, et al.
  *Optimization of epitope processing enhances immunogenicity of multiepitope DNA vaccines.* **Vaccine**
  2001;19:4652–4660 — the residue immediately C-terminal to the epitope dominates immunogenicity, which
  can be modulated by inserting a *single* amino acid.
- **The canonical AAY(class I) + GPGPG(class II) construct** is Depla E, et al. **J Virol**
  2008;82(1):435–450 (PMID 17942551 · PMC2224390) — 30 CTL + 16 HTL epitopes, MS-confirmed presentation.
  It shows the combination *works*; it does not show it is optimal.
- **Where it breaks.** de Oliveira LM, et al. *PLoS One* 2015;10(9):e0138686 justifies AAY as "a proper
  substrate for proteasome mediated cleavage" citing **Pardoll DM, *Nat Rev Immunol* 2002;2:227–238** —
  a general review containing no AAY data. Aurisicchio et al. 2014 attach their AAY citation to
  **Rodriguez et al. *J Virol* 1998**, a paper about *ubiquitination*. And most tellingly, Dam S, et al.
  **Sci Rep** 2025;15:10586 (PMC11950192) separates epitopes with AAY citing **Schubert & Kohlbacher
  2016** — the paper that shows AAY is suboptimal.

**The honest statement about AAY**, if the artifact says anything at all: *no primary paper established
AAY as a proteasomal cleavage site. The defensible claim is that aromatic, basic and small-aliphatic
residues are favourable at proteasomal C-terminal positions (Bergmann 1996; Toes et al. J Exp Med
2001;194:1–12; Dönnes & Kohlbacher 2005).*

### 2.2 The one real optimisation study — and what it says about AAY

Dorigatti E, Schubert B. *Joint epitope selection and spacer design for string-of-beads vaccines.*
**Bioinformatics** 2020;36(Suppl 2):i643–i650. doi:10.1093/bioinformatics/btaa790 · PMC7773482.

- **Formulation:** a **mixed-integer linear program (MILP)** that chooses epitopes *and* designs the
  spacer between each adjacent pair simultaneously — variable spacer length, any of the 20 amino acids
  allowed per position.
- **Cleavage model:** the Proteasomal Cleavage Matrix (PCM) of Dönnes & Kohlbacher (2005), a PSSM over
  4 C-terminal and 1–2 N-terminal residues; validated against NetChop Cterm (Nielsen et al. 2005).
- **Measured, in their model:**
  - cleavage events *inside* epitopes: 9.40 → 6.81 (−27.6 %); at epitope termini: 1.73 → 4.37 (+152 %)
  - effective immunogenicity: 0.287 → 0.574 (**2×**); recovered epitopes ~1.5 → ~2.1
  - **fixed spacers, relative to optimised:** `MWQW` costs **35–45 %** of immunogenicity; **`AAY` costs
    85–95 %**
  - the optimiser converged on only **nine distinct spacer sequences**, dominated by `MWQW`/`MWRW`
    (19 of 40 instances)
- Prior art it cites, which is also our citation chain: Toussaint et al. *PLoS Comput Biol* 2008
  (optimal peptide-set selection); **Schubert & Kohlbacher, *Genome Med* 2016, "Designing
  string-of-beads vaccines with optimal spacers"**; **Velders et al. *J Immunol* 2001** — defined
  flanking spacers were *essential* for tumour eradication by an epitope-string DNA vaccine.

**Its predecessor, and the harder number on AAY.** Schubert B, Kohlbacher O. *Designing string-of-beads
vaccines with optimal spacers.* **Genome Med** 2016;8:9. PMID 26813686 · PMC4728757 ·
doi:10.1186/s13073-016-0263-6. Per-pair spacer design as a **bi-objective MILP** solved by lexicographic
optimisation (P1 maximise junction cleavage using the PCM PSSM; P2 minimise neo-epitope immunogenicity at
the epitope–spacer interfaces; P3 optionally minimise non-junction cleavage), with each pair's optimal
objective becoming a **directed-graph edge weight**, and the resulting **TSP** solved by
**Lin–Kernighan–Helsgaun**. Measured:

| Metric | Optimal spacers | **AAY** | No spacer |
|---|---|---|---|
| Junction cleavage score | **1.74 ± 0.63** | 0.73 ± 0.53 | −0.85 ± 1.09 (below the 0.0 threshold) |
| Epitope recovery | **78.3 ± 16.2 %** | 62.7 ± 15.2 % | 15.4 ± 24.3 % |
| **Neo-immunogenicity (lower is better)** | **1.88 ± 0.59** | **4.31 ± 0.99** | **3.37 ± 0.93** |

**Read the third row carefully: AAY scored *worse than no spacer at all* on the neo-epitope axis.**
Optimal spacers gave a 7.7× increase in cleavage likelihood vs no spacer and 2× vs AAY. An example output
is `KLLEEVLLL-HDH-ALADGVQKV-HH-SVASTTTGV`.

**Two caveats that must travel with these numbers, or we would be doing exactly what §2.1b criticises:**
1. **A real confound in the 2016 paper:** the AAY arm used ten *randomly ordered* strings while the other
   two arms were *optimally ordered*, so the AAY penalty is partly confounded with ordering.
2. **These are computational models of proteasomal cleavage**, not immunised animals or patients. In
   Dorigatti & Schubert 2020 the immunogenicity term is itself a *predicted*-binding proxy.

So the defensible statement is: **"the two published head-to-head scorings of common spacers both rank AAY
below optimised spacers, and one ranks it below no spacer at all, in cleavage/neo-epitope models."** That
is enough to stop us defaulting to AAY. It is **not** enough to claim `MWQW` or `HDH` is better in a
patient — and note that neither `MWQW` nor `HDH` has ever been used in a clinical construct.

### 2.3 Junctional epitopes: is it a real problem? **Yes — there is a decisive primary experiment.**

This is the single most important correction to the folklore: junctional epitopes are **not** a
theoretical worry. There is one clean, causal, published experiment.

#### 2.3a The decisive experiment

**Livingston B, Crimi C, Newman M, Higashimoto Y, Appella E, Sidney J, Sette A.** *A rational strategy to
design multiepitope immunogens based on multiple Th lymphocyte epitopes.* **J Immunol**
2002;168(11):5499–5506. PMID 12023344 · doi:10.4049/jimmunol.168.11.5499

Four HLA-DR-restricted HIV Th epitopes, cross-reactive with murine I-Ab. The design logic rules out the
alternative explanations in sequence: a **peptide pool** induced responses against **all four** (so
intrinsic immunodominance was not the barrier); a multiple-antigen-peptide construct underperformed a
linear polypeptide; and then, verbatim from the abstract:

> "Further characterization of linear polypeptide revealed that **the sequential arrangement of the
> epitopes created a junctional epitope with high affinity class II binding. Disruption of this junctional
> epitope through the introduction of a GPGPG spacer restored the immunogenicity against all four
> epitopes.**"

The junctional epitope spanned **Gag 171 / Pol 335**; the T-cell response *against the junction* was
measured by primary γ-IFN ELISPOT and eliminated by GPGPG; the effect held for both polypeptide and DNA
immunisation.

**That is causal evidence of the full loop:** a junction created a new high-affinity epitope → it raised
its own T-cell response → the intended responses were lost → removing the junction restored them.
**Caveat that must travel with it: all four epitopes are class II.** This experiment says nothing
directly about class I, which is what our pipeline screens.

#### 2.3b Ordering alone can decide whether a construct works

**Cornet S, Miconnet I, Menez J, Lemonnier F, Kosmatopoulos K.** *Optimal organization of a
polypeptide-based candidate cancer vaccine composed of cryptic tumor peptides with enhanced
immunogenicity.* **Vaccine** 2006;24(12):2102–2109. PMID 16455166.
**All six permutations** of three cryptic tumour epitopes were tested in a **linker-free** polypeptide.
**Only one of the six** elicited a trispecific response.

That is the strongest single argument for implementing an ordering step at all, and it is an argument
that does not depend on linkers.

#### 2.3c Other demonstrated instances

- **Aurisicchio L, et al.** *Oncoimmunology* 2014;3(1):e27529 (PMC4002591): in the AAY scaffold, CEA
  epitope 411V10 was **entirely non-immunogenic** while others in the same construct responded strongly —
  a positional/junctional effect.
- **Schubert & Kohlbacher 2016** re-analysed *published, real* constructs and found spacers themselves
  generating neo-epitopes. For Levy A, et al. *Cell Immunol* 2007;250:24–30 (PMC2413004): "With the
  spacer RKSY(L), **only one out of four epitopes could be recovered**, and **ALL induced five
  neo-epitopes spanning the spacer** … the combination of SLL and AAY **generated neo-epitopes**."
- **Gurung 2024** (PMC11251992) shows a distinct *presentation-level* competition mechanism with MS
  evidence: a no-linker A\*02:01 cassette lacking the control epitopes revealed two additional
  neoepitopes, "suggest[ing] that strong binding peptides could inhibit presentation of certain
  neoepitopes."

#### 2.3d Industrial corroboration

Both clinical sponsors hold patents whose *subject matter* is minimising junction epitopes:
- ModernaTx US 2022/0152178 A1: "a linker is used between peptides to **reduce or eliminate
  pseudoepitope formation**"; "It is important that the junction not be an immunogenic peptide that could
  produce an immune response"; epitopes "ordered to minimize pseudo-epitopes".
- **US 11,885,815 — *Reducing junction epitope presentation for neoantigens*** — a granted patent on the
  ordering algorithm: for each ordered epitope pair a **distance metric** is computed from
  **MHC-allele-prevalence weights × per-allele junction-epitope presentation likelihoods**, and the
  ordering is optimised against it. **Unverified: I could not retrieve the full text (Google Patents 503,
  FreePatentsOnline refused). Treat the mechanism summary as second-hand.**
- **VaccineCAD** (in **iVAX**: Moise L, et al. *Hum Vaccin Immunother* 2015;11(9):2312–2321, PMC4635942)
  states the policy explicitly, and it is the policy we should copy:
  > "VaccineCAD **shuffles the order of the peptides until it finds an arrangement in which junctional
  > immunogenicity is minimized** between adjacent peptides. In some cases, spacers that disrupt HLA
  > binding (e.g. GPGPG for class II) **may be inserted if junctional epitopes remain**."
  Primary citation: Moss SF, Moise L, et al. *HelicoVax…* **Vaccine** 2011;29(11):2085–2091 (PMC3046230).

#### 2.3e How often do junctions create binders? The honest answer: barely quantified

This is the thinnest part of the literature, and the little that exists mostly **cuts against alarm**.

- **Lee Y, Ferrari G, Lee SC.** *Estimating design space available for polyepitopes through consideration
  of major histocompatibility complex binding motifs.* **Biomed Microdevices** 2010;12(2):207–222.
  PMID 20033850. The only paper that exhaustively enumerates *all* junction-epitope-free designs for an
  epitope set (tool: CANVAC II). Headline: "the number of such variants of any given polyepitope can be
  **astronomically high**." I.e. **junction-free orderings are usually abundant, so reordering alone
  normally suffices** — which is exactly why "order first, linker only if needed" is the right policy.
- **Antonets & Bazhan** *BMC Res Notes* 2013;6:407 (PMC3853014) give the pessimistic baseline on the
  *cleavage* axis: "the probability of selecting an optimal epitopes permutation at random was **less
  than 0.00139** and **only 17 %** of all possible polyepitope constructs did not contain inefficient
  proteasomal cleavage sites between target CTL epitopes."
- **Dorigatti & Schubert** *PLoS Comput Biol* 2020;16(10):e1008237 (PMC7652351): **96.3 %** of
  Pareto-optimal designs achieved all nine junction cleavage sites vs **50.9 %** of randomly shuffled
  designs (41.1 % had eight, 8.0 % had six–seven).
- Per-linker junctional-binder *counts* exist **only in patent text** (US 11,885,815 family), and are
  **unverified** here.

#### 2.3f What has NOT been published — do not imply it

- **No measured clinical instance** of a junction epitope causing autoimmunity, a safety event, or a
  degraded trial outcome in a human cancer vaccine.
- **No published in-vivo validation** that computational junction screening prevents junctional responses.
- **No published estimate** of how often junctions create *actually presented* class I epitopes in
  patients.
- **No published report** of a T-cell response raised against a *linker-containing* peptide specifically
  (as opposed to an epitope1|epitope2 junction peptide). That gap appears genuine.

Our own screen can report a **predicted** junction-binder frequency on our own demo panel. That is a
measurement we can legitimately make and label as ours, in the style of `research-filters.md` — and it
would partly fill a real gap in the literature.

#### 2.3g Empirical difficulty: the ordering problem is not a formality

`pvacvector` **fails on real cases.** In the pVACtools v6 benchmark over 11 vaccine-design cases × 3
settings, a run is scored green ("produced a linear multi-epitope design **with no junctional epitopes**")
or **red (failed to produce a design)** — and red cases exist at the stricter settings. Average runtime at
the 1500 nM setting was **131–335 minutes**.

### 2.4 `pvacvector` — exactly what it does

Part of **pVACtools**: Hundal J, Kiwala S, McMichael J, et al. *pVACtools: A Computational Toolkit to
Identify and Visualize Cancer Neoantigens.* **Cancer Immunol Res** 2020;8:409–420 · PMID 31907209.
Current description: Hoang MH, Kiwala S, Richters M, et al. *pVACtools v6: A comprehensive suite for
neoantigen prediction, visualization, and therapy design* (2026), arXiv:2606.26659.
Docs: <https://pvactools.readthedocs.io/en/latest/pvacvector.html>

**Algorithm (verbatim from the v6 manuscript):**

> "It attempts to find an optimal ordering of input peptide sequences that avoids strong binding
> junctional peptides (i.e. those formed at the boundary between adjacent input sequences). To find this
> ordering, pVACvector constructs a **directed graph**, in which each **node** represents a peptide
> sequence, and each **directed edge** represents the junction formed by placing one peptide immediately
> after another. **Edges are only added for "valid" junctions where none of the junctional peptides are
> well-binding.** After constructing the graph, a **simulated annealing** procedure is used to find a
> path through the graph … that **maximizes the combined binding affinity of the junctional epitopes**
> across the full sequence."

**Escalation ladder, in order (v5+):**
1. Join pairwise, examine junctions for well-binding k-mers; valid junctions become directed edges.
2. Simulated annealing for a path visiting all peptide nodes.
3. If no valid path: insert **spacers** (`--spacers`) at failing junctions.
4. If still failing: **clip** peptides at either or both ends (`--max-clip-length`, **default 3 aa**);
   v5 tests *all* clipping permutations (clip A only, clip B only, clip both) — v4 tested only "clip
   both". Because the input FASTA now carries the core neoantigen (`{"Best Peptide": "..."}` in the
   header), **v5 refuses to clip into the binding core**.
5. If still failing: **exclude peptides** (`--allow-n-peptide-exclusion`) for a partial solution.
6. The graph is built **iteratively** in v5, retaining valid junctions across spacer/clip attempts
   (v4 rebuilt from scratch).

**Inputs:** a pVACseq output TSV, *or* a FASTA of peptide sequences (optionally with the core
neoantigen named in the header); HLA alleles; prediction algorithms; an IEDB install directory.
**Outputs:** a **Vector FASTA** of the final ordering including spacers and clipped peptides, excluding
removed peptides; partial solutions land in subdirectories naming the excluded peptides.

**The exact junction-test construction (read off the implementation, `VectorFastaGenerator`):**
for each requested epitope length **L**, set **wingspan = L − 1**, and build the test string as
**`last (L−1) residues of seq1` + `spacer` + `first (L−1) residues of seq2`**. Because each flank is
exactly `L−1` long, **every L-mer of that string necessarily spans the junction** — that is the k-mer
enumeration, and it is why the wingspan is `L−1` and not `L`.

**Published parameters — use these numbers, they are citable defaults:**
- **Epitope lengths enumerated:** class I **8, 9, 10, 11**; class II **12, 13, 14, 15, 16, 17, 18**.
- `--spacers` default: `"None", "AAY", "HHHH", "GGS", "GPGPG", "HHAA", "AAL", "HH", "HHC", "HHH", "HHHD", "HHL", "HHHC"`
  — **`"None"` is first**, so direct fusion is tried before any linker. First spacer that yields a clean
  junction wins; later spacers are not tried for that junction (first-fit, for runtime).
- `--binding-threshold`: **IC50 < 500 nM** (default). `--binding-percentile-threshold`: **percentile
  rank < 2.0**.
- `--percentile-threshold-strategy`: **`conservative`** (default) fails the junction on **either**
  criterion; `exploratory` requires **both**.
- `--top-score-metric`: **`median`** (default, median across selected predictors); **`lowest`** is the
  conservative alternative.
- `--max-clip-length`: **3 aa** default (5 aa in the permissive benchmark mode).
- `--allow-n-peptide-exclusion`: default **2**.
- `--allele-specific-binding-thresholds` available.
- **The documentation's own conservatism advice, verbatim in substance:** a lower threshold (500 nM) plus
  the *median* binding value makes a design more likely to be found; the more conservative settings of
  **1000 nM and `lowest`/best binding value** "give more confidence that there are no junctional
  neoepitopes" — and it recommends running pVACvector several ways and taking the most conservative
  path that succeeds. **Do that, and report which setting produced the emitted construct.**

**Also in pVACtools and directly relevant to a "research artifact" framing:** eight **manufacturability**
criteria imported from **VaxRank** (Rubinsteyn et al., bioRxiv 2017, doi:10.1101/142919) —

1. cysteine count, 2. C-terminal cysteine flag (unwanted disulfides, oxidation on storage),
3. C-terminal proline flag (chain-elongation difficulty in SPPS, reduced yield, impurities),
4. N-terminal asparagine flag, 5. Asn–Pro bond count (fragmentation),
6. GRAVY of the C-terminal 7-mer, 7. max 7-mer GRAVY across the peptide (aggregation, poor solubility,
**injection-site depots that interfere with the T-cell response**), 8. difficult N-terminal residue
(Gln/Glu/Cys).

These are *synthesis-difficulty flags*, and reporting them is a good way to be useful without claiming
manufacturability. Their primary sources are worth carrying too, because they are the honest reason a
long hydrophobic stretch is a problem: Hailemichael et al. (persistent antigen at vaccination sites
sequesters and deletes tumour-specific CD8+ T cells), Lynn et al. *Nat Biotechnol* 2020;38:320–332,
Geiger & Clarke *J Biol Chem* 1987;262:785–794 (Asn/Asp deamidation and succinimide-linked degradation),
Wang et al. *ACS Omega* 2022;7:46809–46824 (diketopiperazine formation in SPPS), and Ishizuka et al.
(bioRxiv 2026, doi:10.64898/2026.01.20.699901) on substituting Met/Cys with oxidation-resistant isosteres
to improve manufacturability without losing immunogenicity.

**Note the tension this creates, and put it on the artifact:** a 27-mer stretch is chosen for
*immunology* (§3.0) and is exactly the length most likely to trip the *hydrophobicity/aggregation* flags.
The two criteria pull against each other, and nothing in the published literature resolves it for you.

### 2.5 The junction screen we can implement today

We already have the only component that matters: `PeptideScreen` in `neofold/screen.py` wraps
MHCflurry's `Class1PresentationPredictor`. The screen is:

Use pvacvector's exact construction, so the numbers are comparable to a published tool:

```
for each adjacent pair (A, B) in a candidate ordering, with spacer S (possibly ""):
    for k in (8, 9, 10, 11):                  # class I lengths, pvacvector default
        wingspan = k - 1
        J = A[-wingspan:] + S + B[:wingspan]  # every k-mer of J now spans the junction
        for each k-mer of J:
            score against every patient allele        # PeptideScreen, MHCflurry
            FAIL if affinity < 500 nM  OR  percentile_rank < 2.0    # "conservative" strategy
```

Notes that make this correct rather than decorative:
- **The `wingspan = k − 1` trick is the whole point.** Trimming each flank to `k−1` means *every* k-mer of
  `J` crosses the boundary, so you enumerate the spanning set without a separate span test. For k=8..11
  that is `7+8+9+10 = 34` windows per junction (plus the extra windows a spacer contributes), so a
  6-junction pentatope in a fixed order is a few hundred predictions — trivial.
- **Thresholds: 500 nM *or* percentile < 2.0, failing on either** (pvacvector's `conservative` default).
  Also run the documentation's conservative pass — **1000 nM with the `lowest` score metric** — and report
  which setting the emitted construct survived. Do not invent a threshold.
- **Also screen the `sec|L|E1` and `E5|L|MITD` boundaries**, not only epitope–epitope joins. Any boundary
  the proteasome has never seen before is a junction.
- **Report, don't just reject.** The artifact should carry the junction table: every spanning k-mer, its
  allele, its predicted affinity and percentile, and whether it passed. That is what makes it reviewable.
- **If we add class II later**, pvacvector's class II lengths are **12–18** — a much larger spanning set,
  and the only class where the decisive junctional-epitope experiment (§2.3a) was actually done.
- We can quote our *own* measured junction-binder rate on our own demo panel, as a measurement, and keep it
  clearly separated from the literature — the house style in `research-filters.md`. Per §2.3e this would
  partly fill a genuine gap.

---

## 3. Trafficking and processing signals

### 3.0 First: why the stretch is long, not minimal

This is the best-evidenced design parameter in the whole document, so lead with it.

- **Bijker MS, van den Eeden SJF, Franken KL, Melief CJM, Offringa R, van der Burg SH.** *CD8+ T cell
  priming by exact peptide epitopes in incomplete Freund's adjuvant induces a vanishing CTL response,
  whereas long peptides induce sustained CTL reactivity.* **J Immunol** 2007;179:5033–5040.
  Exact 8–10-mers bind directly to MHC-I on *any* nucleated cell, most of which are not professional
  APCs → suboptimal priming or tolerance. ≥25-mers must be endocytosed and processed by professional
  APCs → sustained CTL. Cross-presented antigen from long peptides remained detectable for ≥3 days.
- **Melief CJM, van der Burg SH.** *Immunotherapy of established (pre)malignant disease by synthetic
  long peptide vaccines.* **Nat Rev Cancer** 2008;8:351–360.

This is the published justification for the 27-mer stretch and for the 15–30-aa SLP range. It is also
why an "assemble the 9-mers" construct would be wrong on the science, not just unfashionable.

### 3.1 sec / MITD (the BioNTech approach)

- **Primary:** Kreiter S, Selmi A, Diken M, et al. *Increased antigen presentation efficiency by coupling
  antigens to MHC class I trafficking signals.* **J Immunol** 2008;180:309–318. PMID 18097032.
  (Correction: *J Immunol* 2012;189:2682.)
  Abstract, verbatim in substance: combining an **N-terminal leader peptide (sec)** with an **MHC class I
  trafficking signal (MITD) at the C terminus** of the antigen "strongly improves the presentation of
  MHC class I **and** class II epitopes" in human and murine DCs; MITD fusion constructs had
  "profoundly higher stimulatory capacity than wild-type controls", giving efficient expansion of
  antigen-specific CD8+ *and* CD4+ T cells. Tested on CMV pp65 and NY-ESO-1.

**Honest limitation, flagged:** I could not obtain the full text (paywalled at Oxford/AAI; the
ResearchGate mirror 403s). **I therefore cannot quote a fold-change, and neither should the artifact.**
The citable claim is "improves class I and class II presentation (Kreiter 2008)", not a number.

**Sequences — and this is the biggest correction in the document: they ARE published.**

The BNT122 / autogene cevumeran phase 1 paper (*Nat Med* 2025, **PMC11750724**, open access) prints them
verbatim in its Methods:

| Feature | Published amino-acid sequence | Length |
|---|---|---|
| **sec** (secretory signal peptide) | `MRVMAPRTLILLLSGALALTETWAGS` | **26 aa** |
| **MITD** (MHC class I trafficking domain) | `IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA` | **55 aa** |
| inter-epitope linker | *sequence not given*, but stated as **"30 bp non-immunogenic glycine and serine linkers"** | **10 aa** |

Methods, verbatim: *"cloned into a starting vector containing the secretory signal peptide (SEC)
(`MRVMAPRTLILLLSGALALTETWAGS`) and the MHC class I trafficking domain (MITD) sequences
(`IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA`)"*, citing Kreiter 2008 for both.

**These cross-check exactly against the independent patent base counts, which is why I am confident in
them.** The patent states "MHC class I signal peptide fragment (**78 bp**, secretion signal (sec))" and
"transmembrane and cytosolic domains **including the stop-codon** (MHC class I trafficking signal (MITD),
**168 bp**)". Computed: 26 aa × 3 = **78 bp** ✓; 55 aa × 3 + 3 (stop) = **168 bp** ✓. And 30 bp ÷ 3 = **10
aa**, which independently confirms Vormehr 2015's "10 mer" linker from a second source. Two unrelated
documents — a patent's nucleotide counts and a journal's amino-acid strings — agree to the residue.

**One discrepancy, recorded rather than smoothed over.** The patent's sec cloning primer
(`5'-aagcttagcggccgcaccatgcgggtcacggcgccccgaacc-3'`) has coding portion `ATG CGG GTC ACG GCG CCC CGA ACC`
= **M R V T A P R T**, while the *Nat Med* Methods give **M R V M A P R T** — differing at position 4
(**T** vs **M**). Both are consistent with an HLA class I leader (HLA-B/-C-type leaders begin `MRVTAPRT`).
Use the **peer-reviewed** string and note the variant.

**What is still NOT published:**
- **The exact 10-mer linker string.** Length confirmed twice (10 aa / 30 bp); sequence never printed. The
  patent's *example* is `GGSGGGGSG` (9 aa). See §7.1.
- **The UTRs as nucleotides** for the cancer vaccine (§4.1a).

**Implementation consequence — revised.** Emit the **actual published sec and MITD sequences**, cited to
*Nat Med* 2025 (PMC11750724) for the strings and Kreiter 2008 for the design rationale. Emit the linker as
a **10-aa G/S-family placeholder**, clearly marked as length-confirmed / sequence-unpublished. That is a
materially stronger artifact than the placeholder-only version, and it requires inventing nothing.

**Also newly citable from the same Methods:** the cap is **β-S-ARCA(D1)**, the D1 diastereoisomer of a
phosphorothioate ARCA analog (**Kuhn AN, et al.** *Gene Ther* 2010;17(8):961–971, PMID 20410931), and IVT
runs with *"ATP, CTP, **UTP**, GTP"* — i.e. **unmodified UTP stated in a manufacturing methods section**,
which is the cleanest possible confirmation of §4.2.

**Beware a citation trap in the literature:** several immunoinformatics papers cite "MITD (UniProt
Q8WV92)". **Q8WV92 is MITD1, "MIT domain-containing protein 1", an unrelated human ESCRT-associated
protein.** It is not the MHC class I trafficking domain, and it bears no resemblance to the real 55-aa
sequence above. Do not propagate that.

**A second trap, for the same reason:** academic reimplementations frequently say only that they used "a
secretion signal sequence … and an MHC class I trafficking signal (MITD)" and cite Kreiter 2008 **without
giving sequences** (e.g. *Front Immunol* 2023;14:1135815; PMC10045729, which gives the layout as
"SP – (G4S)2 – antigen – V5 tag (`GKPIPNPLLGLDST`) – MITD – 120-bp poly(A)"). Those papers are not evidence
about what the sequences are; the *Nat Med* 2025 Methods is.

### 3.2 Other trafficking strategies

| Approach | Primary citation | What the evidence says |
|---|---|---|
| **Ubiquitin fusion** (N-terminal Ub → proteasomal routing) | **Rodriguez F, Zhang J, Whitton JL.** *DNA immunization: ubiquitination of a viral protein enhances cytotoxic T-lymphocyte induction and antiviral protection but abrogates antibody induction.* **J Virol** 1997;71:8497–8503. | Real effect on CTL, and a real cost: it **abrogates antibody induction**. Later work cuts against it — Ub-Gag **impaired DC maturation and reduced** Gag T-cell responses (*PLoS One* 2014;9:e88327), and "**stable antigen is most effective for eliciting CD8 T-cell responses**" (*J Virol* 2012;86:9754). **Contested. Do not present as an improvement.** |
| **LAMP-1 lysosomal targeting** | **Wu T-C, Guarnieri FG, Staveley-O'Carroll KF, et al.** *Engineering an intracellular pathway for major histocompatibility complex class II presentation of antigens.* **PNAS** 1995;92:11671–11675. | Routes antigen into the endosomal/lysosomal MHC-II pathway; increased lymphoproliferation, antibody and CTL vs wild-type E7 in vaccinia. Reproduced for HIV Gag (*Immunology* 2004) and MCPyV LT (*Front Immunol* 2023;14:1253568 → potent CD4). **Class-II-skewing.** |
| **Invariant chain (Ii)** | referenced in ModernaTx US 2022/0152178 A1 alongside LAMP-1 | Same class-II-routing family. No clinical personalised-vaccine precedent. |
| **tPA signal peptide** | common in immunoinformatics constructs, often with `EAAAK` linkers | Academic convention. No clinical personalised-vaccine precedent. |

**Summary for the artifact:** sec/MITD is the only trafficking configuration with both a primary
mechanistic paper *and* use in the clinical personalised-vaccine products. Everything else is optional
and, in ubiquitin's case, actively contested.

---

## 4. Codon optimisation and mRNA elements

**Read §4.5 first.** Most of this layer is proprietary, and the correct engineering answer is *do not emit
nucleotides at all* (§7.4). This section exists so the artifact can say what an mRNA layer *would*
require, with citations, rather than fabricating one.

### 4.1 What the published record actually fixes

| Element | Published value | Source |
|---|---|---|
| Poly(A) tail | **120 nucleotides** | BioNTech US 10,738,355 B2: "RNA comprises a poly(A)-tail consisting of 120 nucleotides" |
| Poly(A) tail (Moderna claim range) | **10–300** adenosine monophosphates; alternative **50–250** | ModernaTx US 2022/0152178 A1 |
| 5′ cap, **BNT122 specifically** | **β-S-ARCA(D1)** — the D1 diastereoisomer of a phosphorothioate ARCA analog, m₂⁷,²′-ᴼGpp(S)pG | *Nat Med* 2025 Methods (PMC11750724); chemistry in **Kuhn AN, et al.** *Gene Ther* 2010;17(8):961–971, PMID 20410931 |
| 5′ cap (patent, generic) | "a 5′-cap analog" (unspecified) | BioNTech US 10,738,355 B2 |
| Poly(A), **segmented** | **`A30 – GCATATGACT – A70`**. The linker was chosen "to contain a balanced contribution of all 4 nucleotides"; A30L70/A40L60 cut poly(dA:dT) instability in *E. coli* from 50–60 % to **3–4 %**, with **no difference vs A120** in translation or CD8⁺ induction — i.e. **a plasmid-stability fix, not a translation optimisation** | **EP 3 167 059 B1** / WO 2016/005324 (BioNTech RNA Pharmaceuticals + TRON), granted 26.06.2019; US 10,717,982 B2 |
| 5′ cap (Moderna claim) | **7mG(5′)ppp(5′)N1mpNp** | ModernaTx US 2022/0152178 A1 |
| Nucleoside modification, **autogene cevumeran / BNT122** | **UNMODIFIED uridine.** "two 5′-capped single-stranded **uridine-based** mRNA molecules"; "**nucleoside-unmodified uridine mRNA**" | Rojas et al. *Nature* 2023; *Nat Med* 2025 (PMC11750724) |
| Nucleoside modification, **Moderna claims** | pseudouridine, **N1-methylpseudouridine (m1Ψ)**, m1Ψ + m5C, Ψ + m5C, 2-thiouridine, 5-methylcytosine … | ModernaTx US 2022/0152178 A1 |
| 5′ / 3′ UTR sequences | **not disclosed** in either the Lancet paper or the patent extract — "a 5′ untranslated region … and encodes a 3′ untranslated region", generically | ModernaTx US 2022/0152178 A1; Weber et al. *Lancet* 2024 |
| Codon usage | "**codon optimized** sequences coding for …" — stated, never specified | BioNTech patent family |
| Translation/stability engineering | "Several modifications in the 5′ cap, 5′ and 3′ untranslated regions (UTR), poly(A) tail, and codon usage increased the translation efficiency and stability" — "increased stability and translational efficacy … by several thousandfold" | Vormehr et al. *J Immunol Res* 2015 |

### 4.1a The actual published BioNTech backbone — this is more citable than expected

Two findings worth having, because they let you *name* the real vector without guessing sequences.

**The vector is named in a peer-reviewed Methods section.** Kreiter S, Vormehr M, van de Roemer N, et al.
*Mutant MHC class II epitopes drive therapeutic immune responses to cancer.* **Nature**
2015;520(7549):692–696 (PMID 25901682 · PMC4838069) names the construct literally:
**`pST1-Sp-MITD-2hBgUTR-A120`** — i.e. signal peptide, MITD, **two human β-globin 3′ UTRs**, **poly(A)
120**. That is the pentatope backbone, stated in the literature, with no sequence disclosed.

**The elements, each with a primary citation:**

| Element | Identity | Primary citation |
|---|---|---|
| 3′ UTR (first generation) | **two sequentially coupled human β-globin 3′ UTRs (2hBg)**, plus a **120-nt poly(A)** with an unmasked free 3′ terminus (vs a conventional 64 nt) — each independently increased RNA stability and translation, raising peptide/MHC density and CD4+/CD8+ stimulation | **Holtkamp S, Kreiter S, Selmi A, Simon P, Koslowski M, Huber C, Türeci O, Sahin U.** *Modification of antigen-encoding RNA increases stability, translational efficacy, and T-cell stimulatory capacity of dendritic cells.* **Blood** 2006;108(13):4009–4017. PMID 16940422 · doi:10.1182/blood-2006-04-015024. **Not in PMC; exact fold-changes unverified.** |
| 3′ UTR (current generation) | **AES–mtRNR1**, i.e. the 3′ UTR of *amino-terminal enhancer of split* (**AES/TLE5**, core motif **136 nt**) followed by **mitochondrially encoded 12S rRNA** (**mtRNR1**, core motif **142 nt**). The **AES–mtRNR1 order was significantly superior** to mtRNR1–AES. Gains over the hBg 3′ UTR: **~2.3–3.6×** protein in myoblasts, **~2.4–3.5×** in fibroblasts; in reprogramming, up to **60-fold** more colony-forming units vs 6.5-fold for 2hBg. Constructs used hAg-Kozak 5′ UTR, **β-S-ARCA(D1)** co-transcriptional cap, poly(A) 60 or 120. **The paper prints no nucleotide sequences for the selected 3′ UTRs.** | **Orlandini von Niessen AG, Poleganov MA, Rechner C, et al.** *Improving mRNA-Based Therapeutic Gene Delivery by Expression-Augmenting 3′ UTRs Identified by Cellular Library Screening.* **Mol Ther** 2019;27(4):824–836. PMID 30638957 · PMC6453560 (**not open access**) |
| 5′ UTR | **`hAg-Kozak`** — the 5′ UTR of **human α-globin** mRNA with an **optimised Kozak sequence** | Kozak M, *Nucleic Acids Res* 1987;15:8125–8148 (the Kozak element); identified as `hAg-Kozak` in BioNTech's own filings and in the BNT162b2 regulatory module (below) |
| Poly(A) (current generation) | **`A30L70`** — two poly(A) tracts of **30** and **~70** adenosines joined by a linker | BioNTech **EP 3167059 B1**; named in the BNT162b2 module |

**Where a real sequence is genuinely public — and it is not the cancer vaccine.** The BNT162b2 CTD module
**"3.2.S.1.2 Structure"**, released by the UK MHRA under FOI 22-1116, states verbatim: *"hAg-Kozak
(nucleotides 1 to 53): 5′-UTR sequence of the human alpha-globin mRNA with an optimized 'Kozak sequence'
to increase translational efficiency"*; *"FI element (nucleotides 3864 to 4158): The 3′-UTR is a
combination of two sequence elements derived from the 'amino terminal enhancer of split' (AES) mRNA
(called F) and the mitochondrial encoded 12S ribosomal RNA (called I)"*; and *"A30L70 (nucleotides 4159 to
4268): … two poly(A) tracts of 30 and approximately 70 adenosine residues joined by a linker"*.
<https://assets.publishing.service.gov.uk/media/65e702542f2b3bd5107cd85f/FOI_22-1116_-_attachment.pdf>

**Do not carry this across to the cancer vaccine without flagging it.** BioNTech has **never published the
BNT122 / autogene cevumeran UTRs as sequences.** There is a suggestive oddity — the *Nat Med* 2025 phase 1
Methods print an **amino-acid** string for the "3′ UTR" while citing von Niessen 2019, and that string is
the in-frame translation of the BNT162b2 3′ region's F/AES element — which implies the cancer vaccine uses
the same F element. **That is an inference from a peculiar Methods entry, not a published claim.** Label it
as such or leave it out.

### 4.2 The m1Ψ question — answered, and it is the opposite of what people assume

**BioNTech's individualised cancer vaccines do *not* use N1-methylpseudouridine.** They use
**nucleoside-unmodified uridine mRNA**, and that is deliberate: the RNA-LPX platform *wants* innate
sensing (TLR7/8) to provide the adjuvant effect, which is precisely what m1Ψ suppresses. This is stated
in the peer-reviewed literature — Rojas et al. *Nature* 2023 ("uridine mRNA–lipoplex nanoparticles") and
the phase 1 ("nucleoside-unmodified uridine mRNA") — so it is citable, and it is the single most common
factual error made about these products (people transfer the COVID-vaccine m1Ψ fact across).

**Four independent peer-reviewed statements, escalating in explicitness:**
1. Rojas 2023 (*Nature*, PMC10171177): *"based on **uridine mRNA**–lipoplex nanoparticles"*; Methods:
   *"two **uridine-based** mRNA strands with noncoding sequences optimized for superior translational
   performance"*.
2. *Nat Med* 2025 (PMC11750724): a safety profile *"**expected based on the desired innate
   immunostimulatory properties of nucleoside-unmodified uridine mRNA**"*, *"in line with the
   preclinically shown ability of RNA–LPX to engage **TLR7/8** receptor-mediated inflammatory cytokine
   production"*, and Methods listing IVT nucleotides as *"ATP, CTP, **UTP**, GTP"*.
3. Sethna 2025 (*Nature* 639:1042–1051): *"an **unmodified uridine-based** mRNA–lipoplex vaccine"*.
4. Adjuvant TNBC (*Nature* 2026;651:1088–1096, PMC13017525): *"two strings of **immunostimulatory,
   non-nucleoside-modified uridine mRNA**"*, and *"The use of uridine mRNA in the RNA–LPX vaccine
   technology links antigen delivery with co-stimulation via **Toll-like receptor (TLR)-mediated,
   type-I-interferon-driven** antiviral immune responses"*.

**The mechanistic basis for the choice** is **Kranz LM, Diken M, Haas H, Kreiter S, … Türeci Ö, Sahin U.**
*Systemic RNA delivery to dendritic cells exploits antiviral defence for cancer immunotherapy.* **Nature**
2016;534(7607):396–401. PMID 27281205 — the title *is* the thesis. RNA-LPX *"triggers interferon-α release
by plasmacytoid DCs and macrophages"* giving *"potent **IFNα-dependent** rejection of progressive
tumours"*. The reactogenicity mechanism: Tahtinen S, et al. *Nat Immunol* 2022;23:532–542 (PMID 35332327).

**Moderna's mRNA-4157 is a different platform**, and its patent family claims m1Ψ among the
modifications, but the **Lancet paper does not state the nucleoside chemistry of mRNA-4157**. So:
- BioNTech cancer vaccine: **unmodified uridine — published four times over, cite it.**
- Moderna cancer vaccine: modified-nucleoside platform, exact chemistry for mRNA-4157 — **not published in
  any primary source** (§4.6). Do not assert m1Ψ for mRNA-4157 from the patent alone.

**Two citation traps on the chemistry papers.** Karikó K, et al. *Immunity* 2005;23(2):165–175 (PMID
16111635) showed m5C, m6A, m5U, s2U and **pseudouridine** ablate TLR signalling — **m1Ψ was not tested in
that paper**, and it is about innate sensing, not translation (for translation/stability cite Karikó et al.
*Mol Ther* 2008;16:1833–1840, PMC2775451). And for m1Ψ specifically: Andries O, et al. *J Control Release*
2015;**217**:337–344, **PMID 26342664** (up to ~44× in cells, ~13× in mice vs Ψ) — **PMID 26264835 is a
different paper** (Pardi et al., same volume, pp. 345–351). Easy mis-cite.

**The contrast is itself the publishable point:** BioNTech's *cancer* vaccines are deliberately
**unmodified** (IV RNA-LPX, TLR7/8 + IFN-α as a built-in adjuvant, systemic reactogenicity accepted as
on-mechanism), while BioNTech's *COVID* vaccine and Moderna's platform are **m1Ψ-modified** (innate evasion
to maximise protein per dose). Same company, opposite chemistry, because the two products want opposite
things from the innate immune system.

### 4.3 Trafficking/processing elements in the Moderna claim set

For completeness, US 2022/0152178 A1 claims, as alternatives: **sec/MITD** (reproducing BioNTech's
design in its background), **LAMP-1 transmembrane domain**, **invariant chain (Ii)**, a **ubiquitination
signal** "attached at either or both ends of the encoded peptide … enables targeting and processing of a
peptide to one or more proteasomes", and generic **targeting sequences of 4–50 aa**. See §3.2 for what
the evidence for each actually is.

### 4.4 Codon optimisation

**Codon optimisation is stated by every sponsor and specified by none.** "Codon optimized sequences"
appears in the BioNTech patent family; Rojas 2023 discloses only "noncoding sequences optimized for
superior translational performance"; Moderna says "optimised concatemeric mRNA-4157 sequence"; and for
mRNA-1273, Corbett et al. *Nature* 2020;586:567–571 says only "sequence-optimized mRNA". **No sponsor
publishes the table, the objective function, or the software.** (Of the commercial tools, GenScript
OptimumGene and IDT have no published algorithm; Thermo GeneArt does — Raab D, et al. *Syst Synth Biol*
2010;4(3):215–225, PMC2955205.)

**The citable, deterministic algorithm, if we ever need one — CAI.**
**Sharp PM, Li W-H.** *The codon Adaptation Index — a measure of directional synonymous codon usage bias,
and its potential applications.* **Nucleic Acids Res** 1987;15(3):1281–1295. PMID 3547335 · **PMC340524
(free)**. Exactly as published:

- `RSCU_ij = X_ij / ((1/n_i) · Σ_j X_ij)` — where `X_ij` is the count of the *j*-th codon for amino acid
  *i*, and `n_i` is the number of synonymous codons (1–6) for amino acid *i*.
- `w_ij = RSCU_ij / RSCU_i,max = X_ij / X_i,max` — **relative adaptiveness, normalised per amino acid**
  (all six codons of Leu/Ser/Arg form one family — *not* per codon box).
- `CAI = (Π_k w_k)^(1/L) = exp( (1/L) · Σ_k ln w_k )` — the geometric mean over the gene's codons. (The
  paper defines it as `CAI_obs / CAI_max` over RSCU and then states this is exactly equivalent.)
- **Implementation rules the paper specifies, and that most implementations get wrong:** any `X` that
  would be zero in the reference set is set to **0.5**; **AUG and UGG counts are subtracted from `L`**
  (their RSCU is fixed at 1.0); **stop codons are excluded entirely**; the **initiation codon is
  excluded**.
- **There is no human reference set in the original paper.** A human CAI is always an extrapolation using
  someone else's reference set — say so.

**Human codon usage table.** Nakamura Y, Gojobori T, Ikemura T. *Codon usage tabulated from international
DNA sequence databases: status for the year 2000.* **Nucleic Acids Res** 2000;28(1):292. PMID 10592250 ·
PMC102460 · <http://www.kazusa.or.jp/codon/>. The *Homo sapiens* [gbpri] table header reads **"93487 CDS's
(40662582 codons)"**. **Kazusa is frozen at GenBank release 160 (June 2007)** — 19 years stale as of today.
Current alternatives: **HIVE-CUTs** (Athey J, et al. *BMC Bioinformatics* 2017;18:391, PMC5581930) and
**CoCoPUTs** (Alexaki A, et al. *J Mol Biol* 2019;431(13):2434–2441, PMID 31029701).

**Published caveats — and one that is directly about creating epitopes.**

- **Mauro VP, Chappell SA.** *A critical analysis of codon optimization in human therapeutics.* **Trends
  Mol Med** 2014;20(11):604–613. PMID 25263172 · PMC4253638. Their stated risks, verbatim: *"(i)
  disrupting the normal patterns of cognate and wobble tRNA usage, affecting protein structure and
  function; (ii) **producing novel peptides with unknown biological activities**; and (iii) altering
  post-transcriptional modifications…"* And, precisely on point for a vaccine: *"In the case of nucleic
  acid vaccines, naturally-occurring cryptic peptides that may contribute to a therapeutic immune
  response, may be lost upon codon-optimization."*
  **Correction to a common claim:** this paper does **not** list cryptic splice sites as a risk. For
  splicing cite **Kowarz E, et al. *eLife* 2022;11:e74974** instead, and note it concerns DNA-templated
  expression, not IVT mRNA.
- **The finding that matters most to a neoantigen pipeline:** **Lorenz FK, et al.** *PLoS One*
  2015;10(3):e0121633 (PMID 25799237 · PMC4370481) — **codon-optimising HPV E7 *created* a dominant CD8
  epitope that was absent from wild-type E7.** Codon optimisation is itself a junction-epitope-class
  hazard: it changes the nucleotide sequence, and in a frame-shifted or alternative reading frame that can
  manufacture new epitopes. If we ever emit nucleotides, that becomes *our* problem to screen for.
- **The caveat that would actually bite *this* construct.** **Vaidyanathan S, Azizian KT, Haque AKMA,
  et al.** *Uridine Depletion and Chemical Modification Increase Cas9 mRNA Activity and Reduce
  Immunogenicity without HPLC Purification.* **Mol Ther Nucleic Acids** 2018;12:530–542. PMID 30195789 ·
  PMC6076213 — **synonymous codon choice changes uridine content, and uridine content is exactly what
  TLR7/8 senses.** Autogene cevumeran deliberately uses unmodified uridine *for* that innate signal
  (§4.2). So codon-optimising a BNT122-style construct for expression could quietly **de-adjuvant it** —
  optimising the protein yield while removing the reason the platform works. Nothing in the
  codon-optimisation literature is written with that trade in mind.
- **Cryptic splicing is probably NOT a risk here, and saying so is the honest move.** The usual citation
  (Kowarz E, et al. *eLife* 2022;11:e74974) concerns **DNA-templated / nuclear** expression — plasmid and
  adenoviral. **IVT mRNA never enters the nucleus**, so cryptic splice sites are not a mechanistic hazard
  for an mRNA vaccine. Do not inherit that caveat uncritically just because it appears in review articles.
- Others: Kudla G, et al. *PLoS Biol* 2006;4(6):e180 (GC-rich genes expressed >100× more — but the
  mechanism is transcriptional/processing, so it **does not transfer cleanly to IVT mRNA**); Presnyak V,
  et al. *Cell* 2015;160:1111–1124 (codon optimality drives mRNA stability, in yeast); **Mauger DM, et al.
  *PNAS* 2019;116:24075–24083 (CDS *secondary structure*, not codon identity, drives functional
  half-life)**; Leppek K, et al. *Nat Commun* 2022;13:1536 (combinatorial structure/stability/translation
  optimisation).
- **The contrasting industrial strategy, for completeness.** CureVac's approach is GC-maximisation of
  *unmodified* mRNA — **Thess A, et al.** *Mol Ther* 2015;23(9):1456–1464 (PMID 26050989): *"only the most
  GC-rich codons were used for each amino acid"*, and chemically modified versions of the same engineered
  sequence expressed **less** protein. **Naming correction worth carrying:** "RNActive" is **CureVac's**
  trademark, not BioNTech's. BioNTech's platform names are FixVac (BNT111/113/116), **iNeST** (BNT122 /
  autogene cevumeran), RiboMab, RiboCytokine, and the separate nucleoside-modified COVID platform.

**Does codon optimisation matter for immunogenicity?** Best primary evidence: **Zhang H, et al.**
*Algorithm for optimized mRNA design improves stability and immunogenicity.* **Nature**
2023;621(7978):396–403. PMID 37130545 · PMC10499610 — **LinearDesign**, objective
`MFE(r) − (|r|/3)·λ·log CAI(r)`; designs gave **57–128× higher anti-spike IgG** and **9–20× higher
neutralising titres** than an OptimumGene-designed benchmark, in mice, unmodified nucleotides, identical
UTRs. **But the authors attribute the effect to structural stability (MFE), with CAI co-varying.**
**No published study isolates codon usage at matched GC content and matched secondary structure and
measures immunogenicity.** Say that explicitly rather than implying CAI drives immunogenicity.

**The honest engineering conclusion: do not emit nucleotides** (§7.4). A CAI-optimised ORF adds nothing for
an expert reviewing epitope selection and junction safety, it would require inventing three proprietary
elements, and — per Lorenz 2015 — it introduces a *new* epitope-creation hazard we would then have to
screen. The construct is an amino-acid artifact.

### 4.5 The proprietary / public boundary — state this on the artifact

| Public and citable | Proprietary / unpublished |
|---|---|
| Overall architecture: epitope count, stretch length, mutation position, G/S linkers, sec+MITD layout | — |
| **The sec and MITD amino-acid sequences themselves** (*Nat Med* 2025 Methods, PMC11750724), cross-checked against the patent's 78 bp / 168 bp | **The 10-aa linker string** — length confirmed twice, sequence never printed |
| The cap: **β-S-ARCA(D1)** (Kuhn 2010); IVT nucleotides listed as "ATP, CTP, UTP, GTP" | — |
| The vector is *named*: `pST1-Sp-MITD-2hBgUTR-A120` (Kreiter 2015 Methods) | Its actual sequence |
| The 3′ UTR *elements*: 2×hBg (Holtkamp 2006), then AES(136 nt)–mtRNR1(142 nt) (von Niessen 2019); 5′ UTR = hAg-Kozak; poly(A) = 120 or A30L70 | **The nucleotide sequences as used in BNT122** — von Niessen 2019 prints none, and BioNTech has never published the cancer-vaccine UTRs |
| A full public mRNA sequence exists **for BNT162b2** (MHRA FOI 22-1116 module + community assembly) | That it is the same as BNT122's — **not published**; the amino-acid-string coincidence in the *Nat Med* 2025 Methods is an inference, not a claim |
| Autogene cevumeran = **unmodified uridine** mRNA, RNA-LPX of DOTMA + DOPE, ~400 nm; preclinical charge ratio (+):(−) **1.3:2** (Salomon N, et al. *Oncoimmunology* 2020;9:1771925) | **Clinical** RNA-LPX charge ratio and liposome process — *Nat Med* 2025 says only "an adopted proprietary protocol" |
| mRNA-4157 = up to 34 neoantigens, concatemeric, 1 mg IM, LNP of SM-102 / PEG2000-DMG / DSPC / cholesterol | mRNA-4157 linkers, UTRs, poly(A) length, **nucleoside chemistry as applied to that product**, LNP ratios |
| Poly(A) = 120 nt (BioNTech patent); β-S-ARCA(D1) cap in von Niessen 2019; 7mG(5′)ppp(5′)N1mpNp in the Moderna claim | Exact production cap structure and capping chemistry; **mRNA-1273's exact poly(A) length — no primary source found for the widely quoted ~100 nt, treat as unverified** |
| "Codon optimized" / "sequence-optimized" | **The codon table, objective function, and software** — for every product |
| Neoantigen selection is algorithmic | **Both selection algorithms.** Moderna's is an "internal neoantigen selection algorithm" in an appendix figure; BioNTech's is likewise unpublished |

**The last row matters most to us.** Neither company has published the neoantigen selection algorithm
that feeds its construct. So a demo cannot claim to reproduce their pipeline — only to run *our own*
selection into *their published construct layout*. Say exactly that.

### 4.6 Explicitly unverified in this pass

Kept separate so nothing here gets quoted as settled:

- **Holtkamp 2006 fold-changes.** The elements (2×hBg 3′ UTR, 120-nt poly(A), free 3′ terminus) are
  confirmed, but the paper is paywalled with no PMC copy, so **the quantitative fold-changes are
  unverified.**
- **von Niessen 2019 sequences.** In PMC but **not open access**; the element identities and fold-gains
  above come from the paper's Table 1 and abstract, but no nucleotide sequences are printed for the
  selected 3′ UTRs.
- **The exact 10-mer G/S linker.** Its **length is now confirmed twice** — Vormehr 2015 "nonimmunogenic
  10 mer glycine/serine linkers" and the *Nat Med* 2025 Methods "30 bp non-immunogenic glycine and serine
  linkers" — but **its sequence is printed nowhere.** The BioNTech patent's *example* is `GGSGGGGSG`
  (9 aa). `GGSGGGGSGG` circulates widely and **could not be confirmed against any primary source.** This
  is now the only gap in an otherwise fully specified construct. See §7.1.
- **The sec variant at position 4.** The patent's cloning primer encodes `MRVTAPRT…`, the *Nat Med* 2025
  Methods `MRVMAPRT…`. Use the peer-reviewed string; the discrepancy is unresolved (§3.1).
- **mRNA-4157's nucleoside chemistry.** Universally asserted to be m1Ψ in reviews, but **no primary source
  states it for mRNA-4157 specifically.** Moderna's platform papers do use complete UTP→m1ΨTP substitution
  with cap 1 (e.g. Shuptrine CW, et al. *Cancer Res* 2024;84:1550–1559, PMC11094416) — but that is a
  different product class. Write it as "consistent with Moderna's published platform chemistry but not
  documented for mRNA-4157 in any primary source."
- **BNT113 / BNT116 nucleoside chemistry.** No primary publication states it. Unmodified uridine is the
  strong inference (they are FixVac/RNA-LPX products, and the *Nat Med* 2025 paper states BNT111 uses "the
  same uridine-based RNA–LPX technology platform"), but do not cite it as established.
- **Huston 1988's exact 15-residue string.** "15-amino acid linker" is confirmed from the paper;
  `(GGGGS)3` is conventional attribution, not read from the primary source.
- **Velders 2001's per-construct spacer sequences** (paywalled).
- **US 11,885,815's per-linker junction-binder counts**, including the claim that the 7-aa linker
  `GGSGGGG` yields the fewest predicted 9-mers (patent text unretrievable).
- **Kreiter 2008's fold-changes** for sec/MITD (§3.1).

Also named for completeness, on the nucleoside-modification question (§4.2): **Karikó K, et al.**
*Immunity* 2005;23:165–175 (modification suppresses TLR recognition — i.e. *why* the cancer vaccines avoid
it) and **Andries O, et al.** *J Control Release* 2015;217:337–344 (m1Ψ outperforms Ψ).

**Kept honest:** §4.4's conclusion — *do not emit nucleotides* — means **nothing in the implementation
depends on any item in this subsection being right.**

---

## 5. What would make this DISHONEST to present

### 5.1 The do-not-claim list

A construct-assembly demo must **not** claim, imply, or structurally suggest any of the following.

**About the artifact itself**
1. That it is a **drug, a vaccine, or a candidate**. It is an amino-acid construct proposal.
2. That it is **manufacturable**, "synthesis-ready", "order-ready", or that a sequence could be sent to
   a vendor. pVACtools' own manufacturability metrics are *difficulty flags*, not a clearance.
3. That it is **GMP**, GMP-compatible, or has passed any release test.
4. That it is **de novo design**. It is deterministic assembly of already-selected peptides into a
   published layout. Say that in the artifact, not just in the README.
5. That **every** sequence in it is BioNTech's actual sequence. `sec` and `MITD` genuinely are (§3.1).
   The **linker string is not** — only its length (10 aa) is published, and `GGSGGGGSG` must be attributed
   to the patent's *example*, never to the product. The **UTRs, cap and codon table** for the cancer
   vaccine are not public either, which is one reason not to emit nucleotides at all (§7.4).

**About the immunology**
6. That the construct **will be immunogenic**, or that a screened-clean junction set means the
   construct is safe. A clean junction screen means *our predictors found no junction binder above
   threshold*, with all of the predictor's own error rates intact.
7. That the epitopes are **validated**. Our upstream shortlist is a prediction. The repo's own
   `research-benchmarks.md` numbers are the honest ceiling; do not let construct assembly launder a
   weak shortlist into an apparently finished product.
8. That junction screening **eliminates** junctional epitopes. It reduces *predicted* ones. There is no
   published in-vivo validation that computational junction screening prevents junctional responses
   (§2.3f).
9. That any linker we insert is **known to help**. Only the G/S family has clinical provenance, and
   "provenance" is not "proven". If a pvacvector fallback spacer ends up in the construct, the artifact
   must say that spacer has **no clinical precedent in this indication** — and for AAY specifically, that
   two published models rank it below no spacer at all (§2.2), and that **no primary paper ever
   established it** (§2.1b).
10. That the junction screen covers class II. It does not — our pipeline screens class I, and the one
    decisive junctional-epitope experiment (Livingston 2002) was **class II**. The construct encodes
    27-mers that certainly contain class II registers we are not screening.

**About the clinical picture**
11. That any efficacy number from KEYNOTE-942, Rojas 2023 or Sahin 2017 says anything about *our*
    construct. They are evidence about *those* products.
12. That the modality is **established** (see §6.4 — a randomised Phase 2 was terminated for futility
    with an OS imbalance).
13. That the construct size is a strength. Per §6.3a, the honest expectation for 20 epitopes is **~2–3
    that induce any response**, and **1–3 on the CD8 side**. Assembly cannot improve the shortlist; it can
    only avoid damaging it.

### 5.2 The real steps between "designed construct" and "a medicine"

In order, none of which a construct-assembly step touches:

1. **Analytical design QC** — sequence verification, off-target/self-similarity re-check on the *final*
   construct including junctions, secondary-structure and cryptic-splice review, synthesis feasibility.
2. **DNA template** — gene synthesis, cloning, sequence-verified plasmid or linear template, master/
   working template banks.
3. **Drug substance manufacture under GMP** — IVT, capping, poly(A), purification (dsRNA removal), fill.
4. **Drug product** — LNP/LPX formulation, encapsulation-efficiency and size/PDI control, fill-finish.
5. **Release testing** — identity (sequencing), purity, integrity, potency, endotoxin, **sterility**,
   residual dsRNA/DNA/solvent, container-closure. Standard sterility testing alone takes **two to three
   weeks**, which is why personalised products lean on **parametric release**, **sterility by design**,
   or **conditional release** pending the sterility result.
6. **Stability** — on a per-patient product this cannot be done per batch; sponsors test a *spectrum of
   product variants*, generate data on "**two engineering and five clinical batches**", and leverage
   platform knowledge.
7. **The potency problem, which has no clean answer.** "A potency assay would need to measure the
   neoantigen-specific T cell responses elicited by the vaccine, but to obtain a meaningful readout,
   these T cells would need to be collected from an already vaccinated patient."
8. **Non-clinical** — platform toxicology, biodistribution; per-patient tox is impossible, so the
   argument is made at platform level.
9. **Regulatory** — IND / CTA. FDA treats these as therapeutic cancer vaccines; in the EU classification
   depends on composition, with synthetic nucleic acids likely moving under **ATMP** rules. Relevant
   guidance: FDA *Clinical Considerations for Therapeutic Cancer Vaccines*; FDA AI/ML discussion paper
   (the FDA asks for "high-level information, including on all databases used to train the model and all
   detailed information regarding the bioinformatic tools" — directly relevant to a predictor-driven
   pipeline); EMA *Reflection paper on classification of ATMPs* (2015); EMA *Guideline on Real Time
   Release Testing*.
   Also: **"All NGS analysis must be conducted on validated protocols, with qualified equipment, and by
   trained staff"** (ISO 15189, ISO 17025, CAP). Our pipeline is none of those things.
10. **Chain of identity / chain of custody** — per-patient product tracking end to end.
11. **Clinical** — dose-finding, expansion, randomisation, DSMB, endpoints.

Source for the regulatory/CMC specifics: *The Complex Regulatory Landscape for Personalized Cancer
Vaccines*, ACRP, 22 Oct 2024.

### 5.3 How long it actually takes, per patient — published numbers

| Trial / product | Published turnaround | Source |
|---|---|---|
| **IVAC MUTANOME** (Sahin 2017) | **median 68 days** raw manufacturing (range 49–102); **median 103 days** total from mutation selection to vaccine release (range **89–160**) once first-in-human analytical testing is included | Sahin et al. *Nature* 2017 |
| **Autogene cevumeran, PDAC** | **median 9.4 weeks** surgery → first vaccine dose (range 7.4–11.0); internal benchmarks: ≤72 h shipping, ≤6 weeks manufacture, ≤9 weeks to first dose | Rojas et al. *Nature* 2023 |
| **Autogene cevumeran, solid-tumour Ph1** | "**best-case turnaround time of 28 days**" from receipt/approval of a complete sample set to end of manufacturing | *Nat Med* 2025, PMC11750724 |
| **mRNA-4157 / KEYNOTE-942** | not reported as a turnaround figure; patients received **pembrolizumab monotherapy during mRNA-4157 manufacturing**, and resection had to be ≤13 weeks before the first pembrolizumab dose | Weber et al. *Lancet* 2024 |
| Regulatory expectation | "**a fast turnaround is needed from biopsy to administration — typically under three months**" | ACRP 2024 |

**Note the gap between 28 days and 103 days.** The difference is *analytical release testing*, not
science. Any demo that implies a construct is minutes from a patient is off by two orders of magnitude.

### 5.4 Published failure / dropout rates

| Trial | Number | Source |
|---|---|---|
| **Rojas 2023 (PDAC)** | **1 of 19 (5 %)** had insufficient neoantigens → **vaccine not manufactured**. Funnel: **34 enrolled → 28 operated → 19 atezolizumab → 16 vaccinated → 15 mFOLFIRINOX** | Rojas et al. *Nature* 2023 |
| **KEYNOTE-942** | **1 of 107** combination patients received pembrolizumab alone because mRNA-4157 "could not be produced owing to insufficient tumour tissue"; manufacture succeeded for **>99 %** of the rest; **91 %** received the full 34 neoantigens (**range 9–34**); inadequate tissue quantity/quality was "**<7 % of those screened**"; **16 of 107** discontinued mRNA-4157 for an adverse event | Weber et al. *Lancet* 2024 |
| **Autogene cevumeran solid-tumour Ph1** | of those screened, **94 patients excluded for reasons related to manufacturing** | PMC11750724 |

The honest headline: **manufacturing succeeds >90 % of the time once you have adequate tissue — and
getting adequate tissue is the actual bottleneck.** A construct-assembly demo silently assumes a tissue
and sequencing success it has not earned.

---

## 6. The honest efficacy picture

### 6.1 KEYNOTE-942 — mRNA-4157 + pembrolizumab, resected melanoma

Weber JS, et al. **Lancet** 2024;403:632–644.

- **Phase 2b**, open-label, randomised **2:1**. **157 patients**: combination **n=107**, pembrolizumab
  monotherapy **n=50**. Stage IIIB–IV resected cutaneous melanoma. Median follow-up 23 / 24 months.
- Primary endpoint **recurrence-free survival**, ITT:
  **HR 0.561 (95 % CI 0.309–1.017), two-sided p = 0.053**.
  Events: **24/107 (22 %) vs 20/50 (40 %)**. **18-month RFS 79 % (69.0–85.6) vs 62 % (46.9–74.3)**.
- Distant metastasis-free survival: **HR 0.347 (95 % CI 0.145–0.828), p = 0.013**.
- Safety: grade ≥3 treatment-related AEs **25 % vs 18 %**; no mRNA-4157-related grade 4–5 events;
  immune-mediated AEs 36 % in both arms. **mRNA-4157-related injection-site reactions in 72/107 (69 %)**;
  AEs led to discontinuation of mRNA-4157 in **16/107 (15 %)**.
- **No immunogenicity result is reported in the primary publication.** The paper states it "was not
  powered for biomarker and immunogenicity analyses, which were exploratory in nature and involved small
  sample sizes". So the best randomised efficacy signal in the field is **not accompanied by published
  evidence that the construct did what it was designed to do** in that trial. Do not fill that gap with
  phase 1 data from a different cohort.
- Confirmatory **phase 3: NCT05933577**.
- **The statistical point that must be stated.** The trial was designed with **~80 % power to detect
  HR 0.5 at an overall one-sided α of 0.10** — success was "recurrence-free survival one-sided
  p < 0.099, corresponding to two-sided p < 0.198". So **p = 0.053 met the trial's prespecified bar and
  would not meet a conventional two-sided α = 0.05.** Both statements are true; publishing only the
  first is how this result gets oversold.
- **Also:** the confidence interval **crosses 1.0**. A phase 2b with 44 total events cannot settle this.
  The paper's own words: "Both a longer follow-up and a larger phase 3 study are needed to make more
  definitive conclusions."
- **Later updates** (3-year, median follow-up **34.9 months**): risk of recurrence or death reduced
  **49 %**, distant metastasis or death **62 %**; **2.5-year RFS 74.8 % vs 55.6 %**. Reported in
  *JCO Oncology Advances* 2025 (doi:10.1200/OA-25-00008) and ASCO 2024 LBA9512. Still **phase 2b, still
  n=157**, still not a phase 3 result. The confirmatory phase 3 programme is what would change this.

### 6.2 BNT122 / autogene cevumeran, pancreatic — Rojas et al. *Nature* 2023

- **Phase 1, single-arm, n = 16 vaccinated.** Adjuvant atezolizumab → autogene cevumeran (≤20
  neoantigens, nine 25 µg IV doses) → mFOLFIRINOX.
- Immunogenicity: **8 of 16 (50 %)** generated T-cell responses; **25 of 230 (11 %)** administered
  neoantigens induced a response.
- RFS: responders **median not reached** vs non-responders **13.4 months**,
  **HR 0.08 (95 % CI 0.01–0.4), P = 0.003** (landmark analysis HR 0.06, 95 % CI 0.008–0.40, P = 0.008).
  18-month median follow-up.
- **Follow-up:** Sethna Z, et al. *RNA neoantigen vaccines prime long-lived CD8+ T cells in pancreatic
  cancer.* **Nature** 2025;639:1042–1051 (PMID 39972124). At **3.2-year median follow-up**, responders
  (n=8) median RFS still not reached vs non-responders (n=8) 13.4 months, **HR 0.14 (95 % CI 0.03–0.6),
  P = 0.007**; induced CD8+ clones with estimated average lifespan **7.7 years** (range 1.5 to ~100).
- **Be blunt about the design.** This is **8 versus 8**, and the comparison is **responders versus
  non-responders within a single arm** — not vaccine versus control. Immune response is a *post-hoc*
  biomarker, and healthier patients with less aggressive disease are both more likely to mount a T-cell
  response and more likely to stay recurrence-free. That confound (guarantee-time / immortal-time bias
  in the responder split) is not removable by any amount of follow-up. **An HR of 0.08 from n=16 is a
  hypothesis, not an effect size.**

### 6.3 Sahin et al. *Nature* 2017 — the immunogenicity picture

- 13 patients. T-cell responses against **60 %** of vaccine neoepitopes; every patient responded to ≥3
  mutations; responses were **predominantly CD4**.
- 8/13 tumour-free at 23 months; 5 had already relapsed before neoepitope vaccination began; 2 objective
  responses; 1 complete response after vaccine + anti-PD-1.
- **Uncontrolled, n=13, heavily pre-selected.** The "reduced cumulative rate of metastatic events" is a
  within-patient before/after comparison.
- Compare NeoVax's split — **CD4 60 % / CD8 16 % of 97 neoantigens** (Ott 2017). Two independent
  platforms, same shape: *these constructs reliably raise CD4 responses and unreliably raise CD8
  responses.* Our pipeline screens class I. That asymmetry belongs on the artifact.

### 6.3a The arithmetic that ties this to our own benchmarks

This is worth doing explicitly, because it is the most honest single statement we can make about what a
20-epitope construct will do.

| Source | Fraction of construct epitopes that induced a T-cell response |
|---|---|
| Rojas 2023 (PDAC, RNA, ≤20 neoantigens) | **25 / 230 = 11 %** |
| Ott 2017 (NeoVax, peptides, CD8 only) | **15 / 97 = 16 %** |
| Hu 2021 (NeoVax follow-up, CD8 only) | **15 / 117 = 13 %** |
| Sahin 2017 (RNA, 10 neoepitopes, CD4 + CD8) | **60 %** — the outlier, and the smallest n |

And from this repo's own `research-benchmarks.md`: the measured base immunogenicity rate is **2.7 %**
(Bjerregaard 2017, 53/1948) with **6 % as the realistic screening prior (TESLA)**. TESLA's headline
metric is literally **TTIF, top-20 immunogenic fraction**, and the reason it is 20 is stated in that
document: *"20 chosen because therapeutic vaccine platforms reported to date have included ~20
neoepitopes."*

So the construct size and the benchmark metric are the same number, by design. The honest expectation for
a 20-epitope construct built from a *good* screen is **roughly 2–3 epitopes that actually induce a
response**, and historically **1–3 of those on the CD8 side**. That is not a failure of the construct
step; it is what the field achieves. But it does mean **the construct step cannot improve on the
shortlist** — it can only avoid damaging it at the junctions. Do not let assembly look like an
enrichment step.

### 6.4 The result that has to be in the honesty section

**BioNTech terminated the randomised Phase 2 of autogene cevumeran in resected colorectal cancer.**

- Trial: **BNT122-01, NCT04486378** — autogene cevumeran as adjuvant monotherapy vs watchful waiting in
  **ctDNA-positive**, resected high-risk stage II / stage III colorectal cancer.
- **The futility boundary was crossed in October 2025.** The independent DSMB "identified a **numerical
  imbalance in overall survival between treatment arms** in this specific patient population" and
  "recommended discontinuing treatment of patients in this trial and terminating the clinical trial".
  No new safety signals. Announced **28 August 2026**.
- The adjuvant PDAC Phase 2 (**IMcode003, NCT05968326**) continues.
- Source: BioNTech statement, 28 Aug 2026.

**What is and is not established, in one paragraph.** Established: personalised polyepitope constructs
can be designed and manufactured per patient within ~1–3 months at >90 % success given adequate tissue;
they reliably induce detectable neoantigen-specific T cells, mostly CD4; they are tolerable. Not
established: that they improve survival. The strongest randomised evidence is a **phase 2b with
two-sided p = 0.053 and a confidence interval crossing 1.0**; the most-cited pancreatic result is
**8 vs 8, responder-split, single-arm**; and the **first randomised trial to read out against a control
in a different indication was stopped for futility with an OS imbalance against the vaccine arm.**
Anyone presenting construct assembly as a step toward a proven therapy is misrepresenting the field.

---

## 7. What to implement

### 7.1 The recommended architecture — "published pentatope"

Assemble **exactly the Sahin/Vormehr layout**, because between Vormehr 2015 (epitope geometry and linker
length) and the *Nat Med* 2025 Methods (sec, MITD, linker length, cap), **every parameter except one has a
primary citation** — the exception being the linker's residue string:

```
MRVMAPRTLILLLSGALALTETWAGS                          <- sec, 26 aa, PUBLISHED (Nat Med 2025)
  ?  [E1: 27 aa, mutation at position 14]            <- Sahin 2017 / Vormehr 2015
  ?  [E2: 27 aa, mutation at position 14]
  ?  [E3: 27 aa, mutation at position 14]
  ?  [E4: 27 aa, mutation at position 14]
  ?  [E5: 27 aa, mutation at position 14]
  ?  IVGIVAGLAVLAVVVIGAVVATVMCRRKSSGGKGGSYSQAASSDSAQGSDVSLTA
                                                     <- MITD, 55 aa, PUBLISHED (Nat Med 2025)

? = NOTHING by default (direct fusion); a 10-aa G/S linker only where a junction needs it
```

**sec and MITD are real, published sequences** — cite *Nat Med* 2025 (PMC11750724) for the strings and
Kreiter 2008 for the rationale (§3.1). They are the one part of this construct we can emit verbatim
without inventing anything.

**On the linker string, be exact about what is known.** Vormehr 2015 says "nonimmunogenic **10 mer**
glycine/serine linkers". The BioNTech patent's *example* linker is **`GGSGGGGSG` — 9 aa**. The widely
circulated `GGSGGGGSGG` (10 aa) **could not be confirmed against any primary source.** So:
- Use **`GGSGGGGSG`** and cite it as *the example linker in US 10,738,355 B2*, **not** as "BioNTech's
  linker".
- Or emit the linker as a **parameterised 10-mer satisfying the patent's own claim** (≥50–95 % G/S), and
  say that the exact clinical string is unpublished.
- **Do not print `GGSGGGGSGG` and attribute it to Sahin 2017.** That is the §2.1b failure mode.

- **Two such molecules for a 10-epitope construct** — that is the pentatope design, not one long
  concatemer. Report it as two records.
- **Where the stretch cannot be 27 aa** (mutation within 13 residues of a protein terminus, or a
  frameshift/indel where the novel sequence is shorter), clip *asymmetrically* and record the actual
  length and mutation offset. Never pad with invented residues.
- **Scale**: 5 epitopes/molecule (BioNTech, published), or up to 10/molecule (autogene cevumeran,
  published), or up to 20 in one molecule (Moderna's 34 is published as a count but its layout is not).
  Default to 5 and make it a parameter with a per-value citation.

### 7.2 Ordering + junction screening (the actual algorithm)

Reimplement **pvacvector's escalation ladder** rather than inventing one. With n=5 the ordering space is
**`5! = 120`** permutations — all 120 distinct, because `sec` and `MITD` anchor the two ends, so this is
a path and not a cycle. 120 is **small enough to enumerate exhaustively and skip simulated annealing
entirely.** That is a real advantage of the pentatope design over a 34-epitope concatemer (`34!` ≈ 3×10³⁸,
which is precisely why pvacvector anneals), and it is worth saying out loud on the artifact: *at n=5 we
are exact where pvacvector must approximate.*

**Order first, linker only where needed.** This is the VaccineCAD / NeoDesign / pvacvector-`"None"`-first
policy, and per §2.1a it is also what the best modern *experimental* evidence supports for long stretches
in native flanking context. It matters concretely: Lee 2010 found junction-free orderings are usually
"astronomically" abundant, so most junctions will not need a linker at all.

```
1. For each of the 120 orderings, with NO linker:
     for each of the 6 junctions (sec|E1, E1|E2, ..., E5|MITD):
         for k in 8..11:
             J = left[-(k-1):] + right[:k-1]        # wingspan = k-1, per pvacvector
             score every k-mer of J against every patient allele (PeptideScreen)
     ordering is CLEAN iff no k-mer has affinity < 500 nM OR percentile < 2.0
2. If >=1 clean ordering: pick the one MAXIMISING THE WEAKEST junction affinity,
   deterministically, tie-broken by lexicographic epitope id -> reproducible artifact.
3. If none: escalate, in pvacvector's order --
   (a) insert the published G/S linker at the FAILING junction(s) only, and rescore
   (b) only if that fails, try the rest of pvacvector's --spacers list
       ["AAY","HHHH","GGS","GPGPG","HHAA","AAL","HH","HHC","HHH","HHHD","HHL","HHHC"]
       -- and flag on the artifact that NONE of these has clinical precedent here,
          that AAY scores worse than no spacer in two models (2.2),
          and that GPGPG is contraindicated near a class I junction (Bergmann 1996)
   (c) clip <= 3 aa from either/both flanks, NEVER inside the 9-mer window
       around the mutation (pvacvector v5's "preserve the binding core" rule)
   (d) drop an epitope, and say which one and why
4. Re-run the winner through the conservative pass (1000 nM + `lowest` metric)
   and report which setting it survived.
5. If nothing survives: FAIL LOUDLY. Emit the junction table and no construct.
   A construct-assembly step that always succeeds is lying.
```

Thresholds: **500 nM OR percentile < 2.0, failing on either** (pvacvector's `conservative` default), plus
the documentation's conservative pass at **1000 nM with the `lowest` score metric**. k range 8–11 covers
the class I registers MHCflurry predicts. Report every setting's verdict.

**Reuse note — this needs almost no new code.** `PeptideScreen._predict()` in `neofold/screen.py`
already filters to `8 <= len(p) <= 15`, which covers k=8–11 exactly, and already returns `affinity`,
`affinity_percentile`, `presentation_score` and `processing_score` per peptide. Two adjustments:
- `_predict` currently calls `predictor.predict(peptides=..., alleles=...)` **without** `n_flanks` /
  `c_flanks`. For a junction k-mer we actually *know* the true flanks — they are the neighbouring
  residues in the construct — so pass them. MHCflurry's antigen-processing predictor is flank-aware, and
  a junction screen that ignores flanks is throwing away the one piece of context that makes the
  processing score mean anything here.
- The junction path needs no `wt_peptide`, so `ScreenResult`'s WT/DAI fields do not apply. Use a separate
  lightweight record (`JunctionHit`) rather than forcing a `ScreenResult` with a fake WT — DAI on a
  junction peptide is meaningless, and a fabricated WT would quietly corrupt the DAI statistics.

**Screen the linker boundaries too.** `sec|L|E1` and `E5|L|MITD` are junctions. So is every
`E|L|E`. A junction is any boundary the patient's proteasome has never seen before.

### 7.3 What the artifact must carry

| Field | Why |
|---|---|
| Construct amino-acid sequence, per molecule | the deliverable |
| Per-epitope: candidate_id, gene, HGVS, allele, MHCflurry affinity, presentation score, DAI, mutation_site | traceability back through the existing pipeline |
| Stretch length and mutation offset actually used, per epitope | so a reviewer sees the clipping |
| Linker sequence + **its citation** | provenance, not assertion |
| `sec` / `MITD` **verbatim published sequences** (26 aa / 55 aa), cited to *Nat Med* 2025 + Kreiter 2008 | real, and requires inventing nothing |
| The **linker** as a 10-aa G/S placeholder, marked *length-confirmed, sequence-unpublished* | honest about the one gap that remains |
| **Full junction table**: every spanning k-mer × allele × affinity × pass/fail, at 500 and 1500 nM | the reviewable core |
| Number of orderings enumerated, and that enumeration was exhaustive | reproducibility |
| pVACtools/VaxRank **manufacturability flags** per stretch (Cys count, C-term Cys/Pro, N-term Asn/Gln/Glu/Cys, Asn-Pro bonds, GRAVY of C-terminal 7-mer, max 7-mer GRAVY) | useful without claiming manufacturability |
| CD4/CD8 asymmetry note (Ott 2017: 60 % / 16 %) | the construct's most likely real behaviour |
| The §5.1 do-not-claim block, verbatim | non-negotiable |

### 7.4 What NOT to build

- **No nucleotide output.** The moment you emit DNA/RNA you are implying a synthesis order, and you
  would have to invent UTRs, a cap, a poly(A) and a codon table — three of which are proprietary. Emit
  **amino acids** and cite §4 for what the mRNA layer would require.
- **No de novo linker search.** JessEV-style spacer optimisation is a research method (§2.2), not
  clinical practice; using it would make this de novo design.
- **No "optimised" or "designed" in the UI.** "Assembled" is the accurate verb.
- **No dose, route, schedule, or adjuvant** fields. Those are clinical decisions and have no place in a
  computational artifact.

### 7.5 Measurements we should make and label as ours

The house style in `research-filters.md` is to separate measured-here from cited. For this step the
measurements worth making on the repo's own demo panel are:

1. **Junction-binder rate**: over N random orderings of the shortlist with the G/S linker, what fraction
   of junctions produce ≥1 spanning k-mer ≤500 nM? This is the number nobody has published well, and we
   can compute it.
2. **Fraction of orderings that are clean** at 500 nM and at 1500 nM — i.e. how constrained the problem
   actually is at n=5.
3. **Whether the linker choice changes the answer** — same shortlist, each spacer from pvacvector's
   list, count clean orderings. If G/S is as good as AAY on our panel, that is a finding.
4. **How often clipping is needed** to reach a clean ordering.

Each of those is cheap, deterministic, and honest — and each is a better demo beat than a prettier
sequence.
