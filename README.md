# alpha-klima-notebooks

Example notebooks demonstrating [Alpha-Klima](https://platform.alpha-klima.com)'s climate-risk API. Each notebook walks through a complete workflow against the platform — from authentication to result visualization — using small synthetic portfolios.

## Notebooks

The public notebooks are organized by workflow area:

| Section / Folder | Notebook | What it shows |
| --- | --- | --- |
| `01_api_fundamentals/` | [`01_hazard_data_api_basics.ipynb`](notebooks/01_api_fundamentals/01_hazard_data_api_basics.ipynb) | Requesting, transforming, and visualizing point-level hazard data. |
|  | [`02_asset_impact_api_basics.ipynb`](notebooks/01_api_fundamentals/02_asset_impact_api_basics.ipynb) | Per-asset impact distributions across hazards and scenarios. |
| `02_portfolio_workflows/` | [`01_real_estate_portfolio_exercise.ipynb`](notebooks/02_portfolio_workflows/01_real_estate_portfolio_exercise.ipynb) | End-to-end physical-risk workflow on a real-estate portfolio. |
|  | [`02_parkings_multihazard_screening.ipynb`](notebooks/02_portfolio_workflows/02_parkings_multihazard_screening.ipynb) | Multi-hazard screening then flood and heat pricing for a Seville car-park portfolio. |
|  | [`03_waste_facility_multihazard_screening.ipynb`](notebooks/02_portfolio_workflows/03_waste_facility_multihazard_screening.ipynb) | Multi-hazard screening then flood, wind, and heat pricing for EU waste facilities. |
| `03_regulatory_reporting/` | [`01_bank_pillar3_pipeline.ipynb`](notebooks/03_regulatory_reporting/01_bank_pillar3_pipeline.ipynb) | Bank pipeline run producing Pillar 3 and ECB physical-risk indicators. |
| `04_methodology_research/` | [`01_postal_code_hazard_screening.ipynb`](notebooks/04_methodology_research/01_postal_code_hazard_screening.ipynb) | Postal-code level hazard screening for Spain. |

**New to the API?** Start here:
1. [`01_hazard_data_api_basics.ipynb`](notebooks/01_api_fundamentals/01_hazard_data_api_basics.ipynb): Requesting, transforming, and visualizing point-level hazard data — the simplest path to a first successful API call and a visual result.
2. [`02_asset_impact_api_basics.ipynb`](notebooks/01_api_fundamentals/02_asset_impact_api_basics.ipynb): Per-asset impact distributions across hazards and scenarios — the core value proposition of the platform in a compact notebook.
3. [`01_real_estate_portfolio_exercise.ipynb`](notebooks/02_portfolio_workflows/01_real_estate_portfolio_exercise.ipynb): An end-to-end physical-risk workflow on a real-estate portfolio — the best full "start to finish" story, mirroring a real client use case.

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

## Documentation

We recommend consulting the **API Handbook** section of the **Documentation**, accessible from the [Alpha-Klima platform](https://platform.alpha-klima.com), while working with the `alpha-klima-notebooks`. It provides more detailed information about the platform setup, available data, API usage, and the example notebooks.

## Layout

- `notebooks/` — example notebooks and supporting helpers
- `resources/` — synthetic portfolios and reference data used by the notebooks

## License

[Apache License 2.0](LICENSE).