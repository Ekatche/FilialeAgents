'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { ParticleBackground } from '@/components/ui/particle-background';

export default function LoginPage() {
  const { isAuthenticated, isLoading, login } = useAuth();
  const router = useRouter();

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleLogin = () => {
    login();
  };

  if (isLoading) {
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
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
              Bienvenue
            </h1>
            <p className="mt-2 text-slate-500">
              Connectez-vous pour accéder à votre espace de travail
            </p>
          </div>

          <div className="mt-8 space-y-6">
            {/* HubSpot Login Button */}
            <button
              onClick={handleLogin}
              className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 border-2 border-slate-100 hover:border-[#FE4D01] bg-white hover:bg-orange-50/30 text-slate-700 hover:text-[#FE4D01] rounded-xl transition-all duration-300 font-medium text-[15px]"
            >
              <svg className="w-5 h-5 text-[#ff7a59]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.164 7.93V5.084a2.198 2.198 0 0 0-1.12-1.938L12.598.465a2.099 2.099 0 0 0-2.158 0l-4.447 2.68A2.198 2.198 0 0 0 4.871 5.085V7.93a5.654 5.654 0 1 0 2.04 9.601l3.838 2.313a2.1 2.1 0 0 0 2.158 0l3.838-2.313a5.654 5.654 0 1 0 2.04-9.601zm-3.986 11.36l-2.129 1.283-2.129-1.283a5.628 5.628 0 0 0 4.258 0zm-8.48-5.672a3.617 3.617 0 1 1 3.617 3.617 3.617 3.617 0 0 1-3.617-3.617zm3.617-7.926L12.049 3.8l2.734 1.647v3.294a5.628 5.628 0 0 0-4.468 0V5.692zm7.987 11.543a3.617 3.617 0 1 1 3.617-3.617 3.617 3.617 0 0 1-3.617 3.617z" />
              </svg>
              <span>Continuer avec HubSpot</span>
              <div className="absolute right-4 opacity-0 group-hover:opacity-100 transition-opacity text-[#FE4D01]">
                →
              </div>
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-100"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-slate-400">ou</span>
              </div>
            </div>

            {/* Local Login Button */}
            <Link href="/login/local">
              <button className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 border-2 border-slate-100 hover:border-[#FE4D01] bg-white hover:bg-orange-50/30 text-slate-700 hover:text-[#FE4D01] rounded-xl transition-all duration-300 font-medium text-[15px]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
                <span>Connexion locale (email/mot de passe)</span>
                <div className="absolute right-4 opacity-0 group-hover:opacity-100 transition-opacity text-[#FE4D01]">
                  →
                </div>
              </button>
            </Link>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-100"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-slate-400">ou</span>
              </div>
            </div>

            {/* Local Register Button */}
            <Link href="/register">
              <button className="w-full group relative flex items-center justify-center gap-3 px-6 py-4 border-2 border-slate-100 hover:border-[#FE4D01] bg-white hover:bg-orange-50/30 text-slate-700 hover:text-[#FE4D01] rounded-xl transition-all duration-300 font-medium text-[15px]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>Créer un compte (mode test local)</span>
                <div className="absolute right-4 opacity-0 group-hover:opacity-100 transition-opacity text-[#FE4D01]">
                  →
                </div>
              </button>
            </Link>

            <div className="text-center">
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
          </div>
        </div>
      </div>
    </div>
  );
}
