'use client';

import { CheckCircle2, RefreshCw, Zap, Shield, BarChart3, Globe } from 'lucide-react';

const benefits = [
    {
        title: 'Analyse automatisée',
        description: 'Obtenez des informations complètes sur les entreprises automatiquement. Notre IA traite les données de manière asynchrone.',
        icon: Zap,
    },
    {
        title: 'Couverture mondiale',
        description: 'Accédez aux données d\'entreprises du monde entier. Aucune limite géographique pour votre analyse.',
        icon: Globe,
    },
    {
        title: 'Insights approfondis',
        description: 'Découvrez les relations cachées, les structures de filiales et les décideurs clés sans effort.',
        icon: BarChart3,
    },
    {
        title: 'Sécurité',
        description: 'Vos données sont chiffrées et sécurisées. Nous respectons les plus hauts standards de protection des données.',
        icon: Shield,
    },
];

export function BenefitsSection() {
    return (
        <section className="w-full py-24 bg-zinc-50 text-zinc-900 relative overflow-hidden">
            {/* Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-b from-white to-zinc-100 pointer-events-none" />

            <div className="container mx-auto px-6 relative z-10">

                {/* Section Header */}
                <div className="text-center max-w-3xl mx-auto mb-20">
                    <h2 className="text-4xl md:text-5xl font-bold mb-6 text-zinc-900">
                        Avantages de l'API
                    </h2>
                    <p className="text-lg text-zinc-600">
                        Une API puissante pour extraire et analyser les données d'entreprises de manière automatisée.
                        Intégrez facilement ces fonctionnalités dans vos applications.
                    </p>
                </div>

                {/* Benefits Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-24">
                    {benefits.map((benefit, index) => (
                        <div
                            key={index}
                            className="p-6 rounded-2xl bg-white border border-zinc-200 hover:border-orange-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-orange-500/5 group"
                        >
                            <div className="w-12 h-12 rounded-full bg-orange-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                                <benefit.icon className="w-6 h-6 text-orange-500" />
                            </div>
                            <h3 className="text-xl font-semibold mb-3 text-zinc-900">{benefit.title}</h3>
                            <p className="text-zinc-600 leading-relaxed">
                                {benefit.description}
                            </p>
                        </div>
                    ))}
                </div>

                {/* HubSpot Integration Feature */}
                <div className="relative rounded-3xl bg-white border border-zinc-200 p-8 md:p-12 overflow-hidden shadow-xl shadow-zinc-200/50">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-orange-500/5 rounded-full blur-3xl -mr-32 -mt-32" />
                    <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -ml-32 -mb-32" />

                    <div className="grid md:grid-cols-2 gap-12 items-center relative z-10">
                        <div>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 text-orange-500 text-sm font-medium mb-6">
                                <RefreshCw className="w-4 h-4" />
                                <span>Intégration native</span>
                            </div>
                            <h3 className="text-3xl md:text-4xl font-bold mb-6 text-zinc-900">
                                Synchronisation avec HubSpot
                            </h3>
                            <p className="text-lg text-zinc-600 mb-8">
                                Mettez à jour votre CRM automatiquement. Envoyez les données d'entreprises, contacts et insights directement dans HubSpot en un clic. Plus besoin de saisie manuelle.
                            </p>
                            <ul className="space-y-4">
                                {[
                                    'Synchronisation en un clic',
                                    'Mise à jour automatique des enregistrements existants',
                                    'Mapping des champs personnalisés sans effort',
                                    'Cohérence des données en temps réel'
                                ].map((item, i) => (
                                    <li key={i} className="flex items-center gap-3 text-zinc-700">
                                        <CheckCircle2 className="w-5 h-5 text-orange-500 flex-shrink-0" />
                                        <span>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="relative">
                            {/* Abstract Visual Representation of Sync */}
                            <div className="relative rounded-xl bg-zinc-50 border border-zinc-200 p-6 shadow-lg">
                                <div className="flex items-center justify-between mb-8">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-white border border-zinc-200 flex items-center justify-center shadow-sm">
                                            {/* Simple Logo Placeholder */}
                                            <div className="w-6 h-6 bg-zinc-900 rounded-sm" />
                                        </div>
                                        <div>
                                            <div className="h-2 w-24 bg-zinc-200 rounded mb-1" />
                                            <div className="h-2 w-16 bg-zinc-200 rounded" />
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                        <div className="w-2 h-2 rounded-full bg-zinc-300" />
                                        <div className="w-2 h-2 rounded-full bg-zinc-300" />
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    {[1, 2, 3].map((i) => (
                                        <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white border border-zinc-200 shadow-sm">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-zinc-100" />
                                                <div className="h-2 w-32 bg-zinc-200 rounded" />
                                            </div>
                                            <RefreshCw className="w-4 h-4 text-zinc-400" />
                                        </div>
                                    ))}
                                </div>

                                {/* Connection Line */}
                                <div className="absolute top-1/2 -right-6 w-12 h-0.5 bg-gradient-to-r from-orange-500 to-transparent hidden md:block" />
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );
}
