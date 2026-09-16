# RNA Clinical Trials

Interventional RNA therapeutics trials from [ClinicalTrials.gov](https://clinicaltrials.gov/),
grouped with the [RNA Therapeutics Monitor](https://github.com/McRae-Lab/rna-therapeutics-monitor)'s
modality categories. Refreshed daily.

- `index.html` — the page
- `data/trials.json` — the list
- `scripts/update.py` — refreshes the list; runs daily in Actions
- `scripts/build_review_sheet.py` — the review spreadsheet: every trial found, with why
  each was kept or left out

How trials are chosen is documented in `trials/classify.py` and `trials/record.py`.

## Get the review spreadsheet

Every trial the search finds, with the suggested action and the reason for it,
built from today's ClinicalTrials.gov data (a few minutes):

```bash
pip install -r requirements.txt
python scripts/build_review_sheet.py
```

This writes `rna-clinical-trials-review.xlsx`. Without Python: fork this repo, enable
workflows in the fork's *Actions* tab, run *Build review spreadsheet*, and download
the file from the finished run.

## Run the page

```bash
pip install -r requirements.txt
python scripts/update.py
python -m http.server 8000
```

## Publish

*Settings → Pages*: deploy from branch `main`, folder `/ (root)`.

On a fork, also enable workflows in the *Actions* tab, and set
*Settings → Actions → General → Workflow permissions* to read and write.

## Credits

Trial data from ClinicalTrials.gov. Modality vocabulary and search terms from the
RNA Therapeutics Monitor (McRae Lab, MIT — see `config/LICENSE-rna-monitor`); not affiliated
with or endorsed by it. Map from Natural Earth (public domain). Fonts DM Sans and
Raleway (SIL OFL — see `fonts/`).
