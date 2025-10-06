"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CompanyData, SubsidiaryDetail } from "@/lib/api";
import { Building2, Globe, TrendingUp } from "lucide-react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

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
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const countryCoordinates: Record<string, [number, number]> = {
  "États-Unis": [39.5, -98.35],
  "Royaume-Uni": [52.3, -1.5],
  France: [46.23, 2.21],
  "Corée du Sud": [35.9078, 127.7669],
  Allemagne: [51.1657, 10.45],
  Canada: [56.1304, -106.3468],
  Chine: [35.8617, 104.1954],
  Mexique: [23.6345, -102.5528],
  "Nouvelle-Zélande": [-40.9006, 174.886],
  Australie: [-25.2744, 133.7751],
  "Pays-Bas": [52.1326, 5.2913],
  Tchéquie: [49.8175, 15.473],
  Russie: [61.524, 105.3188],
  "Hong Kong": [22.3964, 114.1095],
};

const fallbackCenter: [number, number] = [20, 0];

const defaultIcon = L.icon({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  shadowSize: [41, 41],
});

function getCoordinates(detail: SubsidiaryDetail): [number, number] {
  const site = detail.headquarters;
  const country = site?.country;
  if (country && countryCoordinates[country]) {
    return countryCoordinates[country];
  }
  return fallbackCenter;
}

const getConfidenceColor = (score: number) => {
  if (score >= 0.8) return "text-emerald-600 bg-emerald-50 border-emerald-200";
  if (score >= 0.6) return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-red-600 bg-red-50 border-red-200";
};

interface CompanyMappingProps {
  company: CompanyData;
}

export function CompanyMapping({ company }: CompanyMappingProps) {
  const markers = useMemo(() => {
    return company.subsidiaries_details.map((sub) => {
      const [latitude, longitude] = getCoordinates(sub);
      return {
        name: sub.legal_name,
        confidence: typeof sub.confidence === "number" ? sub.confidence : 0,
        country:
          sub.headquarters?.country ||
          "Pays inconnu",
        city:
          sub.headquarters?.city ||
          "Ville inconnue",
        latitude,
        longitude,
      };
    });
  }, [company.subsidiaries_details]);

  const confidenceScores = company.subsidiaries_details
    .map((s) => (typeof s.confidence === "number" ? s.confidence : null))
    .filter((value): value is number => value !== null);

  const avgConfidence =
    confidenceScores.length > 0
      ? confidenceScores.reduce((acc, score) => acc + score, 0) /
        confidenceScores.length
      : 0.8; // Valeur par défaut

  const mapCenter: [number, number] = [20, 0];

  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      <motion.div variants={fadeInUp}>
        <Card className="border-0 shadow-lg">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <CardTitle className="text-3xl font-bold text-gray-900">
                  {company.company_name}
                </CardTitle>
                <div className="flex items-center gap-2 text-gray-600">
                  <span className="text-lg">
                    {company.headquarters_city}, {company.headquarters_country}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-sm">
                     {company.sector || "Secteur"}
                  </Badge>
                  <Badge variant="outline" className="text-sm">
                    Confiance: {Math.round(avgConfidence * 100)}%
                  </Badge>
                </div>
              </div>
              <Building2 className="w-12 h-12 text-blue-600" />
            </div>
          </CardHeader>
        </Card>
      </motion.div>

      <motion.div variants={fadeInUp}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Filiales référencées
                  </p>
                  <p className="text-2xl font-bold text-blue-600">
                     {company.subsidiaries_details.length}
                  </p>
                </div>
                <Globe className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card className="hover-lift">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Confiance moyenne (filiales)
                  </p>
                  <p className="text-2xl font-bold text-purple-600">
                    {Math.round(avgConfidence * 100)}%
                  </p>
                </div>
                <TrendingUp className="w-8 h-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      <motion.div variants={fadeInUp}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="w-5 h-5 text-blue-600" />
              Répartition géographique des filiales
            </CardTitle>
          </CardHeader>
          <CardContent>
            <MapContainer
              center={mapCenter}
              zoom={2}
              style={{ height: "400px", width: "100%" }}
              worldCopyJump
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {markers.map((marker, idx) => (
                <Marker
                  key={idx}
                  position={[marker.latitude, marker.longitude]}
                  icon={defaultIcon}
                >
                  <Popup>
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">{marker.name}</p>
                      <p>{marker.country}</p>
                      {marker.city && <p>{marker.city}</p>}
                      <p>Confiance : {Math.round(marker.confidence * 100)}%</p>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
