"use client";

import { useEffect, useState } from "react";

interface DebugWrapperProps {
  children: React.ReactNode;
  name: string;
}

export function DebugWrapper({ children, name }: DebugWrapperProps) {
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    console.log(`DebugWrapper ${name}: Component mounted`);
    return () => {
      console.log(`DebugWrapper ${name}: Component unmounted`);
    };
  }, [name]);

  if (error) {
    console.error(`DebugWrapper ${name}: Error caught:`, error);
    return (
      <div className="p-4 border border-red-500 bg-red-50 rounded max-h-64 overflow-y-auto">
        <h3 className="text-red-700 font-bold">Erreur dans {name}</h3>
        <div className="mt-2 max-h-20 overflow-y-auto">
          <p className="text-red-600 text-sm break-words">{error.message}</p>
        </div>
        <details className="mt-2">
          <summary className="text-xs text-red-500 cursor-pointer hover:text-red-700">
            Détails techniques
          </summary>
          <div className="mt-2 max-h-32 overflow-y-auto">
            <pre className="text-xs text-red-500 whitespace-pre-wrap break-words">
              {error.stack}
            </pre>
          </div>
        </details>
      </div>
    );
  }

  try {
    return <div data-debug-name={name}>{children}</div>;
  } catch (err) {
    console.error(`DebugWrapper ${name}: Error during render:`, err);
    setError(err instanceof Error ? err : new Error(String(err)));
    return null;
  }
}
