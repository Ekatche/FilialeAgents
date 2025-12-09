import React from 'react';
import { Building2, Globe, TrendingUp, Shield } from 'lucide-react';

const features = [
    {
        icon: <Building2 className="w-8 h-8 text-blue-600" />,
        title: 'Informations complètes',
        description: "Siège social, secteur d'activité, données financières",
    },
    {
        icon: <Globe className="w-8 h-8 text-green-600" />,
        title: 'Filiales internationales',
        description: "Structure organisationnelle et présence mondiale",
    },
    {
        icon: <TrendingUp className="w-8 h-8 text-purple-600" />,
        title: 'Analyse intelligente',
        description: "Détection automatique des relations entre entreprises",
    },
    {
        icon: <Shield className="w-8 h-8 text-orange-600" />,
        title: 'Sources fiables',
        description: "Données vérifiées avec score de confiance",
    },
];

export function FeaturesGrid() {
    return (
        <section className="py-16 bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
                    Nos fonctionnalités
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {features.map((f, idx) => (
                        <div
                            key={idx}
                            className="bg-white/70 backdrop-blur-sm rounded-xl p-6 text-center shadow-lg hover:shadow-xl transition-shadow"
                        >
                            <div className="flex justify-center mb-4">{f.icon}</div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                {f.title}
                            </h3>
                            <p className="text-sm text-gray-600">{f.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
