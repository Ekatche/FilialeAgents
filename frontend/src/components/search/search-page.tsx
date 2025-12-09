
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import { CompanySearch } from "@/components/company/company-search";
import { ApiStatus } from "@/components/features/api-status";
import { Card, CardContent } from "@/components/ui/card";
import { PageHero } from "@/components/sections/PageHero";

export function SearchPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSearch = async (query: string, isURL = false, deepSearch = false) => {
    if (!query.trim()) {
      toast.error("Veuillez entrer un nom d'entreprise ou une URL");
      return;
    }

    setIsLoading(true);

    try {
      // Encoder le query pour l'URL
      const encodedQuery = encodeURIComponent(query.trim());
      const searchType = isURL ? "url" : "name";

      // Rediriger vers la page de résultats avec les paramètres
      router.push(`/results?query=${encodedQuery}&type=${searchType}&deepSearch=${deepSearch}`);

      toast.success(deepSearch ? "Recherche approfondie lancée..." : "Recherche lancée...");
    } catch (error) {
      console.error("Erreur lors de la navigation:", error);
      toast.error("Erreur lors de la navigation");
      setIsLoading(false);
    }
  };

  const fadeInUp = {
    hidden: { opacity: 0, y: 40 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: [0.25, 0.25, 0, 1] },
    },
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* 1. HERO SECTION (Informational) */}
      <PageHero
        backgroundImage="/images/home-background.png"
        title={
          <>
            Cartographiez les entreprises et
            <span className="text-[#FE4D01] block mt-2">
              synchronisez avec HubSpot
            </span>
          </>
        }
        description="Analysez n'importe quelle entreprise automatiquement. Extrayez des informations détaillées sur les filiales, la structure organisationnelle et les relations commerciales grâce à notre IA avancée."
      />

      {/* 2. SEARCH SECTION (Functional) */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <Card className="border border-slate-200 shadow-xl bg-white rounded-2xl overflow-hidden">
            <CardContent className="p-8 md:p-12">
              <div className="text-center mb-8">
                <h3 className="text-2xl font-semibold text-slate-900 mb-2">
                  Commencez votre analyse
                </h3>
                <p className="text-slate-500">
                  Entrez un nom d&apos;entreprise ou une URL pour démarrer
                </p>
              </div>

              <CompanySearch
                onSearch={handleSearch}
                isLoading={isLoading}
                placeholder="Rechercher une entreprise (nom ou URL)..."
              />

              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                <span className="text-sm text-slate-400">Recherches populaires :</span>
                <button
                  onClick={() => handleSearch("Microsoft")}
                  className="text-sm font-medium text-slate-600 hover:text-[#FE4D01] transition-colors"
                >
                  Microsoft
                </button>
                <span className="text-slate-300">•</span>
                <button
                  onClick={() => handleSearch("LVMH")}
                  className="text-sm font-medium text-slate-600 hover:text-[#FE4D01] transition-colors"
                >
                  LVMH
                </button>
                <span className="text-slate-300">•</span>
                <button
                  onClick={() => handleSearch("Tesla")}
                  className="text-sm font-medium text-slate-600 hover:text-[#FE4D01] transition-colors"
                >
                  Tesla
                </button>
                <span className="text-slate-300">•</span>
                <button
                  onClick={() => handleSearch("https://www.google.com", true)}
                  className="text-sm font-medium text-slate-600 hover:text-[#FE4D01] transition-colors"
                >
                  google.com
                </button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
