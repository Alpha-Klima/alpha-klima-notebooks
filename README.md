# alpha-klima-notebooks

Example notebooks demonstrating [Alpha-Klima](https://platform.alpha-klima.com)'s climate-risk API. Each notebook walks through a complete workflow against the platform — from authentication to result visualization — using small synthetic portfolios.

## Notebooks

| Notebook | What it shows |
| --- | --- |
| [`CP_hazard_screening.ipynb`](notebooks/CP_hazard_screening.ipynb) | Postal-code level hazard screening for Spain. |
| [`hazard_data.ipynb`](notebooks/hazard_data.ipynb) | Requesting, transforming, and visualizing point-level hazard data. |
| [`asset_impact.ipynb`](notebooks/asset_impact.ipynb) | Per-asset impact distributions across hazards and scenarios. |
| [`RealEstateExercise.ipynb`](notebooks/RealEstateExercise.ipynb) | End-to-end physical-risk workflow on a real-estate portfolio. |
| [`bank_pipeline.ipynb`](notebooks/bank_pipeline.ipynb) | Bank pipeline run producing Pillar 3 and ECB physical-risk indicators. |
| [`parkings_multihazard_demo.ipynb`](notebooks/parkings_multihazard_demo.ipynb) | Multi-hazard screening then flood and heat pricing for a Seville car-park portfolio. |
| [`waste_facility_multihazard_demo.ipynb`](notebooks/waste_facility_multihazard_demo.ipynb) | Multi-hazard screening then flood, wind, and heat pricing for EU waste facilities. |

## Setup

We recommend using [uv](https://docs.astral.sh/uv/) for installation.
Run

```bash
uv sync
```

to install all necessary dependencies in a local virtual environment (`.venv`). Then, open the notebooks under `notebooks/` in your preferred editor or IDE and select the `.venv` interpreter.

## API credentials

The notebooks call the Alpha-Klima API and require an API key.

To obtain an API key you need to:
1. Register at https://platform.alpha-klima.com or get invited to an existing organization.
1. Generate API keys from the API keys tab of the user menu. Note that only members of the organization with owner privileges can issue API keys.

Then, copy `.env.example` to `.env` and fill in your key:

```
ALPHA_KLIMA_API_BASE_URL=https://platform.alpha-klima.com/prapi
ALPHA_KLIMA_API_KEY=<your-key>
```

Note that for the API key to work, the organization must have an active Quota.
The Quota determines the usage limits of the Alpha-Klima platform.
Email us at [contact@alpha-klima.com](contact@alpha-klima.com) to set up a Quota.

## Layout

- `notebooks/` — example notebooks and supporting helpers
- `resources/` — synthetic portfolios and reference data used by the notebooks

## License

[Apache License 2.0](LICENSE).
