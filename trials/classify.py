"""Assign each trial one RNA Therapeutics Monitor modality label.

The labels are the Monitor's own vocabulary, verbatim from its categories.yml,
so that "compiled following the Monitor's methodology" stays true. Nothing here
invents a category of its own for the published list; where the Monitor's
labels cannot hold a trial, `propose` suggests one for a human reviewer only.

Trial registrations are harder to classify than papers. A paper about siRNA
says "siRNA"; a trial of OLX10010 says "OLX10010". So a trial is identified
through three layers, strongest first:

  1. terms and drug names in its interventions
  2. the same patterns in its title
  3. the sponsor, for companies that make only one kind of RNA drug

Drug names are recovered two ways: WHO INN stems (-siran is always an siRNA,
-rsen always an antisense oligonucleotide) and sponsor code series (ALN-,
OGX-, ARCT-), which is how early-phase drugs named only by code are found.
"""
import re


def rx(*patterns):
    return re.compile("|".join(patterns), re.I)


# Order is precedence, most specific first. saRNA and circRNA are kinds of mRNA
# and must be tested before it; base editors are guide-RNA machinery, so they
# sit under CRISPR RNA rather than RNA editing, which means ADAR.
MODALITIES = [
    ("saRNA", rx(r"self.amplifying", r"\bsa-?rna\b", r"replicon rna",
                 r"\bARCT-1\d{2}", r"\bLUNAR-")),
    ("circRNA", rx(r"circular rna", r"\bcirc-?rna\b")),
    ("siRNA", rx(r"\bsi-?rna", r"small interfering", r"\brna interference", r"\bRNAi\b",
                 r"\bgalnac", r"\w+siran\b",
                 r"\bALN-[A-Z0-9]", r"\bOLX\d", r"\bBMT10\d", r"\bARO-[A-Z]",
                 r"\bSLN\d{3}", r"\bDCR-", r"\bSTP\d{3}", r"\bQPI-\d", r"\bTKM-",
                 r"\bND-L02", r"\bSRSD\d{3}", r"\bRBD\d{4}", r"\bVIR-25\d",
                 r"\bADX-\d", r"\bSYL\d?18", r"\bSYL\d{4}", r"\bNWRD\d", r"\bATR ?10\d{2}")),
    ("ASO", rx(r"antisense oligo", r"\baso\b", r"exon skipping", r"splice.switch", r"\bAOC \d",
               r"\w+rsen\b", r"\w+mersen\b", r"oblimersen",
               r"\bISIS[- ]?\d", r"\bIONIS[- ]", r"\bOGX-\d", r"\bWVE-", r"\bSRP-\d{3}",
               r"\bION-\d", r"\bQR-\d{3}", r"\bGTX-10\d", r"\bAEG351\d", r"\bNIO\d{3}",
               r"\bnL-[A-Z]", r"\bcustirsen\b", r"\bdanvatirsen\b", r"\bNS-06\d",
               r"\bAZD(?:5312|9150|8233|4785)\b", r"\bDYN\d{3}", r"\bSTK-\d",
               r"\bapatorsen\b", r"\bviltolarsen\b", r"\bBIIB\d{3}\b", r"\bAZD8701\b",
               r"\bVO\d{3}\b", r"\bAMX0\d{3}", r"\bOT-101\b", r"\btrabedersen\b",
               r"\bCMP-CPS-\d", r"\bIMT-\d{3}", r"\beplontersen\b", r"\bolezarsen\b")),
    ("aptamer", rx(r"aptamer", r"pegaptanib", r"macugen", r"lexaptepid", r"spiegelmer",
                   r"\bNOX-[A-Z]", r"\bE10030\b", r"\bARC190\d", r"avacincaptad")),
    # "miRNA" as a bare substring matches "Co-mirna-ty", Pfizer's COVID vaccine,
    # which is why it is bounded on both sides here.
    ("miRNA", rx(r"micro-?rna", r"\bmir-\d", r"(?<![a-z])mirna(?![a-z])", r"\bantagomir",
                 r"\bCDR132L\b", r"\bMRG-\d{3}", r"\bremlarsen\b", r"\bcobomarsen\b")),
    ("RNA editing", rx(r"\brna editing\b", r"\bADAR\b", r"adar.mediated", r"\bAIMer\b")),
    ("CRISPR RNA", rx(r"crispr", r"\bcas9\b", r"\bcas12\b", r"\bcas13\b", r"guide rna",
                      r"base edit", r"prime edit", r"\bABE\b",
                      r"\bCTX\d{3}", r"\bNTLA-\d", r"\bEDIT-\d", r"\bVERVE-\d", r"\bBEAM-\d",
                      r"\bCS-1?\d{2}\b", r"\bBRL-10\d", r"\bET-01\b")),
    ("RNA nanostructure", rx(r"rna nanotechnolog", r"rna origami", r"rna nanostructure",
                             r"rna nanoparticle assembl")),
    # Bounded by letters rather than \b: an underscore is a word character, so
    # \bmrna\b never matches "mRNA_Dose".
    ("mRNA", rx(r"(?<![a-z])m-?rna(?![a-z])", r"messenger rna", r"modrna", r"\btrimix\b",
                r"rna.loaded", r"\bBNT1\d{2}", r"\bmRNA-\d{3,4}", r"\bCVn?CoV",
                r"\bARCT-0?\d{2}", r"\bMRT\d{4}")),
]

# Companies that make only one kind of RNA drug. Used only when nothing in the
# trial itself names a modality, and recorded as such, since an RNA company can
# still run a trial of something else.
SPONSORS = [
    ("siRNA", rx(r"alnylam", r"arrowhead", r"dicerna", r"silence therapeutic", r"sirnaomics",
                 r"\bolix\b", r"sylentis", r"sirius therapeutic", r"quark pharm")),
    ("ASO", rx(r"\bionis\b", r"wave life", r"sarepta", r"stoke therapeutic", r"dynacure",
               r"n-lorem", r"nippon shinyaku", r"avidity")),
    ("mRNA", rx(r"\bmoderna\b", r"biontech", r"curevac", r"translate bio", r"recode therapeutic")),
    ("saRNA", rx(r"arcturus")),
    ("CRISPR RNA", rx(r"intellia", r"editas", r"beam therapeutic", r"verve therapeutic",
                      r"correctsequence")),
    ("RNA editing", rx(r"proqr", r"adarx")),
    ("aptamer", rx(r"tme pharma", r"aptarion", r"eyetech", r"ophthotech", r"iveric")),
]

# Trials outside the Monitor's vocabulary that still look like real candidates.
# A reviewer decides whether any of these belong; they never reach the page.
PROPOSED = [
    ("DNAzyme", rx(r"\bdnazym", r"\bhgd40\b", r"\bSB01[0-2]\b")),
    ("Exosome / EV delivery", rx(r"\bexosome", r"extracellular vesicle", r"\bCDK-00\d")),
    ("Ex vivo cell therapy", rx(r"\bcar[- ]?t\b", r"chimeric antigen receptor", r"dendritic cell",
                                r"\bTCR-T\b", r"\bTIL\b", r"autologous.{0,30}cell", r"\bLioCyx")),
    ("RNA-targeting small molecule", rx(r"splicing modulator", r"risdiplam", r"branaplam",
                                        r"rna.targeting small molecule")),
    ("Aptamer (DNA)", rx(r"\bss?dna aptamer", r"dna aptamer")),
    ("Oligonucleotide, unspecified", rx(r"oligonucleotide", r"\boligo\b", r"\bdecoy\b")),
    ("Nanoparticle delivery, no RNA cargo named", rx(r"lipid nanoparticle", r"\blnp\b",
                                                     r"nanoparticle")),
]

# Only the first six intervention names are read. Later entries are mostly
# comparators, procedures and assays: lifting the cap on 2026-09-16 added three
# labels across 3,984 trials, and all three were false positives (an anti-
# streptolysin O "ASO" in a diagnostic study, an mRNA-expression biomarker, and
# an mRNA vaccine named only as a comparator).
MAX_INTERVENTIONS = 6


def intervention_text(names):
    return "; ".join(names[:MAX_INTERVENTIONS])


def classify(interventions, title, sponsor):
    """Return (Monitor label, layer that decided), or (None, "none")."""
    for label, pattern in MODALITIES:
        if pattern.search(interventions):
            return label, "intervention"
    for label, pattern in MODALITIES:
        if pattern.search(title):
            return label, "title"
    for label, pattern in SPONSORS:
        if pattern.search(sponsor or ""):
            return label, "sponsor"
    return None, "none"


def propose(interventions, title):
    """A category outside the Monitor's vocabulary, for review only."""
    for label, pattern in PROPOSED:
        if pattern.search(interventions) or pattern.search(title):
            return label
    return ""
