"use client";
import { PageHero } from "@/components/sections/PageHero";
import { Button } from "@/components/ui/button";
import { ArrowRight, BarChart, Database, GitBranch, Briefcase } from 'lucide-react';

export default function NotreOutilPage() {
    return (
        <div className="min-h-screen bg-slate-50 text-gray-800">
            <PageHero
                backgroundImage="/images/insights-hero.png"
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

            {/* Section Fonctionnalités */}
            <section className="py-20 px-4 bg-white">
                <div className="container mx-auto text-center">
                    <h2 className="text-3xl font-bold mb-4">Fonctionnalités Principales</h2>
                    <p className="text-lg text-gray-600 mb-12 max-w-3xl mx-auto">
                        Découvrez comment notre outil peut transformer votre veille stratégique et commerciale.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <div className="p-6 border border-gray-200 rounded-lg shadow-sm hover:shadow-lg transition-shadow">
                            <BarChart className="h-12 w-12 text-[#FE4D01] mx-auto mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Analyse Automatisée</h3>
                            <p>Lancez une analyse complète à partir d'une simple URL d'entreprise pour découvrir sa structure et ses filiales.</p>
                        </div>
                        <div className="p-6 border border-gray-200 rounded-lg shadow-sm hover:shadow-lg transition-shadow">
                            <Database className="h-12 w-12 text-[#FE4D01] mx-auto mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Synchronisation HubSpot</h3>
                            <p>Intégrez les données collectées directement dans votre CRM HubSpot pour une vision à 360° de vos prospects.</p>
                        </div>
                        <div className="p-6 border border-gray-200 rounded-lg shadow-sm hover:shadow-lg transition-shadow">
                            <GitBranch className="h-12 w-12 text-[#FE4D01] mx-auto mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Cartographie d'Entreprise</h3>
                            <p>Visualisez les relations complexes entre les entités, les dirigeants et les participations financières.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Section Comment ça marche */}
            <section className="py-20 px-4 bg-gradient-to-b from-slate-50 to-white">
                <div className="container mx-auto">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4 text-center text-slate-900">Comment ça marche ?</h2>
                    <p className="text-lg text-slate-600 text-center mb-16 max-w-2xl mx-auto">
                        Un processus simple en trois étapes pour cartographier n'importe quelle entreprise
                    </p>
                    
                    <div className="relative">
                        <div className="flex flex-col md:flex-row items-stretch justify-center gap-8 md:gap-6 relative">
                            {/* Step 1 */}
                            <div className="relative flex flex-col items-center w-full md:w-1/3 max-w-sm mx-auto">
                                <div className="relative z-10 bg-white rounded-2xl shadow-lg p-8 border border-slate-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 w-full h-full flex flex-col">
                                    <div className="bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-20 w-20 flex items-center justify-center text-3xl font-bold mb-6 mx-auto shadow-lg flex-shrink-0">
                                        1
                                    </div>
                                    <h3 className="text-2xl font-bold mb-4 text-slate-900 text-center flex-shrink-0">Analysez</h3>
                                    <p className="text-slate-600 text-center leading-relaxed flex-grow">
                                        Soumettez l'URL du site web de l'entreprise que vous souhaitez analyser.
                                    </p>
                                </div>
                            </div>
                            
                            {/* Flèche entre Step 1 et Step 2 */}
                            <div className="hidden md:flex items-center justify-center flex-shrink-0 z-20 self-center">
                                <div className="bg-white rounded-full p-3 shadow-lg border-2 border-[#FE4D01]/20">
                                    <ArrowRight className="h-8 w-8 text-[#FE4D01]" />
                                </div>
                            </div>
                            
                            {/* Step 2 */}
                            <div className="relative flex flex-col items-center w-full md:w-1/3 max-w-sm mx-auto">
                                <div className="relative z-10 bg-white rounded-2xl shadow-lg p-8 border border-slate-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 w-full h-full flex flex-col">
                                    <div className="bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-20 w-20 flex items-center justify-center text-3xl font-bold mb-6 mx-auto shadow-lg flex-shrink-0">
                                        2
                                    </div>
                                    <h3 className="text-2xl font-bold mb-4 text-slate-900 text-center flex-shrink-0">Visualisez</h3>
                                    <p className="text-slate-600 text-center leading-relaxed flex-grow">
                                        Explorez la cartographie générée par l'IA et les informations clés.
                                    </p>
                                </div>
                            </div>
                            
                            {/* Flèche entre Step 2 et Step 3 */}
                            <div className="hidden md:flex items-center justify-center flex-shrink-0 z-20 self-center">
                                <div className="bg-white rounded-full p-3 shadow-lg border-2 border-[#FE4D01]/20">
                                    <ArrowRight className="h-8 w-8 text-[#FE4D01]" />
                                </div>
                            </div>
                            
                            {/* Step 3 */}
                            <div className="relative flex flex-col items-center w-full md:w-1/3 max-w-sm mx-auto">
                                <div className="relative z-10 bg-white rounded-2xl shadow-lg p-8 border border-slate-200 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 w-full h-full flex flex-col">
                                    <div className="bg-gradient-to-br from-[#FE4D01] to-[#E44200] text-white rounded-full h-20 w-20 flex items-center justify-center text-3xl font-bold mb-6 mx-auto shadow-lg flex-shrink-0">
                                        3
                                    </div>
                                    <h3 className="text-2xl font-bold mb-4 text-slate-900 text-center flex-shrink-0">Synchronisez</h3>
                                    <p className="text-slate-600 text-center leading-relaxed flex-grow">
                                        Exportez les données vers HubSpot en un seul clic pour enrichir votre CRM.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Section CTA */}
            <section className="py-20 px-4 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
                <div className="container mx-auto text-center">
                    <h2 className="text-3xl md:text-4xl font-bold mb-4 text-white">Prêt à commencer ?</h2>
                    <p className="text-lg text-slate-300 mb-8 max-w-2xl mx-auto">
                        Connectez-vous pour accéder à l'outil et lancer votre première analyse.
                    </p>
                    <Button 
                        size="lg" 
                        className="bg-[#FE4D01] hover:bg-[#E44200] text-white px-8 py-6 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105" 
                        onClick={() => window.location.href='/login'}
                    >
                        Se connecter <ArrowRight className="ml-2 h-5 w-5" />
                    </Button>
                </div>
            </section>
        </div>
    );
}

