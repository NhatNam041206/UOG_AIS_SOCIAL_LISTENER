# Phase Experiment Notebooks

The experiment notebooks provide a quick look at the implemented pipeline without
rerunning every full-data stage.

## Available Notebooks

| Notebook | Purpose |
| --- | --- |
| `notebooks/phase2_preprocessing_experiment.ipynb` | Explains the activity audit, filtering order, cleaning rules, production results, and a small integrated-controller experiment. |
| `notebooks/phase2_5_dataset_limitation_experiment.ipynb` | Prototypes the examination-only dataset limitation profiling layer, writes provisional Phase 2.5 diagnostics, and supports quick evaluation before module extraction. |
| `notebooks/phase3_sentiment_experiment.ipynb` | Explains VADER scoring, stratified validation sampling, VADER/RoBERTa comparison, production results, and disagreements. |

## Running the Notebooks

Use the project virtual environment as the notebook kernel. The notebooks can be
opened from the project root or from `notebooks/`.

Install Jupyter separately if it is not already available:

```powershell
.venv\Scripts\python.exe -m pip install jupyter
.venv\Scripts\python.exe -m jupyter lab
```

The notebooks reuse code from `src/` and read completed artifacts from `output/`.
They deliberately avoid rerunning the expensive full-data preprocessing and
RoBERTa inference stages. The Phase 2.5 notebook is currently a prototype for
the future production runner; see `docs/PHASE2_5_NOTEBOOK_TO_PIPELINE_GUIDE.md`
for the extraction path. The authoritative completed-phase runners remain:

```powershell
.venv\Scripts\python.exe verify\phase2\run_phase2.py
.venv\Scripts\python.exe verify\phase3\close_phase3.py
```

## Interpretation

The notebooks summarize integrated implementation behavior and recorded results.
They do not replace the detailed phase reports, automated tests, or reproducibility
manifests. RoBERTa is treated as a comparison model rather than human ground truth.
