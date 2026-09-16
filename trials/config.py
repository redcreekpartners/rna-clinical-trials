"""Load the search terms and the Monitor's category vocabulary."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"


def search_terms():
    """(terms in search order, set of loose terms).

    Ours come first, then the Monitor's; a term in both is searched once, in its
    first position.
    """
    cfg = yaml.safe_load((CONFIG / "search_terms.yml").read_text())
    terms = list(dict.fromkeys(cfg["ours"] + cfg["monitor"]))
    return terms, set(cfg["loose"])


def monitor_categories():
    return yaml.safe_load((CONFIG / "monitor_categories.yml").read_text())
