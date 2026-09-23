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
    if seq[pos-1] != wt:                 # <-- the assertion that catches every mapping bug
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

if __name__ == "__main__":
    prot = read_fasta("uniprot_sprot_human_canonical.fasta")
    for acc, hgvsp, gene in [("P01116","p.Gly12Asp","KRAS"), ("P04637","p.Arg175His","TP53")]:
        wt, pos, mut = parse_hgvsp(hgvsp)
        m = mutate(prot[acc], wt, pos, mut)
        peps = windows(m, pos)
        print(f"{gene} {hgvsp}: {len(peps)} peptides; 9mers={[p for p in peps if len(p)==9]}")
