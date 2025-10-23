"use client";

import { motion } from "framer-motion";
import {
  Building,
  MapPin,
  Globe,
  ExternalLink,
  X,
  TrendingUp,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SubsidiaryDetail } from "@/lib/api";

// Type pour les présences commerciales
interface CommercialPresence {
  name: string;
  type: "office" | "partner" | "distributor" | "representative";
  relationship: "owned" | "partnership" | "authorized_distributor" | "franchise";
  activity?: string;
  location?: {
    city?: string;
    country?: string;
    phone?: string;
    email?: string;
  };
  confidence?: number;
  status?: "active" | "inactive" | "unverified";
}

interface SubsidiaryDetailPanelProps {
  subsidiary: SubsidiaryDetail | null;
  commercialPresence?: CommercialPresence | null;
  onClose: () => void;
}

export function SubsidiaryDetailPanel({
  subsidiary,
  commercialPresence,
  onClose,
}: SubsidiaryDetailPanelProps) {
  if (!subsidiary && !commercialPresence) return null;

  return (
    <motion.div
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -300, opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full max-w-sm"
    >
      <Card className="h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Building className={`w-5 h-5 ${subsidiary ? 'text-blue-600' : 'text-green-600'}`} />
              <div>
                <CardTitle className="text-lg">
                  {subsidiary?.legal_name || commercialPresence?.name}
                </CardTitle>
                <CardDescription className="text-sm">
                  {subsidiary ? '🏢 Filiale juridique' : '🏢 Présence commerciale'}
                </CardDescription>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Affichage conditionnel selon le type d'entité */}
          {subsidiary ? (
            // Affichage pour filiale juridique
            <>
              {/* Siège social */}
              {subsidiary.headquarters && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Siège social</span>
              </div>
              <div className="pl-6 space-y-1">
                {subsidiary.headquarters.line1 && (
                  <p className="text-sm text-gray-600">
                    {subsidiary.headquarters.line1}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  {subsidiary.headquarters.city && (
                    <span className="text-sm text-gray-600">
                      {subsidiary.headquarters.city}
                    </span>
                  )}
                </div>
                {subsidiary.headquarters.country && (
                  <p className="text-sm text-gray-600">
                    {subsidiary.headquarters.country}
                  </p>
                )}
                {subsidiary.headquarters.postal_code && (
                  <p className="text-sm text-gray-500">
                    {subsidiary.headquarters.postal_code}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Informations de contact */}
          {(subsidiary.headquarters?.phone || subsidiary.headquarters?.email) && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Contact</span>
              </div>
              <div className="pl-6 space-y-2">
                {subsidiary.headquarters.phone && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Téléphone:</span>
                    <a
                      href={`tel:${subsidiary.headquarters.phone}`}
                      className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {subsidiary.headquarters.phone}
                    </a>
                  </div>
                )}
                {subsidiary.headquarters.email && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Email:</span>
                    <a
                      href={`mailto:${subsidiary.headquarters.email}`}
                      className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {subsidiary.headquarters.email}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Type d'activité */}
          {subsidiary.activity && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Type d'activité</span>
              </div>
              <div className="pl-6">
                <Badge variant="secondary" className="text-xs">
                  {subsidiary.activity}
                </Badge>
              </div>
            </div>
          )}

          {/* Score de confiance */}
          {subsidiary.confidence && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Score de confiance</span>
              </div>
              <div className="pl-6">
                <Badge
                  variant={
                    subsidiary.confidence >= 0.8
                      ? "default"
                      : subsidiary.confidence >= 0.6
                      ? "secondary"
                      : "outline"
                  }
                  className="text-xs"
                >
                  {(subsidiary.confidence * 100).toFixed(0)}%
                </Badge>
              </div>
            </div>
          )}

          {/* Sources */}
          {subsidiary.sources && subsidiary.sources.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">Sources</span>
              </div>
              <div className="pl-6 space-y-2">
                {subsidiary.sources.slice(0, 3).map((source, index) => (
                  <div key={index} className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant={
                          source.tier === "official"
                            ? "default"
                            : source.tier === "financial_media"
                            ? "secondary"
                            : "outline"
                        }
                        className="text-xs"
                      >
                        {source.tier}
                      </Badge>
                    </div>
                    {source.url && (
                      <div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => window.open(source.url, "_blank")}
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          Ouvrir la source
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
                {subsidiary.sources.length > 3 && (
                  <p className="text-xs text-gray-500">
                    +{subsidiary.sources.length - 3} autres sources
                  </p>
                )}
              </div>
            </div>
          )}
            </>
          ) : (
            // Affichage pour présence commerciale
            <>
              {/* Type et relation */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium">Type</span>
                </div>
                <div className="pl-6">
                  <Badge variant="outline" className="text-xs">
                    {commercialPresence?.type}
                  </Badge>
                  <span className="ml-2 text-sm text-gray-600">
                    ({commercialPresence?.relationship})
                  </span>
                </div>
              </div>

              {/* Activité */}
              {commercialPresence?.activity && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium">Activité</span>
                  </div>
                  <div className="pl-6">
                    <p className="text-sm text-gray-600">
                      {commercialPresence.activity}
                    </p>
                  </div>
                </div>
              )}

              {/* Localisation */}
              {commercialPresence?.location && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium">Localisation</span>
                  </div>
                  <div className="pl-6 space-y-1">
                    {commercialPresence.location.city && (
                      <p className="text-sm text-gray-600">
                        {commercialPresence.location.city}
                        {commercialPresence.location.country && 
                          `, ${commercialPresence.location.country}`}
                      </p>
                    )}
                    {commercialPresence.location.phone && (
                      <p className="text-sm text-gray-600">
                        📞 {commercialPresence.location.phone}
                      </p>
                    )}
                    {commercialPresence.location.email && (
                      <p className="text-sm text-gray-600">
                        ✉️ {commercialPresence.location.email}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Statut */}
              {commercialPresence?.status && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Statut</span>
                  </div>
                  <div className="pl-6">
                    <Badge 
                      variant={commercialPresence.status === 'active' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {commercialPresence.status}
                    </Badge>
                  </div>
                </div>
              )}

              {/* Score de confiance */}
              {commercialPresence?.confidence && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Confiance</span>
                  </div>
                  <div className="pl-6">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-green-500 h-2 rounded-full" 
                          style={{ width: `${commercialPresence.confidence * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-600">
                        {Math.round(commercialPresence.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
