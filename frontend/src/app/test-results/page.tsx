import { Suspense } from "react";
import { SimpleResults } from "@/components/test/simple-results";
import { ErrorBoundary } from "@/components/ui/error-boundary";

export default function TestResults() {
  return (
    <Suspense fallback={<div>Loading test...</div>}>
      <ErrorBoundary>
        <SimpleResults />
      </ErrorBoundary>
    </Suspense>
  );
}
