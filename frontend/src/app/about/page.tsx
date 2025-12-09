"use client";

import { PageHero } from "@/components/sections/PageHero";
import { Search, Map, TestTube, Target, Zap, Lightbulb } from 'lucide-react';

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-slate-50 text-gray-800">
            <PageHero
                backgroundImage="/images/api-architecture-flow.png"
                title={
                    <>
                        Notre Mission : Rendre le monde de l'entreprise 
                        <span className="text-[#FE4D01] block mt-2">
                            transparent et accessible
                        </span>
                    </>
                }
                description="Nous croyons que la connaissance est la clé de la réussite. Notre mission est de fournir des informations claires, précises et exploitables sur la structure des entreprises pour éclairer vos décisions stratégiques."
            />

            {/* Section Introduction API */}
            <section className="py-20 px-4 bg-white">
                <div className="container mx-auto max-w-4xl">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl md:text-4xl font-bold mb-6 text-slate-900">
                            Comprendre l'architecture des agents
                        </h2>
                        <p className="text-lg text-slate-700 leading-relaxed">
                            Notre API utilise une architecture d'agents spécialisés qui travaillent en séquence pour 
                            analyser une entreprise. Chaque agent a un rôle précis et utilise des outils d'intelligence 
                            artificielle pour accomplir sa tâche. Voici comment cela fonctionne concrètement.
                        </p>
                    </div>
                    
                    <div className="bg-slate-50 rounded-2xl p-8 border border-slate-200">
                        <h3 className="text-xl font-semibold mb-4 text-slate-900">Le principe de base</h3>
                        <p className="text-slate-700 mb-4 leading-relaxed">
                            Quand vous envoyez une requête à notre API (une URL d'entreprise par exemple), notre système 
                            orchestre automatiquement une série d'agents. Chaque agent est un programme spécialisé qui 
                            sait comment utiliser des outils d'IA pour rechercher, analyser et extraire des informations.
                        </p>
                        <p className="text-slate-700 leading-relaxed">
                            Les agents communiquent entre eux : le résultat de l'un devient l'input du suivant, créant 
                            ainsi un pipeline d'analyse progressif et structuré.
                        </p>
                    </div>
                </div>
            </section>

            {/* Section Comment ça fonctionne (Timeline) */}
            <section className="py-20 px-4 bg-gradient-to-b from-slate-50 to-white">
                <div className="container mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900">Les trois agents de l'API</h2>
                        <p className="text-lg text-slate-600 max-w-3xl mx-auto">
                            Chaque agent est un composant indépendant de l'API qui reçoit des données en entrée, 
                            effectue son traitement, et retourne des résultats structurés. Voici le détail de chaque phase.
                        </p>
                    </div>
                    <div className="relative">
                        {/* Ligne de la timeline */}
                        <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-slate-300 to-transparent" style={{ transform: 'translateY(-50%)' }}></div>
                        
                        <div className="grid md:grid-cols-3 gap-8 md:gap-12">
                            {/* Étape 1 */}
                            <div className="relative flex flex-col items-center p-8 bg-white rounded-2xl shadow-lg border border-slate-200 hover:shadow-xl transition-all duration-300">
                                <div className="absolute -top-8 bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-16 w-16 flex items-center justify-center text-2xl font-bold shadow-lg">1</div>
                                <Search className="h-12 w-12 text-[#FE4D01] mt-8 mb-4" />
                                <h3 className="text-2xl font-semibold mb-3 text-slate-900">L'Éclaireur</h3>
                                <p className="text-slate-600 text-center mb-4 leading-relaxed">
                                    Identifie la société mère et le périmètre de l'analyse à partir d'une simple URL.
                                </p>
                                <div className="mt-auto pt-4 border-t border-slate-200 w-full">
                                    <p className="text-sm text-slate-500 text-center mb-2">
                                        <strong>Résultat API :</strong> Société mère identifiée, secteur d'activité déterminé, 
                                        site web officiel validé.
                                    </p>
                                    <p className="text-xs text-slate-400 text-center">
                                        <strong>Technique :</strong> Utilise la recherche web en temps réel pour analyser 
                                        les sites officiels et registres d'entreprises.
                                    </p>
                                </div>
                            </div>
                            {/* Étape 2 */}
                            <div className="relative flex flex-col items-center p-8 bg-white rounded-2xl shadow-lg border border-slate-200 hover:shadow-xl transition-all duration-300">
                                <div className="absolute -top-8 bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-16 w-16 flex items-center justify-center text-2xl font-bold shadow-lg">2</div>
                                <Map className="h-12 w-12 text-[#FE4D01] mt-8 mb-4" />
                                <h3 className="text-2xl font-semibold mb-3 text-slate-900">Le Cartographe</h3>
                                <p className="text-slate-600 text-center mb-4 leading-relaxed">
                                    Explore et cartographie toutes les filiales, participations et entités liées à la société mère.
                                </p>
                                <div className="mt-auto pt-4 border-t border-slate-200 w-full">
                                    <p className="text-sm text-slate-500 text-center mb-2">
                                        <strong>Résultat API :</strong> Liste complète des entités identifiées avec leurs noms légaux, 
                                        pays et sites web.
                                    </p>
                                    <p className="text-xs text-slate-400 text-center">
                                        <strong>Technique :</strong> Recherche dans les rapports annuels, registres officiels 
                                        et bases de données corporatives pour identifier jusqu'à 15 entités liées.
                                    </p>
                                </div>
                            </div>
                            {/* Étape 3 */}
                            <div className="relative flex flex-col items-center p-8 bg-white rounded-2xl shadow-lg border border-slate-200 hover:shadow-xl transition-all duration-300">
                                <div className="absolute -top-8 bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-16 w-16 flex items-center justify-center text-2xl font-bold shadow-lg">3</div>
                                <TestTube className="h-12 w-12 text-[#FE4D01] mt-8 mb-4" />
                                <h3 className="text-2xl font-semibold mb-3 text-slate-900">L'Extracteur</h3>
                                <p className="text-slate-600 text-center mb-4 leading-relaxed">
                                    Analyse chaque entité en détail pour en extraire les informations clés (contact, statut, localisation).
                                </p>
                                <div className="mt-auto pt-4 border-t border-slate-200 w-full">
                                    <p className="text-sm text-slate-500 text-center mb-2">
                                        <strong>Résultat API :</strong> Coordonnées complètes, statut légal, et informations 
                                        géographiques pour chaque entité.
                                    </p>
                                    <p className="text-xs text-slate-400 text-center">
                                        <strong>Technique :</strong> Traitement parallèle de plusieurs entités simultanément 
                                        pour optimiser les performances. Chaque extraction est indépendante.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {/* Section technique sur le traitement parallèle */}
                    <div className="mt-12 max-w-4xl mx-auto">
                        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
                            <h4 className="text-lg font-semibold text-blue-900 mb-3">💡 Comment fonctionne le traitement parallèle ?</h4>
                            <p className="text-slate-700 mb-3">
                                L'Extracteur traite plusieurs entités en parallèle pour réduire le temps d'analyse global. 
                                Techniquement, cela signifie que l'API lance plusieurs requêtes simultanées plutôt que d'attendre 
                                que chaque extraction se termine avant de commencer la suivante.
                            </p>
                            <p className="text-slate-700">
                                <strong>Avantage :</strong> Si vous avez 10 filiales à analyser, au lieu de prendre 10 minutes 
                                (1 minute par filiale), le traitement parallèle peut réduire le temps à environ 2-3 minutes, 
                                selon la capacité de traitement disponible.
                            </p>
                        </div>
                    </div>
                    
                    {/* Section sur le format de réponse API */}
                    <div className="mt-8 max-w-4xl mx-auto">
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                            <h4 className="text-lg font-semibold text-slate-900 mb-3">📡 Format de réponse de l'API</h4>
                            <p className="text-slate-700 mb-3">
                                Chaque agent retourne des données structurées en JSON. L'API finale consolide tous ces résultats 
                                en un seul objet JSON que vous recevez, contenant :
                            </p>
                            <ul className="text-slate-700 space-y-2 list-disc list-inside">
                                <li>Les informations de la société mère (identifiées par l'Éclaireur)</li>
                                <li>La liste des entités cartographiées (identifiées par le Cartographe)</li>
                                <li>Les détails complets de chaque entité (extraits par l'Extracteur)</li>
                                <li>Des métadonnées : scores de confiance, sources utilisées, dates d'extraction</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>
            
            {/* Section Garanties techniques */}
            <section className="py-20 px-4 bg-white">
                <div className="container mx-auto max-w-4xl">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900">Garanties et fiabilité de l'API</h2>
                        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                            Comprendre comment l'API garantit la qualité et la traçabilité des données.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="p-6 bg-slate-50 rounded-xl border border-slate-200">
                            <div className="flex justify-center mb-4">
                                <Target className="h-10 w-10 text-[#FE4D01]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2 text-center text-slate-900">Score de confiance</h3>
                            <p className="text-slate-600 text-sm text-center leading-relaxed">
                                Chaque donnée extraite est accompagnée d'un score de confiance (0 à 1) qui indique la fiabilité 
                                de l'information selon la qualité des sources utilisées.
                            </p>
                        </div>
                        <div className="p-6 bg-slate-50 rounded-xl border border-slate-200">
                            <div className="flex justify-center mb-4">
                                <Zap className="h-10 w-10 text-[#FE4D01]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2 text-center text-slate-900">Traçabilité</h3>
                            <p className="text-slate-600 text-sm text-center leading-relaxed">
                                Toutes les sources consultées par les agents sont enregistrées et retournées dans la réponse API, 
                                vous permettant de vérifier l'origine de chaque information.
                            </p>
                        </div>
                        <div className="p-6 bg-slate-50 rounded-xl border border-slate-200">
                            <div className="flex justify-center mb-4">
                                <Lightbulb className="h-10 w-10 text-[#FE4D01]" />
                            </div>
                            <h3 className="text-lg font-semibold mb-2 text-center text-slate-900">Gestion d'erreurs</h3>
                            <p className="text-slate-600 text-sm text-center leading-relaxed">
                                Si un agent rencontre une erreur, l'API continue le traitement avec les autres agents et 
                                retourne les résultats partiels avec des indicateurs d'état clairs.
                            </p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
