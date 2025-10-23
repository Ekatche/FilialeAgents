"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "react-hot-toast";
import {
  Search,
  Building2,
  Zap,
  Globe,
  TrendingUp,
  Shield,
} from "lucide-react";
import { CompanySearch } from "@/components/company/company-search";
import { ApiStatus } from "@/components/features/api-status";
import { Card, CardContent } from "@/components/ui/card";

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

  const stagger = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.3,
      },
    },
  };

  const features = [
    {
      icon: <Building2 className="w-8 h-8 text-blue-600" />,
      title: "Informations complètes",
      description: "Siège social, secteur d'activité, données financières",
    },
    {
      icon: <Globe className="w-8 h-8 text-green-600" />,
      title: "Filiales internationales",
      description: "Structure organisationnelle et présence mondiale",
    },
    {
      icon: <TrendingUp className="w-8 h-8 text-purple-600" />,
      title: "Analyse intelligente",
      description: "Détection automatique des relations entre entreprises",
    },
    {
      icon: <Shield className="w-8 h-8 text-orange-600" />,
      title: "Sources fiables",
      description: "Données vérifiées avec score de confiance",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      {/* Header */}
      <motion.header
        className="border-b border-white/20 backdrop-blur-sm bg-white/30"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                <Search className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Company Analyzer
                </h1>
                <p className="text-sm text-gray-600">
                  Analyse intelligente d&apos;entreprises
                </p>
              </div>
            </div>
            <ApiStatus />
          </div>
        </div>
      </motion.header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
          className="space-y-16"
        >
          {/* Hero Section */}
          <motion.div variants={fadeInUp} className="text-center space-y-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 text-blue-700 text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Powered by OpenAI Agents
            </div>

            <h2 className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight">
              Analysez n&apos;importe quelle
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent block">
                entreprise mondiale
              </span>
            </h2>

            <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
              Obtenez des informations détaillées sur les entreprises, leurs
              filiales, et leur structure organisationnelle en quelques
              secondes.
            </p>
          </motion.div>

          {/* Search Section */}
          <motion.div variants={fadeInUp} className="max-w-4xl mx-auto">
            <Card className="border-0 shadow-2xl bg-white/80 backdrop-blur-sm">
              <CardContent className="p-8">
                <CompanySearch
                  onSearch={handleSearch}
                  isLoading={isLoading}
                  placeholder="Rechercher une entreprise (nom ou URL)..."
                />

                <div className="mt-6 flex flex-wrap gap-3 justify-center">
                  <span className="text-sm text-gray-500">Exemples :</span>
                  <button
                    onClick={() => handleSearch("Microsoft")}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                  >
                    Microsoft
                  </button>
                  <button
                    onClick={() => handleSearch("Apple")}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                  >
                    Apple
                  </button>
                  <button
                    onClick={() => handleSearch("https://www.google.com", true)}
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                  >
                    google.com
                  </button>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Features Grid */}
          <motion.div
            variants={fadeInUp}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {features.map((feature, index) => (
              <motion.div
                key={index}
                variants={fadeInUp}
                whileHover={{ y: -8, scale: 1.02 }}
                transition={{ duration: 0.3 }}
                className="group cursor-default"
              >
                <Card className="border-0 shadow-lg hover:shadow-xl bg-white/70 backdrop-blur-sm transition-all duration-300">
                  <CardContent className="p-6 text-center space-y-4">
                    <motion.div
                      className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r from-gray-100 to-gray-200 group-hover:from-gray-200 group-hover:to-gray-300 transition-all duration-300"
                      whileHover={{ rotate: [0, -10, 10, -10, 0] }}
                      transition={{ duration: 0.5 }}
                    >
                      {feature.icon}
                    </motion.div>
                    <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-gray-600 leading-relaxed">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
