# Validation benchmarks: immunogenicity data and pMHC crystal structures

**Research date:** 2026-09-24 · **Audience:** the engineer wiring the validation harness this week.

Every number in this document that is marked **measured** was computed **in this session**, by
downloading the actual file and parsing it. Nothing in a "measured" row is quoted from a paper
abstract. Where I could not verify something I have written **UNVERIFIED** and said so.

---

## 0. The finding that should change what you build first

Before choosing a benchmark, know what the benchmarks say about the pipeline you already have.

I ran the repo's live `MIN_DAI = 10.0` gate against **two independent curated datasets with
measured T-cell outcomes**, 6,756 peptide–HLA pairs in total. Both were downloaded and parsed in
this session. "Enrichment" is PPV divided by the base positive rate; 1.00× means the filter
achieves nothing.

**Bjerregaard 2017** (n = 1,948; 53 immunogenic = 2.7 %), using the shipped NetMHCpan-4.0
`Mutant_affinity` / `Normal_affinity` columns, DAI = `affinity_WT / affinity_MT`:

| gate | kept | immunogenic kept | recall | PPV | enrichment |
|---|---|---|---|---|---|
| DAI ≥ 1 | 72.0 % | 42 / 53 | 79.2 % | 3.0 % | **1.10×** |
| DAI ≥ 2 | 41.8 % | 31 / 53 | 58.5 % | 3.8 % | **1.40×** |
| DAI ≥ 5 | 24.2 % | 18 / 53 | 34.0 % | 3.8 % | **1.40×** |
| **DAI ≥ 10** (repo default) | **17.9 %** | **13 / 53** | **24.5 %** | **3.7 %** | **1.37×** |
| MT affinity ≤ 50 nM (no DAI) | 31.1 % | 34 / 53 | **64.2 %** | **5.6 %** | **2.07×** |

**Koşaloğlu-Yalçın / Sette CII 2025 Table S4** (n = 4,808; 1,033 positive = 21.5 %), an
independent set 2.5× larger, same calculation:

| gate | kept | recall | PPV | enrichment |
|---|---|---|---|---|
| DAI ≥ 1 | 73.1 % | 74.2 % | 21.8 % | **1.02×** |
| DAI ≥ 3 | 37.3 % | 34.8 % | 20.0 % | **0.93×** |
| **DAI ≥ 10** | **21.9 %** | **19.5 %** | 19.1 % | **0.89×** |
| MT affinity ≤ 50 nM (no DAI) | 32.0 % | 41.1 % | 27.6 % | **1.28×** |
| MT affinity ≤ 50 nM **AND** DAI ≥ 10 | 8.3 % | **10.6 %** | 27.5 % | **1.28×** |

Read the last two rows of the second table together. Adding the DAI ≥ 10 gate on top of an
affinity filter **leaves precision unchanged (27.6 % → 27.5 %) while cutting recall from 41.1 %
to 10.6 %.** On this dataset the enrichment of the DAI gate is *below 1.0*, and it falls
monotonically as the gate tightens — the signature of a filter that is anti-correlated with the
outcome, not merely weak.

On Bjerregaard, DAI is weakly positive (1.37×) but still **strictly worse than a plain
affinity cut on every axis at once**: worse recall (24.5 % vs 64.2 %), worse PPV (3.7 % vs
5.6 %), worse enrichment (1.37× vs 2.07×). Its enrichment is also non-monotonic across
thresholds (1.10, 1.18, 1.40, 1.18, 1.40, 1.37), which is what noise looks like.

`research/audit-science.md` already flagged that the DAI gate discards KRAS G12D, BRAF V600E and
36 of 40 demo binders. This is the measurement behind that worry. **The first thing the
validation harness should produce is this table on your own pipeline** — and the `MIN_DAI` gate
should almost certainly become a reported score rather than a hard filter before it ships.

One honest caveat in the other direction: both datasets are pooled across studies, and TESLA's
own analysis found agretopicity *did* add signal on top of presentation (odds ratio 14.3) when
combined with foreignness — but only *conditional on* the presentation filters, which is a
narrower claim than a standalone gate. The published standalone AUCs for DAI are 0.539–0.59
(§4.2). The disagreement is real, but the burden of proof now sits with the gate.

### And a second finding, about the structure benchmark

**Both of your current structure anchors predate Boltz-2's training cutoff of 2023-06-01** —
`6ULN` (released 2020-05-27) and `3GSO` (2009-08-04). So do 23 of the 25 structures I would
otherwise have recommended on resolution alone.

This matters more than it sounds. Ascunce-París et al. 2026 applied that cutoff uniformly and
measured Boltz-2 going from **mean TCR-iRMSD 0.92 Å pre-cutoff to 4.59 Å post-cutoff** (DockQ
0.88 → 0.43). **A pMHC benchmark built from pre-2023 crystals measures memorisation, not
prediction.** §3.3 therefore splits the recommendation into a 24-structure **post-cutoff held-out
set** (Table A) and a pre-cutoff legacy set (Table B) to be reported separately and never averaged
in. There is no post-cutoff C\*08:02 structure at all, so any C\*08:02 number is necessarily
contaminated — say so rather than averaging it in quietly.

Two incidental wins there: **`6ULK` is the TCR-free twin of `6ULN`** (same HLA-C\*08:02 +
KRAS-G12D pMHC, 1.90 Å, three entities, identity operator), so the symmetry-operator problem that
bit you was avoidable; and the post-cutoff set contains **four matched wild-type/mutant pairs**,
which is the structural analogue of the DAI question above.

---

## 1. Data sources at a glance

Sorted by how usable they are for this pipeline. **Neg** = contains experimentally tested
non-responders (not random decoys). **WT** = ships the germline counterpart peptide.

| # | Source | Rows | Neg | WT | HLA | Offline | Licence |
|---|---|---|---|---|---|---|---|
| **1** | **CII 2025 meta-analysis, Table S4** | 4,808 | ✅ 3,775 | ✅ 100 %, + MT/WT NetMHCpan | ✅ class I | ✅ | CC BY |
| **2** | **Bjerregaard 2017 `table_1.csv`** | 1,948 | ✅ 1,895 | ✅ 100 %, all Hamming-1 | ✅ 27 alleles | ✅ | CC BY 4.0 |
| **3** | **CEDAR `tcell_full_v3`** | 2,718 clean triples | ✅ 1,316 | ✅ via Related Object | ✅ | ✅ | CC BY 4.0 |
| **4** | **IEDB `tcell_full_v3`** | same 2,718 | ✅ | ✅ | ✅ | ✅ | CC BY 4.0 |
| 5 | CII 2025 Table S7 | 16,604 | ✅ 14,426 | ✅ 16,582 Hamming-1 | ❌ no allele | ✅ | CC BY |
| 6 | PRIME 1.0 `mmc2.xlsx` | 7,758 (3,329 WT-paired) | ✅ | ⚠️ 43 % of rows | ✅ | ✅ | academic |
| 7 | ICERFIRE (NAR Cancer 2024) | 3,033 train | ✅ 2,402 | ✅ 100 % | ✅ | ✅ | CC BY |
| 8 | **TESLA `mmc4.xlsx`** | 608 | ✅ 571 **same-patient** | ❌ **none** | ✅ 13 alleles | ✅ | Elsevier © |
| 9 | ITSNdb | 199 | ✅ 70 | ✅ 100 % + anchor flag | ✅ 31 | ✅ | GPL-3.0 |
| 10 | NeoaPred Table S4 | 32,962 (3,647 defensible) | ✅ | ⚠️ not always germline | ✅ | ✅ | Apache-2.0 |
| 11 | NEPdb | 15,912 | ✅ 15,614 | ✅ 100 % | ✅ | ✅ | ⚠️ **none stated** |
| — | dbPepNeo 1.0 | 576 | ❌ | ⚠️ 33–72 % | ✅ | ✅ | none |
| — | TSNAdb v2 | 1,856 | ❌ | ❌ | ✅ | ✅ | none |
| — | TANTIGEN 2.0 | ~4,297 | ❌ | protein-level only | ❌ scrape-only | — | none |
| — | NeoPeptide | — | — | — | — | ❌ **dead** | — |
| — | NeoDB | 8,412 / 1,463 | ✅ | ✅ | ⚠️ **disjoint files** | ✅ | CC BY 4.0 |

**Recommendation: use #1 + #2 as the primary benchmark, #8 (TESLA) held out, #3 for scale.**
Rationale in §2.7.

⚠️ **These sets are not independent.** Measured overlaps on distinct mutant peptides:
NEPdb ∩ CEDAR = 1,788 (64.5 % of NEPdb, 46 label disagreements); CII-S7 ∩ NEPdb = 1,492;
Bjerregaard ∩ CEDAR = 397 (21.2 %, 21 disagreements). PRIME 1.0, NeoaPred and ITSNdb all draw on
the same primary studies (Bobisse, Bentzen, Cohen, Strønen, Robbins, McGranahan). **Training on
one and validating on another leaks.** Note also that ~45 peptides NEPdb calls negative have a
positive assay in CEDAR — "ground truth" here is assay- and dose-dependent.

---

## 2. TASK 1 — the immunogenicity benchmark

### 2.1 IEDB bulk exports — verified live

Base URL pattern: `https://www.iedb.org/downloader.php?file_name=doc/<filename>`

⚠️ **`downloader.php` returns HTTP 200 even for files that do not exist** — a missing file gives
`Content-Type: text/html` and a zero-byte body. Never test with a status code alone; check
`Content-Type: application/x-unknown` or a non-zero body.

| Filename | Status | Compressed | Uncompressed | Date |
|---|---|---|---|---|
| `tcell_full_v3.zip` | **live** | **45,075,473 B (43 MB)** | 1,349,330,563 B (1.26 GB) | 2026-09-21 |
| `epitope_full_v3.zip` | live | 107,444,129 B (102 MB) | ~0.95 GB | 2026-09-21 |
| `tcr_full_v3.zip` | live | 9,128,867 B | 167,223,283 B | 2026-09-22 |
| `receptor_full_v3.zip` | live | 10,488,970 B | — | 2026-09-22 |
| `antigen_full_v3.zip` | live | 2,631,308 B | 18,231,900 B | 2026-09-21 |
| `iedb_public.sql.gz` | live | 240,782,640 B (230 MB) | — | — |
| `mhc_full_v3.zip` | ❌ **DEAD** | 0 B, HTML | — | — |
| `bcell_full_v3.zip` | ❌ **DEAD** | 0 B, HTML | — | — |

**The MHC ligand export was renamed and split.** Replacements:
`mhc_ligand_full_single_file.zip` (301 MB → 9.24 GB, ZIP64) and
`mhc_ligand_full_multi_file.zip` (10 parts, `mhc_ligand_full_00.csv` … `_09.csv`).
B-cell likewise: `bcell_full_v3_single_file.zip` / `_multi_file.zip` (3 parts).
The authoritative machine-readable file list is `https://www.iedb.org/export_data_v3.php`
(plain JSON, no auth) — the HTML export page is a JS shell that renders from it.

**Licence: CC BY 4.0**, plus a NIAID statement placing no restriction on use or distribution.
No account, no DUA, fully anonymous. Offline use and redistribution are fine with attribution.

### 2.2 The CSV format — 161 columns, TWO header rows

Row 1 is a group header (sparse — only filled at the start of each group), row 2 is the field
header. **You must consume both rows before reading data.** Literal field names, 0-indexed:

| Idx | Group | Field |
|---|---|---|
| 3 | `Reference` | `PMID` |
| 9 | `Epitope` | `IEDB IRI` (full URL, e.g. `http://www.iedb.org/epitope/31803`) |
| 10 | `Epitope` | `Object Type` (`Linear peptide` / `Discontinuous peptide` / `Non-peptidic`) |
| **11** | `Epitope` | **`Name`** ← the peptide sequence |
| 19 / 23 | `Epitope` | `Source Molecule` / `Source Organism` |
| **28** | `Related Object` | **`Epitope Relation`** ← neoepitope flag |
| **30** | `Related Object` | **`Name`** ← **the wild-type peptide** |
| 43 | `Host` | `Name` |
| 51 | `1st in vivo Process` | `Disease` |
| 118 | `Assay` | `Method` |
| **122** | `Assay` | **`Qualitative Measurement`** |
| 124 | `Assay` | `Quantitative measurement` (note lowercase `m`) |
| 125 / 126 | `Assay` | `Number of Subjects Tested` / `Number of Subjects Positive` |
| **141** | `MHC Restriction` | **`Name`** (allele) |
| **143** | `MHC Restriction` | **`Evidence Code`** ← read §2.4 |
| **145** | `MHC Restriction` | **`Class`** |

Two naming corrections against the brief: the field is **`Qualitative Measurement`** (not
"Qualitative Measure"), and the responder count is **`Number of Subjects Positive`** (not
"responded").

### 2.3 Negatives — yes, and they are the majority (measured)

I streamed all 578,145 data rows. **Exactly five values occur, and the field is never empty:**

| Value | Count | % |
|---|---|---|
| **`Negative`** | **363,535** | **62.9 %** |
| `Positive` | 185,542 | 32.1 % |
| `Positive-Low` | 18,107 | 3.1 % |
| `Positive-High` | 5,826 | 1.0 % |
| `Positive-Intermediate` | 5,135 | 0.9 % |

**Filtering to human + class I:** col 43 `Host|Name` prefix-match `Homo sapiens` (sub-populations
carry their own labels like `Homo sapiens Caucasian`, so prefix-match, not equality) **and**
col 145 `MHC Restriction|Class` exactly `I`. That gives **125,726 rows: 68,366 Negative (54.4 %)
vs 57,360 positive-of-any-grade.** The T-cell export is already only T-cell assays — no third
filter needed. Note 137,168 rows (23.7 %) have **no class assigned at all**.

Restricting further to cancer-context diseases gives 26,332 rows, 62.6 % negative.

### 2.4 Two traps in the MHC restriction columns (measured)

1. **`MHC Restriction|Name` is often not an allele.** In the human class-I subset, `HLA-A*02:01`
   is 30,681 rows but **`HLA class I` (no allele at all) is 26,327** and `HLA-A2` (serotype only)
   is 5,451. Filter on `*` being present, not just on class.
2. **`MHC Restriction|Evidence Code` = `MHC binding prediction` on 20,295 human class-I rows.**
   Those rows had their allele assigned *by a binding predictor*. Validating a binding-predictor-
   driven pipeline on them is circular. **Drop them.** Other values: `Not determined` (24,596),
   `Cited reference` (23,162), `T cell assay -T cell subset identification` (21,882),
   `MHC binding assay` (16,560), `Single allele present` (14,295).

### 2.5 Wild-type counterparts — IEDB has them (measured)

This was the open question, and the answer is yes. The **`Related Object`** column group carries
the germline peptide for mutant epitopes. Direction confirmed internally against CEDAR's
`Mutation` column: for `M236Y`, `Epitope|Name = CYTWNQMNL` (Tyr) and
`Related Object|Name = CMTWNQMNL` (Met) — **epitope = mutant, related object = wild-type.**

`Related Object|Epitope Relation` values in the human class-I subset:

| Relation | Rows | Use? |
|---|---|---|
| `in-frame neo-epitope` | 16,942 | ✅ |
| `unspecified neo-epitope` | 1,016 | ✅ |
| `frameshift neo-epitope` | 429 | ✅ |
| `fusion neo-epitope` | 73 | ✅ |
| `analog` | 4,107 | ❌ lab-designed heteroclitic peptides |
| `mimotope` | 61 | ❌ |
| *(empty)* | 103,098 | — |

Deduplicating to unique **(mutant, wild-type, allele)** triples where both sequences are plain
8–15-mers of equal length that actually differ:

| Filter | Triples | Positive | Negative |
|---|---|---|---|
| All neo-epitope relations | **7,533** | 2,211 | 5,322 |
| **Drop predicted restriction + require 4-digit allele** | **2,718** | **1,402** | **1,316** |

**2,718 clean, non-circular, WT-paired, allele-resolved pairs, 51.6 % positive** — and
**2,570 of them differ by exactly one residue**, which is precisely the DAI use case. 295 triples
have both positive and negative assays; the extractor below labels those `positive` and flags
them in a `conflicting` column so you can choose your own policy.

⚠️ **That 51.6 % positive rate is a curation artefact, not prevalence.** Labs publish positives.
TESLA's 6 % is the realistic screening prior. Compute PPV and enrichment against the prior you
actually face, not against 51.6 %.

### 2.6 CEDAR — same pairs, 3.7× smaller download, plus a mutation column

CEDAR (`https://cedar.iedb.org/`) is IEDB's cancer sister database and mirrors the same
infrastructure with the **same filenames** but cancer-scoped content:

```
https://cedar.iedb.org/downloader.php?file_name=doc/tcell_full_v3.zip
```

**Measured: 14,395,659 B (13.7 MB) → 359,060,828 B (342 MB) CSV, 156,059 rows, 162 columns,
dated 2026-09-18.** Licence CC BY 4.0.

Two things make it the better download for this job:

1. **It yields the identical pair set.** I ran the same extraction on both: CEDAR gives exactly
   **7,533** triples and exactly **2,718** clean ones — byte-for-byte the same numbers as the
   full IEDB export, from a file 3.7× smaller and a CSV 3.7× smaller.
2. **It adds `[Epitope] Mutation` (column 27)** — the protein-level substitution (`F1637L`,
   `E153K`, `Q285K`), **populated on 81.0 % of neo-epitope WT/MT assay rows**. Combined with
   `Epitope|Source Molecule` (UniProt) this gives you gene + variant, which TESLA lacks entirely.

⚠️ CEDAR's column indices are **shifted by one** after column 27 relative to IEDB, because of that
extra `Mutation` column. Do not reuse IEDB indices on a CEDAR file. In CEDAR:
`Related Object|Epitope Relation` = 29, `Related Object|Name` = 31, `Host|Name` = 44,
`Assay|Qualitative Measurement` = 123, `MHC Restriction|Name` = 142, `Evidence Code` = 144,
`Class` = 146.

⚠️ CEDAR's T-cell export is **not purely cancer** — top diseases include hepatitis C (13,453 rows)
and COVID-19 (2,273). Filter on disease or on the API's `neoantigen_bool`.

**REST API** (undocumented on the export page): `https://cedar-api.iedb.org/` — PostgREST 9.0.1,
serves `text/csv` directly. Notably `/epitope_variant_information` carries 23,118 records with
`accession, protein_mutation_position, protein_mutation_aa, protein_wildtype_aa, chromosome,
dbsnp_id` — genomic-level WT annotation the flat files do not have. `neoantigen_bool` is an
**integer 0/1, not boolean**. Server caps responses at 10,000 rows; page with
`&limit=10000&offset=N&order=structure_id`.

**IEDB's own API** is `https://query-api.iedb.org/` (PostgREST, no auth, 39 tables). Row counts
cross-validate the CSV exactly (`tcell_search` total = 578,145; `mhc_class=eq.I` = 186,471).
Use `tcell_search` (86 cols, has `linear_sequence`, `qualitative_measure`, `mhc_allele_name`) for
search, or `tcell_export` (162 cols, a 1:1 CSV mirror with `group__field` names) if you need the
subject counts. Field names differ between the two — `qualitative_measure` vs
`assay__qualitative_measurement`.

```bash
# exact count without pulling rows -> Content-Range: 0-0/123703
curl -D - -o /dev/null -H "Prefer: count=exact" -H "Range-Unit: items" -H "Range: 0-0" \
  "https://query-api.iedb.org/tcell_search?host_organism_iri=eq.NCBITaxon:9606&mhc_class=eq.I"
```

### 2.7 TESLA — the best negatives, but no wild-type at all

Wells DK et al., *Cell* 2020;183(3):818–834.e13, doi `10.1016/j.cell.2020.09.015`, PMID 33038342,
PMC7652061. Note the correct title ends "…Consortium Approach **to Improve** Neoantigen
Prediction".

**The per-peptide table is Table S4 and it downloads without auth:**

```
https://ars.els-cdn.com/content/image/1-s2.0-S0092867420311569-mmc4.xlsx
```

**Verified: HTTP 200, 88,188 B, sheet `master-bindings-selected`, 608 data rows, 21 columns.**
SHA-256 `5cd384753464e981712af15dffa3b8cb5a3c2c5026e8cd80894a17f9df6236fe`.

```
PMHC, PATIENT_ID, TISSUE_TYPE, MHC, ALT_EPI_SEQ, PEP_LEN, MEASURED_BINDING_AFFINITY,
NETMHC_PAN_BINDING_AFFINITY, TUMOR_ABUNDANCE, BINDING_STABILITY, FRAC_HYDROPHOBIC,
AGRETOPICITY, FOREIGNNESS, MUTATION_POSITION, NUMBER_PREDICTING, VALIDATED,
TCR_FLOW_I, TCR_FLOW_I_QUANT, TCR_NANOPARTICLE, TCR_FLOW_II, TCR_FLOW_II_QUANT
```

- **`VALIDATED` = 37 True / 571 False**, and it is the logical OR of the three multimer assays
  (verified: 0 mismatches across 608 rows).
- **Matched same-patient negatives**, 6 patients (3 melanoma, 3 NSCLC): tested 97/108/97/73/89/144,
  immunogenic 9/4/13/3/4/4. These are **hard negatives** — top-ranked predictions from 25
  pipelines that failed multimer staining, not decoys. That is TESLA's unique value.
- `MEASURED_BINDING_AFFINITY` is a real experimental IC50 in nM (radiolabelled competition),
  105 NA. **There is no mass-spec column** — "presentation" is inferred from affinity + stability
  + abundance, not immunopeptidomics.
- ⚠️ **No wild-type peptide column, and no gene/transcript/variant ID to reconstruct one.**
  `MUTATION_POSITION` is only the position *within* the peptide. The sole WT-derived signal is
  `AGRETOPICITY` (missing on 40 of 608). **And TESLA's agretopicity is the inverse of your DAI** —
  low agretopicity means the mutant binds better. Do not compare the columns directly.
- Only 286 of 608 rows have all five core features non-missing; the paper's feature analyses run
  on that subset.
- Table S7 (`…-mmc7.xlsx`, 45,027 B) is an independent second cohort: 310 peptides, 4 immunogenic,
  3 different melanoma patients — but **no `MHC` column**.

**Access:** PMC7652061 is an NIH author manuscript, free to read but **not open-access licensed**;
Europe PMC refuses the supplements. The Elsevier CDN link above works anonymously, but Elsevier
copyright applies to *redistribution* — ship a fetch script, not the xlsx.
**Synapse `syn21048999` is real but holds only raw WES/RNA-seq (~349 GB) and is controlled
access** (Certified User quiz, ORCID, signing-official letter); melanoma also in dbGaP
`phs000452.v3.p1`. **The table you need is not behind that DUA** — the DUA only gates sequencing.

### 2.8 The two best WT-paired tables

**① Koşaloğlu-Yalçın / Sette, CII 2025** — "A meta-analysis of experimentally validated
neo-epitopes", *Cancer Immunol Immunother* 2025;74(12), doi `10.1007/s00262-025-04209-7`,
PMID 41196374, PMC12592574, **CC BY**. A cleaned, deduplicated CEDAR derivative.

```
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12592574/supplementaryFiles
```
**Verified: 10,653,093 B zip.**

- **`262_2025_4209_MOESM4_ESM.xlsx` — measured: 4,808 rows, 47 columns, 3,775 negative /
  1,033 positive, all MHC class I.** This is the single best drop-in. It ships **paired**
  `Mut_Peptide`/`WT_Peptide`, `Mut_Aff(nM)`/`WT_Aff(nM)`, `Mut_%Rank_EL`/`WT_%Rank_EL`,
  `Mut_Icore`/`WT_Icore`, plus `anchors`, `anchors_secondary`, `aa_mut_pos_in_pep`,
  `aa_mut_pos_in_core`, `uniprot_id`. DAI is computable directly, and the anchor columns map
  straight onto the anchor-vs-TCR-facing split already in `research-filters.md`.
- `MOESM7` — measured: 16,604 rows, 11 cols, **14,426 negative / 2,178 positive**, 16,582 exact
  1-aa pairs. Has `in_strict_subset` (≥3 assays, positive only if ≥2 positive assays) marking a
  high-confidence core of 518 peptides (301 pos / 217 neg). **No allele column.**

⚠️ **MOESM4 will silently read as EMPTY.** The file declares `<dimension ref="A1"/>` — a bogus
one-cell range. `openpyxl` in `read_only=True` trusts it and returns **0 rows and 1 column with
no error**. In normal mode it instead crashes with
`KeyError: "There is no item named 'xl/drawings/drawing1.xml'"`. Workaround that I verified
returns all 4,808 rows:

```python
import zipfile, re, openpyxl
zin = zipfile.ZipFile("262_2025_4209_MOESM4_ESM.xlsx")
zout = zipfile.ZipFile("moesm4_fixed.xlsx", "w", zipfile.ZIP_DEFLATED)
for it in zin.infolist():
    d = zin.read(it.filename)
    if it.filename == "xl/worksheets/sheet1.xml":
        d = d.replace(b'<dimension ref="A1"/>', b'<dimension ref="A1:BU4809"/>')
        d = re.sub(rb"<drawing[^>]*/>", b"", d)
    if it.filename == "xl/worksheets/_rels/sheet1.xml.rels":
        d = re.sub(rb"<Relationship[^>]*drawing[^>]*/>", b"", d)
    zout.writestr(it, d)
zout.close()
```

**② Bjerregaard et al. 2017** — *Front Immunol* 8:1566, doi `10.3389/fimmu.2017.01566`,
PMID 29187854, PMC5694748, **CC BY 4.0**.

⚠️ **No frontiersin.org direct-file endpoint works** (six URL patterns probed, all 404; PMC
`/bin/table_1.csv` also 404). The working route:

```
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC5694748/supplementaryFiles
```
**Verified: 510,717 B zip → `table_1.csv`, 414,431 B, MD5 `c70b6455d5670fbb3a016f8676daf1f0`.**

⚠️ **There is a corrigendum** (doi `10.3389/fimmu.2018.01007`, PMC5961322): the originally
published table was an outdated version **missing the similarity column**. The file served now is
the corrected one — **check that MD5**, because a stale mirror silently lacks both
`Self-similarity` and `DAI`, which are exactly what you would validate against.

**Measured: 1,948 rows, 28 columns, `Tcell_response` = NO 1,895 / YES 53** (matches the abstract),
**`Normal_peptide` populated on all 1,948 rows and Hamming distance exactly 1 on all 1,948**,
27 alleles, 24 patients, `Anchor` = YES 482 / NO 1,466.

```
Study, Mutant_peptide, Tcell_response, Normal_peptide, HLA_allele, AminoAcid_change, Mismatches,
Patient, Analysis_type, Mutant_affinityRank_4.0, Normal_affinityRank_4.0, Mutant_affinity_4.0,
Normal_affinity_4.0, Mutant_elutedligandRank_4.0, Normal_elutedligandRank_4.0,
Mutant_elutedligandScore_4.0, Normal_elutedligandScore_4.0, Normal_pepmatch_identified,
Removed_from_study, pMHC, Length, Mutation_position, Anchor, BindingPosition, BindingDiff,
BindingGroup, Self-similarity, DAI
```

**On the shipped `DAI` column — measured.** Its Spearman correlation with
`log10(Normal_affinity_4.0 / Mutant_affinity_4.0)` is **exactly 1.0000** across all 1,948 rows.
So the **direction matches this repo's convention** (higher = mutant binds better) and it is a
log-scale quantity. But the values do **not** reproduce from the shipped 4.0 columns (0 exact
matches on any of nine candidate formulas), so it was computed with an earlier NetMHCpan version.
**Treat it as a rank-level cross-check on your DAI implementation, not a value-level one** —
and recompute DAI yourself from the MT/WT affinity columns, as I did in §0.

Other gotchas: `Normal_pepmatch_identified` is FALSE on 1,169 rows (WT not found by pepmatch);
`Analysis_type` has casing typos (`ElISPOT` ×10, `Flow Cytocines`); `pMHC` is unique and usable as
a primary key; `Removed_from_study` is FALSE everywhere.

### 2.9 The rest — honest status

- **NEPdb** (`http://nep.whu.edu.cn/`) — **alive, with an undocumented bulk export**. There is no
  `/download/` page (404). Use **`http://nep.whu.edu.cn/search/?download=1`** → 200, `text/csv`,
  `filename="NECID_Query.csv"`, **26,486,239 B, 15,912 rows, 44 columns**. `response` = **N 15,614
  / P 298**; `wt_peptide` populated on **100 %** of rows, plus `wt_aa`, `mut_aa_pos`,
  `mut_pos_in_pep`, `num_mm`, a rendered `pep2aln` alignment and full `protein_sequence`.
  ⚠️ **13,737 of 15,912 rows are 25-mers** from tandem-minigene screens; only **323 are 9-mers**.
  The 52:1 negative ratio is a TMG artefact, not epitope-level testing — filter on `antigen_len`
  first. ⚠️ **No licence statement anywhere**, only "Copyright © NEPdb 2021" — treat as
  all-rights-reserved and email the authors before redistributing. The paper claims >17,000; the
  live file has 15,912.
- **dbPepNeo2.0** — the 234-byte response is a JS stub redirecting to a bare IP,
  `http://119.3.70.71/dbPepNeo2/home.html`. **No downloadable file**: the download page is a gated
  request form whose AJAX posts to an empty URL and then unconditionally claims success. **There
  is no automated delivery.** dbPepNeo **1.0** does have real files in an open directory at
  `http://www.biostatistics.online/dbPepNeo/download/` (`HC neoantigens.xlsx` 54,441 B / 308 rows;
  `MC` 41,824 B / 259; `LC` 11,944 B / 9). **No negatives** — `Verification` records only how a
  positive was shown, and `Bind Level` (SB/WB/NB) is a **NetMHCpan prediction**, so `NB` is not a
  validated negative. WT partial (HC 72 %, MC 33 %). The "2,200 non-immunogenic" peptides in the
  paper are model training data and are in no downloadable file.
- **TANTIGEN 2.0** — `tantigen.cvc.dfci.harvard.edu` and `projects.met-hilab.org/tantigen2` both
  time out; `tantigen2.cancerimmunity.org` is a squatted Apache index whose only file is a 2014
  error page. **Live only at `https://projects.met-hilab.org/tadb/`**, and it has **no bulk
  download at all** (scrape-only; `cgi/searchL.pl` returns 0 bytes every time — broken).
  **No negatives** — the only outcome-ish field is `Experimental method`. WT at protein level only.
- **NeoPeptide** — **dead and unrecoverable.** Both domains 301 to a Tencent domain-block page.
  Wayback holds 11 captures, all homepage/CSS/JS; `/bic/html/download.do` was **never archived**.
  The GitHub mirror is source code only, and its schema had no WT column anyway.
- **TSNAdb** — v1 at `biopharm.zju.edu.cn` returns 502; **v2 is live at
  `https://pgx.zju.edu.cn/tsnadb/`**. `validated_tsnadb2_download.zip` (66,675 B) → 1,856 rows.
  **No negatives and no WT column** — all validated positives, `Mutant Peptide` only.
- **NeoDB** — published URL `liuxslab.com/Neodb` is NXDOMAIN. Data rehomed to Zenodo
  `10.5281/zenodo.16892216` (CC BY 4.0, `Neodb_data.zip` 884,811,288 B). ⚠️ Negatives and WT are in
  **two disjoint files with no shared key**, and some rows in `neodb_all.csv` are column-shifted.
- **PRIME** — the repo ships **no** training data (weights and 5,123 calibration files only);
  `GfellerLab/PRIME2` does not exist. Use **PRIME 1.0**: PMC7897774 →
  `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7897774/supplementaryFiles` → `mmc2.xlsx`
  (1,421,682 B, sheet `TableS1`, **header on row 3**), 7,758 rows, 1,282 immunogenic. Ships
  `ratio_Kd` (agretopicity), `DisToSelf` and `Foreignness` precomputed — three direct external
  checks on filters already in this repo. **`StudyOrigin == 'Random'` isolates exactly 2,800
  decoys — drop them.** 3,329 rows carry `WT_peptide`, 3,295 Hamming-1.
- **NeoaPred** — `Supplementary file2.xls` is **legacy BIFF** (needs `xlrd`; openpyxl refuses),
  32,962 rows. ⚠️ **"WT" is not uniformly germline**: only 13,380 rows are Hamming-1. The IEDB
  bulk portion (27,130 rows) is 34 % Hamming-1, where "WT" is a BLAST-derived nearest-self peptide.
  Filtering to cancer sources ∧ Hamming-1 gives a defensible **3,647 rows (97 pos / 3,550 neg)**.
- **BigMHC** — repo has weights and metrics only. Data on Mendeley `10.17632/dvmz6pkzvb`:
  `im_train.csv` (7,940 rows, 956 pos / 6,984 neg — assay-tested, not decoys), `iedb.csv` (9,615),
  `manafest.csv` (837), `ifng.csv` (250). Header `mhc,pep,tgt`. **No WT column.**
  ⚠️ `neg.csv.zip` (1.7 GB) is the decoy pool for the *presentation* model — a different thing.
- **ITSNdb** — `https://github.com/elmerfer/ITSNdb`, **GPL-3.0**, data in-repo at
  `data/ITSNdb.csv` (30,265 B, **199 rows, 129 Positive / 70 Negative**, WT on all 199 and ≠ mutant
  on all 199, 31 alleles, `PositionType` = 145 Non-anchor / 54 Anchor). Small but clean and
  anchor-annotated.
- **DeepNeo** — `github.com/kaistomics/DeepNeo` is **404**. A surviving copy has a licence that
  **forbids redistribution** and its only labelled file is 45 bytes. **TLimmuno2** is MHC class II
  only. **Caleydo "Neoantigen Atlas"** does not exist (misattribution; Caleydo's tool is Ordino).
- **NeoRanking / HiTIDE** (Müller et al., *Immunity* 2023) — `github.com/bassanilab/NeoRanking`,
  code only, no licence. The harmonized 131-patient matrices (NCI + TESLA + HiTIDE) are on
  **figshare links that return HTTP 202 bot challenges to curl — UNVERIFIED**, needs a browser
  session. Probably the largest such benchmark; worth a manual pull.

### 2.10 Extraction script — tested end to end

Produces **2,718 rows, 1,402 positive / 1,316 negative, 295 conflicting, 2,570 Hamming-1**.
Runs against either IEDB or CEDAR (adjust the index map — see §2.6).

```python
#!/usr/bin/env python3
"""
Neoepitope immunogenicity benchmark with matched wild-type counterparts, from the
IEDB/CEDAR T-cell bulk export.

    curl -L -o tcell_full_v3.zip \
      'https://cedar.iedb.org/downloader.php?file_name=doc/tcell_full_v3.zip'
    unzip -p tcell_full_v3.zip tcell_full_v3.csv | python3 extract_iedb.py > bench.tsv
"""
import csv, sys
from collections import defaultdict, Counter

csv.field_size_limit(10**9)

# IEDB tcell_full_v3.csv: 161 cols. For CEDAR (162 cols) add 1 to every index >= 27.
C = dict(pmid=3, epi_name=11, rel=28, rel_name=30, host=43, disease=51,
         method=118, qual=122, allele=141, evidence=143, mhc_class=145)

NEO = {"in-frame neo-epitope", "unspecified neo-epitope",
       "frameshift neo-epitope", "fusion neo-epitope"}   # excludes analog / mimotope

def main(drop_predicted_restriction=True, require_allele_resolution=True):
    r = csv.reader(sys.stdin)
    next(r); next(r)                       # discard BOTH header rows
    acc = defaultdict(lambda: {"qual": Counter(), "pmid": set(),
                               "method": Counter(), "disease": set()})
    for row in r:
        if len(row) < 161:                                        continue
        if not row[C["host"]].strip().startswith("Homo sapiens"): continue
        if row[C["mhc_class"]].strip() != "I":                    continue
        if row[C["rel"]].strip() not in NEO:                      continue

        mt, wt = row[C["epi_name"]].strip(), row[C["rel_name"]].strip()
        allele = row[C["allele"]].strip()

        if not (mt.isalpha() and wt.isalpha()):          continue
        if len(mt) != len(wt) or not 8 <= len(mt) <= 15: continue
        if mt == wt:                                     continue

        # Restriction assigned BY a binding predictor is circular evidence for a
        # pipeline whose first stage is a binding predictor.
        if drop_predicted_restriction and \
           "prediction" in row[C["evidence"]].strip().lower():    continue
        if require_allele_resolution and "*" not in allele:       continue

        a = acc[(mt, wt, allele)]
        a["qual"][row[C["qual"]].strip()] += 1
        a["pmid"].add(row[C["pmid"]].strip())
        a["method"][row[C["method"]].strip()] += 1
        if row[C["disease"]].strip():
            a["disease"].add(row[C["disease"]].strip())

    print("\t".join(["mt_peptide", "wt_peptide", "allele", "n_mismatch", "mut_position",
                     "label", "n_pos_assays", "n_neg_assays", "conflicting",
                     "methods", "pmids", "diseases"]))
    for (mt, wt, allele), a in sorted(acc.items()):
        npos = sum(v for k, v in a["qual"].items() if k.startswith("Positive"))
        nneg = a["qual"].get("Negative", 0)
        diffs = [i for i, (x, y) in enumerate(zip(wt, mt), start=1) if x != y]
        print("\t".join([
            mt, wt, allele, str(len(diffs)), ",".join(map(str, diffs)),
            "positive" if npos else "negative", str(npos), str(nneg),
            "yes" if (npos and nneg) else "no",
            ";".join(sorted(a["method"])),
            ";".join(sorted(p for p in a["pmid"] if p)),
            ";".join(sorted(a["disease"])[:3]),
        ]))

if __name__ == "__main__":
    main()
```

### 2.11 Recommended split

1. **Primary: CII 2025 MOESM4 (4,808) + Bjerregaard (1,948).** Both CC BY, both 100 % WT-paired,
   both ship independent DAI/agretopicity and anchor columns you can check your implementation
   against. Together ~6.7k pairs. This is what §0 was computed on.
2. **Scale-up: CEDAR extraction (2,718 clean triples).** Same licence, adds alleles and diseases.
   ⚠️ Deduplicate against #1 — CII 2025 *is* a CEDAR derivative, so they overlap heavily.
3. **Held out, never trained on: TESLA (608).** The only set with same-patient matched negatives
   and a realistic 6 % prevalence. ⚠️ **TESLA is already curated into IEDB/CEDAR** — PMID 33038342
   contributes 907 rows — so you must *exclude* it from #2 by PMID or you are testing on train.
4. Report per-patient where patient IDs exist (TESLA, Bjerregaard) as well as pooled — see §3.4.

---

## 3. TASK 2 — pMHC class I crystal structure benchmark

Everything in this section was **executed against the live RCSB API on 2026-09-24**, not quoted.
Reproduce with `scripts/fetch_pmhc_benchmark.py` (listed in full below).

### 3.1 Measured facts

| Fact | Value |
|---|---|
| RCSB entries matching the query (InterPro IPR001039 + human + X-ray + res < 2.5 Å + 3 polymer entities + one entity 8–15 aa) | **622** |
| After removing mouse H-2 / rabbit / non-classical human heavy chains | **582** |
| Fully clean (canonical peptide residues, identity operator only, single copy in ASU) | **413** |
| Entries needing a non-identity symmetry operator for assembly 1 | **5 / 620 (0.8 %)** — `9F13`, `3BH9`, `7RZJ`, `1YDP`, `3DTX` |
| Entries with >1 copy of the complex in the asymmetric unit | **159 / 620 (26 %)** |
| Entries whose "peptide" contains a modified/non-standard residue | **45 / 620 (7 %)** |
| Distinct 4-digit alleles parseable from entry titles | **47** (301 of 582 rows; the other 235 titles do not name a 4-digit allele) |
| Using Pfam `PF00129` instead of InterPro `IPR001039` | loses **148 entries**, including most KRAS neoantigen structures |

### 3.2 The gotcha you hit with 6ULN — measured, with numbers

`6ULN` assembly 1 is generated by **two** `pdbx_struct_assembly_gen` records:

| gen record | oper | symop | asym_ids |
|---|---|---|---|
| 1 | `1` | identity, `1_555`, `x,y,z` | A, B, C, F, G, H, I, P, Q, R  (**HLA-C\*08:02 + B2M + peptide**) |
| 2 | `2` | crystal symmetry, `1_455`, `x-1,y,z` | D, E, J, K, L, M, N, O, S, T  (**TCR α + β**) |

Measured CA centroids (Å):

| chain | in `6ULN.cif` (asymmetric unit) | in `6ULN-assembly1.cif` | shift |
|---|---|---|---|
| A (HLA heavy) | 13.4, −8.4, 35.1 | 13.4, −8.4, 35.1 | none (identity) |
| C (peptide) | −3.2, −16.4, 29.3 | −3.2, −16.4, 29.3 | none (identity) |
| D (TCR) | 41.4, −2.9, 3.0 | **−31.4**, −2.9, 3.0 | **−72.8 Å in x** |
| E (TCR) | 34.7, −19.4, 9.2 | **−38.1**, −19.4, 9.2 | **−72.8 Å in x** |

`_cell.length_a = 72.787 Å`, space group `P 1 21 1`. The shift is exactly one unit cell along **a**.
In the deposited asymmetric unit the TCR is **not** docked on its pMHC — it is docked on the
symmetry mate. Superposing the AU as-is gives a nonsense complex.

**Two further traps in the same file:**

1. The assembly file **renames** the moved chains: `D` → `D-2`, `E` → `E-2`. Any code that
   looks up chain `D` in `6ULN-assembly1.cif` finds nothing.
2. Chain letters are **not** consistent across PDB entries. In `6MT3` the peptide is chain **B**
   and B2M is chain **C**; in `3GSO` and `3MRE` the peptide is chain **P**; in most others it is
   chain `C`. **Never** select the peptide by chain letter — select by polymer entity length
   (≤ 20 residues) or by `pdbx_description`.

**Recommendation:** never reconstruct operators yourself. Download the pre-assembled file

```
https://files.rcsb.org/download/<PDBID>-assembly1.cif      # operators already applied
```

(verified: `6ULN-assembly1.cif` 1,599,359 B; `3GSO-assembly1.cif` 416,233 B). Then select chains
by entity, not by letter. For the 413 clean entries this is identical to the AU file, so the same
code path works everywhere.

### 3.3 The recommended benchmark — date-split, because Boltz-2 memorises

⚠️ **Read this before picking structures.** Ascunce-París et al. 2026 (*Front Immunol* 17:1869810,
PMID 42568581) applied Boltz-2's training cutoff of **2023-06-01** uniformly and measured
**mean TCR-iRMSD 0.92 Å on pre-cutoff structures vs 4.59 Å on post-cutoff ones; DockQ 0.88 → 0.43.**
Chai-1 went 2.61 → 4.98 Å, AF3 2.75 → 3.59 Å. **A pMHC benchmark built from pre-2023 crystals
measures memorisation, not prediction.**

Your current two anchors are both pre-cutoff: `6ULN` (2020-05-27) and `3GSO` (2009-08-04). So is
every structure I would otherwise have recommended on resolution grounds alone — **23 of the 25
best-resolution entries predate the cutoff.**

**Measured: 70 of the 582 clean entries were released after 2023-06-01.** That is the pool your
headline numbers must come from.

### Table A — primary held-out set (all released after 2023-06-01)

All X-ray, 3 polymer entities (heavy + B2M + peptide), no TCR, assembly 1 identity operator only,
canonical residues only. Verified against the RCSB Data API on 2026-09-24.

| # | PDB | Released | Allele | Peptide | Len | Res (Å) | pep/hc/B2M | ASU | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `9SKO` | 2025-09-17 | A\*02:01 | LLWNGPMAVS | 10 | 1.49 | C/A/B | 1 | |
| 2 | `9X7U` | 2026-09-23 | A\*02:01 | AMDLGIHKV | 9 | 1.59 | C,F/A,D/B,E | 2 | UTP20 **mutant** ← pair |
| 3 | `9XME` | 2026-09-23 | A\*02:01 | AMDLGIDKV | 9 | 2.04 | C,F/A,D/B,E | 2 | UTP20 **wild-type** ← pair |
| 4 | `8FU4` | 2024-03-27 | A\*02:01 | TLFDEPPPL | 9 | 1.60 | C/A/B | 1 | HCMV US11 |
| 5 | `9WK0` | 2026-06-17 | A\*02:01 | FSGEYIPTV | 9 | 1.80 | C/A/B | 1 | **Rac1 P29S neoantigen** |
| 6 | `21GJ` | 2026-09-09 | A\*02:01 | VVPDEPPEV | 9 | 1.83 | C/A/B | 1 | **p53 Y220D neoantigen** ← pair |
| 7 | `21EX` | 2026-09-09 | A\*02:01 | VVPYEPPEV | 9 | 2.02 | C/A/B | 1 | **p53 wild-type** ← pair |
| 8 | `8TBW` | 2024-01-10 | A\*02:01 | KLSHQPVLL | 9 | 2.08 | C,F/A,D/B,E | 2 | SNX24 WT ← pair |
| 9 | `8VJZ` | 2024-12-11 | A\*03:01 | VVVGAGGVGK | 10 | 1.90 | C/A/B | 1 | **KRAS wild-type** |
| 10 | `8RNI` | 2025-01-22 | A\*03:01 | VVVGAVGVGK | 10 | 2.49 | C/A/B | 1 | **KRAS G12V** ← pair with 9 |
| 11 | `9WTJ` | 2026-09-23 | A\*11:01 | VVGAVGVGK | 9 | 1.65 | C/A/B | 1 | **KRAS G12V** |
| 12 | `9UV8` | 2025-12-24 | A\*11:01 | VVGADGVGK | 9 | 1.79 | C/A/B | 1 | **KRAS G12D** |
| 13 | `8I5E` | 2023-08-23 | A\*11:01 | VVGAGGVGK | 9 | 2.20 | **P/H/L** | 1 | **KRAS WT** ← pair with 11, 12 |
| 14 | `8SBK` | 2023-12-06 | A\*24:02 | LYLPVRVLI | 9 | 1.80 | C/A/B | 1 | ATG2A |
| 15 | `8YZR` | 2025-01-29 | A\*24:02 | NYNYLYRLL | 9 | 1.80 | C/A/B | 1 | |
| 16 | `8V8Q` | 2025-03-19 | B\*07:02 | SPRWYFYYT | 9 | 1.85 | C/A/B | 1 | MERS-CoV N |
| 17 | `9EK4` | 2026-06-24 | B\*07:02 | MPILTIITL | 9 | 2.05 | C,F/A,D/B,E | 2 | **TP53 mutant peptide** |
| 18 | `7YG3` | 2023-07-26 | B\*13:01 | RQDILDLWI | 9 | 1.50 | **B/A/C** | 1 | |
| 19 | `8ROP` | 2024-05-08 | B\*18:01 | QEIRTFSF | 8 | **1.15** | C/A/B | 1 | 8-mer, highest res |
| 20 | `8ROO` | 2024-05-08 | B\*18:01 | YERMCNIL | 8 | 1.40 | **B/A/C** | 1 | 8-mer |
| 21 | `8EMI` | 2024-03-27 | B\*35:01 | LPFDKATIM | 9 | 1.57 | C/A/B | 1 | |
| 22 | `8F7M` | 2024-06-05 | B\*57:01 | TSNLQEQIGW | 10 | 1.88 | C/A/B | 1 | |
| 23 | `9L48` | 2025-03-19 | C\*12:02 | RAFPGLRYV | 9 | 1.90 | C/A/B | 1 | HLA-C |
| 24 | `9K2U` | 2025-09-17 | C\*12:02 | ILKEPVHGAYY | 11 | 2.10 | C/A/B | 1 | 11-mer |

**10 alleles, lengths 8–11, four matched wild-type/mutant pairs, four cancer neoantigens.**

Optional 25th: **`8U9G`** (2024-01-10, A\*02:01, `KLSHQLVLL`, **2.87 Å** — above the 2.5 Å cut, so
flag it) is the SNX24 **neoantigen** whose wild-type is `8TBW` (#8). It is worth including anyway
because TFold published comparator numbers on exactly this target: peptide Cα-RMSD **0.6 Å**
(TFold) vs **1.0 Å** (PANDORA), the latter failing specifically on the bulge at P5/P6.

### Table B — legacy set (pre-cutoff; use only for cross-checks and allele coverage)

Report these separately and never mix them into a headline accuracy figure. Their value is
(a) alleles Table A lacks, above all **C\*08:02**, and (b) a crystallographic noise floor.

| PDB | Allele | Peptide | Len | Res (Å) | Released | Note |
|---|---|---|---|---|---|---|
| `6ULK` | **C\*08:02** | GADGVGKSAL | 10 | 1.90 | 2020-05-27 | **KRAS G12D — the TCR-free twin of `6ULN`** |
| `6ULI` | **C\*08:02** | GADGVGKSA | 9 | 1.88 | 2020-05-27 | KRAS G12D 9-mer |
| `6JTN` | **C\*08:02** | GADGVGKSAL | 10 | 1.90 | 2020-04-15 | independent determination of `6ULK` |
| `6JTP` | **C\*08:02** | GADGVGKSA | 9 | 1.90 | 2020-04-15 | independent determination of `6ULI` |
| `7OW4` | A\*11:01 | VVVGADGVGK | 10 | 1.81 | 2022-07-20 | KRAS G12D, 4 copies in ASU |
| `7OW3` | A\*11:01 | VVVGAGGVGK | 10 | 2.46 | 2022-07-20 | KRAS WT, matched to `7OW4` |
| `3MRE` | A\*02:01 | GLCTLVAML | 9 | **1.10** | 2011-05-25 | EBV BMLF1 |
| `1I4F` | A\*02:01 | GVYDGREHTV | 10 | 1.40 | 2001-07-25 | MAGE-A4 tumour antigen |
| `3GSO` | A\*02:01 | NLVPMVATV | 9 | 1.60 | 2009-08-04 | your existing anchor |
| `6JOZ` | A\*11:01 | ATIGTAMYK | 9 | 1.35 | 2020-01-29 | EBV BRLF1 |
| `5IB2` | B\*27:05 | RRKWRRWHL | 9 | 1.44 | 2017-02-01 | pVIPR |
| `6AT5` | B\*07:02 | APRGPHGGAASGL | 13 | 1.50 | 2018-02-28 | NY-ESO-1, 13-mer |
| `5TXS` | B\*15:01 | AQDIYRASY | 9 | 1.70 | 2017-11-29 | ALK neuroblastoma antigen |
| `6PBH` | A\*68:01 | DATYQRTRALVR | 12 | 1.89 | 2019-12-11 | 12-mer, bulged |
| `1ZHK` | B\*35:01 | LPEPLPQGQLTAY | 13 | 1.60 | 2005-05-17 | 13-mer |
| `4NT6` | C\*08:01 | GILGFVFTL | 9 | 1.84 | 2014-07-23 | flu M1 on HLA-C |

**`6ULK` replaces `6ULN` outright** — same pMHC (HLA-C\*08:02 + KRAS-G12D `GADGVGKSAL`), 1.90 Å,
three entities, no TCR, identity operator. You validated against the hard version of a structure
that exists in easy form.

**There is no post-cutoff C\*08:02 pMHC structure**, so any C\*08:02 number you report is
necessarily contaminated. Say so rather than quietly averaging it in.

**The crystallographic noise floor is measurable from this set.** `6ULI`/`6JTP` are independent
determinations of the same pMHC, as are `6ULK`/`6JTN`. The RMSD between each crystal pair is the
experimental reproducibility limit — report your predictions against that, not against 0.0 Å.
Published context: TFold measured median Cα-pRMSD **0.38 Å between two unbound structures of the
same pMHC** and 0.57 Å unbound-vs-TCR-bound. **Sub-0.5 Å is at the noise floor, not a win.**

### Matched wild-type/mutant pairs — the structural analogue of DAI

Six pairs across the two tables let you ask whether the structure layer resolves a single-residue
substitution at all:

| Wild-type | Mutant | Allele | Substitution | Both post-cutoff? |
|---|---|---|---|---|
| `9XME` AMDLGIDKV | `9X7U` AMDLGIHKV | A\*02:01 | D→H | ✅ |
| `21EX` VVPYEPPEV | `21GJ` VVPDEPPEV | A\*02:01 | p53 Y220D | ✅ |
| `8TBW` KLSHQPVLL | `8U9G` KLSHQLVLL | A\*02:01 | SNX24 P→L | ✅ (mutant 2.87 Å) |
| `8VJZ` VVVGAGGVGK | `8RNI` VVVGAVGVGK | A\*03:01 | KRAS G12V | ✅ |
| `8I5E` VVGAGGVGK | `9WTJ` / `9UV8` | A\*11:01 | KRAS G12V / G12D | ✅ |
| `7OW3` VVVGAGGVGK | `7OW4` VVVGADGVGK | A\*11:01 | KRAS G12D | ❌ pre-cutoff |

This is the highest-value part of the structure benchmark for this pipeline specifically. If
Boltz-2 returns near-identical structures for `21EX` and `21GJ`, the structure layer is adding
nothing the sequence layer did not already have — the structural counterpart of the §0 finding.

### 3.4 The RCSB Search API payload

`POST https://search.rcsb.org/rcsbsearch/v2/query`, `Content-Type: application/json`.
**Verified live: returns `total_count = 622`.**

```json
{
  "query": {
    "type": "group",
    "logical_operator": "and",
    "nodes": [
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "rcsb_polymer_entity_annotation.annotation_id",
                      "operator": "exact_match", "value": "IPR001039"}},
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "rcsb_entity_source_organism.taxonomy_lineage.id",
                      "operator": "exact_match", "value": "9606"}},
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "rcsb_entry_info.resolution_combined",
                      "operator": "less", "value": 2.5}},
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "rcsb_entry_info.polymer_entity_count",
                      "operator": "equals", "value": 3}},
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "exptl.method",
                      "operator": "exact_match", "value": "X-RAY DIFFRACTION"}},
      {"type": "terminal", "service": "text",
       "parameters": {"attribute": "entity_poly.rcsb_sample_sequence_length",
                      "operator": "range",
                      "value": {"from": 8, "to": 15,
                                "include_lower": true, "include_upper": true}}}
    ]
  },
  "return_type": "entry",
  "request_options": {
    "results_content_type": ["experimental"],
    "sort": [{"sort_by": "rcsb_entry_info.resolution_combined", "direction": "asc"}],
    "paginate": {"start": 0, "rows": 200}
  }
}
```

**Four things that will bite you if you change this payload:**

1. **Use InterPro `IPR001039` ("MHC class I alpha chain, alpha1 alpha2 domains"), not Pfam
   `PF00129`.** Verified: `PF00129` → 474 hits, `IPR001039` → 622. RCSB only attaches Pfam
   annotations to entities mapped to **reviewed** (Swiss-Prot) UniProt accessions. Several HLA
   heavy chains map to unreviewed TrEMBL accessions (`A0A583ZB34` for `7OW3`/`7OW4`,
   `C1K0Y1` for `6ULI`/`6ULK`/`6JTP`/`6JTN`) and carry **InterPro but no Pfam**. Filtering on
   Pfam silently drops most of the KRAS neoantigen structures — exactly the ones you care about.
2. **The taxonomy filter is entry-level, not entity-level, and does not exclude mouse.** Murine
   H-2 crystals routinely use **human** β2-microglobulin, so `taxonomy_lineage.id = 9606` matches
   them. Verified: 19 mouse H-2 and 2 rabbit entries survive the search. They must be removed by
   checking the **heavy chain entity's** own organism afterwards.
3. **`IPR001039` also matches non-classical loci** — HLA-E, HLA-G, HLA-F, MICA/B, MR1, CD1, HFE.
   Verified: 7 human non-classical entries (HLA-E\*01:03, HLA-G) survive. Post-filter on the heavy
   chain description.
4. **`polymer_entity_count = 3` is what excludes TCRs.** Change it to `5` for the TCR-bound set
   (verified: **65** entries, e.g. `1OGA`, `2BNQ`, `5TEZ`, `7QPJ`, `3VXS`). `entity_poly.
   rcsb_sample_sequence_length` in the 8–15 range is an entry-level "some entity matches"
   filter, so it does not on its own guarantee the short entity is the peptide.

### 3.5 Pulling peptide sequences from the results

Do **not** use the per-entry REST endpoint in a loop (487+ round trips). Use the GraphQL Data
API at `https://data.rcsb.org/graphql`, 50 entry IDs per call:

```graphql
query($ids:[String!]!){
  entries(entry_ids:$ids){
    rcsb_id
    struct{title}
    rcsb_entry_info{resolution_combined deposited_polymer_entity_instance_count}
    polymer_entities{
      entity_poly{
        pdbx_seq_one_letter_code          # shows modified residues as (XXX)
        pdbx_seq_one_letter_code_can      # canonical one-letter, modified residues collapsed
        rcsb_sample_sequence_length}
      rcsb_polymer_entity{pdbx_description}
      rcsb_polymer_entity_container_identifiers{auth_asym_ids}
      rcsb_entity_source_organism{ncbi_scientific_name}}
    assemblies{
      rcsb_id
      pdbx_struct_assembly_gen{oper_expression asym_id_list}
      pdbx_struct_oper_list{id type name}}}}
```

**Parsing notes:**

- **`pdbx_seq_one_letter_code_can` will lie to you about modified residues.** `9ASF` returns
  `AHHGGWTTK` canonically, but the raw `pdbx_seq_one_letter_code` shows a benzothienyl-alanine
  analogue at position 6 (the title says "Trp-6 Bta"). Always read the **raw** field and reject
  any peptide containing `(`. Verified: 45 of 620 entries fail this test. Other examples:
  `6BXP` (kynurenine), `7S7D` (sulfo-peptide), `5IEH` (phospho-peptide), `6PYW`/`3DTX`
  (these two additionally carry **engineered MHC point mutants** — W60A and a double
  citrullination — so also screen titles for `mutant`, `W60A`, `E152V`, `T73C`, `P47G`).
- **Classify entities by length and description, never by chain letter** (see `6MT3` above).
  Rule that works on all 620: length ≤ 20 → peptide; `"microglobulin"` in description → B2M;
  otherwise → heavy chain.
- **`deposited_polymer_entity_instance_count > 3` means multiple copies in the ASU** (159/620).
  Take the chains listed in a single `pdbx_struct_assembly_gen.asym_id_list`, or just take the
  first instance of each entity. `7OW3`/`7OW4` have 4 copies; `4NQX` has 6.
- **Allele assignment is the weak link.** Only 301 of 582 titles name a 4-digit allele; RCSB does
  not carry an allele field. For the rest, match the heavy chain sequence against IMGT/HLA
  (`https://raw.githubusercontent.com/ANHIG/IMGTHLA/Latest/fasta/A_prot.fasta`, `B_prot.fasta`,
  `C_prot.fasta`) on the α1/α2 region. For the 22 curated structures above I have already read
  the allele out of the title or the entity description, so you do not need this to get started.

---

## 4. TASK 3 — what to report

### 4.1 Screening layer: the metrics the field actually uses

| Metric | Used by | Definition as published |
|---|---|---|
| **AUPRC / PR-AUC** | TESLA, Buckley 2022, BigMHC, PRIME | TESLA: "the ability of a team to rank immunogenic pMHC ahead of the peptides for which T cell responses were not identified" (R `PRROC::pr.curve`) |
| **PPVn** | MHCflurry, NetMHCpan-4.1, BigMHC | BigMHC: "the pMHCs are first sorted by a predictor's output. Then, PPVn is the fraction of the top n pMHCs that are actually immunogenic" |
| **TTIF** (top-20 immunogenic fraction) | TESLA | ratio of top-20 ranked pMHC with detected immunogenicity to all top-20 tested; 20 chosen because "therapeutic vaccine platforms reported to date have included ~20 neoepitopes" |
| **FR** (fraction ranked) | TESLA | fraction of a subject's immunogenic peptides that appear in that team's top 100 |
| **FRANK** | NetMHCpan-4.1, NetMHCIIpan | "the proportion of peptides with a prediction score higher than that of the epitope". 0 = perfect, 0.5 = random |
| **AUC0.1** | IMPROVE, ICERFIRE | partial AUC at 10 % FPR, "to focus on the high specificity part of the ROC curve" |
| **ISSR** | PredIG 2025 | immunogenic pHLAs found among top-X, X ∈ {10,25,50,100,200,400,1000} — the "number needed to test" framing |

⚠️ **FRANK's denominator is all overlapping peptides of the source protein**, not a patient's
candidate list. If you repurpose it, say what your denominator is or the number is not comparable.
Reference medians (NetMHCpan-4.1 CD8 benchmark): NetMHCpan-4.1 **0.00220**, MixMHCpred 0.00264,
MHCflurry 0.00383.

**Why AUROC misleads here — with a measured demonstration.** Buckley et al. 2022
(*Brief Bioinform* 23(3):bbac141, PMID 35471658) ran the same models on three datasets:

| Dataset | Positive rate | PR-AUC range |
|---|---|---|
| SARS-CoV-2 peptides | ~63 % | 0.621 – 0.694 |
| GBM neoantigens (n = 123) | 20 % | 0.20 – 0.437 |
| TESLA subset | **~6 %** | **0.051 – 0.211** |

Same models, performance collapsing purely with prevalence — and AUROC would have looked roughly
flat across all three. Their words: "ROC-AUC can be misleading as this metric can underrepresent
the minority class. Thus, we diagnosed model performance… using PR-AUC."

**Three citable ways pooling inflates results:**

1. **Intra-HLA label imbalance.** Zhang et al. 2026, *Cell Genomics*, PMID 41985452: across four
   immunogenicity datasets, over half the alleles show >10-fold positive:negative ratio
   differences, and **an HLA-only model using no peptide information beat all 15 previously
   evaluated models by 3.18–15.95 % AUROC.**
2. **Study/batch effects.** PRIME (Schmidt et al. 2021, PMID 33665637): "Standard cross-validation
   results can be artificially boosted by batch effects because different peptides from the same
   study are found in both the training and testing sets." Their fix: leave-one-study-out and
   leave-one-allele-out.
3. **Dataset-specific overfitting.** ICERFIRE (Wan et al. 2024, PMID 38288446): the CEDAR-optimal
   model drops 0.742 → 0.655 AUC on PRIME data; AXEL-F drops to **0.466 and 0.415 — worse than
   random** on data it did not train on.

**Honest value ranges.** Presentation and immunogenicity are different difficulty regimes:

| Task | Benchmark | AUROC | AUPRC | PPVn |
|---|---|---|---|---|
| **Presentation** (eluted ligand) | BigMHC, 45,409 ligands / 900,592 decoys | **0.9733** | 0.8779 | 0.8617 |
| Presentation, stratified by MHC **and** length | same | 0.9290 | 0.6132 | — |
| **Immunogenicity** | BigMHC neoepitope set, 198 pos / 739 neg (21 %) | **0.5736** | 0.3234 | 0.4375 (random 0.2113) |
| Immunogenicity | ITSNdb, 129/70 (Nibeyro 2023, PMID 37564650) | **0.52 – 0.60** across all 16 predictors | — | — |
| Immunogenicity | IMPROVE, >17,000 candidates, ~2.7 % positive | **0.630** (best) | AUC0.1 **0.0139** | — |
| Immunogenicity | ICERFIRE, CEDAR/PRIME/NEPDB | 0.60 – 0.75 in-domain, 0.604–0.655 out | — | — |
| Mutation-level (not peptide-level) | Gartner 2021, PMID 34927080 | **0.911** | — | 24/46 positives in top 10 |

**Expect AUROC ~0.55–0.75 for immunogenicity, not 0.9.** Gartner's 0.911 is higher because the
unit of evaluation changed from peptide to mutation and ranking is per-patient — a legitimate
choice, but not comparable to peptide-level numbers.

⚠️ **A provenance warning about BigMHC.** I parsed `data/val/imval_results.csv` and
`elval_results.csv` from `github.com/KarchinLab/bigmhc` and got immunogenicity AUROC median
**0.764** (max 0.788), AUPRC 0.539, PPVn 0.509; presentation AUROC median **0.990**. These are
**hyperparameter-sweep results over 3,500 / 350 model-selection configurations**, not the
published held-out test-set benchmark, which is the 0.5736 / 0.9733 row above. Both are real and
they measure different things. **Do not mix them in one table** — cite the published test-set
figures for comparison against other tools, and treat the repo sweep as internal validation only.

⚠️ **The widely-repeated claim that TESLA reported "PPV ~7 % improved to 50 % by ensembling" is
not in the TESLA paper.** Use the verified ladder below.

**TESLA's actual precision ladder** (Figure 4H; "optimal" = max of precision + recall):

| Ranking strategy | Optimal precision | Recall |
|---|---|---|
| MHC binding affinity alone | **< 20 %** | — |
| Presented, then affinity | **~50 %** | 55 % |
| Presented + recognized, then affinity | **> 70 %** | 45 % |

Thresholds: presentation = **affinity < 34 nM, tumour abundance > 33 TPM, stability > 1.4 h**
(93 % of non-immunogenic removed, 55 % of immunogenic kept, p = 3.7×10⁻⁸); recognition =
**agretopicity < 0.1 OR foreignness > 10⁻¹⁶** (OR 14.3, p = 0.003). Combined: 98 % removed,
45 % preserved, **OR 51.7**, p = 6×10⁻¹⁰. Independent cohort (310 pMHC, 4 immunogenic): recall
75 %, 99 % removed, **OR 348**.

⚠️ **Two corrections.** (a) **Hydrophobicity is not in the final filter set** — TESLA state
plainly "Neither peptide hydrophobicity nor mutational position was found to be important for
optimal filtering." (b) The >70 % precision is **in-sample and threshold-optimised** on the same
608 peptides (286-row complete-case subset), so it is an **upper bound, not a held-out PPV**.

**Report these six numbers**, with bootstrap CIs **resampling patients, not peptides** (peptides
within a patient share HLA, tumour and expression, so they are not independent). Precedents:
BigMHC 1,000-fold bootstrap; ICERFIRE 10,000 rounds. For paired model comparison use DeLong
(`pROC::roc.test`) or a paired Wilcoxon across patients.

1. **Prevalence** — n, n positive, positive rate, per patient and pooled.
2. **AUPRC with the random baseline (= prevalence) printed beside it.** Report AUROC too, but
   never alone and never as the headline.
3. **PPV at top-20 and top-50 per patient**, plus **enrichment = PPV@N / prevalence**.
4. **Recall at the same N.** §0 shows exactly why: a filter can buy precision by discarding
   three-quarters of the true positives.
5. **Number needed to test = 1 / PPV@N**, against the random comparator (1/0.06 ≈ 16 at TESLA's
   prevalence). This is the number a wet-lab collaborator acts on.
6. **AUC0.1** as the imbalance-aware discrimination summary.

Also report **the count of patients with ≥1 immunogenic peptide in the top N** (Gartner: "23 of 26
samples had at least one positive nmer ranked in the top 25") — clinically the most interpretable
single number for a vaccine pipeline. Split **per-patient as primary**, pooled as secondary and
explicitly labelled.

### 4.2 Evaluating DAI specifically

**First, publish your formula — the literature does not agree on one:**

| Source | DAI |
|---|---|
| Duan 2014 (PMID 25245761) | **difference** in NetMHC scores, mutant vs WT |
| Rech 2018 (PMID 29339376) | **ratio** of MHC binding affinity, mutant vs normal ("fold change") |
| TESLA 2020 | **ratio** mutant : WT affinity (their *agretopicity*, inverse of this repo's DAI) |
| Nibeyro 2023 | evaluates both: `DAI_BA = WT_BA − mut_BA`; `DAI_R = mut_Rank / WT_Rank` |
| ICERFIRE 2024 | rank ratio, scaled by the absolute difference |

"DAI ≥ 10" is meaningless without saying which of these it is. This repo uses
`affinity_WT / affinity_MT`, higher = mutant binds better.

**Published standalone performance is poor, and consistent with §0:**

- **Nibeyro 2023** (ITSNdb): ratio-DAI AUC **0.59** at anchor positions, **0.56** at non-anchor.
  "**no significant difference was found between immunogenic and non-immunogenic TSNs according to
  DAI values (P = 0.25)**."
- **ICERFIRE 2024**: standalone AUC **0.539** (affinity-ratio) and **0.589** (rank-based). Their
  agretopicity feature is **not used at all** in the final consensus model.
- **IMPROVE 2024**: self-similarity shows "no significant difference… (p = 0.24)"; mutation
  position *was* significant (p = 0.01).

**Evidence for is real but is a different claim.** Ghorani 2018 (PMID 29361136) found mean DAI
correlated with survival in 3/5 cohorts — a **sample-level mean**, not a per-peptide classifier.
Rech 2018 likewise reports **cohort-level ADN load**, and notes median DAI of classical
neopeptides was only **1.183**. TESLA's OR 14.3 holds **only conditional on the presentation
filters**, which the authors state explicitly. **Do not cite cohort-level survival associations as
evidence that a per-peptide DAI gate works.**

**Protocol:**

1. **Stratify by anchor vs non-anchor** and report separate AUCs. At anchors DAI partly restates
   mutant affinity; at non-anchors it is ≈1 by construction, so the pooled number is a mixture of
   two different populations. Bjerregaard ships `Anchor`; CII 2025 ships `anchors` /
   `anchors_secondary`; `research-filters.md` already measures a 75 % vs 3 % pass-rate split.
2. **Evaluate DAI conditional on presentation**, i.e. within the set that already passes your
   MHCflurry filters. That is TESLA's design and the only setting where DAI showed a large effect.
3. **Report incremental value, not standalone.** Fit rank-only vs rank + DAI; report ΔAUPRC and
   ΔPPV@20 with bootstrap CIs and a DeLong test. §0 measures this as **+0.0 precision points for
   −30 recall points**.
4. **Test both formulations** (difference and ratio, affinity and %Rank) — ICERFIRE found
   rank-based beat affinity-based (0.589 vs 0.539).
5. Sweep the threshold and report the whole curve. A filter whose enrichment is non-monotonic in
   its own threshold is measuring noise.

### 4.3 Structure layer

**The superposition convention is settled, and it is the one you guessed.** Superpose on the
**MHC α1/α2 G-domain Cα atoms only**, then compute peptide RMSD in that frame with **no
re-superposition on the peptide**.

- **PANDORA** (Marzella et al. 2022, PMID 35619705): "the **G-domains (positions 1-180)** of models
  and target structures were superposed and the L-RMSD was calculated as the RMSD between the atoms
  of the experimentally determined peptide conformation and the modelled peptide." Backbone =
  Cα, N, C, O. Computed with ProFit.
- **Keller, Weiss & Baker 2022** (PMID 35547730): "superimposed on the heavy chain… via the
  **Cα atoms of residues 1-180**. The RMSD… was then calculated between peptide residues only."
- **SwiftMHC** (Baakman et al. 2026, PMID 41923631) is the most robust variant and what I would
  copy: superpose on **IMGT 3–179**, omitting the two most N-terminal residues (absent in some
  structures) and the C-terminal residue (orientation varies across X-ray structures).
- **TFold** (Mikhaylov et al. 2024, PMID 38113889): "superimposing a model onto a true structure
  **by MHC chains only**, and then computing the error for the peptide"; G-domains truncated.

Also consistent: DockTope ("always fitted by MHC-I residues"), PMGen, HLA3DB, APE-Gen2.0.
The "no re-superposition" step is corroborated by DockQ's own source, which computes LRMS with
"the private `_rms` function which does not superimpose".

⚠️ **Do not cite Motmaen et al. 2023 (PNAS, PMID 36802421) for this convention** — neither the main
text nor the SI states which atoms or residues are superposed.

**Recommendation: fit on heavy-chain Cα IMGT 3–179; report peptide backbone (N/CA/C/O) RMSD in
that frame, with Cα-only and all-atom alongside.**

**What counts as correct.** Use APE-Gen2.0's pMHC-tuned ladder rather than CAPRI, for the reason
its authors give — "pMHC modeling tools have long succeeded in producing near-native (≤2 Å)
conformations of most pMHC complexes", so CAPRI's bins do not discriminate:

| Band | Peptide L-RMSD |
|---|---|
| High | ≤ 1.0 Å |
| Medium | ≤ 1.5 Å |
| Acceptable | ≤ 2.0 Å |
| Incorrect | > 2.0 Å |

**But anchor your "good" at the noise floor, not at zero: 0.38–0.57 Å** (TFold, crystal-vs-crystal
for the same pMHC). Your own `6ULI`/`6JTP` and `6ULK`/`6JTN` pairs let you measure this directly.

**Published class I values, for calibration:**

| Method | Metric | Value |
|---|---|---|
| TFold (AF2-based) | median Cα-pRMSD, discovery / test | **0.73 / 0.77 Å** |
| TFold by length | median Cα-pRMSD | **0.46 Å (8-mers) → 2.14 Å (>11-mers)** |
| TFold, 16 "difficult pairs" (1–3 substitutions) | median Cα-pRMSD | **1.37 Å** |
| PANDORA (re-benchmarked by TFold, date-matched templates) | median Cα-pRMSD | 1.48 Å |
| Motmaen AF2 pipeline | median peptide RMSD | 0.8 Å backbone / 1.8 Å all-atom |
| MHC-Fine | median Cα | **0.65 Å** |
| PMGen (n = 176) | median Cα-pRMSD | **0.65 Å**; full-atom 1.39 Å |
| APE-Gen2.0 | best-scored median Cα / backbone / all-atom | 0.791 / 0.871 / 1.676 Å |
| RosettaMHC | backbone heavy-atom | 75 % within 1.5 Å, 98 % within 2 Å |

Note the length dependence: **8-mers 0.46 Å → >11-mers 2.14 Å.** Report per-length, because a
9-mer-heavy benchmark flatters any method.

⚠️ **There is no published peptide-RMSD benchmark for AF3, Boltz-1, Boltz-2 or Chai-1 on
peptide–MHC class I alone (no TCR).** Every AF3/Boltz-era pMHC number in the literature is embedded
in TCR–pMHC work. PMGen states why: "AlphaFold3's recent training cutoff complicates unbiased
benchmarking." **A properly date-split Boltz-2 peptide-RMSD benchmark on class I pMHC does not
currently exist — which is exactly what §3.3's Table A would produce, and is publishable.**

The closest indirect evidence, and it is encouraging for the pMHC sub-problem: *Brief Bioinform*
2026 (PMID 42248582) found for the pMHC sub-complex "median and mean DockQ scores both above
0.8… **the main bottleneck in TCR–pMHC structure prediction lies not in modeling peptide
positioning within the MHC groove, but in resolving the geometric complexity of TCR docking
orientation.**" Boltz-1 "showed the most similar performance to AlphaFold3."

**Report the central bulge separately — there is direct precedent.** TFold: "it is easy to position
the primary anchor residues in the corresponding MHC pockets, and **the challenge lies in modeling
the peptide middle**… **These middle residues are the most important for TCR recognition**… even
for 9-mer peptides, inaccurate models can substantially misrepresent the molecular features seen by
a TCR." HLA3DB (*Nat Commun* 2023;14:6179) computes exactly "the backbone heavy atom RMSD of
**P4 to P7**", reports per-position deviations, and achieves sub-Å middle-peptide RMSD for **92 %**
of A\*02:01 targets.

⚠️ **HLA3DB also shows Cartesian RMSD hides real differences**: "a large dihedral angle difference
at P5 can cause a substantial backbone deviation at P6 and P7… Nonetheless, the resulting RMSD is
less than 1 Å." They introduce **D-score** over central φ/ψ; only **63 %** of the targets that pass
sub-Å RMSD also pass D-score < 1.5. If bulge geometry matters to you — and for TCR recognition it
does — report a dihedral-space metric alongside RMSD.

⚠️ **Publish a naive baseline.** HLA3DB: "nearly half of the A02 targets are neighbors to a discrete
backbone (PDB ID 6J1V). Hence, **a naive method could achieve 50 % accuracy by simply adopting this
backbone conformation for all targets.**" Report your accuracy off the most common backbone too.

**DockQ / CAPRI — thresholds confirmed, but do not gate on them.** Basu & Wallner 2016
(PMID 27560519) fit **C1 = 0.23, C2 = 0.49, C3 = 0.80** (incorrect / acceptable / medium / high),
confirmed verbatim in DockQ v2's source. **But those cutoffs were fit on 56,015 globular
protein–protein models with no peptide targets**, so applying them to a 9-mer in a groove is
extrapolation. DockQ v1 refuses outright:

```python
def capri_class_DockQ(DockQ, capri_peptide=False):
    if capri_peptide:
        return 'Undef for capri_peptides'
```

and its argparse help reads `--capri_peptide … (DockQ cannot not be trusted for this setting)`.
`--capri_peptide` changes contact thresholds (fnat 5.0 → 4.0 Å, interface 10 Å all-heavy → 8 Å
Cβ–Cβ) and the **CAPRI class** bands from Marcu et al. 2017 (PMID 28002624) — not the DockQ formula
and not 0.23/0.49/0.80. ⚠️ Marcu's Table 1 gives L-RMSD ≤ **4.0 Å** for "Acceptable" while DockQ
v1's code uses **5.0** — cite the paper.

**None of PANDORA, APE-Gen, APE-Gen2.0, DockTope, TFold, MHC-Fine, PMGen, SwiftMHC or HLA3DB
report DockQ.** All report peptide L-RMSD. Where DockQ *is* reported for the peptide–MHC interface
it saturates above 0.8 and gives no discrimination. **Use peptide L-RMSD as primary; DockQ
`--capri_peptide` and fnat@4 Å as secondary diagnostics only.** fnat is still worth having — it is
superposition-free and catches anchor-pocket contact loss that a 1.2 Å L-RMSD can mask.

**Confidence as self-assessment — moderate, and it fails where you need it.**

| Score | Target | Statistic |
|---|---|---|
| AF2 predicted error (100−pLDDT) | Cα-pRMSD class I | Spearman **ρ = 0.55** / 0.42; **0.70** on difficult pairs (TFold) |
| PANDORA molpdf | Cα-pRMSD | ρ = 0.07 |
| Rosetta ref2015 energy | peptide heavy-atom RMSD | **no correlation** (R² ≈ 0) |
| MHC-Fine predicted lDDT | actual lDDT | Pearson r = 0.62 |
| AF3 confidence suite | TCR-iRMSD / DockQ | ρ −0.61 to −0.84; best pDockQ2 0.84 |

⚠️ **TFold, on single-mutation pairs — precisely the neoantigen-vs-wild-type regime:** "it also
produces some fairly inaccurate models… and **the pLDDT score for them is not lower**." Aggregate
filtering still works (top half by score: 10 % poor vs 39.2 % in the bottom half), but do not trust
confidence on the WT/MT pairs, which is where you most want it.

⚠️ **Confidence is not binding affinity.** Motmaen 2023: "the discrimination between binders and
non-binders was considerably poorer than NetMHCpan, and AlphaFold tended to dock non-binding
peptides in the MHC-peptide-binding groove." Their fitted inter-PAE midpoint is **8.03 for class I
vs 4.34 for class II** — never port a confidence threshold across classes.

**Ensemble spread beats any single confidence score** (Ascunce-París 2026): median pairwise
model-vs-model distance correlates with truth at **ρ = 0.76 (TCR-iRMSD) / 0.79 (DockQ)**. Since you
already run Boltz-2 with `--diffusion_samples`, computing the spread across samples costs you
nothing and is likely your best confidence signal.

**UNVERIFIED:** no published Boltz-2 confidence calibration for pMHC class I exists.

---

## 5. Provenance and what I did not verify

Everything in §0, §2 and §3 was downloaded and parsed in this session. §4 is sourced from primary
literature (PMC full text, publisher PDFs, and package source code) rather than executed, with
these specific gaps:

- **No published peptide-RMSD benchmark exists for AF3 / Boltz-1 / Boltz-2 / Chai-1 on class I
  pMHC alone.** The §4.3 numbers are from AF2-era tools (TFold, PANDORA, MHC-Fine, PMGen,
  APE-Gen2.0). Treat them as the bar to clear, not as Boltz-2 expectations.
- **No Boltz-2 confidence calibration for pMHC class I** has been published.
- **Motmaen et al. 2023's superposition convention is undocumented** in both main text and SI —
  I cite PANDORA / Keller / SwiftMHC for the 1–180 convention instead.
- **Marcu 2017 (L-RMSD ≤ 4.0 Å) and DockQ v1's code (5.0 Å) disagree** on the CAPRI-peptide
  "Acceptable" threshold.
- **NeoRanking / HiTIDE** figshare matrices return an HTTP 202 bot challenge to curl — likely the
  largest harmonized benchmark available; needs a manual browser download.
- **Allele assignment for 235 of the 582** clean structures whose titles do not name a 4-digit
  allele — these need IMGT/HLA sequence matching. All 41 structures recommended in §3.3
  (24 in Table A, 16 in Table B, plus `8U9G`) have had their allele read off the title or the
  entity description individually, so you do not need this to get started.
- **dbPepNeo 2.0** per-tier counts (801 HC / 251 MC / 842,289 LC) — paper only, no obtainable file;
  and whether its email request form ever delivers anything.
- The 51 non-validated TSNAdb v2 zips (HEAD returns no `Content-Length`).
- The claim that TESLA reported "PPV ~7 % improved to 50 % by ensembling" — **checked and it is
  not in the paper.** Do not repeat it.

**Artifacts downloaded and parsed in this session.** `tcell_full_v3.zip` (IEDB, 43 MB),
`tcell_full_v3.zip` (CEDAR, 13.7 MB), `table_1.csv` (Bjerregaard), CII 2025 supplement zip
(10.7 MB, MOESM4 + MOESM7), BigMHC `imval_results.csv` / `elval_results.csv`, and 622 RCSB
entries (plus release dates for the date split) and `6ULN.cif` / `6ULN-assembly1.cif`. Licences: IEDB/CEDAR/Bjerregaard/CII 2025 are
CC BY; TESLA's table is downloadable but Elsevier-copyright, so fetch it rather than vendoring it;
NEPdb states no licence at all.
