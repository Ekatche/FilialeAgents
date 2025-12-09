'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface YearSelectorProps {
  availableYears: number[];
  selectedYears: number[];
  onYearsChange: (years: number[]) => void;
}

export function YearSelector({ availableYears, selectedYears, onYearsChange }: YearSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const toggleYear = (year: number) => {
    if (selectedYears.includes(year)) {
      // Si toutes les années sont sélectionnées et qu'on en désélectionne une, garder au moins une
      if (selectedYears.length === 1) {
        return; // Ne pas permettre de tout désélectionner
      }
      onYearsChange(selectedYears.filter((y) => y !== year));
    } else {
      onYearsChange([...selectedYears, year]);
    }
  };

  const selectAllYears = () => {
    onYearsChange(availableYears);
  };

  const clearSelection = () => {
    // Garder au moins l'année la plus récente
    const currentYear = Math.max(...availableYears);
    onYearsChange([currentYear]);
  };

  const displayText =
    selectedYears.length === availableYears.length
      ? 'Toutes les années'
      : selectedYears.length === 1
      ? `${selectedYears[0]}`
      : `${selectedYears.length} années`;

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="min-w-[200px] justify-between"
      >
        <span>{displayText}</span>
        <ChevronDown className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </Button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-zinc-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
          <div className="p-2 border-b border-zinc-200 flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={selectAllYears}
              className="flex-1 text-xs"
            >
              Tout sélectionner
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearSelection}
              className="flex-1 text-xs"
            >
              Réinitialiser
            </Button>
          </div>
          <div className="p-2">
            {availableYears.map((year) => {
              const isSelected = selectedYears.includes(year);
              return (
                <label
                  key={year}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-zinc-50 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleYear(year)}
                    className="w-4 h-4 rounded border-zinc-300 text-[#FE4D01] focus:ring-[#FE4D01] focus:ring-offset-0"
                  />
                  <span className="flex-1 text-sm text-zinc-900">{year}</span>
                  {isSelected && <Check className="w-4 h-4 text-[#FE4D01]" />}
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

