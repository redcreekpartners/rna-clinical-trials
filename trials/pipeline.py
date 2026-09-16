"""Fetch, classify and shape — the whole run, shared by every script."""
import json

from . import config, fetch, record


def load_or_fetch(raw_path=None, save_raw=None, log=None):
    """Studies and their matched terms, from a saved fetch or a live one."""
    if raw_path:
        raw = json.loads(open(raw_path).read())
        return raw["studies"], raw["matched"]
    terms, _ = config.search_terms()
    studies, matched = fetch.search_all(terms, **({"log": log} if log else {}))
    if save_raw:
        with open(save_raw, "w") as fh:
            json.dump({"studies": studies, "matched": matched}, fh)
    return studies, matched


def records(studies, matched):
    """Every study as a reviewed record, in ClinicalTrials.gov's order."""
    _, loose = config.search_terms()
    cats = record.MonitorCategories(config.monitor_categories())
    return [record.build(study, matched.get(nct, []), loose, cats)
            for nct, study in studies.items()]
