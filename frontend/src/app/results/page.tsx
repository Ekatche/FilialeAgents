import { Suspense } from "react";
import { ResultsPage } from "@/components/results/results-page";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import { DebugWrapper } from "@/components/debug/debug-wrapper";

function ResultsPageWrapper() {
  return (
    <ErrorBoundary>
      <DebugWrapper name="ResultsPage">
        <ResultsPage />
      </DebugWrapper>
    </ErrorBoundary>
  );
}

export default function Results() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Chargement des résultats...</p>
          </div>
        </div>
      }
    >
      <ResultsPageWrapper />
    </Suspense>
  );
}
