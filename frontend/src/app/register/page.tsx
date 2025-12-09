'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { ParticleBackground } from '@/components/ui/particle-background';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8012';

export default function RegisterPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, setUser, setTokens } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirmPassword: '',
    team_name: 'Local Development', // Valeur par défaut pour mode local
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    if (formData.password.length < 6) {
      setError('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }

    if (!formData.first_name || !formData.last_name || !formData.email) {
      setError('Tous les champs sont requis');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/auth/local/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          first_name: formData.first_name,
          last_name: formData.last_name,
          email: formData.email,
          password: formData.password,
          team_name: formData.team_name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur lors de l\'inscription');
      }

      const data = await response.json();

      // Formater les tokens pour l'AuthContext
      const authTokens = {
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type || 'bearer',
        expires_in: data.expires_in || 3600, // 1 heure par défaut
      };

      // Mettre à jour l'AuthContext
      setTokens(authTokens);
      setUser(data.user);

      // Rediriger vers le dashboard
      router.push('/dashboard');
    } catch (err) {
      console.error('Erreur inscription:', err);
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'inscription');
    } finally {
      setIsLoading(false);
    }
  };

  // Rediriger si déjà authentifié
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, authLoading, router]);

  // Afficher un loader pendant le chargement de l'auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#FE4D01] mx-auto mb-4" />
          <p className="text-zinc-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2">
      {/* Left Side - Visual & Branding */}
      <div className="relative hidden lg:flex flex-col justify-between p-12 pt-24 bg-black overflow-hidden">
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
            Commencez à analyser vos entreprises
          </h2>
          <p className="text-lg text-slate-300 leading-relaxed">
            Créez votre compte et accédez à notre plateforme d'intelligence artificielle pour l'analyse structurée d'entreprises et de leurs filiales.
          </p>
        </div>

        <div className="relative z-10 text-sm text-slate-500">
          © 2024 FilialeAgents. All rights reserved.
        </div>
      </div>

      {/* Right Side - Register Form */}
      <div className="flex items-center justify-center p-8 pt-24 bg-white min-h-screen">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
              Créer un compte
            </h1>
            <p className="mt-2 text-slate-500">
              Remplissez le formulaire pour commencer
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {/* Prénom et Nom */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="first_name" className="block text-sm font-medium text-slate-700 mb-2">
                  Prénom
                </label>
                <input
                  id="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#FE4D01] focus:border-[#FE4D01] transition-all text-black placeholder-slate-400"
                  placeholder="John"
                />
              </div>
              <div>
                <label htmlFor="last_name" className="block text-sm font-medium text-slate-700 mb-2">
                  Nom
                </label>
                <input
                  id="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#FE4D01] focus:border-[#FE4D01] transition-all text-black placeholder-slate-400"
                  placeholder="Doe"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                Email professionnel
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#FE4D01] focus:border-[#FE4D01] transition-all text-black placeholder-slate-400"
                placeholder="john.doe@example.com"
              />
            </div>

            {/* Nom de l'équipe (mode local - partagé) */}
            <div>
              <label htmlFor="team_name" className="block text-sm font-medium text-slate-700 mb-2">
                Organisation
              </label>
              <input
                id="team_name"
                type="text"
                value={formData.team_name}
                disabled
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 cursor-not-allowed"
                placeholder="Local Development"
              />
              <p className="mt-1 text-xs text-slate-500">
                En mode local, tous les utilisateurs partagent la même organisation pour faciliter les tests.
              </p>
            </div>

            {/* Mot de passe */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#FE4D01] focus:border-[#FE4D01] transition-all text-black placeholder-slate-400"
                placeholder="••••••••"
                minLength={6}
              />
              <p className="mt-1 text-xs text-slate-500">Minimum 6 caractères</p>
            </div>

            {/* Confirmation mot de passe */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-2">
                Confirmer le mot de passe
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                required
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#FE4D01] focus:border-[#FE4D01] transition-all text-black placeholder-slate-400"
                placeholder="••••••••"
                minLength={6}
              />
            </div>

            {/* Message d'erreur */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Bouton Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#FE4D01] hover:bg-[#FE4D01]/90 text-white font-medium px-6 py-4 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-[#FE4D01]/20 hover:shadow-xl hover:shadow-[#FE4D01]/30"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Création du compte...</span>
                </>
              ) : (
                <span>Créer mon compte</span>
              )}
            </button>

            {/* Lien vers login */}
            <div className="text-center pt-4">
              <p className="text-sm text-slate-500">
                Vous avez déjà un compte ?{' '}
                <Link href="/login/local" className="text-[#FE4D01] hover:underline font-medium">
                  Se connecter
                </Link>
              </p>
            </div>
          </form>

          {/* Info mode local */}
          <div className="text-center">
            <p className="text-xs text-slate-400">
              Mode test local • Pour production, utilisez{' '}
              <Link href="/login" className="text-slate-600 hover:text-[#FE4D01] underline">
                HubSpot OAuth
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
