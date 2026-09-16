"""Turn one ClinicalTrials.gov study into a reviewed record.

Every study any search term returned becomes a record; nothing is dropped here.
Each carries a suggested action — Include, Review or Exclude — and the reasons
behind it in plain English, so a subject-matter expert can overrule any call.
Only Include records reach the published page.
"""
import re

from .classify import classify, intervention_text, propose, rx

COVID = rx(r"covid", r"sars-cov-2", r"coronavirus")
# Engineered outside the body: the patient receives cells, not an RNA drug.
EX_VIVO = rx(r"\bex vivo\b", r"\bcar[- ]?t\b", r"\bautologous\b", r"dendritic cell",
             r"hematopoietic stem cell", r"\bHSPC\b", r"\bTIL\b", r"edited cell",
             r"\bCAR-NK\b", r"chimeric antigen receptor")
PROPHYLACTIC = rx(r"\bprophyla", r"healthy (volunteer|adult|participant)s?.{0,40}vaccin",
                  r"immunogenicity.{0,30}vaccin")
DIAGNOSTIC = rx(r"biosensor", r"\bdiagnos", r"\bimaging\b", r"\b68ga\b", r"biomarker",
                r"screening test")
DNA_APTAMER = rx(r"\bss?dna\b", r"dna aptamer", r"biosensor")
# The Monitor's exclusion vocabulary, as literal phrases. Its global negative
# regexes are applied alongside these.
NON_THERAPEUTIC = rx(r"transcriptomic profiling", r"rna sequencing", r"single-cell rna-seq",
                     r"viral rna surveillance", r"rna biomarker", r"non-coding rna expression",
                     r"\bcrop\b", r"\bplant\b", r"agriculture")

# Flags that exclude a trial outright, whatever it is labelled.
HARD = ("diagnostic-or-imaging", "monitor-negative", "non-rna-aptamer")

REASONS = {
    "no-rna-term": "No Monitor modality is named in the interventions or title, and the sponsor "
                   "is not one that makes a single kind of RNA drug.",
    "loose-term-only": "Matched only via a multi-word search term whose words ClinicalTrials.gov "
                       "ORs apart (e.g. \"nucleic acid medicine\"), so the match may be on a common "
                       "word alone.",
    "covid": "COVID-19 / SARS-CoV-2 trial. Some are protein or viral-vector vaccine studies that "
             "matched only because an mRNA vaccine sits in the comparator arm.",
    "ex-vivo-cell-therapy": "Ex vivo cell therapy: cells are engineered outside the body and the "
                            "patient receives cells, not an RNA drug. In scope only if SRT counts "
                            "cell products as RNA therapeutics.",
    "status-unknown": "Recruitment status 'Unknown' — the sponsor has not updated the record in over "
                      "two years. Kept by default; the trial may be inactive.",
    "diagnostic-or-imaging": "Appears to be a diagnostic, biomarker or imaging study rather than a "
                             "therapeutic.",
    "prophylactic-vaccine": "Prophylactic vaccine in healthy volunteers rather than a therapeutic "
                            "intervention.",
    "non-rna-aptamer": "Aptamer trial, but the aptamer appears to be DNA rather than RNA.",
    "monitor-negative": "Matches one of the Monitor's own exclusion patterns (RNA-seq, "
                        "transcriptomics, viral RNA surveillance, RNA biomarker, plant/crop).",
}

LEAD = {
    "title": "Modality inferred from the trial title rather than its intervention.",
    "sponsor": "Modality inferred from the sponsor only; the trial names no RNA term.",
    "proposed": "The Monitor's modality labels do not cover this trial; a category outside their "
                "vocabulary is proposed instead.",
}


class MonitorCategories:
    """The Monitor's non-modality category patterns, for the review sheet.

    Coverage on trial records is poor — these patterns are tuned for papers, where
    an abstract discusses mechanism — so they inform a reviewer but decide nothing.
    """

    GROUPS = ("delivery_systems", "disease_areas", "therapeutic_targets", "topics")

    def __init__(self, config):
        self.negatives = [re.compile(p, re.I) for p in config.get("global_negative_patterns", [])]
        self.groups = {}
        for group in self.GROUPS:
            self.groups[group] = [
                (item["label"],
                 [re.compile(p, re.I) for p in item.get("patterns", [])],
                 [re.compile(p, re.I) for p in item.get("negative_patterns", [])])
                for item in config["categories"].get(group, [])
            ]

    def labels(self, group, text):
        return [label for label, pats, negs in self.groups[group]
                if any(p.search(text) for p in pats) and not any(n.search(text) for n in negs)]

    def is_negative(self, text):
        return any(n.search(text) for n in self.negatives) or bool(NON_THERAPEUTIC.search(text))


def phase_label(phases):
    return "/".join(p.replace("PHASE", "Phase ").replace("EARLY_Phase ", "Early Phase ")
                    for p in phases or []) or "Not applicable"


def build(study, matched_terms, loose_terms, categories):
    ident = study["identificationModule"]
    status = study["statusModule"]
    design = study.get("designModule", {})
    sponsor = study.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    arms = study.get("armsInterventionsModule", {}).get("interventions", [])
    names = [a.get("name", "") for a in arms]
    conditions = study.get("conditionsModule", {}).get("conditions", [])
    summary = study.get("descriptionModule", {}).get("briefSummary", "") or ""
    title = ident.get("briefTitle", "")
    countries = sorted({loc.get("country", "") for loc in
                        study.get("contactsLocationsModule", {}).get("locations", [])
                        if loc.get("country")})

    # the whole record, for flags that can fire on context
    text = " ".join([title, ident.get("officialTitle", "") or "",
                     " ".join(names), " ".join(a.get("description", "") or "" for a in arms),
                     " ".join(conditions), summary])

    ivs = intervention_text(names)
    label, source = classify(ivs, title, sponsor.get("name", ""))
    proposal = "" if label else propose(ivs, title)

    flags = []
    if not label:
        flags.append("no-rna-term")
    if matched_terms and all(t in loose_terms for t in matched_terms):
        flags.append("loose-term-only")
    if COVID.search(text):
        flags.append("covid")
    ex_vivo = bool(EX_VIVO.search(text))
    if ex_vivo:
        flags.append("ex-vivo-cell-therapy")
    if status["overallStatus"] == "UNKNOWN":
        flags.append("status-unknown")
    if DIAGNOSTIC.search(text):
        flags.append("diagnostic-or-imaging")
    if PROPHYLACTIC.search(text) and "vaccin" in text.lower():
        flags.append("prophylactic-vaccine")
    if label == "aptamer" and DNA_APTAMER.search(text):
        flags.append("non-rna-aptamer")
    if categories.is_negative(text):
        flags.append("monitor-negative")
    if source == "title":
        flags.append("title-only-match")
    if source == "sponsor":
        flags.append("sponsor-implied-only")

    hard = any(f in flags for f in HARD)
    if label and source == "intervention" and not hard and "covid" not in flags:
        action, lead = "Include", ""
    elif label or proposal:
        action = "Review"
        lead = LEAD.get(source) or (LEAD["proposed"] if proposal else "")
    else:
        action, lead = "Exclude", ""

    why = " ".join([lead] + [REASONS[f] for f in flags if f in REASONS]).strip()

    return {
        "nct": ident["nctId"],
        "title": title,
        "action": action,
        "why": why,
        "flags": flags,
        "modality": label or "",
        "proposed": proposal,
        "source": source,
        "delivery": categories.labels("delivery_systems", text),
        "disease_area": categories.labels("disease_areas", text),
        "targets": categories.labels("therapeutic_targets", text),
        "topics": categories.labels("topics", text),
        "ex_vivo": ex_vivo,
        "covid": "covid" in flags,
        "phase": phase_label(design.get("phases")),
        "status": status["overallStatus"].replace("_", " ").title(),
        "start": status.get("startDateStruct", {}).get("date", ""),
        "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "enrollment": design.get("enrollmentInfo", {}).get("count", ""),
        "sponsor": sponsor.get("name", ""),
        "sponsor_type": (sponsor.get("class", "") or "").title(),
        "conditions": conditions,
        "interventions": names,
        "countries": countries,
        "matched_terms": matched_terms,
        "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
    }
