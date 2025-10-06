"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SubsidiaryDetail } from "@/lib/api";
import {
  Building2,
  MapPin,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Globe,
  TrendingUp,
} from "lucide-react";

interface SubsidiariesNavbarProps {
  subsidiaries: SubsidiaryDetail[];
  companyName: string;
  onSubsidiarySelect?: (subsidiary: SubsidiaryDetail) => void;
}

export function SubsidiariesNavbar({
  subsidiaries,
  companyName,
  onSubsidiarySelect,
}: SubsidiariesNavbarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedSubsidiary, setSelectedSubsidiary] =
    useState<SubsidiaryDetail | null>(null);
  const [filteredSubsidiaries, setFilteredSubsidiaries] =
    useState<SubsidiaryDetail[]>(subsidiaries);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"name" | "country" | "confidence">(
    "name"
  );

  // Filtrer et trier les filiales
  useEffect(() => {
    if (!subsidiaries || subsidiaries.length === 0) {
      setFilteredSubsidiaries([]);
      return;
    }

    const filtered = subsidiaries.filter(
      (sub) =>
        sub?.legal_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        sub?.headquarters?.country
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase()) ||
        sub?.headquarters?.city
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase())
    );

    // Trier les filiales
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return (a?.legal_name || "").localeCompare(b?.legal_name || "");
        case "country":
          return (a?.headquarters?.country || "").localeCompare(
            b?.headquarters?.country || ""
          );
        case "confidence":
          return (
            ((b?.confidence as number) || 0) - ((a?.confidence as number) || 0)
          );
        default:
          return 0;
      }
    });

    setFilteredSubsidiaries(filtered);
  }, [subsidiaries, searchTerm, sortBy]);

  // Statistiques des filiales
  const stats = useMemo(() => {
    const confidenceValues =
      subsidiaries
        ?.map((sub) =>
          typeof sub?.confidence === "number" ? sub.confidence : null
        )
        .filter((value): value is number => value !== null) || [];

    const avgConfidence =
      confidenceValues.length > 0
        ? confidenceValues.reduce((acc, value) => acc + value, 0) /
          confidenceValues.length
        : 0;

    return {
      total: subsidiaries?.length || 0,
      countries: new Set(
        subsidiaries
          ?.map((s) => s?.headquarters?.country)
          .filter((value): value is string => Boolean(value)) || []
      ).size,
      avgConfidence,
    };
  }, [subsidiaries]);

  const handleSubsidiaryClick = (subsidiary: SubsidiaryDetail) => {
    if (!subsidiary) return;

    setSelectedSubsidiary(subsidiary);
    onSubsidiarySelect?.(subsidiary);

    // Scroll vers la filiale dans la page
    if (subsidiary.legal_name) {
      const element = document.getElementById(
        `subsidiary-${subsidiary.legal_name.replace(/\s+/g, "-")}`
      );
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  };

  return (
    <motion.div
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="relative z-50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo et titre */}
          <div className="flex items-center gap-3">
            <Building2 className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                {companyName}
              </h1>
              <p className="text-xs text-gray-500">Filiales & Structure</p>
            </div>
          </div>

          {/* Statistiques rapides */}
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-1 text-sm">
              <Building2 className="w-4 h-4 text-blue-600" />
              <span className="font-medium">{stats.total}</span>
              <span className="text-gray-500">filiales</span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <Globe className="w-4 h-4 text-green-600" />
              <span className="font-medium">{stats.countries}</span>
              <span className="text-gray-500">pays</span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendingUp className="w-4 h-4 text-orange-600" />
              <span className="font-medium">
                {Math.round(stats.avgConfidence * 100)}%
              </span>
              <span className="text-gray-500">confiance</span>
            </div>
          </div>

          {/* Bouton d'expansion */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Masquer
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                Explorer
              </>
            )}
          </Button>
        </div>

        {/* Panneau d'expansion */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <Card className="mb-4 border-0 shadow-lg">
                <CardContent className="p-4">
                  <div className="space-y-4">
                    {/* Contrôles de recherche et tri */}
                    <div className="flex flex-col sm:flex-row gap-4">
                      <div className="flex-1">
                        <input
                          type="text"
                          placeholder="Rechercher une filiale..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                      <div className="flex gap-2">
                        <select
                          value={sortBy}
                          onChange={(e) =>
                            setSortBy(
                              e.target.value as
                                | "name"
                                | "country"
                                | "confidence"
                            )
                          }
                          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="name">Nom</option>
                          <option value="country">Pays</option>
                          <option value="confidence">Confiance</option>
                        </select>
                      </div>
                    </div>

                    {/* Liste des filiales */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 max-h-64 overflow-y-auto">
                      {filteredSubsidiaries.map((subsidiary, index) => (
                        <motion.div
                          key={subsidiary.legal_name}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.05 }}
                          className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 hover:shadow-md ${
                            selectedSubsidiary?.legal_name ===
                            subsidiary.legal_name
                              ? "border-blue-500 bg-blue-50"
                              : "border-gray-200 hover:border-blue-300"
                          }`}
                          onClick={() => handleSubsidiaryClick(subsidiary)}
                        >
                          <div className="space-y-2">
                            <div className="flex items-start justify-between">
                              <h3 className="font-medium text-sm text-gray-900 leading-tight">
                                {subsidiary.legal_name.length > 25
                                  ? subsidiary.legal_name.substring(0, 25) +
                                    "..."
                                  : subsidiary.legal_name}
                              </h3>
                              {typeof subsidiary.confidence === "number" && (
                                <Badge
                                  variant={
                                    subsidiary.confidence >= 0.8
                                      ? "default"
                                      : subsidiary.confidence >= 0.6
                                      ? "secondary"
                                      : "destructive"
                                  }
                                  className="text-xs ml-2 flex-shrink-0"
                                >
                                  {Math.round(subsidiary.confidence * 100)}%
                                </Badge>
                              )}
                            </div>

                            <div className="space-y-1 text-xs text-gray-600">
                              <div className="flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                <span>
                                  {[
                                    subsidiary.headquarters?.line1,
                                    subsidiary.headquarters?.city,
                                    subsidiary.headquarters?.country,
                                  ]
                                    .filter(Boolean)
                                    .join(", ") || "Localisation inconnue"}
                                </span>
                              </div>

                              {subsidiary.sources &&
                                subsidiary.sources.length > 0 && (
                                  <div className="flex items-center gap-1">
                                    <ExternalLink className="w-3 h-3" />
                                    <span>
                                      {subsidiary.sources.length} source
                                      {subsidiary.sources.length > 1 ? "s" : ""}
                                    </span>
                                  </div>
                                )}
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {filteredSubsidiaries.length === 0 && (
                      <div className="text-center py-8 text-gray-500">
                        <Building2 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                        <p>Aucune filiale trouvée</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
