"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Building2,
  MapPin,
  Users,
  DollarSign,
  Clock,
  Shield,
  TrendingUp,
  Globe,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CompanyData } from "@/lib/api";
import {
  formatDate,
  formatCurrency,
  getConfidenceColor,
  getConfidenceLabel,
} from "@/lib/utils";

interface CompanyOverviewProps {
  company: CompanyData;
}

export function CompanyOverview({ company }: CompanyOverviewProps) {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header Card */}
      <motion.div variants={itemVariants}>
        <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-none shadow-lg">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <CardTitle className="text-3xl font-bold text-gray-900">
                  {company.company_name}
                </CardTitle>
                <CardDescription className="text-lg text-gray-600">
                  {company.activities?.join(", ") || "N/A"}
                </CardDescription>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-sm">
                    {company.sector}
                  </Badge>
                  <Badge variant="outline" className="text-sm">
                    Données extraites
                  </Badge>
                </div>
              </div>
              <Building2 className="w-12 h-12 text-blue-600" />
            </div>
          </CardHeader>
        </Card>
      </motion.div>

      {/* Key Metrics */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Chiffre d&apos;affaires
                  </p>
                  <p className="text-2xl font-bold text-green-600">
                    {company.revenue_recent
                      ? formatCurrency(company.revenue_recent)
                      : "N/A"}
                  </p>
                </div>
                <DollarSign className="w-8 h-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Employés
                  </p>
                  <p className="text-2xl font-bold text-blue-600">
                    {company.employees || "N/A"}
                  </p>
                </div>
                <Users className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Filiales
                  </p>
                  <p className="text-2xl font-bold text-purple-600">
                    {company.subsidiaries_details?.length || 0}
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Temps d&apos;analyse
                  </p>
                  <p className="text-2xl font-bold text-orange-600">
                    {company.extraction_metadata?.processing_time
                      ? `${(
                          company.extraction_metadata.processing_time / 1000
                        ).toFixed(1)}s`
                      : "N/A"}
                  </p>
                </div>
                <Clock className="w-8 h-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      {/* Company Details */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Headquarters */}
          <Card className="hover-lift">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-red-500" />
                Siège Social
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Adresse
                </p>
                <p className="text-lg">
                  {company.headquarters_address || "Non spécifiée"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Ville
                </p>
                <p className="text-lg font-medium">
                  {company.headquarters_city}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Pays
                </p>
                <p className="text-lg font-medium flex items-center gap-2">
                  <Globe className="w-4 h-4" />
                  {company.headquarters_country}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Company Structure */}
          <Card className="hover-lift">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-500" />
                Structure Organisationnelle
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Société mère
                </p>
                <p className="text-lg">
                  {company.parent_company || "Société indépendante"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Nombre de filiales
                </p>
                <p className="text-lg font-medium">
                  {company.subsidiaries_details?.length || 0}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Filiales détaillées
                </p>
                <p className="text-lg font-medium">
                  {company.subsidiaries_details?.length || 0}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      {/* Data Sources & Metadata */}
      <motion.div variants={itemVariants}>
        <Card className="bg-gray-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-green-500" />
              Métadonnées d&apos;extraction
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Date d&apos;extraction
                </p>
                <p className="text-lg">
                  {company.extraction_date
                    ? formatDate(company.extraction_date)
                    : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Statut
                </p>
                <Badge variant="default">Succès</Badge>
              </div>
            </div>

            {company.sources && company.sources.length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Sources de données
                </p>
                <div className="space-y-2">
                  {company.sources.map((source, index) => (
                    <div key={index} className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-gray-600">
                          {source.title}
                        </span>
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
                          {source.tier || "autre"}
                        </Badge>
                      </div>
                      {source.url && (
                        <button
                          onClick={() => window.open(source.url, "_blank")}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 hover:text-blue-700 transition-colors duration-200"
                        >
                          <Globe className="w-3 h-3" />
                          Ouvrir la source
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(company.phone || company.email) && (
              <div className="mt-4">
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Informations de contact
                </p>
                <div className="space-y-2">
                  {company.phone && (
                    <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-100 rounded-md text-sm text-gray-700">
                      <Globe className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      <span className="font-medium">Téléphone :</span>
                      <a
                        href={`tel:${company.phone}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {company.phone}
                      </a>
                    </div>
                  )}
                  {company.email && (
                    <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-100 rounded-md text-sm text-gray-700">
                      <Globe className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      <span className="font-medium">Email :</span>
                      <a
                        href={`mailto:${company.email}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {company.email}
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
