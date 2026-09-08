"""Client-side cooling cost: excess-over-baseline cooling demand scaled by building floor area.

This is a provisional model, computed client-side so the demo notebooks can express chronic heat
in euros today. An enhanced methodology for this calculation is being onboarded into the platform,
after which the notebooks can read the figure from the API instead.

It computes the *additional* annual cooling energy and cost attributable to warming, scaled by
building floor area, from the cooling-degree-day (CDD) field the notebooks already request at the
historical baseline and at the scenario.

Formula
-------
    excess_cdd  = max(cdd_scenario - cdd_baseline, 0)        # degree-days above the model base temp
    UA          = floor_area_m2 * transfer_coeff_per_m2      # W/K   (UA[W/K] = U[W/K/m2] * A[m2])
    excess_kwh  = excess_cdd * UA * 24 / 1000 / cop          # kWh/yr of cooling electricity
    excess_cost = excess_kwh * tariff_eur_per_kwh            # EUR/yr

Defaults: ``transfer_coeff_per_m2 = 1.5`` W/K/m2 (a realistic whole-building envelope and
ventilation UA per unit floor area is about 1 to 3 W/K/m2), ``cop = 3``, baseline = historical.
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
