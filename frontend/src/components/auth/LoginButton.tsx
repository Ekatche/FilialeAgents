'use client';

import { useAuth } from '@/contexts/AuthContext';

interface LoginButtonProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoginButton({ className = '', size = 'md' }: LoginButtonProps) {
  const { login } = useAuth();

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <button
      onClick={login}
      className={`
        flex items-center justify-center gap-2
        bg-[#FF7A59] hover:bg-[#FF6444]
        text-white font-medium rounded-lg
        transition-colors duration-200
        shadow-md hover:shadow-lg
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {/* HubSpot Icon */}
      <svg
        className="w-5 h-5"
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M18.164 7.93V5.084a2.198 2.198 0 0 0-1.12-1.938L12.598.465a2.099 2.099 0 0 0-2.158 0l-4.447 2.68A2.198 2.198 0 0 0 4.871 5.085V7.93a5.654 5.654 0 1 0 2.04 9.601l3.838 2.313a2.1 2.1 0 0 0 2.158 0l3.838-2.313a5.654 5.654 0 1 0 2.04-9.601zm-3.986 11.36l-2.129 1.283-2.129-1.283a5.628 5.628 0 0 0 4.258 0zm-8.48-5.672a3.617 3.617 0 1 1 3.617 3.617 3.617 3.617 0 0 1-3.617-3.617zm3.617-7.926L12.049 3.8l2.734 1.647v3.294a5.628 5.628 0 0 0-4.468 0V5.692zm7.987 11.543a3.617 3.617 0 1 1 3.617-3.617 3.617 3.617 0 0 1-3.617 3.617z" />
      </svg>
      <span>Se connecter avec HubSpot</span>
    </button>
  );
}
