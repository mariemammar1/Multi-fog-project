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
  TrendingDown,
  Star,
} from 'lucide-react';
import {
  Recommendation,
  ScoringWeights,
  UserPreferences,
  Station,
} from '../types';

interface RecommendationSectionProps {
  recommendations: Recommendation[];
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
  recommendations,
  weights,
  onWeightsChange,
  preferences,
  onPreferencesChange,
  onOpenDetails,
  onNavigateToStation,
  activeDestinationId,
  filtersOpen,
  onToggleFilters,
  onShowToast,
}) => {
  const [showAllAlternatives, setShowAllAlternatives] = useState<boolean>(false);

  const topPick = recommendations[0];
  const alternatives = showAllAlternatives
    ? recommendations.slice(1, 7)
    : recommendations.slice(1, 4);

  const handleResetFilters = () => {
    onWeightsChange({ travelTime: 0.45, predictedOccupancy: 0.35, waitingTime: 0.20 });
    onPreferencesChange({
      vehicleType: 'ALL',
      minPowerKw: 0,
      maxDistanceKm: 25,
      selectedFog: 'ALL',
      onlyAvailable: true,
    });
    onShowToast('Filtres Réinitialisés', 'Paramètres par défaut appliqués.', 'info');
  };

  /* ── Helpers ── */
  const scoreColor = (score: number) => {
    if (score >= 85) return 'text-emerald-600';
    if (score >= 65) return 'text-amber-500';
    return 'text-rose-500';
  };

  const availLabel = (avail: number, total: number) => {
    const pct = total > 0 ? avail / total : 0;
    if (pct >= 0.6) return { text: 'Très disponible', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' };
    if (pct >= 0.3) return { text: 'Disponibilité modérée', color: 'text-amber-600 bg-amber-50 border-amber-200' };
    if (avail > 0)  return { text: 'Presque complet', color: 'text-orange-600 bg-orange-50 border-orange-200' };
    return { text: 'Complet', color: 'text-rose-600 bg-rose-50 border-rose-200' };
  };

  return (
    <section className="space-y-5">

      {/* ── Section Header ── */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-700 text-xs font-bold mb-2">
            <Sparkles className="w-3.5 h-3.5 text-cyan-500" />
            <span>Recommandation en temps réel</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight leading-none">
            Où charger maintenant ?
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">
            {recommendations.length} station{recommendations.length !== 1 ? 's' : ''} analysée{recommendations.length !== 1 ? 's' : ''} dans votre rayon
          </p>
        </div>

        <button
          onClick={onToggleFilters}
          aria-label="Filtres et préférences"
          className={`flex-shrink-0 flex items-center gap-1.5 px-3.5 py-2.5 rounded-2xl text-xs font-bold border transition-all cursor-pointer ${
            filtersOpen
              ? 'bg-cyan-600 text-white border-cyan-600 shadow-sm'
              : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200 hover:border-slate-300'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Filtres</span>
        </button>
      </div>

      {/* ── Filters Drawer ── */}
      {filtersOpen && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-cyan-600" />
              Personnaliser vos critères
            </span>
            <button
              onClick={handleResetFilters}
              className="text-xs text-cyan-700 font-bold hover:underline px-2.5 py-1 bg-cyan-50 rounded-lg border border-cyan-200 cursor-pointer"
            >
              Réinitialiser
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              {
                label: 'Vitesse de recharge',
                value: preferences.vehicleType,
                onChange: (v: string) => onPreferencesChange({ ...preferences, vehicleType: v as any }),
                options: [
                  { value: 'ALL', label: 'Toutes vitesses (AC + DC)' },
                  { value: 'DC_FAST', label: '⚡ Recharge Rapide DC (>30 kW)' },
                  { value: 'AC_SLOW', label: 'Recharge Normale AC (≤22 kW)' },
                ],
              },
              {
                label: 'Puissance minimale',
                value: String(preferences.minPowerKw),
                onChange: (v: string) => onPreferencesChange({ ...preferences, minPowerKw: parseInt(v) }),
                options: [
                  { value: '0', label: 'Toutes puissances' },
                  { value: '50', label: 'Au moins 50 kW' },
                  { value: '120', label: 'Au moins 120 kW' },
                ],
              },
              {
                label: 'Distance maximale',
                value: String(preferences.maxDistanceKm),
                onChange: (v: string) => onPreferencesChange({ ...preferences, maxDistanceKm: parseInt(v) }),
                options: [
                  { value: '5', label: 'Rayon 5 km' },
                  { value: '10', label: 'Rayon 10 km' },
                  { value: '25', label: 'Rayon 25 km' },
                  { value: '50', label: 'Rayon 50 km' },
                ],
              },
              {
                label: 'Secteur territorial',
                value: preferences.selectedFog,
                onChange: (v: string) => onPreferencesChange({ ...preferences, selectedFog: v as any }),
                options: [
                  { value: 'ALL', label: 'Tous les secteurs' },
                  { value: 'fog-a', label: 'Fog A — Centre (Nanshan)' },
                  { value: 'fog-b', label: 'Fog B — Est (Luohu)' },
                  { value: 'fog-c', label: 'Fog C — Ouest (Bao\'an)' },
                ],
              },
            ].map(({ label, value, onChange, options }) => (
              <div key={label}>
                <label className="block text-[11px] font-bold text-slate-500 mb-1 uppercase tracking-wider">{label}</label>
                <select
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  {options.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── TOP PICK HERO CARD ── */}
      {topPick ? (
        <div
          className={`rounded-3xl border transition-all relative overflow-hidden ${
            activeDestinationId === topPick.station.id
              ? 'bg-gradient-to-br from-emerald-50 via-white to-cyan-50/40 border-emerald-300 ring-2 ring-emerald-100 shadow-glow-emerald'
              : 'bg-white border-slate-200 hover:border-slate-300 shadow-card hover:shadow-card-hover'
          }`}
        >
          {/* Top decorative accent */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-emerald-500 to-teal-500 rounded-t-3xl" />

          <div className="p-6 sm:p-8">
            {/* Badges row */}
            <div className="flex flex-wrap items-center gap-2 mb-5">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-emerald-600 text-white text-xs font-black tracking-wide uppercase shadow-sm">
                <Star className="w-3.5 h-3.5" />
                Option n°1 Conseillée
              </span>
              <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
                {topPick.station.fogName}
              </span>
              {activeDestinationId === topPick.station.id && (
                <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Itinéraire actif
                </span>
              )}
              <span className={`ml-auto text-sm font-black ${scoreColor(topPick.compositeScore)}`}>
                Score {topPick.compositeScore}%
              </span>
            </div>

            {/* Station name */}
            <h3 className="text-2xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight">
              {topPick.station.name}
            </h3>
            <p className="flex items-center gap-1.5 text-sm text-slate-500 font-medium mt-2">
              <MapPin className="w-4 h-4 text-cyan-500 flex-shrink-0" />
              Secteur {topPick.station.district} · Station #{topPick.station.id}
            </p>

            {/* Three key metrics */}
            <div className="grid grid-cols-3 gap-3 mt-6">
              {/* Travel */}
              <div className="bg-slate-50 rounded-2xl p-4 text-center border border-slate-200">
                <div className="flex items-center justify-center gap-1 text-[11px] text-slate-500 font-bold mb-2">
                  <Clock className="w-3.5 h-3.5 text-cyan-500" /> Trajet
                </div>
                <div className="text-3xl font-black text-slate-900 leading-none">
                  {topPick.travelTimeMin}
                </div>
                <div className="text-xs text-slate-400 font-semibold mt-1">min · {topPick.distanceKm} km</div>
              </div>

              {/* Piles */}
              <div className="bg-emerald-50 rounded-2xl p-4 text-center border border-emerald-200">
                <div className="flex items-center justify-center gap-1 text-[11px] text-emerald-700 font-bold mb-2">
                  <BatteryCharging className="w-3.5 h-3.5 text-emerald-600" /> Libres
                </div>
                <div className="text-3xl font-black text-emerald-700 leading-none">
                  {topPick.station.availablePiles}
                </div>
                <div className="text-xs text-emerald-600 font-semibold mt-1">/ {topPick.station.totalPiles} bornes</div>
              </div>

              {/* Power */}
              <div className="bg-amber-50 rounded-2xl p-4 text-center border border-amber-200">
                <div className="flex items-center justify-center gap-1 text-[11px] text-amber-700 font-bold mb-2">
                  <Zap className="w-3.5 h-3.5 text-amber-500" /> Puissance
                </div>
                <div className="text-3xl font-black text-amber-700 leading-none">
                  {topPick.station.maxPowerKw}
                </div>
                <div className="text-xs text-amber-600 font-semibold mt-1">
                  kW · {topPick.station.fastCount > 0 ? 'DC Rapide' : 'AC Standard'}
                </div>
              </div>
            </div>

            {/* Explanation */}
            <div className="mt-5 flex items-start gap-3 p-4 rounded-2xl bg-slate-50 border border-slate-200">
              <TrendingDown className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-slate-700 font-medium leading-relaxed">{topPick.explanation}</p>
            </div>

            {/* Action buttons */}
            <div className="mt-6 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
              <button
                type="button"
                onClick={() => onNavigateToStation(topPick.station)}
                className="flex-1 flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-black text-sm shadow-glow-emerald transition-all cursor-pointer hover:shadow-lg active:scale-[0.98]"
              >
                <Navigation className="w-4 h-4" />
                Y aller · Voir l'itinéraire
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                type="button"
                onClick={() => onOpenDetails(topPick.station)}
                className="sm:w-auto px-5 py-4 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-sm border border-slate-200 hover:border-slate-300 transition-colors cursor-pointer"
              >
                Fiche détaillée
              </button>
            </div>

            {/* Live indicator */}
            <div className="mt-4 flex items-center gap-2 text-xs text-slate-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
              Calculé en temps réel sur {recommendations.length} stations disponibles
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white p-10 rounded-3xl border border-slate-200 text-center shadow-card">
          <ShieldAlert className="w-10 h-10 text-amber-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-900">Aucune station dans ce rayon</h3>
          <p className="text-sm text-slate-500 mt-1">Ajustez vos filtres pour voir plus de bornes disponibles.</p>
          <button
            onClick={handleResetFilters}
            className="mt-4 px-5 py-2.5 rounded-xl bg-cyan-600 text-white text-sm font-bold hover:bg-cyan-700 transition-colors cursor-pointer"
          >
            Réinitialiser les filtres
          </button>
        </div>
      )}

      {/* ── Alternatives ── */}
      {alternatives.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between pt-1">
            <h4 className="text-base font-black text-slate-900 flex items-center gap-2">
              Autres bonnes options
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-500">
                {recommendations.length - 1}
              </span>
            </h4>
            {recommendations.length > 4 && (
              <button
                onClick={() => setShowAllAlternatives(!showAllAlternatives)}
                className="flex items-center gap-1.5 text-xs font-bold text-cyan-700 hover:text-cyan-900 cursor-pointer"
              >
                {showAllAlternatives ? (
                  <><ChevronUp className="w-3.5 h-3.5" /> Réduire</>
                ) : (
                  <><ChevronDown className="w-3.5 h-3.5" /> Voir plus</>
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
                  className={`bg-white rounded-2xl border p-4 flex flex-col justify-between transition-all shadow-card hover:shadow-card-hover hover:-translate-y-0.5 ${
                    isActive
                      ? 'border-emerald-400 ring-2 ring-emerald-100'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  {/* Header */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="px-2 py-0.5 rounded-lg bg-slate-100 text-[10px] font-black text-slate-600">
                        #{rec.rank}
                      </span>
                      <span className={`text-sm font-black ${scoreColor(rec.compositeScore)}`}>
                        {rec.compositeScore}%
                      </span>
                    </div>

                    <h5 className="text-sm font-extrabold text-slate-900 truncate leading-tight" title={rec.station.name}>
                      {rec.station.name}
                    </h5>
                    <p className="text-[11px] text-slate-400 font-medium mt-0.5">{rec.station.fogName}</p>

                    {/* Quick stats */}
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                      <div className="flex items-center gap-1 text-slate-600">
                        <Clock className="w-3 h-3 text-cyan-500" />
                        <span className="font-bold">~{rec.travelTimeMin} min</span>
                        <span className="text-slate-400">{rec.distanceKm} km</span>
                      </div>
                      <div className="flex items-center gap-1 text-slate-600">
                        <Zap className="w-3 h-3 text-amber-500" />
                        <span className="font-bold">{rec.station.maxPowerKw} kW</span>
                      </div>
                    </div>

                    <div className={`mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border text-[10px] font-bold ${avail.color}`}>
                      <BatteryCharging className="w-3 h-3" />
                      {rec.station.availablePiles} libre{rec.station.availablePiles !== 1 ? 's' : ''} · {avail.text}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-3 pt-3 border-t border-slate-100 flex gap-2">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(rec.station)}
                      className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] font-bold transition-colors cursor-pointer flex-shrink-0"
                    >
                      Détails
                    </button>
                    <button
                      type="button"
                      onClick={() => onNavigateToStation(rec.station)}
                      className="flex-1 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-[11px] font-bold transition-colors flex items-center justify-center gap-1 cursor-pointer"
                    >
                      <Navigation className="w-3 h-3" />
                      Itinéraire
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
};
