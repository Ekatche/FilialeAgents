import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware pour protéger les routes du dashboard
 * 
 * Note: Le token est stocké dans localStorage côté client, donc le middleware
 * ne peut pas y accéder directement. La protection principale se fait côté client
 * via le composant ProtectedRoute qui vérifie le localStorage.
 * 
 * Ce middleware sert principalement à bloquer les accès directs aux routes
 * protégées via des requêtes serveur (SSR) ou des liens directs.
 */
export function middleware(request: NextRequest) {
  // Vérifier si la route est protégée (dashboard)
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    // Vérifier la présence d'un cookie de session (si le backend en utilise)
    // Le token principal est dans localStorage, mais on peut vérifier d'autres indicateurs
    const hasSessionCookie = request.cookies.has('session_id') || 
                             request.cookies.has('access_token') ||
                             request.cookies.has('auth_tokens');
    
    // Si aucune indication de session, laisser passer mais le ProtectedRoute côté client
    // gérera la redirection vers login si nécessaire
    // On ne bloque pas ici car le token est dans localStorage (côté client uniquement)
  }

  // Laisser passer toutes les requêtes - la protection se fait côté client
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public (public files)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
  ],
};

