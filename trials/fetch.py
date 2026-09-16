"""Query the ClinicalTrials.gov v2 API.

Public, keyless, and the same source the RNA Therapeutics Monitor's own
clinical-trials adapter uses. AACT would give relational depth and revision
history; this needs current phase and status for a few hundred trials, which
the API returns directly with no credential to expire.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = "|".join([
    "NCTId", "BriefTitle", "OfficialTitle", "OverallStatus", "Phase", "StudyType",
    "StartDate", "CompletionDate", "PrimaryCompletionDate", "LeadSponsorName",
    "LeadSponsorClass", "Condition", "InterventionName", "InterventionType",
    "InterventionDescription", "EnrollmentCount", "LocationCountry", "BriefSummary",
])
PAGE_SIZE = 1000
MAX_PAGES = 12            # the broadest term needs three
ATTEMPTS = 4
PAUSE = 0.25              # between terms; the API asks for restraint, not a rate

USER_AGENT = os.environ.get(
    "TRIALS_USER_AGENT",
    "rna-clinical-trials/1.0 (+https://github.com/redcreekpartners/rna-clinical-trials)")


class FetchError(RuntimeError):
    pass


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt == ATTEMPTS:
                raise FetchError(f"{params.get('query.intr')!r}: {error}") from error
            time.sleep(2 ** attempt)


def search(term):
    """Every interventional study whose interventions match `term`.

    Raises rather than returning a partial list. A term that silently came back
    short would shrink the published list with nothing to show for it; failing
    leaves the previous day's data in place instead.
    """
    studies, token = [], None
    for _ in range(MAX_PAGES):
        params = {"query.intr": term, "pageSize": str(PAGE_SIZE), "fields": FIELDS,
                  "filter.advanced": "AREA[StudyType]INTERVENTIONAL"}
        if token:
            params["pageToken"] = token
        page = _get(params)
        studies += page.get("studies", [])
        token = page.get("nextPageToken")
        if not token:
            return studies
    raise FetchError(f"{term!r}: more than {MAX_PAGES} pages; raise MAX_PAGES if this is real")


def search_all(terms, log=sys.stderr):
    """Run every term; return ({nct: study}, {nct: [terms that found it]})."""
    studies, matched = {}, {}
    for i, term in enumerate(terms, 1):
        found = search(term)
        added = 0
        for s in found:
            p = s["protocolSection"]
            nct = p["identificationModule"]["nctId"]
            if nct not in studies:
                studies[nct] = p
                added += 1
            matched.setdefault(nct, []).append(term)
        print(f"  {i:>2}/{len(terms)}  {term[:38]:<38} {len(found):>5}  +{added}", file=log)
        time.sleep(PAUSE)
    return studies, matched
