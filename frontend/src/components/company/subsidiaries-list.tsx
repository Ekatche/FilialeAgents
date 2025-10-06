"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building,
  MapPin,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  ExternalLink,
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
import { SiteInfo, SubsidiaryDetail } from "@/lib/api";
import { getConfidenceColor, getConfidenceLabel } from "@/lib/utils";

interface SubsidiariesListProps {
  subsidiaries: SubsidiaryDetail[];
  totalCount: number;
}

interface SubsidiaryCardProps {
  subsidiary: SubsidiaryDetail;
  index: number;
}

function SubsidiaryCard({ subsidiary, index }: SubsidiaryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        delay: index * 0.1,
        duration: 0.5,
      },
    },
  };

  const renderSite = (site: SiteInfo, siteIdx: number) => {
    const addressParts = [site.line1, site.city, site.country]
      .filter(Boolean)
      .join(", ");

    return (
      <div key={siteIdx} className="border rounded-md p-3 space-y-1 text-sm">
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">
            {site.label || `Implantation ${siteIdx + 1}`}
          </span>
          {(site.phone || site.email || site.website) && (
            <div className="flex gap-2 text-xs text-blue-600">
              {site.phone && <span>{site.phone}</span>}
              {site.email && (
                <a href={`mailto:${site.email}`} className="underline">
                  {site.email}
                </a>
              )}
              {site.website && (
                <a
                  href={site.website}
                  target="_blank"
                  rel="noreferrer"
                  className="underline"
                >
                  Site web
                </a>
              )}
            </div>
          )}
        </div>
        <p className="text-muted-foreground text-xs">
          {addressParts || "Adresse non renseignée"}
        </p>
      </div>
    );
  };

  return (
    <motion.div variants={cardVariants} initial="hidden" animate="visible">
      <Card
         id={`subsidiary-${subsidiary.legal_name.replace(/\s+/g, "-")}`}
        className="hover-lift cursor-pointer transition-all duration-300 hover:shadow-lg"
      >
        <CardHeader className="pb-3" onClick={() => setIsExpanded(!isExpanded)}>
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-600" />
                <CardTitle className="text-xl">
                  {subsidiary.legal_name}
                </CardTitle>
                <Button variant="ghost" size="sm" className="ml-auto p-1">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <CardDescription className="text-base">
                {subsidiary.activity || "Activité non spécifiée"}
              </CardDescription>
              <div className="flex flex-wrap gap-2">
                 <Badge variant="secondary">
                   Filiale
                 </Badge>
                {typeof subsidiary.confidence === "number" && (
                  <Badge
                    className={`${getConfidenceColor(subsidiary.confidence)}`}
                  >
                    {getConfidenceLabel(subsidiary.confidence)} (
                    {Math.round(subsidiary.confidence * 100)}%)
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardHeader>

        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <CardContent className="pt-0">
                <div className="space-y-6">
                  <div className="space-y-3">
                    <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-red-500" />
                      Siège principal
                    </h4>
                    {subsidiary.headquarters ? (
                      renderSite(subsidiary.headquarters, 0)
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Siège non renseigné.
                      </p>
                    )}
                  </div>


                  <div className="space-y-2 text-sm">
                    <span className="font-medium text-muted-foreground">
                      Commentaire:
                    </span>
                    <span>
                      {subsidiary.activity || "Information non fournie"}
                    </span>
                  </div>
                </div>

                {/* Sources */}
                {subsidiary.sources && subsidiary.sources.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-gray-500" />
                      Sources
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {subsidiary.sources.map((source, idx) => {
                        const displayLabel = source.title || "Source";
                        const isUrl = Boolean(source.url);

                        return (
                          <Badge
                            key={idx}
                            variant="outline"
                            className={`text-xs ${
                              isUrl
                                ? "cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-colors"
                                : ""
                            }`}
                            onClick={
                              isUrl
                                ? () =>
                                     window.open(
                                       source.url,
                                       "_blank",
                                       "noopener,noreferrer"
                                     )
                                : undefined
                            }
                          >
                            {isUrl ? (
                              <div className="flex items-center gap-1">
                                <ExternalLink className="w-3 h-3" />
                                {displayLabel.length > 40
                                  ? `${displayLabel.substring(0, 40)}...`
                                  : displayLabel}
                              </div>
                            ) : (
                              displayLabel
                            )}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  );
}

export function SubsidiariesList({
  subsidiaries,
  totalCount,
}: SubsidiariesListProps) {
  console.log(
    "📋 [DEBUG] SubsidiariesList rendu avec subsidiaries:",
    subsidiaries,
    "totalCount:",
    totalCount
  );

  if (!subsidiaries || subsidiaries.length === 0) {
    return (
      <Card className="text-center py-12">
        <CardContent>
          <Building className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <CardTitle className="text-xl text-gray-600 mb-2">
            Aucune filiale trouvée
          </CardTitle>
          <CardDescription>
            Cette entreprise n&apos;a pas de filiales répertoriées ou les
            données ne sont pas disponibles.
          </CardDescription>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Filiales ({totalCount})
          </h2>
          <p className="text-muted-foreground">
            {subsidiaries.length} filiale{subsidiaries.length > 1 ? "s" : ""}{" "}
            détaillée{subsidiaries.length > 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {subsidiaries.length}
              </p>
              <p className="text-sm text-muted-foreground">
                Filiales détaillées
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-orange-600">
                {(() => {
                  const countries = subsidiaries
                    .map((s) => s.headquarters?.country)
                    .filter((value): value is string => Boolean(value));
                  return new Set(countries).size;
                })()}
              </p>
              <p className="text-sm text-muted-foreground">Pays représentés</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">
                {(() => {
                  const scores = subsidiaries
                    .map((s) =>
                      typeof s.confidence === "number" ? s.confidence : null
                    )
                    .filter((value): value is number => value !== null);

                  if (!scores.length) {
                    return "N/A";
                  }

                  const avg =
                    scores.reduce((acc, value) => acc + value, 0) /
                    scores.length;
                  return `${Math.round(avg * 100)}%`;
                })()}
              </p>
              <p className="text-sm text-muted-foreground">Confiance moyenne</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Subsidiaries List */}
      <div className="space-y-4">
        {subsidiaries.map((subsidiary, index) => (
          <SubsidiaryCard
            key={`${subsidiary.legal_name}-${index}`}
            subsidiary={subsidiary}
            index={index}
          />
        ))}
      </div>

      {totalCount > subsidiaries.length && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4 text-center">
            <p className="text-blue-800">
              <strong>{totalCount - subsidiaries.length}</strong> filiale
              {totalCount - subsidiaries.length > 1 ? "s" : ""} supplémentaire
              {totalCount - subsidiaries.length > 1 ? "s" : ""} identifiée
              {totalCount - subsidiaries.length > 1 ? "s" : ""}
              mais non détaillée
              {totalCount - subsidiaries.length > 1 ? "s" : ""} dans cette
              analyse.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
