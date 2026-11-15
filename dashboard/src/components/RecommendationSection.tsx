import React, { useState } from 'react';
import {
  Sparkles,
  Zap,
  MapPin,
  Clock,
  BatteryCharging,
  Sliders,
  CheckCircle,
  ArrowRight,
  ShieldAlert,
  SlidersHorizontal,
  Navigation,
  ChevronDown,
  ChevronUp,
  Star,
  Activity,
  Cpu,
  Layers,
  ShieldCheck,
  Server,
  Info
} from 'lucide-react';
import {
  Recommendation,
  ScoringWeights,
  UserPreferences,
  Station,
  FogId,
  FogCapacity,
  TerritoryForecast,
  TerritoryMeta,
  MultiFogRecommendations
} from '../types';

interface RecommendationSectionProps {
  selectedFog: FogId;
  onSelectFog: (fogId: FogId) => void;
  recommendations: Recommendation[];
  allFogRecommendations?: MultiFogRecommendations;
  capacities: Record<FogId, FogCapacity>;
  forecasts: Record<FogId, TerritoryForecast>;
  territoriesMeta: Record<FogId, TerritoryMeta>;
  weights: ScoringWeights;
  onWeightsChange: (weights: ScoringWeights) => void;
  preferences: UserPreferences;
  onPreferencesChange: (prefs: UserPreferences) => void;
  onOpenDetails: (station: Station) => void;
  onNavigateToStation: (station: Station) => void;
  selectedStationId: string | null;
  activeDestinationId: string | null;
  filtersOpen: boolean;
  onToggleFilters: () => void;
  onShowToast: (title: string, message?: string, type?: 'success' | 'info' | 'warning') => void;
}

export const RecommendationSection: React.FC<RecommendationSectionProps> = ({
  selectedFog,
  onSelectFog,
  recommendations,
  allFogRecommendations,
  capacities,
  forecasts,
  territoriesMeta,
  weights,
  onWeightsChange,
  preferences,
  onPreferencesChange,
  onOpenDetails,
  onNavigateToStation,
  activeDestinationId,
  onShowToast,
}) => {
  const [showAllAlternatives, setShowAllAlternatives] = useState<boolean>(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  const topPick = recommendations[0];
  const alternatives = showAllAlternatives
    ? recommendations.slice(1, 7)
    : recommendations.slice(1, 4);

  const currentCapacity = capacities[selectedFog];
  const currentForecast = forecasts[selectedFog];
  const currentMeta = territoriesMeta[selectedFog];

  const handleResetFilters = () => {
    onWeightsChange({ travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.20 });
    onPreferencesChange({
      vehicleType: 'ALL',
      minPowerKw: 0,
      maxDistanceKm: 25,
      selectedFog: 'ALL',
      onlyAvailable: true,
    });
    onShowToast('Filtres Réinitialisés', 'Paramètres optimaux par défaut appliqués.', 'info');
  };

  /* Friendly helper labels */
  const availLabel = (avail: number, total: number) => {
    const pct = total > 0 ? avail / total : 0;
    if (pct >= 0.5) return { text: 'Beaucoup de places libres', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (pct >= 0.2) return { text: 'Places disponibles', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    if (avail > 0)  return { text: 'Dernières places', color: 'text-orange-700 bg-orange-50 border-orange-200' };
    return { text: 'Actuellement complet', color: 'text-rose-700 bg-rose-50 border-rose-200' };
  };

  const fogZones: Array<{
    id: FogId;
    title: string;
    neighborhood: string;
    icon: string;
    colorBadge: string;
    activeClass: string;
  }> = [
    {
      id: 'fog-a',
      title: 'Zone Centre',
      neighborhood: 'Nanshan & Futian',
      icon: '🏢',
      colorBadge: 'bg-sky-500',
      activeClass: 'border-sky-500 bg-sky-50/50 ring-2 ring-sky-200 text-sky-950',
    },
    {
      id: 'fog-b',
      title: 'Zone Commerciale',
      neighborhood: 'Luohu & Longgang',
      icon: '🛍️',
      colorBadge: 'bg-emerald-500',
      activeClass: 'border-emerald-500 bg-emerald-50/50 ring-2 ring-emerald-200 text-emerald-950',
    },
    {
      id: 'fog-c',
      title: 'Zone Ouest',
      neighborhood: 'Bao\'an & Qianhai',
      icon: '🅿️',
      colorBadge: 'bg-amber-500',
      activeClass: 'border-amber-500 bg-amber-50/50 ring-2 ring-amber-200 text-amber-950',
    },
  ];

  return (
    <section className="space-y-6">

      {/* ── 1. Clean & Friendly Header ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold mb-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Réseau Opérationnel · Mode Local Autonome</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Où charger maintenant ?
          </h2>
          <p className="text-sm text-slate-500 font-medium mt-1">
            Sélectionnez votre zone, nous trouvons la borne la plus rapide et disponible pour vous.
          </p>
        </div>

        {/* ── Quick 1-Click Filters (Visible, No Hidden Drawer Required) ── */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Filter: All vs Fast */}
          <button
            onClick={() => {
              const newType = preferences.vehicleType === 'DC_FAST' ? 'ALL' : 'DC_FAST';
              onPreferencesChange({ ...preferences, vehicleType: newType });
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer border flex items-center gap-1.5 ${
              preferences.vehicleType === 'DC_FAST'
                ? 'bg-amber-500 text-white border-amber-500 shadow-sm'
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>⚡ Charge Rapide</span>
          </button>

          {/* Quick Filter: Only Available */}
          <button
            onClick={() => {
              onPreferencesChange({ ...preferences, onlyAvailable: !preferences.onlyAvailable });
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer border flex items-center gap-1.5 ${
              preferences.onlyAvailable
                ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
            }`}
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>🟢 Libres uniquement</span>
          </button>

          {/* Quick Radius Selector */}
          <div className="flex items-center bg-white border border-slate-200 rounded-xl px-2 py-1 text-xs font-bold text-slate-600">
            <span className="text-[10px] text-slate-400 uppercase mr-1">Rayon :</span>
            <select
              value={preferences.maxDistanceKm}
              onChange={(e) => onPreferencesChange({ ...preferences, maxDistanceKm: Number(e.target.value) })}
              className="bg-transparent font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              <option value={10}>10 km</option>
              <option value={25}>25 km</option>
              <option value={50}>50 km</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── 2. Friendly Zone Selector (Fog Nodes) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {fogZones.map((z) => {
          const isSelected = selectedFog === z.id;
          const fogRecs = allFogRecommendations ? allFogRecommendations[z.id] : [];
          const count = allFogRecommendations ? fogRecs.length : (isSelected ? recommendations.length : 0);
          const topScore = fogRecs[0]?.compositeScore;

          return (
            <button
              key={z.id}
              onClick={() => {
                onSelectFog(z.id);
                onShowToast(`Zone Sélectionnée`, `${z.title} (${z.neighborhood})`, 'info');
              }}
              className={`p-4 rounded-2xl border text-left transition-all cursor-pointer relative ${
                isSelected
                  ? `${z.activeClass} shadow-md`
                  : 'bg-white border-slate-200/90 hover:border-slate-300 text-slate-700 hover:bg-slate-50/80 shadow-xs'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{z.icon}</span>
                  <div>
                    <h3 className="text-sm font-black tracking-tight">{z.title}</h3>
                    <div className="text-[11px] text-slate-500 font-medium">{z.neighborhood}</div>
                  </div>
                </div>
                {isSelected && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-white text-slate-800 border border-slate-200 shadow-2xs">
                    Actif
                  </span>
                )}
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">
                  <strong className="text-slate-900 font-bold">{count}</strong> borne{count > 1 ? 's' : ''} éligible{count > 1 ? 's' : ''}
                </span>
                {topScore && (
                  <span className="text-emerald-700 font-black text-[11px] bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                    Top {topScore}%
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* ── 3. HERO RECOMMENDATION CARD (The Best Choice) ── */}
      {topPick ? (
        <div
          className={`rounded-3xl border transition-all relative overflow-hidden ${
            activeDestinationId === topPick.station.id
              ? 'bg-gradient-to-br from-emerald-50/70 via-white to-cyan-50/40 border-emerald-300 ring-4 ring-emerald-100/70 shadow-lg'
              : 'bg-white border-slate-200/90 shadow-md hover:shadow-lg'
          }`}
        >
          {/* Top color bar */}
          <div className="h-2 w-full bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" />

          <div className="p-6 sm:p-8 space-y-6">
            {/* Header row */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-600 text-white text-xs font-black uppercase tracking-wider shadow-sm">
                  <Star className="w-3.5 h-3.5 fill-current text-amber-300" />
                  <span>Meilleure Borne Recommandée</span>
                </span>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                  {topPick.station.fogName}
                </span>
                {activeDestinationId === topPick.station.id && (
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 inline-flex items-center gap-1">
                    <CheckCircle className="w-3 h-3 text-emerald-600" />
                    Itinéraire Actif
                  </span>
                )}
              </div>

              <div className="text-xs font-bold text-slate-500">
                Score de confort : <strong className="text-emerald-700 text-sm font-black">{topPick.compositeScore}%</strong>
              </div>
            </div>

            {/* Station Title */}
            <div>
              <h3 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {topPick.station.name}
              </h3>
              <p className="flex items-center gap-1.5 text-xs sm:text-sm text-slate-500 font-medium mt-1">
                <MapPin className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                <span>Secteur {topPick.station.district} · Station #{topPick.station.id}</span>
              </p>
            </div>

            {/* 3 Large, Clean Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              {/* Travel Time */}
              <div className="bg-slate-50 rounded-2xl p-4 text-center border border-slate-200/80">
                <div className="flex items-center justify-center gap-1.5 text-xs text-slate-500 font-bold mb-1.5">
                  <Clock className="w-4 h-4 text-cyan-600" />
                  <span>Temps de Route</span>
                </div>
                <div className="text-3xl font-black text-slate-900 leading-none">
                  ~{topPick.travelTimeMin} <span className="text-base font-bold text-slate-500">min</span>
                </div>
                <div className="text-xs text-slate-400 font-medium mt-1">Distance : {topPick.distanceKm} km</div>
              </div>

              {/* Free Spots */}
              <div className="bg-emerald-50 rounded-2xl p-4 text-center border border-emerald-200">
                <div className="flex items-center justify-center gap-1.5 text-xs text-emerald-700 font-bold mb-1.5">
                  <BatteryCharging className="w-4 h-4 text-emerald-600" />
                  <span>Bornes Libres</span>
                </div>
                <div className="text-3xl font-black text-emerald-700 leading-none">
                  {topPick.station.availablePiles}{' '}
                  <span className="text-base font-bold text-emerald-600">/ {topPick.station.totalPiles}</span>
                </div>
                <div className="text-xs text-emerald-600 font-semibold mt-1">Disponibilité Immédiate</div>
              </div>

              {/* Power */}
              <div className="bg-amber-50 rounded-2xl p-4 text-center border border-amber-200">
                <div className="flex items-center justify-center gap-1.5 text-xs text-amber-700 font-bold mb-1.5">
                  <Zap className="w-4 h-4 text-amber-600" />
                  <span>Puissance Max</span>
                </div>
                <div className="text-3xl font-black text-amber-700 leading-none">
                  {topPick.station.maxPowerKw} <span className="text-base font-bold text-amber-600">kW</span>
                </div>
                <div className="text-xs text-amber-600 font-semibold mt-1">
                  {topPick.station.fastCount > 0 ? '⚡ Recharge Rapide DC' : 'Recharge Standard AC'}
                </div>
              </div>
            </div>

            {/* Natural Language Explanation */}
            <div className="flex items-start gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200 text-slate-700 text-xs sm:text-sm font-medium leading-relaxed">
              <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <p>{topPick.explanation}</p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={() => onNavigateToStation(topPick.station)}
                className="flex-1 flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-black text-sm shadow-lg shadow-emerald-600/25 transition-all cursor-pointer active:scale-98"
              >
                <Navigation className="w-4 h-4" />
                <span>Choisir cette borne & Lancer l'Itinéraire</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={() => onOpenDetails(topPick.station)}
                className="sm:w-auto px-5 py-4 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-sm border border-slate-200 transition-colors cursor-pointer"
              >
                Fiche détaillée
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white p-10 rounded-3xl border border-slate-200 text-center shadow-xs">
          <ShieldAlert className="w-10 h-10 text-amber-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-900">
            Aucune station trouvée avec ces filtres
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Augmentez le rayon de distance ou réinitialisez vos filtres pour voir d'autres bornes.
          </p>
          <button
            onClick={handleResetFilters}
            className="mt-4 px-5 py-2.5 rounded-xl bg-cyan-600 text-white text-sm font-bold hover:bg-cyan-700 transition-colors cursor-pointer"
          >
            Réinitialiser les filtres
          </button>
        </div>
      )}

      {/* ── 4. Alternative Stations ── */}
      {alternatives.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <h4 className="text-base font-black text-slate-900 flex items-center gap-2">
              <span>Autres alternatives conseillées</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600">
                {recommendations.length - 1} options
              </span>
            </h4>
            {recommendations.length > 4 && (
              <button
                onClick={() => setShowAllAlternatives(!showAllAlternatives)}
                className="flex items-center gap-1 text-xs font-bold text-cyan-700 hover:text-cyan-900 cursor-pointer"
              >
                {showAllAlternatives ? (
                  <><ChevronUp className="w-3.5 h-3.5" /> Réduire</>
                ) : (
                  <><ChevronDown className="w-3.5 h-3.5" /> Voir plus d'alternatives</>
                )}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {alternatives.map((rec) => {
              const isActive = activeDestinationId === rec.station.id;
              const avail = availLabel(rec.station.availablePiles, rec.station.totalPiles);

              return (
                <div
                  key={rec.station.id}
                  className={`bg-white rounded-2xl border p-4 flex flex-col justify-between transition-all shadow-xs hover:shadow-md ${
                    isActive
                      ? 'border-emerald-400 ring-2 ring-emerald-100'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="px-2 py-0.5 rounded-lg bg-slate-100 text-[10px] font-black text-slate-600">
                        #{rec.rank} dans cette zone
                      </span>
                      <span className="text-xs font-bold text-emerald-700">
                        {rec.compositeScore}%
                      </span>
                    </div>

                    <h5 className="text-sm font-black text-slate-900 truncate" title={rec.station.name}>
                      {rec.station.name}
                    </h5>
                    <div className="text-[11px] text-slate-400 font-medium">Secteur {rec.station.district}</div>

                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                      <div className="flex items-center gap-1 font-semibold">
                        <Clock className="w-3 h-3 text-cyan-500" />
                        <span>~{rec.travelTimeMin} min</span>
                      </div>
                      <div className="flex items-center gap-1 font-semibold">
                        <Zap className="w-3 h-3 text-amber-500" />
                        <span>{rec.station.maxPowerKw} kW</span>
                      </div>
                    </div>

                    <div className={`mt-2.5 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border text-[10px] font-bold ${avail.color}`}>
                      <BatteryCharging className="w-3 h-3" />
                      <span>{rec.station.availablePiles} libre{rec.station.availablePiles > 1 ? 's' : ''}</span>
                    </div>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-100 flex gap-2">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(rec.station)}
                      className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] font-bold transition-colors cursor-pointer"
                    >
                      Détails
                    </button>
                    <button
                      type="button"
                      onClick={() => onNavigateToStation(rec.station)}
                      className="flex-1 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-[11px] font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <Navigation className="w-3 h-3" />
                      <span>Itinéraire</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 5. OPTIONAL COLLAPSIBLE ADVANCED MODE (Architecture Multi-Fog, Chronos-2, Scoring Weights) ── */}
      <div className="pt-2">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full flex items-center justify-between p-4 rounded-2xl bg-slate-100/80 hover:bg-slate-100 border border-slate-200 text-slate-600 text-xs font-bold transition-all cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-600" />
            <span>⚙️ Détails Techniques & Architecture Multi-Fog (Mode Expert)</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-400">
            <span>{showTechnicalDetails ? 'Masquer' : 'Déplier'}</span>
            {showTechnicalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </button>

        {showTechnicalDetails && (
          <div className="mt-3 p-5 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-5 animate-fadeIn">
            {/* Scénario 1 Architecture note */}
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-cyan-50/60 border border-cyan-100 text-xs text-cyan-900">
              <ShieldCheck className="w-4 h-4 text-cyan-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong>Isolation Architecturale S1 :</strong> Chaque Fog Node prend ses décisions localement à partir de sa propre base SQLite et de son modèle Chronos-2 dédié. Aucune communication inter-fog n'est déclenchée dans ce scénario.
              </div>
            </div>

            {/* 4 Technical Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Capacité Réelle</div>
                <div className="text-base font-black text-slate-900 mt-0.5">
                  {(currentCapacity?.total_piles || currentMeta?.total_piles || 0).toLocaleString()} bornes
                </div>
                <div className="text-[10px] text-slate-500">
                  ~{(currentCapacity?.available_piles || Math.floor((currentMeta?.total_piles || 0) * 0.78)).toLocaleString()} libres
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Chronos-2 Forecast</div>
                <div className="text-base font-black text-cyan-700 mt-0.5">
                  {currentForecast?.expectedOccupancyPercent || 25.0}%
                </div>
                <div className="text-[10px] text-slate-500">
                  q50: {currentForecast?.forecastBusyQ50 || 1400} (+1h)
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Stations Éligibles</div>
                <div className="text-base font-black text-slate-900 mt-0.5">
                  {recommendations.length} stations
                </div>
                <div className="text-[10px] text-slate-500">
                  sur {currentMeta?.total_stations || 524} dans {selectedFog}
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Précision ML (MAE)</div>
                <div className="text-base font-black text-slate-900 mt-0.5">
                  MAE: {currentMeta?.mae_chronos || 32.36}
                </div>
                <div className="text-[10px] text-slate-500">
                  Baseline: {currentMeta?.mae_baseline || 34.54}
                </div>
              </div>
            </div>

            {/* Scoring weights */}
            <div className="pt-3 border-t border-slate-100">
              <div className="flex items-center justify-between mb-3 text-xs font-bold text-slate-700">
                <div className="flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-cyan-600" />
                  <span>Pondérations du Moteur de Recommandation</span>
                </div>
                <button
                  onClick={handleResetFilters}
                  className="text-cyan-700 text-[11px] hover:underline cursor-pointer"
                >
                  Valeurs par défaut
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                  <div className="flex justify-between font-bold mb-1">
                    <span className="text-slate-600">Temps de Trajet</span>
                    <span className="text-slate-900">{Math.round(weights.travelTime * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    value={Math.round(weights.travelTime * 100)}
                    onChange={(e) => onWeightsChange({ ...weights, travelTime: Number(e.target.value) / 100 })}
                    className="w-full accent-cyan-600 cursor-pointer"
                  />
                </div>

                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                  <div className="flex justify-between font-bold mb-1">
                    <span className="text-slate-600">Occupation Prévue (IA)</span>
                    <span className="text-slate-900">{Math.round(weights.predictedOccupancy * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    value={Math.round(weights.predictedOccupancy * 100)}
                    onChange={(e) => onWeightsChange({ ...weights, predictedOccupancy: Number(e.target.value) / 100 })}
                    className="w-full accent-cyan-600 cursor-pointer"
                  />
                </div>

                <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                  <div className="flex justify-between font-bold mb-1">
                    <span className="text-slate-600">Temps d'Attente</span>
                    <span className="text-slate-900">{Math.round(weights.waitingTime * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="80"
                    value={Math.round(weights.waitingTime * 100)}
                    onChange={(e) => onWeightsChange({ ...weights, waitingTime: Number(e.target.value) / 100 })}
                    className="w-full accent-cyan-600 cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

    </section>
  );
};
