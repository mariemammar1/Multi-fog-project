import {
  FogCapacity,
  FogId,
  TerritoryForecast,
  ChronosForecastRaw,
  Station,
  TerritoryMeta,
  EvaluationDataPoint,
  HistoricalOccupancyPoint
} from '../types';

import staticStations from '../data/stations.json';
import staticTerritories from '../data/territories.json';
import staticEvaluation from '../data/evaluation_results.json';
import staticHistoricalOccupancy from '../data/historical_occupancy.json';

const FOG_CONFIG: Record<FogId, { port: number; proxyPrefix: string; totalPilesFallback: number }> = {
  'fog-a': { port: 8001, proxyPrefix: '/fog-a', totalPilesFallback: 6083 },
  'fog-b': { port: 8002, proxyPrefix: '/fog-b', totalPilesFallback: 7403 },
  'fog-c': { port: 8003, proxyPrefix: '/fog-c', totalPilesFallback: 8652 },
};

export interface MultiFogStatus {
  isLive: boolean;
  activeFogs: FogId[];
  chronosLive: boolean;
  lastUpdated: string;
}

export class FogDataService {
  private static cachedStations: Station[] = staticStations as unknown as Station[];
  private static cachedTerritories: Record<FogId, TerritoryMeta> = staticTerritories as unknown as Record<FogId, TerritoryMeta>;

  /**
   * Load full station list
   */
  public static getStations(): Station[] {
    return this.cachedStations;
  }

  /**
   * Load territory metadata
   */
  public static getTerritoriesMeta(): Record<FogId, TerritoryMeta> {
    return this.cachedTerritories;
  }

  /**
   * Load historical Chronos-2 evaluation results (24h benchmark)
   */
  public static getEvaluationResults(): EvaluationDataPoint[] {
    return staticEvaluation as EvaluationDataPoint[];
  }

  /**
   * Load historical hourly observations
   */
  public static getHistoricalOccupancy(): Record<FogId, HistoricalOccupancyPoint[]> {
    return staticHistoricalOccupancy as unknown as Record<FogId, HistoricalOccupancyPoint[]>;
  }

  /**
   * Fetch live capacity from a Fog node
   */
  public static async fetchFogCapacity(fogId: FogId): Promise<FogCapacity> {
    const config = FOG_CONFIG[fogId];
    try {
      const response = await fetch(`${config.proxyPrefix}/api/v1/piles/capacity`, {
        signal: AbortSignal.timeout(4000),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        fog_id: fogId,
        total_piles: data.total_piles || config.totalPilesFallback,
        available_piles: data.available_piles ?? config.totalPilesFallback,
        occupied_piles: data.occupied_piles ?? 0,
        out_of_service_piles: data.out_of_service_piles ?? 0,
        non_reservable_piles: data.non_reservable_piles ?? 0,
        available_power_kw: data.available_power_kw ?? 100000,
        isOnline: true,
        lastUpdated: new Date().toLocaleTimeString(),
      };
    } catch (err) {
      // Graceful fallback to static data
      const meta = this.cachedTerritories[fogId];
      return {
        fog_id: fogId,
        total_piles: meta ? meta.total_piles : config.totalPilesFallback,
        available_piles: meta ? Math.floor(meta.total_piles * 0.78) : 5000,
        occupied_piles: meta ? Math.floor(meta.total_piles * 0.22) : 1000,
        out_of_service_piles: 0,
        available_power_kw: meta ? meta.total_power_kw * 0.8 : 95000,
        isOnline: false,
        lastUpdated: new Date().toLocaleTimeString() + ' (Demo)',
      };
    }
  }

  /**
   * Fetch live Chronos-2 forecast from a Fog node
   */
  public static async fetchFogForecast(fogId: FogId, totalPiles: number): Promise<TerritoryForecast> {
    const config = FOG_CONFIG[fogId];
    try {
      const response = await fetch(`${config.proxyPrefix}/api/v1/forecasts`, {
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const raw: ChronosForecastRaw = await response.json();
      const q10 = raw.forecasts.q10[0] ?? 1200;
      const q50 = raw.forecasts.q50[0] ?? 1350;
      const q90 = raw.forecasts.q90[0] ?? 1480;

      const expectedOccupancyPercent = Math.min(100, Math.max(0, (q50 / totalPiles) * 100));

      let occupancyLevel: 'low' | 'moderate' | 'high' = 'low';
      if (expectedOccupancyPercent > 65) {
        occupancyLevel = 'high';
      } else if (expectedOccupancyPercent > 35) {
        occupancyLevel = 'moderate';
      }

      return {
        fogId,
        forecastBusyQ10: q10,
        forecastBusyQ50: q50,
        forecastBusyQ90: q90,
        totalPiles,
        expectedOccupancyPercent: parseFloat(expectedOccupancyPercent.toFixed(1)),
        occupancyLevel,
        horizonMin: raw.horizon_min || 60,
        lastUpdated: new Date().toLocaleTimeString(),
        isLive: true,
      };
    } catch (err) {
      // Fallback from historical baseline
      const defaultOccupancy: Record<FogId, { q10: number; q50: number; q90: number }> = {
        'fog-a': { q10: 1364, q50: 1403, q90: 1448 },
        'fog-b': { q10: 2035, q50: 2167, q90: 2325 },
        'fog-c': { q10: 2031, q50: 2136, q90: 2301 },
      };

      const baseline = defaultOccupancy[fogId];
      const percent = (baseline.q50 / totalPiles) * 100;
      let level: 'low' | 'moderate' | 'high' = 'low';
      if (percent > 65) level = 'high';
      else if (percent > 35) level = 'moderate';

      return {
        fogId,
        forecastBusyQ10: baseline.q10,
        forecastBusyQ50: baseline.q50,
        forecastBusyQ90: baseline.q90,
        totalPiles,
        expectedOccupancyPercent: parseFloat(percent.toFixed(1)),
        occupancyLevel: level,
        horizonMin: 60,
        lastUpdated: new Date().toLocaleTimeString() + ' (Demo)',
        isLive: false,
      };
    }
  }

  /**
   * Fetch all fogs capacity and forecasts in parallel
   */
  public static async fetchAllFogData(): Promise<{
    capacities: Record<FogId, FogCapacity>;
    forecasts: Record<FogId, TerritoryForecast>;
    systemStatus: MultiFogStatus;
  }> {
    const fogs: FogId[] = ['fog-a', 'fog-b', 'fog-c'];

    const capacityResults = await Promise.all(fogs.map((id) => this.fetchFogCapacity(id)));

    const capacities: Record<FogId, FogCapacity> = {
      'fog-a': capacityResults[0],
      'fog-b': capacityResults[1],
      'fog-c': capacityResults[2],
    };

    const forecastResults = await Promise.all(
      fogs.map((id) => this.fetchFogForecast(id, capacities[id].total_piles))
    );

    const forecasts: Record<FogId, TerritoryForecast> = {
      'fog-a': forecastResults[0],
      'fog-b': forecastResults[1],
      'fog-c': forecastResults[2],
    };

    const activeFogs = fogs.filter((f) => capacities[f].isOnline);
    const anyLiveForecast = fogs.some((f) => forecasts[f].isLive);

    return {
      capacities,
      forecasts,
      systemStatus: {
        isLive: activeFogs.length > 0,
        activeFogs,
        chronosLive: anyLiveForecast,
        lastUpdated: new Date().toLocaleTimeString(),
      },
    };
  }
}

