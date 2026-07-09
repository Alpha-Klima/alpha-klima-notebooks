"""Preview of a proposed physrisk ``AKCoolingModel`` change: excess-over-baseline cooling
demand scaled by building floor area.

Why this module exists
-----------------------
The current physrisk ``AKCoolingModel``
(``physrisk/vulnerability_models/real_estate_models.py``) returns an *absolute* annual
cooling-electricity figure from a single hazard request, using a fixed whole-building heat-transfer
coefficient (1500 W/K) with **no floor-area scaling** and **no baseline subtraction**. That makes the
demo cooling numbers both mislabelled (they are not an "excess over baseline") and low (independent of
building size).

This module previews the proposed fix **without editing physrisk**: it computes the *additional* annual
cooling energy/cost attributable to warming, scaled by building floor area. The notebooks already fetch
the cooling-degree-day (CDD) field at the historical baseline and the scenario, so this runs client-side.
When the equivalent change lands in physrisk, the platform ``impact_mean`` should match this and the
notebooks can read it from the API again.

Formula (keep aligned with the eventual physrisk change)
--------------------------------------------------------
    excess_cdd  = max(cdd_scenario - cdd_baseline, 0)        # degree-days above the model base temp
    UA          = floor_area_m2 * transfer_coeff_per_m2      # W/K   (UA[W/K] = U[W/K/m2] * A[m2])
    excess_kwh  = excess_cdd * UA * 24 / 1000 / cop          # kWh/yr of cooling electricity
    excess_cost = excess_kwh * tariff_eur_per_kwh            # EUR/yr

Defaults: ``transfer_coeff_per_m2 = 1.5`` W/K/m2 (a realistic whole-building envelope + ventilation UA
per unit floor area is ~1-3 W/K/m2; the flat 1500 W/K in physrisk implies a ~500-1500 m2 building),
``cop = 3``, baseline = historical.
"""

from __future__ import annotations

import math

DEFAULT_TRANSFER_COEFF_PER_M2 = 1.5  # W/K per m2 of floor area
DEFAULT_COOLING_COP = 3.0            # electricity -> heat removed
DEFAULT_TARIFF_EUR_PER_KWH = 0.155   # Spain non-household, Eurostat nrg_pc_205


def _finite(x) -> bool:
    try:
        return not math.isnan(float(x))
    except (TypeError, ValueError):
        return False


def excess_cooling_energy_kwh(cdd_scenario, cdd_baseline, floor_area_m2,
                              transfer_coeff_per_m2=DEFAULT_TRANSFER_COEFF_PER_M2,
                              cop=DEFAULT_COOLING_COP):
    """Additional annual cooling electricity (kWh/yr) vs the baseline, scaled by floor area.

    Returns 0.0 when inputs are missing/NaN, when floor area is non-positive, or when the scenario CDD
    does not exceed the baseline (no additional cooling load).
    """
    if not (_finite(cdd_scenario) and _finite(cdd_baseline) and _finite(floor_area_m2)):
        return 0.0
    if floor_area_m2 <= 0:
        return 0.0
    excess_cdd = max(float(cdd_scenario) - float(cdd_baseline), 0.0)
    ua = float(floor_area_m2) * transfer_coeff_per_m2  # W/K
    return excess_cdd * ua * 24.0 / 1000.0 / cop       # kWh/yr


def excess_cooling_cost_eur(cdd_scenario, cdd_baseline, floor_area_m2,
                            tariff_eur_per_kwh=DEFAULT_TARIFF_EUR_PER_KWH,
                            transfer_coeff_per_m2=DEFAULT_TRANSFER_COEFF_PER_M2,
                            cop=DEFAULT_COOLING_COP):
    """Additional annual cooling-energy cost (EUR/yr) vs the baseline."""
    return excess_cooling_energy_kwh(cdd_scenario, cdd_baseline, floor_area_m2,
                                     transfer_coeff_per_m2, cop) * tariff_eur_per_kwh
