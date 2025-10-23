"use client";

import { useState } from "react";
import { Search, Globe, Building2, Loader2, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { motion } from "framer-motion";

interface CompanySearchProps {
  onSearch: (query: string, isURL?: boolean, deepSearch?: boolean) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function CompanySearch({
  onSearch,
  isLoading = false,
  placeholder = "Rechercher une entreprise...",
}: CompanySearchProps) {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState<"name" | "url">("name");
  const [deepSearch, setDeepSearch] = useState(false);

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query.trim(), searchType === "url", deepSearch);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);

    // Auto-detect URL
    if (
      value.startsWith("http://") ||
      value.startsWith("https://") ||
      value.includes("www.")
    ) {
      setSearchType("url");
    } else {
      setSearchType("name");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card className="w-full max-w-2xl mx-auto shadow-lg hover:shadow-xl transition-all duration-300">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold gradient-text">
            Analyseur d&apos;Entreprises
          </CardTitle>
          <CardDescription className="text-lg">
            Découvrez les informations détaillées sur n&apos;importe quelle
            entreprise et ses filiales
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 mb-4">
            {/* Type de recherche */}
            <div className="flex gap-2">
              <Button
                variant={searchType === "name" ? "default" : "outline"}
                size="sm"
                onClick={() => setSearchType("name")}
                className="flex items-center gap-2"
              >
                <Building2 className="w-4 h-4" />
                Nom d&apos;entreprise
              </Button>
              <Button
                variant={searchType === "url" ? "default" : "outline"}
                size="sm"
                onClick={() => setSearchType("url")}
                className="flex items-center gap-2"
              >
                <Globe className="w-4 h-4" />
                Site web
              </Button>
            </div>

            {/* Mode de recherche approfondie - Toggle */}
            <div className="flex items-center justify-between p-4 bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg transition-colors ${deepSearch ? 'bg-blue-500' : 'bg-slate-300'}`}>
                  <Zap className={`w-5 h-5 ${deepSearch ? 'text-white' : 'text-slate-600'}`} />
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-900">
                      Recherche Approfondie
                    </span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {deepSearch
                      ? 'Analyse exhaustive avec sources multiples et vérifications croisées'
                      : 'Analyse rapide et efficace pour des résultats optimaux'
                    }
                  </span>
                </div>
              </div>
              <Switch
                checked={deepSearch}
                onCheckedChange={setDeepSearch}
                className="data-[state=checked]:bg-blue-500"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type="text"
                placeholder={
                  searchType === "url" ? "https://www.example.com" : placeholder
                }
                value={query}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="pl-10 text-lg h-12"
              />
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-5 h-5" />
            </div>
            <Button
              onClick={handleSearch}
              disabled={isLoading || !query.trim()}
              size="lg"
              className="px-8"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Analyse...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Analyser
                </>
              )}
            </Button>
          </div>

          <div className="text-sm text-muted-foreground text-center">
            {searchType === "name" ? (
              <p>Exemples: Apple Inc., Microsoft Corporation, Tesla</p>
            ) : (
              <p>Exemples: https://www.apple.com, https://microsoft.com</p>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
