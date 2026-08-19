import { useState } from "react";
import { Toaster } from "@/components/ui/sonner";
import { SearchForm } from "@/components/SearchForm";
import { ResultsView } from "@/components/ResultsView";
import { HealthBadge } from "@/components/HealthBadge";
import type { SearchResponse } from "@/lib/api";

export default function App() {
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-semibold tracking-tight">🥄 Scoop</span>
            <span className="text-sm text-muted-foreground hidden sm:inline">
              Australian Liquor Price Search — POC
            </span>
          </div>
          <HealthBadge />
        </div>
      </header>

      <main className="container py-6 space-y-6">
        <SearchForm
          onResults={setResponse}
          onLoading={setLoading}
          initial={{ query: "Jack Daniels", postcode: "4000" }}
        />
        <ResultsView response={response} loading={loading} />
      </main>

      <footer className="container py-6 text-xs text-muted-foreground border-t">
        Live results from Dan Murphy&apos;s, BWS, Liquorland. Pricing varies by
        location; refreshes are cached for 30 minutes. Historical observations are
        retained in PostgreSQL.
      </footer>

      <Toaster />
    </div>
  );
}