'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, ArrowLeft } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { ParticleBackground } from '@/components/ui/particle-background';

export default function LocalLoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, loginLocal } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  // Rediriger si déjà authentifié
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.email || !formData.password) {
      setError('Email et mot de passe requis');
      return;
    }

    setIsLoading(true);

    try {
      const success = await loginLocal(formData.email, formData.password);

      if (success) {
        // Rediriger vers le dashboard
        router.push('/dashboard');
      } else {
        setError('Identifiants invalides ou erreur de connexion');
      }
    } catch (err) {
      console.error('Erreur connexion:', err);
      setError('Erreur inattendue lors de la connexion');
    } finally {
      setIsLoading(false);
    }
  };

  // Afficher un loader pendant le chargement de l'auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#FE4D01]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2">
      {/* Left Side - Visual & Branding */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-black overflow-hidden">
        {/* Background Image */}
        <div className="absolute inset-0 z-0">
          <Image
            src="/images/home-background.png"
            alt="Background"
            fill
            className="object-cover opacity-60"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/80" />
        </div>

        {/* Animated Particles Background */}
        <ParticleBackground
          className="absolute inset-0 w-full h-full"
          style={{ zIndex: 1 }}
        />

        {/* Content */}
        <div className="relative z-10">
          <Link href="/" className="flex items-center gap-2 text-white hover:opacity-80 transition-opacity w-fit">
            <div className="w-8 h-8 flex items-center justify-center bg-white rounded-lg">
              <svg width="20" height="20" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M15.5 6.23193V0.5H23.1954L30.7185 8.25535V31.5786H23.5864L16.6647 25.2076L15.826 24.4357V25.5755V31.5786H7.91851L0.5 24.1762V0.5H8.40788L8.48824 0.891908L8.48993 0.900138L8.49189 0.908307L8.49217 0.909494L8.49234 0.910165C8.4953 0.922434 8.50053 0.943081 8.50848 0.971234L8.98967 0.835366L8.50848 0.97124C8.5244 1.0276 8.55115 1.11381 8.59237 1.22294L9.05671 1.04757L8.59237 1.22295C8.6749 1.44146 8.81468 1.74987 9.04016 2.09399C9.48867 2.77846 10.281 3.61237 11.6613 4.16449C12.8777 4.65107 13.8582 5.58062 14.6057 6.53935L15.5 7.68648V6.23193Z" stroke="#000000" strokeWidth="1" />
              </svg>
            </div>
            <span className="font-bold text-xl tracking-tight">FilialeAgents</span>
          </Link>
        </div>

        <div className="relative z-10 max-w-lg">
          <h2 className="text-4xl font-bold text-white mb-6 leading-tight">
            Intelligence artificielle pour l'analyse d'entreprise
          </h2>
          <p className="text-lg text-slate-300 leading-relaxed">
            Accédez à des données structurées, visualisez les relations corporatives et prenez des décisions éclairées grâce à notre technologie avancée.
          </p>
        </div>

        <div className="relative z-10 text-sm text-slate-500">
          © 2024 FilialeAgents. All rights reserved.
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <Link href="/login" className="inline-flex items-center gap-2 text-slate-600 hover:text-[#FE4D01] mb-6 transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Retour</span>
            </Link>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
              Connexion locale
            </h1>
            <p className="mt-2 text-slate-500">
              Connectez-vous avec votre email et mot de passe
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                Email
              </label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="w-full px-4 py-3 border-2 border-slate-100 rounded-xl focus:border-[#FE4D01] focus:ring-0 bg-white text-slate-900 placeholder:text-slate-400 transition-colors"
                placeholder="john.doe@example.com"
                autoComplete="email"
              />
            </div>

            {/* Mot de passe */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                Mot de passe
              </label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="w-full px-4 py-3 border-2 border-slate-100 rounded-xl focus:border-[#FE4D01] focus:ring-0 bg-white text-slate-900 placeholder:text-slate-400 transition-colors"
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>

            {/* Message d'erreur */}
            {error && (
              <div className="p-4 bg-red-50 border-2 border-red-200 rounded-xl text-sm text-red-600">
                {error}
              </div>
            )}

            {/* Bouton Submit */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 bg-[#FE4D01] hover:bg-[#FE4D01]/90 text-white rounded-xl transition-all duration-300 font-medium text-[15px] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Connexion en cours...</span>
                </>
              ) : (
                <>
                  <span>Se connecter</span>
                  <div className="absolute right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    →
                  </div>
                </>
              )}
            </Button>

            {/* Lien vers register */}
            <div className="text-center text-sm text-slate-500">
              Pas encore de compte ?{' '}
              <Link href="/register" className="text-[#FE4D01] hover:underline font-medium">
                S'inscrire
              </Link>
            </div>

            {/* Info mode local */}
            <div className="text-center text-xs text-slate-400">
              Mode authentification locale (pour tests)
            </div>

            {/* Footer */}
            <div className="text-center pt-4">
              <p className="text-sm text-slate-400">
                En vous connectant, vous acceptez nos{' '}
                <Link href="/terms" className="text-slate-600 hover:text-[#FE4D01] underline underline-offset-4">
                  Conditions d'utilisation
                </Link>
                {' '}et notre{' '}
                <Link href="/privacy" className="text-slate-600 hover:text-[#FE4D01] underline underline-offset-4">
                  Politique de confidentialité
                </Link>
                .
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
