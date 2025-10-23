"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapPin, Building2, Users, TruckIcon, UserCheck, Phone, Mail } from "lucide-react";
import type { CommercialPresence } from "@/lib/api";

interface CommercialPresenceListProps {
  presences: CommercialPresence[];
  onPresenceSelect?: (presence: CommercialPresence) => void;
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

const RELATIONSHIP_LABELS = {
  owned: "Propriété",
  partnership: "Partenariat",
  authorized_distributor: "Distributeur autorisé",
  franchise: "Franchise",
};

const STATUS_COLORS = {
  active: "default",
  inactive: "secondary",
  unverified: "outline",
} as const;

export function CommercialPresenceList({
  presences,
  onPresenceSelect,
}: CommercialPresenceListProps) {
  if (!presences || presences.length === 0) {
    return (
      <Card className="p-6">
        <p className="text-sm text-gray-500">
          Aucune présence commerciale identifiée
        </p>
      </Card>
    );
  }

  // Grouper par type
  const groupedByType = presences.reduce((acc, presence) => {
    if (!acc[presence.type]) {
      acc[presence.type] = [];
    }
    acc[presence.type].push(presence);
    return acc;
  }, {} as Record<string, CommercialPresence[]>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Présence commerciale</h3>
        <Badge variant="secondary">{presences.length} sites</Badge>
      </div>

      {Object.entries(groupedByType).map(([type, items]) => {
        const Icon = TYPE_ICONS[type as keyof typeof TYPE_ICONS];
        return (
          <Card key={type} className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <Icon className="h-5 w-5 text-blue-600" />
              <h4 className="font-medium">
                {TYPE_LABELS[type as keyof typeof TYPE_LABELS]}
              </h4>
              <Badge variant="outline">{items.length}</Badge>
            </div>

            <div className="space-y-3">
              {items.map((presence, idx) => (
                <div
                  key={idx}
                  className="border-l-2 border-blue-200 pl-3 hover:border-blue-400 transition-colors cursor-pointer"
                  onClick={() => onPresenceSelect?.(presence)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{presence.name}</p>
                      <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
                        <MapPin className="h-3 w-3" />
                        <span>
                          {presence.location.city}, {presence.location.country}
                        </span>
                      </div>
                      
                      {presence.activity && (
                        <p className="text-xs text-gray-500 mt-1">
                          {presence.activity}
                        </p>
                      )}

                      {/* Relation */}
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">
                          {RELATIONSHIP_LABELS[presence.relationship as keyof typeof RELATIONSHIP_LABELS]}
                        </Badge>
                        {presence.since_year && (
                          <span className="text-xs text-gray-500">
                            Depuis {presence.since_year}
                          </span>
                        )}
                      </div>

                      {/* Contacts */}
                      {(presence.phone || presence.email || presence.location.phone || presence.location.email) && (
                        <div className="flex items-center gap-3 mt-2">
                          {(presence.phone || presence.location.phone) && (
                            <a
                              href={`tel:${presence.phone || presence.location.phone}`}
                              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Phone className="h-3 w-3" />
                              <span>{presence.phone || presence.location.phone}</span>
                            </a>
                          )}
                          {(presence.email || presence.location.email) && (
                            <a
                              href={`mailto:${presence.email || presence.location.email}`}
                              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Mail className="h-3 w-3" />
                              <span>{presence.email || presence.location.email}</span>
                            </a>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col items-end gap-1">
                      <Badge
                        variant={STATUS_COLORS[presence.status as keyof typeof STATUS_COLORS] || "outline"}
                        className="text-xs"
                      >
                        {presence.status === "active" ? "Actif" : 
                         presence.status === "inactive" ? "Inactif" : 
                         "Non vérifié"}
                      </Badge>
                      {presence.confidence && (
                        <span className="text-xs text-gray-500">
                          {Math.round(presence.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Sources */}
                  {presence.sources && presence.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100">
                      <div className="flex items-center gap-2 flex-wrap">
                        {presence.sources.slice(0, 2).map((source, sourceIdx) => (
                          <Button
                            key={sourceIdx}
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(source.url, '_blank');
                            }}
                          >
                            Voir la source
                          </Button>
                        ))}
                        {presence.sources.length > 2 && (
                          <span className="text-xs text-gray-500">
                            +{presence.sources.length - 2} sources
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
