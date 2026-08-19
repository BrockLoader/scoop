import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { searchProducts, type SearchResponse } from "@/lib/api";
import { toast } from "sonner";

export type SearchState = {
  query: string;
  postcode: string;
  volume_ml: number | null;
};

type Props = {
  onResults: (r: SearchResponse) => void;
  onLoading: (loading: boolean) => void;
  initial?: Partial<SearchState>;
};

const VOLUME_OPTIONS: { label: string; ml: number | null }[] = [
  { label: "Any size", ml: null },
  { label: "200 mL", ml: 200 },
  { label: "375 mL", ml: 375 },
  { label: "500 mL", ml: 500 },
  { label: "700 mL", ml: 700 },
  { label: "750 mL", ml: 750 },
  { label: "1 L", ml: 1000 },
  { label: "1.136 L", ml: 1136 },
];

export function SearchForm({ onResults, onLoading, initial }: Props) {
  const [query, setQuery] = useState(initial?.query ?? "Jack Daniels");
  const [postcode, setPostcode] = useState(initial?.postcode ?? "4000");
  const [volumeLabel, setVolumeLabel] = useState(
    VOLUME_OPTIONS.find((v) => v.ml === (initial?.volume_ml ?? 1000))?.label ?? "1 L",
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // run once on mount
    void runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runSearch() {
    const trimmed = query.trim();
    if (!trimmed) return;
    const volume = VOLUME_OPTIONS.find((v) => v.label === volumeLabel)?.ml ?? null;
    setLoading(true);
    onLoading(true);
    try {
      const r = await searchProducts(trimmed, postcode.trim(), volume ?? undefined);
      onResults(r);
      if (r.errors.length > 0) {
        toast.warning(
          `Some retailers failed: ${r.errors.map((e) => e.retailer).join(", ")}`,
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Search failed: ${msg}`);
      onResults({ query: trimmed, postcode, results: [], errors: [{ retailer: "search", message: msg }] });
    } finally {
      setLoading(false);
      onLoading(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void runSearch();
          }}
          className="grid gap-3 md:grid-cols-[1fr_180px_180px_auto] md:items-end"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Product</label>
            <Input
              data-testid="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Jack Daniels"
              autoComplete="off"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Postcode</label>
            <Input
              data-testid="postcode-input"
              value={postcode}
              onChange={(e) => setPostcode(e.target.value)}
              placeholder="4000"
              inputMode="numeric"
              maxLength={10}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Bottle size</label>
            <Select value={volumeLabel} onValueChange={setVolumeLabel}>
              <SelectTrigger data-testid="volume-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {VOLUME_OPTIONS.map((v) => (
                  <SelectItem key={v.label} value={v.label}>
                    {v.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" disabled={loading} data-testid="search-button">
            {loading ? "Searching…" : "Search"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}