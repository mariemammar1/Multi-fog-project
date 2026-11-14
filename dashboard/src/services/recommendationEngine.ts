import {
  Station,
  Recommendation,
  ScoringWeights,
  UserPreferences,
  DriverLocation,
  TerritoryForecast,
  OccupancyLevel,
  FogId
} from '../types';

/**
 * Calculate Great-Circle distance using Haversine formula (km)
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
      rationale: `${availablePiles} piles immediately available. No queue expected.`,
    };
  }

  if (availablePiles > 0) {
    return {
      waitingTimeMin: 2,
      isEstimate: true,
      rationale: `Limited capacity (${availablePiles} left). Short access delay expected.`,
    };
  }

  // All piles currently occupied: estimate based on average charge turnover & territory saturation
  const territoryFactor = territoryOccupancyPercent > 60 ? 1.5 : 1.0;
  const estimatedQueue = Math.round(15 * territoryFactor);
  return {
    waitingTimeMin: estimatedQueue,
    isEstimate: true,
    rationale: `All local piles in use. Estimated turnover wait based on territory load (~${estimatedQueue} min).`,
  };
}

/**
 * Generate human-readable explanation for a recommended station
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
  const powerDesc = isDc ? `${station.maxPowerKw} kW DC Fast` : `${station.maxPowerKw} kW Standard AC`;

  // Pros
  if (station.availablePiles >= 4) {
    pros.push(`High availability: ${station.availablePiles} open piles ready right now`);
  } else if (station.availablePiles > 0) {
    pros.push(`${station.availablePiles} pile(s) currently open`);
  }

  if (station.maxPowerKw >= 120) {
    pros.push(`Ultra-fast charging capability (${station.maxPowerKw} kW DC)`);
  } else if (station.maxPowerKw >= 50) {
    pros.push(`Rapid charging available (${station.maxPowerKw} kW DC)`);
  }

  if (distanceKm < 3.5) {
    pros.push(`Close proximity (${distanceKm} km, ~${travelTimeMin} min drive)`);
  }

  if (occupancyLevel === 'low') {
    pros.push(`Favorable low territory congestion (${occupancyPercent}% forecast)`);
  }

  if (waitingTimeMin === 0) {
    pros.push(`Zero estimated wait time upon arrival`);
  }

  // Cons
  if (station.availablePiles <= 1 && station.totalPiles > 2) {
    cons.push(`High local demand (${station.availablePiles} pile left)`);
  }

  if (occupancyLevel === 'high') {
    cons.push(`Elevated regional demand in ${station.fogName} territory (${occupancyPercent}%)`);
  }

  if (distanceKm > 10) {
    cons.push(`Longer transit distance (${distanceKm} km, ~${travelTimeMin} min)`);
  }

  if (!isDc && station.maxPowerKw <= 7) {
    cons.push(`Standard AC only (up to 7 kW, slower session)`);
  }

  if (cons.length === 0) {
    cons.push(`Popular charging location during peak hours`);
  }

  // Full narrative
  const explanation = `Recommended because this station has ${station.availablePiles} available charging capacity with ${powerDesc} power, a short travel time of ${travelTimeMin} min (${distanceKm} km), and is located in ${station.fogName} where the Chronos-2 territory forecast indicates a ${occupancyLevel} expected occupancy (${occupancyPercent}%).`;

  return { explanation, pros, cons };
}

/**
 * Filter and Rank Stations according to multi-objective score
 */
export function rankStations(
  stations: Station[],
  driverLoc: DriverLocation,
  forecasts: Record<FogId, TerritoryForecast>,
  weights: ScoringWeights = { travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.2 },
  preferences: UserPreferences = {
    vehicleType: 'ALL',
    minPowerKw: 0,
    maxDistanceKm: 25,
    selectedFog: 'ALL',
    onlyAvailable: true,
  }
): Recommendation[] {
  // Step 1: Filter incompatible candidates
  const eligible = stations.filter((station) => {
    // Availability constraint
    if (preferences.onlyAvailable && station.availablePiles <= 0) {
      return false;
    }

    // Fog territory constraint
    if (preferences.selectedFog !== 'ALL' && station.fogId !== preferences.selectedFog) {
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

    // Distance pre-filter
    const dist = calculateDistanceKm(driverLoc.lat, driverLoc.lng, station.lat, station.lng);
    if (dist > preferences.maxDistanceKm) {
      return false;
    }

    return true;
  });

  if (eligible.length === 0) {
    return [];
  }

  // Step 2: Compute raw features for all eligible stations
  const featureList = eligible.map((station) => {
    const dist = calculateDistanceKm(driverLoc.lat, driverLoc.lng, station.lat, station.lng);
    const travelTime = estimateTravelTimeMin(dist);

    const territoryFc = forecasts[station.fogId];
    const occupancyPercent = territoryFc ? territoryFc.expectedOccupancyPercent : 30.0;
    const occupancyLevel = territoryFc ? territoryFc.occupancyLevel : 'low';

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

  // Step 3: Find min and max for normalization
  const maxTravelTime = Math.max(...featureList.map((f) => f.travelTimeMin), 30);
  const minTravelTime = Math.min(...featureList.map((f) => f.travelTimeMin), 2);

  const maxOccupancy = Math.max(...featureList.map((f) => f.occupancyPercent), 80);
  const minOccupancy = Math.min(...featureList.map((f) => f.occupancyPercent), 15);

  const maxWait = Math.max(...featureList.map((f) => f.waitingTimeMin), 15);
  const minWait = 0;

  // Step 4: Compute normalized score (Lower is better)
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

  // Assign ranks
  scored.forEach((rec, idx) => {
    rec.rank = idx + 1;
  });

  return scored;
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

