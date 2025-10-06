"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { CompanyData } from "@/lib/api";
import {
  MapPin,
  Building2,
  TrendingUp,
  CheckCircle2,
  Globe,
  ArrowDown,
  Zap,
} from "lucide-react";

interface CompanyAnalyticsProps {
  company: CompanyData;
}

export function CompanyAnalytics({ company }: CompanyAnalyticsProps) {
  const insights = useMemo(() => {
    // Répartition géographique simplifiée
    const countries = company.subsidiaries_details.reduce(
      (acc, sub) => {
        const key = sub.headquarters?.country ?? "Pays inconnu";
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    const topCountries = Object.entries(countries)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([country, count]) => ({ country, count }));

    // Score de confiance global
    const confidenceScores = company.subsidiaries_details
      .map((s) => (typeof s.confidence === "number" ? s.confidence : null))
      .filter((value): value is number => value !== null);

    const avgConfidence =
      confidenceScores.length > 0
        ? confidenceScores.reduce((acc, score) => acc + score, 0) /
          confidenceScores.length
        : 0.8; // Valeur par défaut

    // Structure organisationnelle pour le company tree
    const companyTree = {
      parent: company.parent_company,
      main: company.company_name,
      subsidiaries: company.subsidiaries_details.slice(0, 8), // Top 8 filiales
      hasMore: company.subsidiaries_details.length > 8,
    };

    return {
      topCountries,
      avgConfidence,
      totalCountries: Object.keys(countries).length,
      companyTree,
    };
  }, [company]);

  const fadeInUp = {
    hidden: { opacity: 0, y: 24 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: [0.25, 0.25, 0, 1] },
    },
  };

  const stagger = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.1,
      },
    },
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8)
      return "text-emerald-600 bg-emerald-50 border-emerald-200";
    if (score >= 0.6) return "text-amber-600 bg-amber-50 border-amber-200";
    return "text-red-600 bg-red-50 border-red-200";
  };

  const getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle2 className="w-4 h-4" />;
    if (score >= 0.6) return <TrendingUp className="w-4 h-4" />;
    return <Building2 className="w-4 h-4" />;
  };

  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      {/* Core Company Information */}
      <motion.div variants={fadeInUp} className="space-y-6">
        <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
          <CardContent className="p-8">
            <div className="space-y-8">
              {/* Header avec score de confiance */}
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <motion.h2
                    className="text-3xl font-bold tracking-tight text-gray-900"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                  >
                    {company.company_name}
                  </motion.h2>
                  <motion.div
                    className="flex items-center gap-2 text-gray-600"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                  >
                    <MapPin className="w-4 h-4" />
                    <span className="text-lg">
                      {company.headquarters_city},{" "}
                      {company.headquarters_country}
                    </span>
                  </motion.div>
                </div>
                <motion.div
                  className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-all duration-300 cursor-default hover:shadow-md border ${getConfidenceColor(
                    insights.avgConfidence
                  )}`}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.4 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <motion.div
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      repeatDelay: 4,
                    }}
                  >
                    {getConfidenceIcon(insights.avgConfidence)}
                  </motion.div>
                  <span className="text-sm font-semibold">
                    {Math.round(insights.avgConfidence * 100)}% fiabilité
                  </span>
                </motion.div>
              </div>

              {/* Informations critiques */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <motion.div
                  className="space-y-2 group cursor-pointer"
                  variants={fadeInUp}
                  whileHover={{ y: -2 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex items-center gap-2 text-gray-500 group-hover:text-gray-700 transition-colors">
                    <Building2 className="w-4 h-4" />
                    <span className="text-sm font-medium uppercase tracking-wide">
                      Secteur
                    </span>
                  </div>
                  <p className="text-xl font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                     {company.sector}
                  </p>
                </motion.div>

                {company.revenue_recent && (
                  <motion.div
                    className="space-y-2 group cursor-pointer"
                    variants={fadeInUp}
                    whileHover={{ y: -2 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="flex items-center gap-2 text-gray-500 group-hover:text-gray-700 transition-colors">
                      <TrendingUp className="w-4 h-4" />
                      <span className="text-sm font-medium uppercase tracking-wide">
                        Chiffre d&apos;affaires
                      </span>
                    </div>
                    <p className="text-xl font-semibold text-gray-900 group-hover:text-green-600 transition-colors">
                      {company.revenue_recent}
                    </p>
                  </motion.div>
                )}

                {company.employees && (
                  <motion.div
                    className="space-y-2 group cursor-pointer"
                    variants={fadeInUp}
                    whileHover={{ y: -2 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="flex items-center gap-2 text-gray-500 group-hover:text-gray-700 transition-colors">
                      <Building2 className="w-4 h-4" />
                      <span className="text-sm font-medium uppercase tracking-wide">
                        Employés
                      </span>
                    </div>
                    <p className="text-xl font-semibold text-gray-900 group-hover:text-purple-600 transition-colors">
                      {company.employees}
                    </p>
                  </motion.div>
                )}
              </div>

              {/* Core Business */}
              <motion.div className="border-t pt-6" variants={fadeInUp}>
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Activité principale
                  </h3>
                  <p className="text-gray-700 leading-relaxed">
                     {company.activities?.join(", ") || "N/A"}
                  </p>
                </div>
              </motion.div>

              {/* Company Tree Structure */}
              {(company.parent_company ||
                company.subsidiaries_details.length > 0) && (
                <motion.div className="border-t pt-6" variants={fadeInUp}>
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Structure organisationnelle
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <motion.span
                        className="flex items-center gap-1 px-3 py-1 bg-blue-50 rounded-full"
                        whileHover={{ scale: 1.05 }}
                      >
                        <Globe className="w-4 h-4" />
                        {insights.totalCountries} pays
                      </motion.span>
                      <motion.span
                        className="flex items-center gap-1 px-3 py-1 bg-purple-50 rounded-full"
                        whileHover={{ scale: 1.05 }}
                      >
                        <Building2 className="w-4 h-4" />
                        {company.subsidiaries_details.length} filiales
                      </motion.span>
                    </div>
                  </div>

                  <div className="space-y-6">
                    {/* Parent Company (if exists) */}
                    {insights.companyTree.parent && (
                      <motion.div
                        className="flex items-center justify-center"
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                      >
                        <div className="flex flex-col items-center">
                          <div className="px-4 py-2 bg-gradient-to-r from-slate-100 to-slate-200 rounded-lg border-2 border-slate-300 text-slate-700 font-medium text-sm">
                            {insights.companyTree.parent}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            Société mère
                          </div>
                          <ArrowDown className="w-4 h-4 text-gray-400 mt-2" />
                        </div>
                      </motion.div>
                    )}

                    {/* Main Company */}
                    <motion.div
                      className="flex items-center justify-center"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 }}
                    >
                      <div className="flex flex-col items-center">
                        <div className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl text-white font-bold text-lg shadow-lg relative">
                          <Zap className="w-5 h-5 absolute -top-2 -right-2 text-yellow-300" />
                          {insights.companyTree.main}
                        </div>
                        <div className="text-xs text-gray-600 mt-1 font-medium">
                          Entreprise principale
                        </div>
                      </div>
                    </motion.div>

                    {/* Subsidiaries */}
                    {insights.companyTree.subsidiaries.length > 0 && (
                      <motion.div
                        className="space-y-4"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.3 }}
                      >
                        <div className="flex items-center justify-center">
                          <ArrowDown className="w-4 h-4 text-gray-400" />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {insights.companyTree.subsidiaries.map(
                            (subsidiary, index) => (
                              <motion.div
                                key={subsidiary.legal_name}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.4 + index * 0.05 }}
                                whileHover={{ scale: 1.02, y: -2 }}
                                className="group cursor-pointer"
                              >
                                <div className="p-3 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200">
                                  <div className="flex items-start justify-between mb-2">
                                    <h4 className="font-medium text-gray-900 text-sm leading-tight group-hover:text-blue-600 transition-colors">
                                      {subsidiary.legal_name.length > 25
                                        ? subsidiary.legal_name.substring(
                                            0,
                                            25
                                          ) + "..."
                                        : subsidiary.legal_name}
                                    </h4>
                                    {typeof subsidiary.confidence ===
                                      "number" && (
                                      <div
                                        className={`w-2 h-2 rounded-full flex-shrink-0 mt-1 ${
                                          subsidiary.confidence >= 0.8
                                            ? "bg-emerald-500"
                                            : subsidiary.confidence >= 0.6
                                            ? "bg-amber-500"
                                            : "bg-red-500"
                                        }`}
                                      />
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
                                          .join(", ") ||
                                          "Localisation inconnue"}
                                      </span>
                                    </div>
                                    {subsidiary.activity && (
                                      <div className="text-gray-500 truncate">
                                        {subsidiary.activity.length > 35
                                          ? subsidiary.activity.substring(0, 35) + "..."
                                          : subsidiary.activity}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </motion.div>
                            )
                          )}

                          {insights.companyTree.hasMore && (
                            <motion.div
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{
                                delay:
                                  0.4 +
                                  insights.companyTree.subsidiaries.length *
                                    0.05,
                              }}
                              className="flex items-center justify-center p-3 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg border border-dashed border-blue-300 text-blue-600"
                            >
                              <div className="text-center">
                                <div className="font-medium text-sm">
                                  +{company.subsidiaries_details.length - 8}{" "}
                                  autres
                                </div>
                                <div className="text-xs text-blue-500">
                                  filiales
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </div>
                </motion.div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
