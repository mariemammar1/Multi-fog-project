import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import {
  Search,
  CheckCircle,
  Compass,
  Navigation,
  FileText,
  X,
  Zap,
  Clock,
  BatteryCharging
} from 'lucide-react';
import { Station, FogId, DriverLocation, TerritoryMeta } from '../types';
import { calculateDistanceKm, estimateTravelTimeMin } from '../services/recommendationEngine';

interface StationMapProps {
  stations: Station[];
  driverLocation: DriverLocation;
  selectedStation: Station | null;
  activeDestination: Station | null;
  onSelectStation: (station: Station) => void;
  onSetDestination: (station: Station) => void;
  onOpenDetails: (station: Station) => void;
  territoriesMeta: Record<FogId, TerritoryMeta>;
  recommendedStationId?: string;
}

export const StationMap: React.FC<StationMapProps> = ({
  stations,
  driverLocation,
  selectedStation,
  activeDestination,
  onSelectStation,
  onSetDestination,
  onOpenDetails,
  territoriesMeta,
  recommendedStationId,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const userMarkerRef = useRef<L.Marker | null>(null);
  const territoryCirclesRef = useRef<L.LayerGroup | null>(null);
  const routePolylineRef = useRef<L.Polyline | null>(null);

  // Local map filters
  const [fogFilter, setFogFilter] = useState<'ALL' | FogId>('ALL');
  const [powerFilter, setPowerFilter] = useState<'ALL' | 'FAST_DC' | 'SLOW_AC'>('ALL');
  const [onlyAvailable, setOnlyAvailable] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const territoryCenters: Record<FogId, { lat: number; lng: number; radiusM: number; color: string; label: string }> = {
    'fog-a': { lat: 22.5822, lng: 114.0469, radiusM: 11000, color: '#0284c7', label: 'Fog A - Territoire Central (Nanshan/Futian)' },
    'fog-b': { lat: 22.6346, lng: 114.1904, radiusM: 14000, color: '#16a34a', label: 'Fog B - Territoire Est (Luohu/Longgang)' },
    'fog-c': { lat: 22.6052, lng: 113.9028, radiusM: 15000, color: '#d97706', label: 'Fog C - Territoire Ouest (Bao\'an/Qianhai)' },
  };

  const displayedStations = stations.filter((station) => {
    if (fogFilter !== 'ALL' && station.fogId !== fogFilter) return false;
    if (onlyAvailable && station.availablePiles <= 0) return false;
    if (powerFilter === 'FAST_DC' && station.fastCount === 0) return false;
    if (powerFilter === 'SLOW_AC' && station.slowCount === 0) return false;
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      if (!station.id.toLowerCase().includes(q) && !station.name.toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  });

  // 1. Initialize Map once with CartoDB Voyager Light Basemap
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [22.60, 114.05],
      zoom: 11,
      minZoom: 9,
      maxZoom: 18,
      zoomControl: true,
      preferCanvas: true,
    });

    // CartoDB Voyager Light Basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    // Territory circles layer
    const territoryLayer = L.layerGroup().addTo(map);
    territoryCirclesRef.current = territoryLayer;

    Object.entries(territoryCenters).forEach(([fogKey, conf]) => {
      L.circle([conf.lat, conf.lng], {
        radius: conf.radiusM,
        color: conf.color,
        weight: 2,
        dashArray: '6, 8',
        fillColor: conf.color,
        fillOpacity: 0.05,
      })
        .bindTooltip(`<strong>${conf.label}</strong>`, { permanent: false, direction: 'top' })
        .addTo(territoryLayer);
    });

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Update User Location Marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
    }

    const userIcon = L.divIcon({
      className: 'driver-location-marker',
      html: `
        <div style="position: relative; width: 28px; height: 28px;">
          <div style="position: absolute; width: 28px; height: 28px; background: rgba(2, 132, 199, 0.25); border-radius: 50%; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
          <div style="position: absolute; top: 4px; left: 4px; width: 20px; height: 20px; background: #0284c7; border: 3px solid #ffffff; border-radius: 50%; box-shadow: 0 3px 8px rgba(0,0,0,0.25); display: flex; align-items: center; justify-content: center;">
            <div style="width: 6px; height: 6px; background: white; border-radius: 50%;"></div>
          </div>
        </div>
      `,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });

    const userMarker = L.marker([driverLocation.lat, driverLocation.lng], {
      icon: userIcon,
      zIndexOffset: 1000,
    })
      .bindPopup(
        `<div style="text-align: center; font-size: 12px; font-family: inherit;">
          <strong style="color: #0284c7; font-size: 13px;">Votre Position Actuelle</strong><br/>
          <span style="font-size: 11px; color: #64748b; font-weight: 500;">${driverLocation.label}</span>
        </div>`
      )
      .addTo(map);

    userMarkerRef.current = userMarker;
  }, [driverLocation]);

  // 3. Render Stations on Canvas Layer
  useEffect(() => {
    const markersLayer = markersLayerRef.current;
    const map = mapInstanceRef.current;
    if (!markersLayer || !map) return;

    markersLayer.clearLayers();

    displayedStations.forEach((station) => {
      const isTarget = activeDestination?.id === station.id;
      const isSelected = selectedStation?.id === station.id;
      const isTopRecommended = recommendedStationId === station.id;

      // Color coding
      let fillColor = '#10b981'; // Green (Available)
      if (station.availablePiles === 0) {
        fillColor = '#ef4444'; // Red (Occupied)
      } else if (station.availablePiles <= 2 && station.totalPiles > 3) {
        fillColor = '#f59e0b'; // Amber (Limited)
      }

      if (isTarget) {
        fillColor = '#059669'; // Emerald for active destination
      } else if (isTopRecommended) {
        fillColor = '#0284c7'; // Blue for Top Pick
      }

      const radius = isTarget || isTopRecommended ? 9 : isSelected ? 8 : station.fastCount > 0 ? 5.5 : 4.5;
      const weight = isTarget || isSelected || isTopRecommended ? 3 : 1;
      const strokeColor = isTarget ? '#10b981' : isTopRecommended ? '#0284c7' : isSelected ? '#38bdf8' : '#ffffff';

      const circle = L.circleMarker([station.lat, station.lng], {
        radius,
        fillColor,
        color: strokeColor,
        weight,
        opacity: 0.95,
        fillOpacity: isTarget || isSelected || isTopRecommended ? 0.95 : 0.8,
      });

      // Click immediately selects station in React state
      circle.on('click', () => {
        onSelectStation(station);
      });

      markersLayer.addLayer(circle);
    });
  }, [displayedStations, selectedStation, activeDestination, recommendedStationId, onSelectStation]);

  // 4. Update Route Line between User and Target/Selected Station
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (routePolylineRef.current) {
      routePolylineRef.current.remove();
      routePolylineRef.current = null;
    }

    const target = activeDestination || selectedStation;
    if (target) {
      const points: [number, number][] = [
        [driverLocation.lat, driverLocation.lng],
        [target.lat, target.lng],
      ];

      const polyline = L.polyline(points, {
        color: activeDestination ? '#10b981' : '#0284c7',
        weight: 3.5,
        dashArray: '8, 8',
        opacity: 0.85,
      }).addTo(map);

      routePolylineRef.current = polyline;
    }
  }, [driverLocation, selectedStation, activeDestination]);

  // 5. Fly to selected station
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedStation) return;

    map.flyTo([selectedStation.lat, selectedStation.lng], 14, {
      duration: 1.0,
    });
  }, [selectedStation]);

  const zoomToFog = (fogId: FogId) => {
    const map = mapInstanceRef.current;
    if (!map) return;
    const center = territoryCenters[fogId];
    map.flyTo([center.lat, center.lng], 12, { duration: 0.8 });
    setFogFilter(fogId);
  };

  const resetView = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.flyTo([22.60, 114.05], 11, { duration: 0.8 });
    setFogFilter('ALL');
  };

  // Compute distance for active card
  const focusStation = selectedStation || activeDestination;
  const distKm = focusStation
    ? calculateDistanceKm(driverLocation.lat, driverLocation.lng, focusStation.lat, focusStation.lng)
    : 0;
  const transitMin = estimateTravelTimeMin(distKm);

  return (
    <div className="bg-white rounded-3xl border border-slate-200 shadow-card overflow-hidden flex flex-col">
      {/* Map Header Toolbar */}
      <div className="p-4 border-b border-slate-100 bg-white flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
            <Compass className="w-5 h-5 text-cyan-600" />
            Carte Interactive Multi-Fog
            <span className="text-xs font-semibold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
              {displayedStations.length} / {stations.length}
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 font-medium">
            Cliquez sur un marqueur pour sélectionner · Utilisez les boutons pour filtrer par secteur
          </p>
        </div>

        {/* Quick Fog Navigation */}
        <div className="flex items-center gap-1.5 text-xs flex-wrap">
          <span className="text-slate-400 font-semibold hidden sm:inline">Focus :</span>
          {([
            { id: 'fog-a', label: 'Fog A', activeClass: 'bg-sky-50 text-sky-700 border-sky-300' },
            { id: 'fog-b', label: 'Fog B', activeClass: 'bg-emerald-50 text-emerald-700 border-emerald-300' },
            { id: 'fog-c', label: 'Fog C', activeClass: 'bg-amber-50 text-amber-700 border-amber-300' },
          ] as const).map(({ id, label, activeClass }) => (
            <button
              key={id}
              type="button"
              onClick={() => zoomToFog(id)}
              className={`px-3 py-1.5 rounded-xl font-bold border transition-colors cursor-pointer ${
                fogFilter === id ? activeClass : 'bg-slate-50 text-slate-600 border-slate-200 hover:border-slate-300 hover:text-slate-900'
              }`}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={resetView}
            className="px-3 py-1.5 rounded-xl bg-slate-50 text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 font-bold transition-colors cursor-pointer"
          >
            Tout voir
          </button>
        </div>
      </div>

      {/* Filter Row */}
      <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2.5 text-xs">
        {/* Search Input */}
        <div className="relative flex-grow max-w-xs">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Rechercher par identifiant de station..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 font-medium"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={powerFilter}
            onChange={(e) => setPowerFilter(e.target.value as any)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-700 font-semibold focus:outline-none"
          >
            <option value="ALL">Toutes puissances</option>
            <option value="FAST_DC">Recharge Rapide DC</option>
            <option value="SLOW_AC">Recharge Normale AC</option>
          </select>

          <button
            onClick={() => setOnlyAvailable(!onlyAvailable)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border font-bold transition-colors ${
              onlyAvailable
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-xs'
                : 'bg-white text-slate-600 border-slate-200 hover:text-slate-900'
            }`}
          >
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            <span>Bornes Libres Uniquement</span>
          </button>
        </div>

        {/* Map Legend */}
        <div className="flex items-center space-x-3 text-[11px] text-slate-600 ml-auto font-semibold">
          <span className="flex items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1 border border-white shadow-xs" />
            Disponible
          </span>
          <span className="flex items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1 border border-white shadow-xs" />
            Limité
          </span>
          <span className="flex items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1 border border-white shadow-xs" />
            Occupé
          </span>
          <span className="flex items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-600 ring-2 ring-cyan-200 mr-1" />
            Candidat n°1
          </span>
        </div>
      </div>

      {/* Map DOM Container */}
      <div className="relative w-full h-[560px] bg-slate-100">
        <div ref={mapContainerRef} className="w-full h-full z-10" />

        {/* Bottom Floating Interactive Card */}
        {focusStation && (
          <div className="absolute bottom-4 left-4 z-20 bg-white/97 backdrop-blur-md p-4 rounded-2xl border border-slate-200 shadow-xl max-w-sm w-[calc(100%-2rem)] sm:w-auto sm:max-w-md animate-slideUp">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-black uppercase tracking-widest text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded-full border border-cyan-200">
                    Station Sélectionnée
                  </span>
                  <span className="text-xs font-bold text-slate-400">{focusStation.fogName}</span>
                </div>
                <h4 className="text-base font-extrabold text-slate-900 mt-1 truncate">{focusStation.name}</h4>
                <p className="text-xs text-slate-400 font-medium mt-0.5">
                  Zone TAZ #{focusStation.tazId} · Secteur {focusStation.district}
                </p>
              </div>

              <button
                type="button"
                onClick={() => onSelectStation(null as any)}
                className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Masquer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Metrics */}
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-100 text-xs">
              <div className="bg-slate-50 p-2.5 rounded-xl text-center border border-slate-100">
                <span className="text-[10px] text-slate-400 block font-semibold">Trajet</span>
                <strong className="text-slate-900 text-sm font-extrabold">~{transitMin} min</strong>
                <span className="text-[10px] text-slate-400 block">{distKm} km</span>
              </div>
              <div className={`p-2.5 rounded-xl text-center border ${focusStation.availablePiles > 0 ? 'bg-emerald-50 border-emerald-100' : 'bg-rose-50 border-rose-100'}`}>
                <span className={`text-[10px] block font-semibold ${focusStation.availablePiles > 0 ? 'text-emerald-600' : 'text-rose-500'}`}>Libres</span>
                <strong className={`text-sm font-extrabold ${focusStation.availablePiles > 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
                  {focusStation.availablePiles}/{focusStation.totalPiles}
                </strong>
                <span className={`text-[10px] block ${focusStation.availablePiles > 0 ? 'text-emerald-500' : 'text-rose-400'}`}>bornes</span>
              </div>
              <div className="bg-amber-50 p-2.5 rounded-xl text-center border border-amber-100">
                <span className="text-[10px] text-amber-600 block font-semibold">Puissance</span>
                <strong className="text-amber-700 text-sm font-extrabold">{focusStation.maxPowerKw} kW</strong>
                <span className="text-[10px] text-amber-500 block">
                  {focusStation.fastCount > 0 ? 'DC Rapide' : 'AC'}
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-3.5 pt-3 border-t border-slate-100 flex items-center gap-2">
              <button
                type="button"
                onClick={() => onSetDestination(focusStation)}
                className={`flex-1 py-2.5 px-3 rounded-xl font-extrabold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  activeDestination?.id === focusStation.id
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-glow-emerald'
                    : 'bg-cyan-600 hover:bg-cyan-700 text-white'
                }`}
              >
                <Navigation className="w-3.5 h-3.5" />
                {activeDestination?.id === focusStation.id ? '✓ Destination confirmée' : 'Définir comme cible'}
              </button>

              <button
                type="button"
                onClick={() => onOpenDetails(focusStation)}
                className="py-2.5 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs border border-slate-200 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5" />
                Détails
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
