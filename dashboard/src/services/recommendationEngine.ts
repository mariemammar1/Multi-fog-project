import type {
  Station,
  Recommendation,
  ScoringWeights,
  UserPreferences,
  DriverLocation,
  TerritoryForecast,
  OccupancyLevel,
  FogId,
  MultiFogRecommendations
} from '../types/index.ts';

/**
 * Calculate Great-Circle distance using Haversine formula (km)
 * Note: Haversine distance is a simulated spatial estimation (straight-line),
 * not an actual road-network routing service distance.
 */
export function calculateDistanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // Earth's radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return parseFloat((R * c).toFixed(2));
}

/**
 * Estimate travel time in minutes based on average urban speed (35 km/h) and traffic overhead
 * Note: Simulated estimate based on urban speed model, clearly identified as non-GPS navigation.
 */
export function estimateTravelTimeMin(distanceKm: number): number {
  const averageUrbanSpeedKmH = 35;
  const transitTime = (distanceKm / averageUrbanSpeedKmH) * 60;
  const trafficOverhead = 2; // Fixed lights / parking time
  return Math.max(2, Math.round(transitTime + trafficOverhead));
}

/**
 * Estimate waiting time based on station available piles and territory pressure
 */
export function estimateWaitingTimeMin(
  availablePiles: number,
  totalPiles: number,
  territoryOccupancyPercent: number
): { waitingTimeMin: number; isEstimate: boolean; rationale: string } {
  if (availablePiles >= 3) {
    return {
      waitingTimeMin: 0,
      isEstimate: false,
      rationale: `${availablePiles} bornes immédiatement disponibles. Aucune attente prévue.`,
    };
  }

  if (availablePiles > 0) {
    return {
      waitingTimeMin: 2,
      isEstimate: true,
      rationale: `Capacité résiduelle limitée (${availablePiles} restante(s)). Court délai d'accès possible (~2 min).`,
    };
  }

  // All piles currently occupied: estimate based on average charge turnover & territory saturation
  const territoryFactor = territoryOccupancyPercent > 60 ? 1.5 : 1.0;
  const estimatedQueue = Math.round(15 * territoryFactor);
  return {
    waitingTimeMin: estimatedQueue,
    isEstimate: true,
    rationale: `Toutes les bornes locales sont occupées. Attente estimée par rotation selon la charge territoriale (~${estimatedQueue} min).`,
  };
}

/**
 * Generate human-readable explanation for a recommended station.
 * Clearly mentions the local Fog decision (Scenario S1) and simulated transit estimation.
 */
function generateExplanation(
  station: Station,
  travelTimeMin: number,
  distanceKm: number,
  occupancyPercent: number,
  occupancyLevel: OccupancyLevel,
  waitingTimeMin: number
): { explanation: string; pros: string[]; cons: string[] } {
  const pros: string[] = [];
  const cons: string[] = [];

  const isDc = station.fastCount > 0;
  const powerDesc = isDc ? `${station.maxPowerKw} kW DC Rapide` : `${station.maxPowerKw} kW AC Standard`;

  // Pros
  if (station.availablePiles >= 4) {
    pros.push(`Excellente disponibilité locale : ${station.availablePiles} bornes libres immédiatement`);
  } else if (station.availablePiles > 0) {
    pros.push(`${station.availablePiles} borne(s) libre(s) actuellement`);
  }

  if (station.maxPowerKw >= 120) {
    pros.push(`Recharge ultra-rapide (${station.maxPowerKw} kW DC)`);
  } else if (station.maxPowerKw >= 50) {
    pros.push(`Recharge rapide disponible (${station.maxPowerKw} kW DC)`);
  }

  if (distanceKm < 4.0) {
    pros.push(`Proximité géographique (${distanceKm} km, ~${travelTimeMin} min de route estimée)`);
  }

  if (occupancyLevel === 'low') {
    pros.push(`Faible affluence territoriale prévue par Chronos-2 (${occupancyPercent}%)`);
  }

  if (waitingTimeMin === 0) {
    pros.push(`Aucune attente estimée à l'arrivée`);
  }

  // Cons
  if (station.availablePiles <= 1 && station.totalPiles > 2) {
    cons.push(`Forte sollicitation locale (${station.availablePiles} borne restante)`);
  }

  if (occupancyLevel === 'high') {
    cons.push(`Affluence régionale soutenue dans ${station.fogName} (${occupancyPercent}%)`);
  }

  if (distanceKm > 12) {
    cons.push(`Distance de trajet plus longue (${distanceKm} km, ~${travelTimeMin} min estimées)`);
  }

  if (!isDc && station.maxPowerKw <= 7) {
    cons.push(`Recharge AC standard (7 kW max, session de charge plus longue)`);
  }

  if (cons.length === 0) {
    cons.push(`Station recherchée pendant les heures de forte demande`);
  }

  // Narrative explanation adhering to S1: autonomous local decision without Fog-to-Fog cooperation
  const explanation = `Recommandée localement par ${station.fogName} (Scénario S1 — Décision autonome sans coopération) : ${station.availablePiles} bornes libres sur ${station.totalPiles} (${powerDesc}), temps de route simulé à ~${travelTimeMin} min (${distanceKm} km), et prévision Chronos-2 territoriale favorable avec ${occupancyPercent}% d'occupation attendue (${occupancyLevel} affluence).`;

  return { explanation, pros, cons };
}

/**
 * Filter and Rank Stations strictly for ONE specific Fog node.
 *
 * Architectural Invariants of Scenario S1 (Normal Operation):
 * 1. Fog node evaluates ONLY its own local stations (fogId matching).
 * 2. Uses ONLY its own local availability data.
 * 3. Uses ONLY its own Chronos-2 territory forecast.
 * 4. Normalization is strictly localized within this Fog's candidate set.
 * 5. No cross-Fog data access or Fog-to-Fog communication is triggered.
 */
export function rankFogStations(
  fogId: FogId,
  stations: Station[],
  driverLoc: DriverLocation,
  fogForecast: TerritoryForecast | undefined,
  weights: ScoringWeights = { travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.20 },
  preferences: UserPreferences = {
    vehicleType: 'ALL',
    minPowerKw: 0,
    maxDistanceKm: 25,
    selectedFog: 'ALL',
    onlyAvailable: true,
  }
): Recommendation[] {
  // Rule 1: Strictly isolate stations belonging to this Fog node
  const localCandidates = stations.filter((station) => station.fogId === fogId);

  // If preferences explicitly filter out this Fog, return empty list
  if (preferences.selectedFog !== 'ALL' && preferences.selectedFog !== fogId) {
    return [];
  }

  // Step 1: Filter incompatible candidates according to driver preferences
  const eligible = localCandidates.filter((station) => {
    // Availability constraint
    if (preferences.onlyAvailable && station.availablePiles <= 0) {
      return false;
    }

    // Vehicle connector constraint
    if (preferences.vehicleType === 'DC_FAST' && station.fastCount === 0) {
      return false;
    }
    if (preferences.vehicleType === 'AC_SLOW' && station.slowCount === 0) {
      return false;
    }

    // Minimum power constraint
    if (station.maxPowerKw < preferences.minPowerKw) {
      return false;
    }

    // Distance pre-filter (simulated Haversine)
    const dist = calculateDistanceKm(driverLoc.lat, driverLoc.lng, station.lat, station.lng);
    if (dist > preferences.maxDistanceKm) {
      return false;
    }

    return true;
  });

  if (eligible.length === 0) {
    return [];
  }

  // Step 2: Compute raw features using strictly this Fog's Chronos-2 forecast
  const occupancyPercent = fogForecast ? fogForecast.expectedOccupancyPercent : 30.0;
  const occupancyLevel = fogForecast ? fogForecast.occupancyLevel : 'low';

  const featureList = eligible.map((station) => {
    const dist = calculateDistanceKm(driverLoc.lat, driverLoc.lng, station.lat, station.lng);
    const travelTime = estimateTravelTimeMin(dist);

    const { waitingTimeMin } = estimateWaitingTimeMin(
      station.availablePiles,
      station.totalPiles,
      occupancyPercent
    );

    return {
      station,
      distanceKm: dist,
      travelTimeMin: travelTime,
      occupancyPercent,
      occupancyLevel,
      waitingTimeMin,
    };
  });

  // Step 3: Find min and max for normalization strictly within this Fog's candidate set
  const maxTravelTime = Math.max(...featureList.map((f) => f.travelTimeMin), 30);
  const minTravelTime = Math.min(...featureList.map((f) => f.travelTimeMin), 2);

  const maxOccupancy = Math.max(...featureList.map((f) => f.occupancyPercent), 80);
  const minOccupancy = Math.min(...featureList.map((f) => f.occupancyPercent), 15);

  const maxWait = Math.max(...featureList.map((f) => f.waitingTimeMin), 15);
  const minWait = 0;

  // Step 4: Compute normalized multi-criteria score
  // formula: score = W_travel * norm_travel + W_occupancy * norm_occupancy + W_wait * norm_wait
  const totalWeight = weights.travelTime + weights.predictedOccupancy + weights.waitingTime || 1;
  const wTravel = weights.travelTime / totalWeight;
  const wOcc = weights.predictedOccupancy / totalWeight;
  const wWait = weights.waitingTime / totalWeight;

  const scored: Recommendation[] = featureList.map((item) => {
    const normTravel =
      maxTravelTime > minTravelTime
        ? (item.travelTimeMin - minTravelTime) / (maxTravelTime - minTravelTime)
        : 0;

    const normOcc =
      maxOccupancy > minOccupancy
        ? (item.occupancyPercent - minOccupancy) / (maxOccupancy - minOccupancy)
        : 0;

    const normWait = maxWait > minWait ? (item.waitingTimeMin - minWait) / (maxWait - minWait) : 0;

    const rawScore = parseFloat((wTravel * normTravel + wOcc * normOcc + wWait * normWait).toFixed(4));

    // Convert rawScore (0=best, 1=worst) to composite score (100=best, 0=worst)
    const compositeScore = Math.max(0, Math.min(100, Math.round((1 - rawScore) * 100)));

    const { explanation, pros, cons } = generateExplanation(
      item.station,
      item.travelTimeMin,
      item.distanceKm,
      item.occupancyPercent,
      item.occupancyLevel,
      item.waitingTimeMin
    );

    return {
      station: item.station,
      rank: 0,
      distanceKm: item.distanceKm,
      travelTimeMin: item.travelTimeMin,
      waitingTimeMin: item.waitingTimeMin,
      expectedOccupancyPercent: item.occupancyPercent,
      occupancyLevel: item.occupancyLevel,
      territoryName: item.station.fogName,
      rawScore,
      compositeScore,
      normalizedTravelTime: parseFloat(normTravel.toFixed(3)),
      normalizedOccupancy: parseFloat(normOcc.toFixed(3)),
      normalizedWaitTime: parseFloat(normWait.toFixed(3)),
      explanation,
      pros,
      cons,
    };
  });

  // Step 5: Sort ascending by rawScore (lowest penalty first)
  scored.sort((a, b) => a.rawScore - b.rawScore);

  // Assign local ranks 1..N
  scored.forEach((rec, idx) => {
    rec.rank = idx + 1;
  });

  return scored;
}

/**
 * Compute Scenario S1 (Normal Operation) recommendations for all 3 Fog nodes.
 *
 * Calculates three separate and independent rankings:
 * - recommendationsA: stations where fogId === 'fog-a'
 * - recommendationsB: stations where fogId === 'fog-b'
 * - recommendationsC: stations where fogId === 'fog-c'
 *
 * Each Fog computes its ranking locally and independently without cross-Fog comparison.
 */
export function computeScenario1Recommendations(
  allStations: Station[],
  driverLoc: DriverLocation,
  forecasts: Record<FogId, TerritoryForecast>,
  weights: ScoringWeights = { travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.20 },
  preferences: UserPreferences = {
    vehicleType: 'ALL',
    minPowerKw: 0,
    maxDistanceKm: 25,
    selectedFog: 'ALL',
    onlyAvailable: true,
  }
): MultiFogRecommendations {
  // Data partition: each Fog accesses strictly its own local database records
  const stationsA = allStations.filter((s) => s.fogId === 'fog-a');
  const stationsB = allStations.filter((s) => s.fogId === 'fog-b');
  const stationsC = allStations.filter((s) => s.fogId === 'fog-c');

  return {
    'fog-a': rankFogStations('fog-a', stationsA, driverLoc, forecasts['fog-a'], weights, preferences),
    'fog-b': rankFogStations('fog-b', stationsB, driverLoc, forecasts['fog-b'], weights, preferences),
    'fog-c': rankFogStations('fog-c', stationsC, driverLoc, forecasts['fog-c'], weights, preferences),
  };
}

/**
 * Filter and Rank Stations according to multi-objective score.
 * Maintained for backward compatibility.
 */
export function rankStations(
  stations: Station[],
  driverLoc: DriverLocation,
  forecasts: Record<FogId, TerritoryForecast>,
  weights: ScoringWeights = { travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.20 },
  preferences: UserPreferences = {
    vehicleType: 'ALL',
    minPowerKw: 0,
    maxDistanceKm: 25,
    selectedFog: 'ALL',
    onlyAvailable: true,
  }
): Recommendation[] {
  const targetFog: FogId = preferences.selectedFog === 'ALL' ? 'fog-a' : preferences.selectedFog;
  return rankFogStations(
    targetFog,
    stations.filter((s) => s.fogId === targetFog),
    driverLoc,
    forecasts[targetFog],
    weights,
    preferences
  );
}

/**
 * Driver preset locations across the metropolitan region
 */
export const PRESET_LOCATIONS: DriverLocation[] = [
  { label: 'Nanshan Tech Park (Fog A)', lat: 22.5401, lng: 113.9452, district: 'Nanshan' },
  { label: 'Futian CBD / Convention (Fog A)', lat: 22.5358, lng: 114.0543, district: 'Futian' },
  { label: 'Bao’an Airport / West Hub (Fog C)', lat: 22.6289, lng: 113.8122, district: 'Baoan' },
  { label: 'Qianhai Free Trade Zone (Fog C)', lat: 22.5184, lng: 113.9015, district: 'Qianhai' },
  { label: 'Luohu Railway Station (Fog B)', lat: 22.5323, lng: 114.1189, district: 'Luohu' },
  { label: 'Longgang Center (Fog B)', lat: 22.7214, lng: 114.2483, district: 'Longgang' },
];
