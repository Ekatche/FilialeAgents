"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L, { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";

// Styles pour différencier les marqueurs
const markerStyles = `
  .subsidiary-marker {
    filter: hue-rotate(200deg) saturate(1.5); /* Bleu pour filiales */
  }
  .commercial-marker {
    filter: hue-rotate(100deg) saturate(1.5); /* Vert pour présences commerciales */
  }
`;
import { SubsidiaryDetail, SiteInfo } from "@/lib/api";

type CountryKey = string;

const COUNTRY_COORDINATES: Record<CountryKey, [number, number]> = {
  "united states": [39.5, -98.35],
  usa: [39.5, -98.35],
  us: [39.5, -98.35],
  "etats unis": [39.5, -98.35],
  "etats-unis": [39.5, -98.35],
  "états-unis": [39.5, -98.35],
  canada: [56.1304, -106.3468],
  mexico: [23.6345, -102.5528],
  mexique: [23.6345, -102.5528],
  france: [46.2276, 2.2137],
  "royaume uni": [52.3555, -1.1743],
  "royaume-uni": [52.3555, -1.1743],
  "united kingdom": [52.3555, -1.1743],
  germany: [51.1657, 10.4515],
  allemagne: [51.1657, 10.4515],
  italy: [41.8719, 12.5674],
  italie: [41.8719, 12.5674],
  spain: [40.4637, -3.7492],
  espagne: [40.4637, -3.7492],
  portugal: [39.3999, -8.2245],
  belgium: [50.5039, 4.4699],
  belgique: [50.5039, 4.4699],
  netherlands: [52.1326, 5.2913],
  "pays bas": [52.1326, 5.2913],
  "pays-bas": [52.1326, 5.2913],
  switzerland: [46.8182, 8.2275],
  suisse: [46.8182, 8.2275],
  austria: [47.5162, 14.5501],
  ireland: [53.1424, -7.6921],
  irlande: [53.1424, -7.6921],
  sweden: [60.1282, 18.6435],
  suede: [60.1282, 18.6435],
  norway: [60.472, 8.4689],
  denmark: [56.2639, 9.5018],
  finland: [61.9241, 25.7482],
  poland: [51.9194, 19.1451],
  pologne: [51.9194, 19.1451],
  czechia: [49.8175, 15.473],
  tchequie: [49.8175, 15.473],
  slovakia: [48.669, 19.699],
  hungary: [47.1625, 19.5033],
  romania: [45.9432, 24.9668],
  bulgaria: [42.7339, 25.4858],
  croatia: [45.1, 15.2],
  slovenia: [46.1512, 14.9955],
  estonia: [58.5953, 25.0136],
  latvia: [56.8796, 24.6032],
  lithuania: [55.1694, 23.8813],
  iceland: [64.9631, -19.0208],
  russia: [61.524, 105.3188],
  china: [35.8617, 104.1954],
  chine: [35.8617, 104.1954],
  japan: [36.2048, 138.2529],
  japon: [36.2048, 138.2529],
  southkorea: [35.9078, 127.7669],
  "coree du sud": [35.9078, 127.7669],
  india: [20.5937, 78.9629],
  inde: [20.5937, 78.9629],
  singapore: [1.3521, 103.8198],
  malaysia: [4.2105, 101.9758],
  thailand: [15.87, 100.9925],
  vietnam: [14.0583, 108.2772],
  indonesia: [-0.7893, 113.9213],
  philippines: [12.8797, 121.774],
  australia: [-25.2744, 133.7751],
  "nouvelle zelande": [-40.9006, 174.886],
  "nouvelle-zelande": [-40.9006, 174.886],
  brazil: [-14.235, -51.9253],
  bresil: [-14.235, -51.9253],
  argentina: [-38.4161, -63.6167],
  chile: [-35.6751, -71.543],
  colombia: [4.5709, -74.2973],
  peru: [-9.19, -75.0152],
  uruguay: [-32.5228, -55.7658],
  paraguay: [-23.4425, -58.4438],
  bolivia: [-16.2902, -63.5887],
  ecuador: [-1.8312, -78.1834],
  venezuela: [6.4238, -66.5897],
  "cote d ivoire": [7.539989, -5.54708],
  "cote d'ivoire": [7.539989, -5.54708],
  "ivory coast": [7.539989, -5.54708],
  nigeria: [9.082, 8.6753],
  ghana: [7.9465, -1.0232],
  senegal: [14.4974, -14.4524],
  morocco: [31.7917, -7.0926],
  egypt: [26.8206, 30.8025],
  southafrica: [-30.5595, 22.9375],
  "south africa": [-30.5595, 22.9375],
  kenya: [-0.0236, 37.9062],
  tanzania: [-6.369, 34.8888],
  tunisia: [33.8869, 9.5375],
  algeria: [28.0339, 1.6596],
  turkey: [38.9637, 35.2433],
  israel: [31.0461, 34.8516],
  uae: [23.4241, 53.8478],
  "emirats arabes unis": [23.4241, 53.8478],
  qatar: [25.3548, 51.1839],
  saudiarabia: [23.8859, 45.0792],
  "arabie saoudite": [23.8859, 45.0792],
};

const COUNTRY_SYNONYMS: Record<string, CountryKey> = {
  "etats-unis": "etats-unis",
  "etats unis": "etats-unis",
  "états-unis": "etats-unis",
  "états unis": "etats-unis",
  "u.s.a": "usa",
  "u.s.": "usa",
  "royaume uni": "royaume-uni",
  "royaume-uni": "royaume-uni",
  "coree du sud": "coree du sud",
  "corée du sud": "coree du sud",
  "cote d ivoire": "cote d'ivoire",
  "côte d'ivoire": "cote d'ivoire",
  "sud afrique": "south africa",
  "sud-afrique": "south africa",
};

const mapCenter: [number, number] = [20, 0];

// Icônes différenciées pour filiales vs présences commerciales
const subsidiaryIcon = L.icon({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  shadowSize: [41, 41],
  className: "subsidiary-marker" // Pour le style CSS
});

const commercialIcon = L.icon({
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
  shadowSize: [41, 41],
  className: "commercial-marker" // Pour le style CSS
});

const defaultIcon = subsidiaryIcon;

function normalizeCountry(value?: string | null): string | null {
  if (!value) return null;

  const normalized = value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^\w\s-]/gu, "")
    .toLowerCase()
    .trim();

  if (normalized in COUNTRY_COORDINATES) {
    return normalized;
  }

  if (normalized in COUNTRY_SYNONYMS) {
    return COUNTRY_SYNONYMS[normalized];
  }

  return normalized;
}

function getCoordinates(
  site?: SiteInfo | null,
  subsidiary?: SubsidiaryDetail
): [number, number] | null {
  if (!site && !subsidiary) return null;

  // Debug logging pour voir la structure des données
  if (subsidiary && console && typeof console.log === "function") {
    console.log(`🗺️ Analyzing coordinates for ${subsidiary.legal_name}:`, {
      subsidiary_root: {
        latitude: (subsidiary as any).latitude,
        longitude: (subsidiary as any).longitude,
      },
      headquarters: subsidiary.headquarters
        ? {
            latitude: subsidiary.headquarters.latitude,
            longitude: subsidiary.headquarters.longitude,
          }
        : null,
      site_param: site
        ? {
            latitude: site.latitude,
            longitude: site.longitude,
          }
        : null,
    });
  }

  // Priorité 1: Coordonnées directes du site
  if (site) {
    if (
      typeof site.latitude === "number" &&
      !Number.isNaN(site.latitude) &&
      typeof site.longitude === "number" &&
      !Number.isNaN(site.longitude)
    ) {
      console.log(`✅ Found coordinates in site:`, [
        site.latitude,
        site.longitude,
      ]);
      return [site.latitude, site.longitude];
    }
  }

  // Priorité 2: Coordonnées de la filiale (au niveau racine)
  if (subsidiary) {
    const subData = subsidiary as any;
    if (
      typeof subData.latitude === "number" &&
      !Number.isNaN(subData.latitude) &&
      typeof subData.longitude === "number" &&
      !Number.isNaN(subData.longitude)
    ) {
      console.log(`✅ Found coordinates in subsidiary root:`, [
        subData.latitude,
        subData.longitude,
      ]);
      return [subData.latitude, subData.longitude];
    }

    // Priorité 3: Coordonnées dans headquarters
    if (subData.headquarters) {
      const hq = subData.headquarters;
      if (
        typeof hq.latitude === "number" &&
        !Number.isNaN(hq.latitude) &&
        typeof hq.longitude === "number" &&
        !Number.isNaN(hq.longitude)
      ) {
        console.log(`✅ Found coordinates in headquarters:`, [
          hq.latitude,
          hq.longitude,
        ]);
        return [hq.latitude, hq.longitude];
      }
    }
  }

  // Priorité 4: Coordonnées par défaut basées sur le pays
  const countryCandidate =
    site?.country || subsidiary?.headquarters?.country || site?.label || null;
  const normalized = normalizeCountry(countryCandidate || undefined);

  if (normalized && COUNTRY_COORDINATES[normalized]) {
    console.log(
      `🌍 Using country coordinates for ${countryCandidate}:`,
      COUNTRY_COORDINATES[normalized]
    );
    return COUNTRY_COORDINATES[normalized];
  }

  console.log(
    `❌ No coordinates found for ${subsidiary?.legal_name || "unknown"}`
  );
  return null;
}

function getCity(site?: SiteInfo | null): string {
  return site?.city?.trim() || site?.postal_code?.trim() || "";
}

interface SubsidiariesVisualizationProps {
  subsidiaries: SubsidiaryDetail[];
  highlightedSubsidiary?: SubsidiaryDetail | null;
  onSubsidiarySelect?: (subsidiary: SubsidiaryDetail) => void;
}

interface NodeData {
  id: string;
  name: string;
  country: string;
  city: string;
  confidence: number;
  type: "main" | "subsidiary";
  latitude: number;
  longitude: number;
  siteLabel?: string | null;
  subsidiary?: SubsidiaryDetail;
}

export function SubsidiariesVisualization({
  subsidiaries,
  highlightedSubsidiary,
  onSubsidiarySelect,
}: SubsidiariesVisualizationProps) {
  const safeSubsidiaries = subsidiaries;
  const [selectedNode, setSelectedNode] = useState<NodeData | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  const { nodes, locatedSubsidiaries } = useMemo(() => {
    const markerMap = new Map<string, NodeData>();
    const located = new Set<string>();

    const registerSite = (
      sub: SubsidiaryDetail,
      site: SiteInfo | null | undefined,
      markerId: string,
      label?: string | null
    ) => {
      const coords = getCoordinates(site, sub);
      if (!coords) return false;

      const [latitude, longitude] = coords;
      const key = `${latitude.toFixed(4)}-${longitude.toFixed(4)}-${markerId}`;

      if (markerMap.has(key)) {
        return false;
      }

      markerMap.set(key, {
        id: key,
        name: sub.legal_name,
        country: site?.country || "",
        city: getCity(site),
        confidence: typeof sub.confidence === "number" ? sub.confidence : 0,
        type: "subsidiary",
        siteLabel: label || site?.label || null,
        subsidiary: sub,
        latitude,
        longitude,
      });
      located.add(sub.legal_name);
      return true;
    };

    const fallbackSiteFromLegacy = (sub: SubsidiaryDetail): SiteInfo | null => {
      const legacy = sub as SubsidiaryDetail & {
        address?: string | null;
        city?: string | null;
        country?: string | null;
        postal_code?: string | null;
        latitude?: number | null;
        longitude?: number | null;
      };

      if (
        !legacy.city &&
        !legacy.country &&
        typeof legacy.latitude !== "number" &&
        typeof legacy.longitude !== "number"
      ) {
        return null;
      }

      return {
        label: "Siège",
        line1: null,
        city: legacy.city ?? null,
        country: legacy.country ?? null,
        postal_code: legacy.postal_code ?? null,
        latitude: legacy.latitude ?? undefined,
        longitude: legacy.longitude ?? undefined,
      };
    };

    safeSubsidiaries.forEach((subsidiary, idx) => {
      const mainSite =
        subsidiary.headquarters ?? fallbackSiteFromLegacy(subsidiary);
      if (mainSite) {
        registerSite(subsidiary, mainSite, `${idx}-hq`, "Siège");
      }

      // [] n'existe plus dans l'API
      // ([] || []).forEach((site, siteIdx) => {
      //   registerSite(
      //     subsidiary,
      //     site,
      //     `${idx}-site-${siteIdx}`,
      //     site.label || `Site ${siteIdx + 1}`
      //   );
      // });
    });

    return {
      nodes: Array.from(markerMap.values()),
      locatedSubsidiaries: located,
    };
  }, [safeSubsidiaries]);

  useEffect(() => {
    if (highlightedSubsidiary) {
      const match = nodes.find(
        (node) =>
          node.subsidiary?.legal_name === highlightedSubsidiary.legal_name
      );
      if (match) {
        setSelectedNode(match);
        return;
      }
    }
    setSelectedNode((prev) => prev ?? nodes[0] ?? null);
  }, [nodes, highlightedSubsidiary]);

  const bounds = useMemo<LatLngBoundsExpression | undefined>(() => {
    if (!nodes.length) return undefined;
    const latLngs = nodes.map((node) => [node.latitude, node.longitude]) as [
      number,
      number
    ][];
    return L.latLngBounds(latLngs);
  }, [nodes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !bounds) return;
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [bounds]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedNode) return;
    map.flyTo([selectedNode.latitude, selectedNode.longitude], 4, {
      duration: 0.8,
    });
  }, [selectedNode]);

  const locatedCount = locatedSubsidiaries.size;
  const totalSubsidiaries = safeSubsidiaries.length;
  const missingCount = Math.max(totalSubsidiaries - locatedCount, 0);

  return (
    <Card className="relative z-10">
      {/* Injection des styles CSS */}
      <style dangerouslySetInnerHTML={{ __html: markerStyles }} />
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-600" />
          Carte mondiale des présences commerciales
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Légende pour distinguer les types d'entités */}
        <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span>Filiales juridiques</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>Présences commerciales</span>
          </div>
        </div>
        
        <div className="relative bg-gray-50 rounded-lg p-6">
          <MapContainer
            center={mapCenter}
            zoom={2}
            bounds={bounds}
            style={{ height: "400px", width: "100%" }}
            worldCopyJump
            ref={mapRef}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {nodes.map((node) => {
              // Déterminer l'icône selon le type d'entité
              const isSubsidiary = node.subsidiary !== undefined;
              const markerIcon = isSubsidiary ? subsidiaryIcon : commercialIcon;
              
              return (
                <Marker
                  key={node.id}
                  position={[node.latitude, node.longitude]}
                  icon={markerIcon}
                  eventHandlers={{
                    click: () => {
                      setSelectedNode(node);
                      if (node.subsidiary && onSubsidiarySelect) {
                        onSubsidiarySelect(node.subsidiary);
                      }
                    },
                  }}
                />
              );
            })}
          </MapContainer>
          {!nodes.length && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
              Aucune localisation disponible pour le moment
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600">
          <span>
            Filiales localisées : {locatedCount}/{totalSubsidiaries}
          </span>
        </div>

        {/* Détails sous la carte supprimés pour éviter le doublon avec le panneau latéral */}
      </CardContent>
    </Card>
  );
}
