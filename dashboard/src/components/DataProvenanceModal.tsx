import React, { useEffect } from 'react';
import {
  X,
  ShieldCheck,
  Cpu,
  Database,
  Layers,
  Zap,
  CheckCircle2
} from 'lucide-react';

interface DataProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataProvenanceModal: React.FC<DataProvenanceModalProps> = ({
  isOpen,
  onClose,
}) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white border border-slate-200 rounded-3xl max-w-2xl w-full p-6 sm:p-7 shadow-2xl relative overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Close Button X */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          aria-label="Fermer"
          className="absolute top-5 right-5 p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-900 transition-colors cursor-pointer z-20"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="pr-12">
          <div className="flex items-center space-x-2 text-cyan-700 text-xs font-bold uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-cyan-600" />
            <span>Architecture & Transparence des Données</span>
          </div>
          <h3 className="text-xl font-extrabold text-slate-900 mt-1">
            Provenance des Données & Fonctionnement du Système
          </h3>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Explication détaillée des sources de données réelles, prédictions et garanties techniques.
          </p>
        </div>

        {/* Matrix Grid */}
        <div className="mt-6 space-y-4 text-xs">
          {/* 1. Real SQLite Database Telemetry */}
          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-emerald-900 flex items-center">
                <Database className="w-4 h-4 mr-1.5 text-emerald-600" />
                1. Bases de données locales SQLite (Fog A, Fog B, Fog C)
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                DONNÉES RÉELLES
              </span>
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed font-medium">
              Contient <strong>1 635 stations de recharge</strong> avec leurs coordonnées réelles WGS-84 et <strong>22 138 bornes</strong> avec puissances nominales réelles (3.5 kW à 360 kW DC).
            </p>
          </div>

          {/* 2. Chronos-2 Forecasting Model */}
          <div className="p-4 rounded-2xl bg-sky-50/70 border border-sky-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sky-900 flex items-center">
                <Cpu className="w-4 h-4 mr-1.5 text-cyan-600" />
                2. Modèle d'IA Amazon Chronos-2
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-300">
                INFÉRENCE TEMPS RÉEL
              </span>
            </div>
            <p className="text-[11px] text-slate-700 leading-relaxed font-medium">
              Prédit le volume d'occupation global du secteur à +1 heure pour orienter le conducteur vers des zones où le réseau n'est pas saturé.
            </p>
          </div>

          {/* 3. Scope Restrictions Confirmation */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center space-x-2 text-slate-900 font-bold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Garanties DevOps & Mode Lecture Seule</span>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
              Le frontend fonctionne en lecture seule stricte sans altérer les protocoles Fog-to-Fog ou les réservations en base de données.
            </p>
          </div>
        </div>

        {/* Modal Action Footer */}
        <div className="mt-6 pt-4 border-t border-slate-200 flex justify-end">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors cursor-pointer"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
};
