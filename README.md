# alpha-klima-notebooks

Example notebooks demonstrating the [Alpha-Klima](https://platform.alpha-klima.com) climate-risk API. Each notebook walks through a complete workflow against the platform — from authentication to result visualization — using small synthetic portfolios.

## Notebooks

| Notebook | What it shows |
| --- | --- |
| [`CP_hazard_screening.ipynb`](notebooks/CP_hazard_screening.ipynb) | Postal-code level hazard screening for Spain. |
| [`hazard_data.ipynb`](notebooks/hazard_data.ipynb) | Requesting, transforming, and visualizing point-level hazard data. |
| [`asset_impact.ipynb`](notebooks/asset_impact.ipynb) | Per-asset impact distributions across hazards and scenarios. |
| [`RealEstateExercise.ipynb`](notebooks/RealEstateExercise.ipynb) | End-to-end physical-risk workflow on a real-estate portfolio. |
| [`bank_pipeline.ipynb`](notebooks/bank_pipeline.ipynb) | Bank pipeline run producing Pillar 3 and ECB physical-risk indicators. |

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
```

Open the notebooks under `notebooks/` in VS Code and select the `.venv` interpreter.

## API credentials

The notebooks call the Alpha-Klima API and require an API key. Copy `.env.example` to `.env` and fill in your key:

```
ALPHA_KLIMA_API_BASE_URL=https://platform.alpha-klima.com/prapi
ALPHA_KLIMA_API_KEY=<your-key>
```

Contact the Alpha-Klima team to be issued an API key for these notebooks.

## Layout

- `notebooks/` — example notebooks and supporting helpers
- `resources/` — synthetic portfolios and reference data used by the notebooks

## License

[Apache License 2.0](LICENSE).
