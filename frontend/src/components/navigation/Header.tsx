'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, User } from 'lucide-react';

interface DropdownItem {
  label: string;
  href: string;
}

interface NavItem {
  label: string;
  href: string;
  dropdown?: DropdownItem[];
}

const navItems: NavItem[] = [
  { label: 'Accueil', href: '/' },
  { label: "L'outil", href: '/notre-outil' },
  { label: 'Fonctionnement', href: '/about' },
];

export function Header() {
  const pathname = usePathname();
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }

      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  const isActive = (href: string) => {
    if (href === '/' && pathname === '/') return true;
    if (href !== '/' && pathname.startsWith(href)) return true;
    return false;
  };

  return (

    <header
      className={`w-full fixed top-0 z-50 bg-transparent pointer-events-none transition-transform duration-300 ease-in-out ${isVisible ? 'translate-y-0' : '-translate-y-full'
        }`}
    >
      <div className="relative w-full pointer-events-auto">
        {/* White background bridge */}
        <span className="absolute top-0 left-0 w-full h-[10px] bg-white z-10" />

        <div className="w-full flex items-start justify-between relative z-10">
          {/* LEFT SECTION: Logo + Navigation */}
          <div className="flex items-center gap-12 pl-5 sm:pl-8 lg:pl-12 pr-8 py-5 relative bg-white rounded-br-[30px] shadow-[0_4px_20px_rgba(0,0,0,0.08)]">
            {/* Fillet Span Left - Connects to bridge with concave curve */}
            <span
              className="absolute right-[-30px] top-0 w-[40px] h-[40px] bg-white z-[5]"
              style={{
                maskImage: 'radial-gradient(circle at 100% 100%, transparent 30px, black 31px)',
                WebkitMaskImage: 'radial-gradient(circle at 100% 100%, transparent 30px, black 31px)',
              }}
            />

            {/* Logo */}
            <Link
              href="/"
              className="flex items-center gap-2.5 hover:opacity-80 transition-opacity flex-shrink-0"
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
                    stroke="#000000"
                    strokeWidth="1"
                  />
                </svg>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-10">
              {navItems.map((item) => (
                <div key={item.label} className="relative group">
                  <Link
                    href={item.href}
                    className="flex items-center gap-1.5 transition-colors duration-200 hover:opacity-70 text-[15px] font-medium text-black no-underline"
                  >
                    {item.label}
                  </Link>
                </div>
              ))}
            </nav>
          </div>

          {/* RIGHT SECTION: CTA Button */}
          <div className="hidden lg:flex pl-8 pr-5 sm:pr-8 lg:pr-12 py-5 relative bg-white rounded-bl-[30px] shadow-[0_4px_20px_rgba(0,0,0,0.08)]">
            {/* Fillet Span Right - Connects to bridge with concave curve */}
            <span
              className="absolute left-[-30px] top-0 w-[40px] h-[40px] bg-white z-[5]"
              style={{
                maskImage: 'radial-gradient(circle at 0% 100%, transparent 30px, black 31px)',
                WebkitMaskImage: 'radial-gradient(circle at 0% 100%, transparent 30px, black 31px)',
              }}
            />
            <div className="flex items-center gap-6 relative z-20">
              <Link
                href="/login"
                className="flex items-center gap-2 text-[15px] font-medium text-black hover:opacity-70 transition-opacity no-underline relative z-20 cursor-pointer"
              >
                <User className="w-5 h-5" />
                <span>Login</span>
              </Link>
              <a
                href="https://www.agencenile.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2.5 transition-all duration-300 hover:scale-105 bg-[#FE4D01] text-white rounded-full px-[30px] py-[12px] text-[14px] font-semibold no-underline border-none"
              >
                <span>Get in touch</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M4.20687 14.938L13.1804 5.96443C13.4511 5.69377 13.2594 5.23097 12.8766 5.23098L4 5.23118L4 4L16.0301 4L16.0301 16.0301H14.7989L14.7989 7.13951C14.7989 6.75674 14.3361 6.56505 14.0655 6.8357L5.08481 15.8159L4.20687 14.938Z"
                    fill="white"
                  />
                </svg>
              </a>
            </div>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 transition-colors text-black"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-100 py-4 px-5 bg-white">
            <nav className="flex flex-col gap-4">
              {navItems.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  className="text-lg font-medium text-black"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
              <Link
                href="/login"
                className="flex items-center gap-2 text-lg font-medium text-black"
                onClick={() => setMobileMenuOpen(false)}
              >
                <User className="w-5 h-5" />
                <span>Login</span>
              </Link>
              <a
                href="https://www.agencenile.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 flex items-center justify-center gap-2 w-full py-3 rounded-full font-medium bg-[#FE4D01] text-white"
              >
                Get in touch
              </a>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
