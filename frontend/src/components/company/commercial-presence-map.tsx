"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Building2, Users, TruckIcon, UserCheck, Home } from "lucide-react";
import type { CommercialPresence } from "@/lib/api";

interface CommercialPresenceMapProps {
  presences: CommercialPresence[];
  headquartersCity?: string;
  headquartersCountry?: string;
}

const TYPE_ICONS = {
  office: Building2,
  partner: Users,
  distributor: TruckIcon,
  representative: UserCheck,
};

const TYPE_LABELS = {
  office: "Bureau commercial",
  partner: "Partenaire",
  distributor: "Distributeur",
  representative: "Représentant",
};

const TYPE_COLORS = {
  office: "text-blue-600",
  partner: "text-green-600",
  distributor: "text-orange-600",
  representative: "text-purple-600",
};

const TYPE_BG_COLORS = {
  office: "bg-blue-100",
  partner: "bg-green-100",
  distributor: "bg-orange-100",
  representative: "bg-purple-100",
};

export function CommercialPresenceMap({ presences, headquartersCity, headquartersCountry }: CommercialPresenceMapProps) {
  if (!presences || presences.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Présence commerciale</h3>
        <p className="text-sm text-gray-500">
          Aucune présence commerciale à cartographier
        </p>
      </Card>
    );
  }

  // Grouper par pays
  const byCountry = presences.reduce((acc, presence) => {
    const country = presence.location.country || "Inconnu";
    if (!acc[country]) {
      acc[country] = [];
    }
    acc[country].push(presence);
    return acc;
  }, {} as Record<string, CommercialPresence[]>);

  // Ajouter le siège social s'il est fourni
  const headquartersCountryName = headquartersCountry || "";
  const byCountryWithHQ = { ...byCountry };

  if (headquartersCountryName && !byCountryWithHQ[headquartersCountryName]) {
    byCountryWithHQ[headquartersCountryName] = [];
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Carte mondiale des présences commerciales</h3>

      {/* Légende */}
      <div className="mb-6">
        <h4 className="text-sm font-medium mb-3">Légende</h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center gap-2">
            <Home className="h-4 w-4 text-red-600" />
            <span className="text-xs">Siège social</span>
          </div>
          {Object.entries(TYPE_ICONS).map(([type, Icon]) => (
            <div key={type} className="flex items-center gap-2">
              <Icon className={`h-4 w-4 ${TYPE_COLORS[type as keyof typeof TYPE_COLORS]}`} />
              <span className="text-xs">{TYPE_LABELS[type as keyof typeof TYPE_LABELS]}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Couverture par pays */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Présence par pays</h4>
        {Object.entries(byCountryWithHQ)
          .sort(([, a], [, b]) => b.length - a.length)
          .map(([country, items]) => {
            const isHeadquartersCountry = country === headquartersCountryName;
            const hasHeadquarters = isHeadquartersCountry && headquartersCity;
            const totalItems = items.length + (hasHeadquarters ? 1 : 0);

            return (
              <div key={country} className="border-b pb-3 last:border-b-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-gray-500" />
                    <span className="font-medium">{country}</span>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {totalItems} site{totalItems > 1 ? 's' : ''}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 gap-2">
                  {/* Afficher le siège social en premier s'il est dans ce pays */}
                  {hasHeadquarters && (
                    <div className="flex items-center justify-between p-2 bg-red-50 rounded text-xs border border-red-200">
                      <div className="flex items-center gap-2">
                        <Home className="h-3 w-3 text-red-600" />
                        <span className="font-medium">Siège social</span>
                        <span className="text-gray-500">•</span>
                        <span className="text-gray-600">{headquartersCity}</span>
                      </div>
                      <Badge variant="outline" className="text-xs px-1 py-0 border-red-300 text-red-700">
                        Siège
                      </Badge>
                    </div>
                  )}

                  {items.map((presence, idx) => {
                    const Icon = TYPE_ICONS[presence.type];
                    const colorClass = TYPE_COLORS[presence.type as keyof typeof TYPE_COLORS];
                    const bgClass = TYPE_BG_COLORS[presence.type as keyof typeof TYPE_BG_COLORS];

                    return (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-2 ${bgClass} rounded text-xs`}
                      >
                        <div className="flex items-center gap-2">
                          <Icon className={`h-3 w-3 ${colorClass}`} />
                          <span className="font-medium">{presence.name}</span>
                          <span className="text-gray-500">•</span>
                          <span className="text-gray-600">{presence.location.city}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="outline"
                            className="text-xs px-1 py-0"
                          >
                            {TYPE_LABELS[presence.type]}
                          </Badge>
                          {presence.confidence && (
                            <span className="text-gray-500">
                              {Math.round(presence.confidence * 100)}%
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
      </div>

      {/* Résumé */}
      <div className="mt-6 pt-4 border-t">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Total présences commerciales</span>
          <span className="font-semibold">{presences.length} sites</span>
        </div>
        <div className="flex items-center justify-between text-sm mt-1">
          <span className="text-gray-600">Pays couverts</span>
          <span className="font-semibold">{Object.keys(byCountry).length} pays</span>
        </div>
      </div>
    </Card>
  );
}
