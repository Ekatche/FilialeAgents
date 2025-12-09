'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ParticleBackground } from '@/components/ui/particle-background';

export function HeroSection() {
  return (
    <div className="w-full min-h-screen bg-white px-4 pb-4 pt-0">
      {/* Hero Container - Dark background with background image */}
      <div
        className="w-full relative overflow-hidden rounded-b-[2.5rem] rounded-t-none"
        style={{
          backgroundColor: '#000000',
          minHeight: 'calc(100vh - 1rem)', // Adjust height to account for bottom padding only
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Background Image */}
        <div className="absolute inset-0 z-0">
          <Image
            src="/images/home-background.png"
            alt="Hero Background"
            fill
            className="object-cover"
            style={{
              objectPosition: 'center center',
            }}
            priority
          />
          {/* Dark Overlay for readability */}
          <div className="absolute inset-0 bg-black/30" />
        </div>

        {/* Animated Particles Background */}
        <ParticleBackground
          className="absolute inset-0 w-full h-full"
          style={{ zIndex: 1 }}
        />

        {/* Overlay pour masquer le logo Gemini en bas à droite */}
        <div 
          className="absolute bottom-0 right-0 w-40 h-20"
          style={{ 
            zIndex: 2,
            background: 'linear-gradient(135deg, transparent 0%, transparent 30%, rgba(0,0,0,0.9) 50%, rgba(0,0,0,0.9) 100%)',
          }}
        />

        {/* Content Wrapper */}
        <div className="relative z-10 flex flex-col items-center justify-center w-full max-w-5xl mx-auto px-6 text-center">

          {/* Title */}
          <h1
            style={{
              color: 'rgb(255, 255, 255)',
              fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
              fontSize: '90px', // Increased size
              fontWeight: 600, // Slightly bolder
              lineHeight: '1.1',
              marginBottom: '30px',
              letterSpacing: '-0.03em',
            }}
          >
            Cartographiez les entreprises
            <br />
            en quelques clics
          </h1>

          {/* Description */}
          <p
            style={{
              color: 'rgba(255, 255, 255, 0.9)',
              fontSize: '18px',
              lineHeight: '1.6',
              maxWidth: '600px',
              margin: '0 auto 40px auto',
            }}
          >
            Analysez n'importe quelle entreprise automatiquement. Extrayez des informations détaillées sur
            les filiales, la structure organisationnelle et les relations commerciales grâce à notre API IA.
          </p>

          {/* CTA Button */}
          <Link
            href="/notre-outil"
            className="inline-flex items-center justify-center gap-2.5 transition-all duration-300 hover:scale-105"
            style={{
              border: '2px solid rgb(254, 77, 1)',
              backgroundColor: 'rgb(254, 77, 1)',
              color: 'rgb(255, 255, 255)',
              padding: '18px 40px',
              textDecoration: 'none',
              fontSize: '16px',
              fontWeight: 500,
              borderRadius: '100px', // More rounded like modern buttons
              boxShadow: '0 4px 20px rgba(254, 77, 1, 0.3)',
            }}
          >
            <span>Découvrir l'outil</span>
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M4.20687 14.938L13.1804 5.96443C13.4511 5.69377 13.2594 5.23097 12.8766 5.23098L4 5.23118L4 4L16.0301 4L16.0301 16.0301H14.7989L14.7989 7.13951C14.7989 6.75674 14.3361 6.56505 14.0655 6.8357L5.08481 15.8159L4.20687 14.938Z"
                fill="white"
              />
            </svg>
          </Link>
        </div>
      </div>
    </div>
  );
}
