"""Shape Include records into the compact file the page reads."""
import re

from .classify import intervention_text

# Comparator and vehicle arms are not the drug under study, and "Placebo" would
# otherwise be the most common intervention name on the page.
COMPARATOR = re.compile(
    r"^\s*(placebo|saline|vehicle|normal saline|sham|matching placebo|standard of care|"
    r"best supportive care|no intervention|water|phosphate-buffered saline)\b", re.I)


def page_record(rec):
    names = [n.strip() for n in intervention_text(rec["interventions"]).split("; ")]
    drugs = [n for n in names if n and not COMPARATOR.match(n)]
    conditions = [c for c in "; ".join(rec["conditions"][:6]).split("; ") if c]
    return {
        "n": rec["nct"],
        "t": rec["title"],
        "m": rec["modality"],
        "p": rec["phase"],
        "s": rec["status"],
        "d": rec["start"],
        "sp": rec["sponsor"],
        "c": conditions[:2],
        "iv": drugs[:3],
        "co": rec["countries"],
    }


def page_records(records):
    out = [page_record(r) for r in records if r["action"] == "Include"]
    # newest first; the NCT number breaks ties so the file's order never depends
    # on the order ClinicalTrials.gov happened to return results in, which would
    # otherwise produce a spurious commit on days when nothing changed
    out.sort(key=lambda r: r["n"])
    out.sort(key=lambda r: r["d"] or "", reverse=True)
    return out
