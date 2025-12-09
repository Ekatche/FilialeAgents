'use client';

import { usePathname } from 'next/navigation';
import { Header } from '@/components/navigation/Header';

export function ConditionalHeader() {
  const pathname = usePathname();
  const isDashboard = pathname?.startsWith('/dashboard');
  
  if (isDashboard) {
    return null;
  }
  
  return <Header />;
}

