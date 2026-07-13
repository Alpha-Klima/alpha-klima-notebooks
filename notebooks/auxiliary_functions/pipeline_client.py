from time import sleep
from typing import Any
from urllib.parse import urljoin

import requests

POLL_INTERVAL_S = 3
REQUEST_TIMEOUT_S = 30


class PhysicalAssetPipeline:
    """Run the risk and clustering pipelines for one portfolio."""

    def __init__(self, *, api_base: str, api_key: str, portfolio: dict[str, Any]):
        self.api_base = f"{api_base.rstrip('/')}/"
        self.headers = {"X-API-Key": api_key, "Accept": "application/json"}
        self._risk_succeeded = False

        response = requests.post(
            self._url("api/physical-asset-portfolios"),
            json=portfolio,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_S,
        )
        response.raise_for_status()
        self._portfolio_code = response.json()["portfolio_code"]

    @property
    def portfolio_code(self) -> str:
        return self._portfolio_code

    def run_risk_analysis(
        self, requested_results: list[str] | None = None
    ) -> dict[str, Any]:
        self._risk_succeeded = False
        result_links = self._trigger_and_poll("risk-pipeline")
        self._risk_succeeded = True
        return self._fetch_results(result_links, requested_results)

    def run_clustering(
        self, requested_results: list[str] | None = None
    ) -> dict[str, Any]:
        if not self._risk_succeeded:
            raise RuntimeError(
                "Clustering requires risk analysis to complete successfully first"
            )

        result_links = self._trigger_and_poll("cluster-pipeline")
        return self._fetch_results(result_links, requested_results)

    def _trigger_and_poll(self, pipeline: str) -> dict[str, str]:
        response = requests.post(
            self._url(f"api/physical-asset-portfolios/{self.portfolio_code}/{pipeline}"),
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_S,
        )
        response.raise_for_status()
        status = response.json()

        if response.status_code == 202:
            status_url = response.headers.get("Location") or status["links"]["status"]

            while status["state"] != "success":
                if status["state"] == "failed":
                    raise RuntimeError(status.get("message", f"{pipeline} failed"))

                sleep(POLL_INTERVAL_S)
                response = requests.get(
                    self._url(status_url),
                    headers=self.headers,
                    timeout=REQUEST_TIMEOUT_S,
                )
                response.raise_for_status()
                status = response.json()

        if status["state"] != "success":
            raise RuntimeError(status.get("message", f"{pipeline} failed"))

        return status["links"]["results"]

    def _fetch_results(
        self,
        result_links: dict[str, str],
        requested_results: list[str] | None,
    ) -> dict[str, Any]:
        if requested_results is None:
            requested_results = list(result_links.values())

        results: dict[str, Any] = {}
        for endpoint in requested_results:
            response = requests.get(
                self._url(endpoint),
                headers=self.headers,
                timeout=REQUEST_TIMEOUT_S,
            )
            response.raise_for_status()
            results[endpoint] = response.json()

        return results

    def _url(self, path_or_url: str) -> str:
        return urljoin(self.api_base, path_or_url)
