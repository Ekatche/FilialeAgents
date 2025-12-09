'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Search, 
  History, 
  Settings, 
  DollarSign,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  LogOut
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/analyses', label: 'Analyses', icon: Search },
  { href: '/dashboard/historique', label: 'Historique', icon: History },
  { href: '/dashboard/couts', label: 'Coûts & API', icon: DollarSign },
  { href: '/dashboard/account', label: 'Paramètres', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('sidebarCollapsed') === 'true';
    }
    return false;
  });
  
  const isActive = (href: string) => {
    if (href === '/dashboard' && pathname === '/dashboard') return true;
    if (href !== '/dashboard' && pathname?.startsWith(href)) return true;
    return false;
  };

  return (
    <>
      {/* Mobile Hamburger Button */}
      <button
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-white border border-zinc-200 shadow-md hover:bg-zinc-100 transition-colors"
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <Menu className="w-6 h-6" />
        )}
      </button>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 h-screen bg-white border-r border-zinc-200 z-40 transition-all duration-300 ease-in-out flex flex-col",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          isCollapsed ? "w-20" : "w-64"
        )}
      >
        {/* Logo/Header */}
        <div className="p-6 border-b border-zinc-200 flex items-center justify-between flex-shrink-0">
          {!isCollapsed && (
            <Link
              href="/dashboard"
              className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
              onClick={() => setMobileMenuOpen(false)}
            >
              <div className="w-10 h-10 flex items-center justify-center">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 32 32"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M15.5 6.23193V0.5H23.1954L30.7185 8.25535V31.5786H23.5864L16.6647 25.2076L15.826 24.4357V25.5755V31.5786H7.91851L0.5 24.1762V0.5H8.40788L8.48824 0.891908L8.48993 0.900138L8.49189 0.908307L8.49217 0.909494L8.49234 0.910165C8.4953 0.922434 8.50053 0.943081 8.50848 0.971234L8.98967 0.835366L8.50848 0.97124C8.5244 1.0276 8.55115 1.11381 8.59237 1.22294L9.05671 1.04757L8.59237 1.22295C8.6749 1.44146 8.81468 1.74987 9.04016 2.09399C9.48867 2.77846 10.281 3.61237 11.6613 4.16449C12.8777 4.65107 13.8582 5.58062 14.6057 6.53935L15.5 7.68648V6.23193Z"
                    stroke="currentColor"
                    strokeWidth="1"
                  />
                </svg>
              </div>
              <span className="text-xl font-bold">Company Analyzer</span>
            </Link>
          )}
          {isCollapsed && (
            <Link
              href="/dashboard"
              className="flex items-center justify-center hover:opacity-80 transition-opacity"
              onClick={() => setMobileMenuOpen(false)}
            >
              <div className="w-10 h-10 flex items-center justify-center">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 32 32"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M15.5 6.23193V0.5H23.1954L30.7185 8.25535V31.5786H23.5864L16.6647 25.2076L15.826 24.4357V25.5755V31.5786H7.91851L0.5 24.1762V0.5H8.40788L8.48824 0.891908L8.48993 0.900138L8.49189 0.908307L8.49217 0.909494L8.49234 0.910165C8.4953 0.922434 8.50053 0.943081 8.50848 0.971234L8.98967 0.835366L8.50848 0.97124C8.5244 1.0276 8.55115 1.11381 8.59237 1.22294L9.05671 1.04757L8.59237 1.22295C8.6749 1.44146 8.81468 1.74987 9.04016 2.09399C9.48867 2.77846 10.281 3.61237 11.6613 4.16449C12.8777 4.65107 13.8582 5.58062 14.6057 6.53935L15.5 7.68648V6.23193Z"
                    stroke="currentColor"
                    strokeWidth="1"
                  />
                </svg>
              </div>
            </Link>
          )}
          {/* Collapse Button - Desktop only */}
          <button
            onClick={() => {
              const newState = !isCollapsed;
              setIsCollapsed(newState);
              localStorage.setItem('sidebarCollapsed', String(newState));
            }}
            className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg hover:bg-zinc-100 transition-colors text-zinc-600"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="px-4 py-6 space-y-2 flex-grow overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-lg transition-all duration-200",
                  "text-sm font-medium",
                  isCollapsed ? "justify-center px-3 py-3" : "px-4 py-3",
                  active
                    ? "bg-[#FE4D01] text-white shadow-sm"
                    : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900"
                )}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!isCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-200 space-y-4 flex-shrink-0 bg-white">
          {/* Logout Button */}
          <button
            onClick={logout}
            className={cn(
              "w-full flex items-center gap-3 rounded-lg transition-all duration-200",
              "text-sm font-medium text-red-600 hover:bg-red-50 hover:text-red-700",
              isCollapsed ? "justify-center px-3 py-3" : "px-4 py-3"
            )}
            title={isCollapsed ? "Se déconnecter" : undefined}
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!isCollapsed && <span>Se déconnecter</span>}
          </button>

          {!isCollapsed && (
            <div className="text-xs text-zinc-500 text-center pt-2">
              Version 1.0.0
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

