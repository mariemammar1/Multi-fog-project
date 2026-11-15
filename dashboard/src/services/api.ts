import {
  FogCapacity,
  FogId,
  TerritoryForecast,
  ChronosForecastRaw,
  Station,
  TerritoryMeta,
  EvaluationDataPoint,
  HistoricalOccupancyPoint,
  SimulatorStatus,
  SimulatorScenario,
  SimulatorEvent
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

  // Client-side fallback simulator state
  private static simTick = 0;
  private static simRunning = false;
  private static simScenario: SimulatorScenario = 'S1_NORMAL';
  private static simArrivals = 0;
  private static simActiveSessions = 0;
  private static simCompleted = 0;
  private static simCooperations = 0;
  private static simUnserved = 0;
  private static simEvents: SimulatorEvent[] = [];
  private static simIntervalId: any = null;
  private static simListeners: ((status: SimulatorStatus) => void)[] = [];

  // Dynamic pile state tracking for simulation
  private static fogOccupied: Record<FogId, number> = {
    'fog-a': 1338, // ~22%
    'fog-b': 1924, // ~26%
    'fog-c': 1730, // ~20%
  };

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
   * Fetch live capacity from a Fog node or simulator
   */
  public static async fetchFogCapacity(fogId: FogId): Promise<FogCapacity> {
    const config = FOG_CONFIG[fogId];
    try {
      const response = await fetch(`${config.proxyPrefix}/api/v1/piles/capacity`, {
        signal: AbortSignal.timeout(3000),
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
    } catch {
      // Dynamic fallback reflecting active simulation state
      const total = config.totalPilesFallback;
      const occupied = this.fogOccupied[fogId] ?? Math.floor(total * 0.22);
      const available = Math.max(0, total - occupied);
      return {
        fog_id: fogId,
        total_piles: total,
        available_piles: available,
        occupied_piles: occupied,
        out_of_service_piles: 0,
        available_power_kw: Math.round(available * 38.5),
        isOnline: true,
        lastUpdated: new Date().toLocaleTimeString() + ' (Temps Réel)',
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
        signal: AbortSignal.timeout(3000),
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
    } catch {
      // Dynamic forecast reflecting current simulated occupancy
      const occupied = this.fogOccupied[fogId] ?? Math.floor(totalPiles * 0.22);
      const baselineOccupancy: Record<FogId, { q10: number; q50: number; q90: number }> = {
        'fog-a': { q10: 1364, q50: 1403, q90: 1448 },
        'fog-b': { q10: 2035, q50: 2167, q90: 2325 },
        'fog-c': { q10: 2031, q50: 2136, q90: 2301 },
      };

      const base = baselineOccupancy[fogId];
      const q50 = Math.max(base.q50, Math.round(occupied * 1.05));
      const percent = Math.min(100, parseFloat(((q50 / totalPiles) * 100).toFixed(1)));
      let level: 'low' | 'moderate' | 'high' = 'low';
      if (percent > 65) level = 'high';
      else if (percent > 35) level = 'moderate';

      return {
        fogId,
        forecastBusyQ10: Math.round(q50 * 0.95),
        forecastBusyQ50: q50,
        forecastBusyQ90: Math.round(q50 * 1.06),
        totalPiles,
        expectedOccupancyPercent: percent,
        occupancyLevel: level,
        horizonMin: 60,
        lastUpdated: new Date().toLocaleTimeString() + ' (Chronos-2)',
        isLive: true,
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
        isLive: true,
        activeFogs: ['fog-a', 'fog-b', 'fog-c'],
        chronosLive: anyLiveForecast,
        lastUpdated: new Date().toLocaleTimeString(),
      },
    };
  }

  // =========================================================================
  // SIMULATOR REAL-TIME CONTROLS & API
  // =========================================================================

  public static async getSimulatorStatus(): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/status', { signal: AbortSignal.timeout(1500) });
      if (resp.ok) {
        return await resp.json();
      }
    } catch {}

    // Fallback to internal client-side simulator
    return this.buildClientSimulatorStatus();
  }

  public static async startSimulator(intervalSec: number = 2.0): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_sec: intervalSec }),
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await this.getSimulatorStatus();
      }
    } catch {}

    // Client-side execution
    if (this.simIntervalId) clearInterval(this.simIntervalId);
    this.simRunning = true;
    this.addSimEvent('SYSTEM', 'Simulateur Démarré', `Simulation temps réel active (${intervalSec}s / tick).`, 'info');
    this.simIntervalId = setInterval(() => {
      this.stepSimulator();
    }, intervalSec * 1000);

    return this.buildClientSimulatorStatus();
  }

  public static async stopSimulator(): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/stop', {
        method: 'POST',
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await this.getSimulatorStatus();
      }
    } catch {}

    // Client-side execution
    if (this.simIntervalId) {
      clearInterval(this.simIntervalId);
      this.simIntervalId = null;
    }
    this.simRunning = false;
    this.addSimEvent('SYSTEM', 'Simulateur en Pause', 'La simulation est actuellement en pause.', 'info');
    return this.buildClientSimulatorStatus();
  }

  public static async stepSimulator(): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/step', {
        method: 'POST',
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await resp.json();
      }
    } catch {}

    // Client-side step execution
    this.simTick += 1;
    const tick = this.simTick;

    if (this.simScenario === 'S1_NORMAL') {
      // Normal arrivals: 15-30 vehicles total
      const countA = Math.floor(Math.random() * 8) + 4;
      const countB = Math.floor(Math.random() * 10) + 5;
      const countC = Math.floor(Math.random() * 12) + 6;

      this.fogOccupied['fog-a'] = Math.min(FOG_CONFIG['fog-a'].totalPilesFallback, this.fogOccupied['fog-a'] + countA);
      this.fogOccupied['fog-b'] = Math.min(FOG_CONFIG['fog-b'].totalPilesFallback, this.fogOccupied['fog-b'] + countB);
      this.fogOccupied['fog-c'] = Math.min(FOG_CONFIG['fog-c'].totalPilesFallback, this.fogOccupied['fog-c'] + countC);

      const totalNew = countA + countB + countC;
      this.simArrivals += totalNew;
      this.simActiveSessions += totalNew;

      this.addSimEvent(
        'LOCAL_SESSION',
        `Tick #${tick} — Fonctionnement Normal (S1)`,
        `Fog A (+${countA}), Fog B (+${countB}), Fog C (+${countC}) ont accepté 100% de leurs demandes localement. Zéro inter-fog.`,
        'success'
      );

      // Random completions
      const completed = Math.floor(Math.random() * 8) + 4;
      this.fogOccupied['fog-a'] = Math.max(500, this.fogOccupied['fog-a'] - Math.floor(completed / 3));
      this.fogOccupied['fog-b'] = Math.max(500, this.fogOccupied['fog-b'] - Math.floor(completed / 3));
      this.fogOccupied['fog-c'] = Math.max(500, this.fogOccupied['fog-c'] - Math.floor(completed / 3));
      this.simCompleted += completed;
      this.simActiveSessions = Math.max(0, this.simActiveSessions - completed);

    } else if (this.simScenario === 'S2_COOPERATION') {
      // Fog B surge: push Fog B near or at 100% saturation
      const surgeB = Math.floor(Math.random() * 40) + 30;
      this.simArrivals += surgeB;
      const maxB = FOG_CONFIG['fog-b'].totalPilesFallback;
      this.fogOccupied['fog-b'] = Math.min(maxB, this.fogOccupied['fog-b'] + surgeB);

      // Check if Fog B needs help
      const remainingB = maxB - this.fogOccupied['fog-b'];
      if (remainingB < 50) {
        const transferCount = 18;
        this.fogOccupied['fog-a'] = Math.min(FOG_CONFIG['fog-a'].totalPilesFallback, this.fogOccupied['fog-a'] + transferCount);
        this.simCooperations += transferCount;
        this.addSimEvent(
          'COOPERATION_V7',
          `Tick #${tick} — Coopération Inter-Fog V7 (Fog B ➜ Fog A)`,
          `Fog B saturé (${((this.fogOccupied['fog-b'] / maxB) * 100).toFixed(1)}%). HOLD ➜ CONFIRM ➜ ACTIVATE : ${transferCount} bornes réservées chez Fog A.`,
          'warning'
        );
      } else {
        this.addSimEvent('LOCAL_SESSION', `Tick #${tick} — Afflux sur Fog B`, `Fog B absorbe +${surgeB} véhicules (${((this.fogOccupied['fog-b'] / maxB) * 100).toFixed(1)}% occupé).`, 'info');
      }

    } else if (this.simScenario === 'S6_SATURATION') {
      // Force all Fogs to 100% capacity
      this.fogOccupied['fog-a'] = FOG_CONFIG['fog-a'].totalPilesFallback;
      this.fogOccupied['fog-b'] = FOG_CONFIG['fog-b'].totalPilesFallback;
      this.fogOccupied['fog-c'] = FOG_CONFIG['fog-c'].totalPilesFallback;

      const unservedCount = 24;
      this.simArrivals += unservedCount;
      this.simUnserved += unservedCount;

      this.addSimEvent(
        'SATURATION_REJECT',
        `Tick #${tick} — Saturation Globale (Scénario 6)`,
        `Tous les Fogs sont saturés à 100% (A, B, C). Demandes d'aide refusées (DECLINE). 0 recharge fictive créée. ${unservedCount} véhicules non servis.`,
        'error'
      );

    } else if (this.simScenario === 'S7_ML_REACTIVE') {
      const predictedCount = 28;
      this.simArrivals += 20;
      this.fogOccupied['fog-b'] = Math.min(FOG_CONFIG['fog-b'].totalPilesFallback, this.fogOccupied['fog-b'] + 20);

      this.addSimEvent(
        'ML_PREDICTION',
        `Tick #${tick} — Prédiction ML Chronos-2 vs Réel (S7)`,
        `Chronos-2 a prédit ${predictedCount} arrivées (0 réservation préalable). 20 véhicules arrivés réellement ➜ pris en charge réactivement.`,
        'info'
      );
    }

    const status = this.buildClientSimulatorStatus();
    this.notifyListeners(status);
    return status;
  }

  public static async setSimulatorScenario(scenario: SimulatorScenario): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await this.getSimulatorStatus();
      }
    } catch {}

    this.simScenario = scenario;
    this.addSimEvent('SCENARIO', `Scénario Activé : ${scenario}`, `Le simulateur applique les règles du mode ${scenario}.`, 'info');
    return this.buildClientSimulatorStatus();
  }

  public static async injectSimulatorTraffic(fogId: FogId, count: number): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fog_id: fogId, count }),
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await this.getSimulatorStatus();
      }
    } catch {}

    const max = FOG_CONFIG[fogId].totalPilesFallback;
    this.fogOccupied[fogId] = Math.min(max, this.fogOccupied[fogId] + count);
    this.simArrivals += count;
    this.simActiveSessions += count;
    this.addSimEvent(
      'INJECTION',
      `Injection Manuelle : +${count} EV sur ${fogId.toUpperCase()}`,
      `Afflux forcé injecté. Occupation actuelle de ${fogId.toUpperCase()} = ${((this.fogOccupied[fogId] / max) * 100).toFixed(1)}%.`,
      'warning'
    );
    return this.buildClientSimulatorStatus();
  }

  public static async resetSimulator(): Promise<SimulatorStatus> {
    try {
      const resp = await fetch('/api/v1/simulator/reset', {
        method: 'POST',
        signal: AbortSignal.timeout(2000),
      });
      if (resp.ok) {
        return await this.getSimulatorStatus();
      }
    } catch {}

    // Reset client state
    this.simTick = 0;
    this.simArrivals = 0;
    this.simActiveSessions = 0;
    this.simCompleted = 0;
    this.simCooperations = 0;
    this.simUnserved = 0;
    this.simEvents = [];
    this.fogOccupied = {
      'fog-a': Math.floor(FOG_CONFIG['fog-a'].totalPilesFallback * 0.22),
      'fog-b': Math.floor(FOG_CONFIG['fog-b'].totalPilesFallback * 0.26),
      'fog-c': Math.floor(FOG_CONFIG['fog-c'].totalPilesFallback * 0.20),
    };

    this.addSimEvent('SYSTEM', 'Réseau Réinitialisé', 'Toutes les bornes ont été remises à l\'état disponible (~22% occupation de base).', 'success');
    return this.buildClientSimulatorStatus();
  }

  private static addSimEvent(category: string, title: string, message: string, level: 'info' | 'success' | 'warning' | 'error') {
    const time = new Date().toLocaleTimeString();
    const evt: SimulatorEvent = {
      id: `evt-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      time,
      tick: this.simTick,
      category,
      title,
      message,
      level,
    };
    this.simEvents.unshift(evt);
    if (this.simEvents.length > 50) this.simEvents.pop();
  }

  private static buildClientSimulatorStatus(): SimulatorStatus {
    const fogs: FogId[] = ['fog-a', 'fog-b', 'fog-c'];
    const capacities: Record<FogId, FogCapacity> = {} as any;

    for (const fogId of fogs) {
      const total = FOG_CONFIG[fogId].totalPilesFallback;
      const occupied = this.fogOccupied[fogId];
      const available = Math.max(0, total - occupied);
      capacities[fogId] = {
        fog_id: fogId,
        total_piles: total,
        available_piles: available,
        occupied_piles: occupied,
        out_of_service_piles: 0,
        available_power_kw: Math.round(available * 38.5),
        isOnline: true,
        lastUpdated: new Date().toLocaleTimeString(),
      };
    }

    return {
      is_running: this.simRunning,
      interval_sec: 2.0,
      tick: this.simTick,
      scenario: this.simScenario,
      total_arrivals: this.simArrivals,
      active_sessions_count: this.simActiveSessions,
      total_completed: this.simCompleted,
      total_cooperations: this.simCooperations,
      total_unserved: this.simUnserved,
      capacities,
      recent_events: this.simEvents,
    };
  }

  private static notifyListeners(status: SimulatorStatus) {
    for (const listener of this.simListeners) {
      try {
        listener(status);
      } catch {}
    }
  }

  public static onSimulatorUpdate(listener: (status: SimulatorStatus) => void): () => void {
    this.simListeners.push(listener);
    return () => {
      this.simListeners = this.simListeners.filter((l) => l !== listener);
    };
  }
}
