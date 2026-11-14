export type FogId = 'fog-a' | 'fog-b' | 'fog-c';

export type StationStatus = 'AVAILABLE' | 'LIMITED' | 'OCCUPIED' | 'OUT_OF_SERVICE';

export type OccupancyLevel = 'low' | 'moderate' | 'high';

export interface Station {
  id: string;
  name: string;
  fogId: FogId;
  fogName: string;
  district: string;
  tazId: string;
  lat: number;
  lng: number;
  slowCount: number;
  fastCount: number;
  totalPiles: number;
  availablePiles: number;
  occupiedPiles: number;
  outOfServicePiles: number;
  maxPowerKw: number;
  totalPowerKw: number;
  pileTypes: string[];
  status: StationStatus;
  isReservable: boolean;
}

export interface FogCapacity {
  fog_id: FogId;
  total_piles: number;
  available_piles: number;
  occupied_piles: number;
  out_of_service_piles: number;
  non_reservable_piles?: number;
  available_power_kw: number;
  isOnline: boolean;
  lastUpdated: string;
}

export interface ChronosForecastRaw {
  fog_id: FogId;
  metric: string;
  history_points: number;
  horizon_min: number;
  created_at: string;
  model_version: string;
  forecasts: {
    q10: number[];
    q50: number[];
    q90: number[];
  };
}

export interface TerritoryForecast {
  fogId: FogId;
  forecastBusyQ10: number;
  forecastBusyQ50: number;
  forecastBusyQ90: number;
  totalPiles: number;
  expectedOccupancyPercent: number; // e.g. 23.4%
  occupancyLevel: OccupancyLevel; // 'low' | 'moderate' | 'high'
  horizonMin: number;
  lastUpdated: string;
  isLive: boolean;
}

export interface TerritoryMeta {
  name: string;
  color: string;
  total_stations: number;
  total_piles: number;
  total_power_kw: number;
  mae_chronos: number;
  mae_baseline: number;
  center: [number, number];
}

export interface EvaluationDataPoint {
  fogId: FogId;
  time: string;
  hour: string;
  actual: number;
  chronosQ50: number;
  baseline: number;
}

export interface HistoricalOccupancyPoint {
  time: string;
  hour: string;
  busy: number;
}

export interface DriverLocation {
  label: string;
  lat: number;
  lng: number;
  district?: string;
  isCustomGps?: boolean;
}

export interface ScoringWeights {
  travelTime: number;       // default 0.45
  predictedOccupancy: number; // default 0.35
  waitingTime: number;      // default 0.20
}

export interface UserPreferences {
  vehicleType: 'ALL' | 'DC_FAST' | 'AC_SLOW';
  minPowerKw: number;
  maxDistanceKm: number;
  selectedFog: 'ALL' | FogId;
  onlyAvailable: boolean;
}

export interface Recommendation {
  station: Station;
  rank: number;
  distanceKm: number;
  travelTimeMin: number;
  waitingTimeMin: number;
  expectedOccupancyPercent: number;
  occupancyLevel: OccupancyLevel;
  territoryName: string;
  rawScore: number;
  compositeScore: number; // 0 - 100 scaled (100 = best)
  normalizedTravelTime: number;
  normalizedOccupancy: number;
  normalizedWaitTime: number;
  explanation: string;
  pros: string[];
  cons: string[];
}

export interface ToastMessage {
  id: string;
  title: string;
  message?: string;
  type: 'success' | 'info' | 'warning';
}
