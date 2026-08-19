import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ProductResult, SearchResponse } from "@/lib/api";
import { formatAUD, formatVolume, retailerLabel } from "@/lib/utils";

type SortKey = "price" | "price_per_litre" | "volume" | "retailer";

type Props = { response: SearchResponse | null; loading: boolean };

export function ResultsView({ response, loading }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("price_per_litre");
  const [retailerFilter, setRetailerFilter] = useState<string>("all");
  const [exactSize, setExactSize] = useState<boolean>(false);
  const [inStockOnly, setInStockOnly] = useState<boolean>(false);
  const [sizeFilter, setSizeFilter] = useState<string>("all");

  const sorted = useMemo(() => {
    if (!response) return [];
    let items = response.results.slice();
    if (retailerFilter !== "all") items = items.filter((r) => r.retailer === retailerFilter);
    if (inStockOnly) items = items.filter((r) => r.available);
    if (exactSize && sizeFilter !== "all") {
      const targetMl = Number(sizeFilter);
      items = items.filter((r) => r.volume_ml === targetMl);
    } else if (sizeFilter !== "all") {
      const targetMl = Number(sizeFilter);
      items = items.filter((r) => r.volume_ml === targetMl);
    }

    items.sort((a, b) => {
      switch (sortKey) {
        case "price":
          return Number(a.price) - Number(b.price);
        case "price_per_litre":
          return (
            (a.price_per_litre == null ? Number.POSITIVE_INFINITY : Number(a.price_per_litre)) -
            (b.price_per_litre == null ? Number.POSITIVE_INFINITY : Number(b.price_per_litre))
          );
        case "volume":
          return (a.volume_ml ?? Number.POSITIVE_INFINITY) - (b.volume_ml ?? Number.POSITIVE_INFINITY);
        case "retailer":
          return a.retailer.localeCompare(b.retailer);
      }
    });
    return items;
  }, [response, sortKey, retailerFilter, exactSize, inStockOnly, sizeFilter]);

  // Annotate best-price and best-$/L
  const bestPriceId = useMemo(() => {
    if (sorted.length === 0) return null;
    let best = sorted[0];
    for (const r of sorted) {
      if (Number(r.price) < Number(best.price)) best = r;
    }
    return best.retailer_product_id;
  }, [sorted]);

  const bestPplId = useMemo(() => {
    const withPpl = sorted.filter((r) => r.price_per_litre != null);
    if (withPpl.length === 0) return null;
    let best = withPpl[0];
    for (const r of withPpl) {
      if (Number(r.price_per_litre!) < Number(best.price_per_litre!)) best = r;
    }
    return best.retailer_product_id;
  }, [sorted]);

  const retailersInResults = useMemo(() => {
    if (!response) return [];
    return Array.from(new Set(response.results.map((r) => r.retailer)));
  }, [response]);

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!response) return null;

  if (response.results.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No matching products found</CardTitle>
          <CardDescription>
            Try a broader product name (e.g. "Jack Daniels" instead of "Jack Daniel's
            Single Barrel Select 750ml") or remove the bottle-size filter.
          </CardDescription>
        </CardHeader>
        {response.errors.length > 0 && (
          <CardContent>
            <ErrorAlert errors={response.errors} />
          </CardContent>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {response.errors.length > 0 && (
        <ErrorAlert errors={response.errors} resultsCount={response.results.length} />
      )}

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Sort by</label>
              <Select value={sortKey} onValueChange={(v) => setSortKey(v as SortKey)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="price_per_litre">$ / L (best value)</SelectItem>
                  <SelectItem value="price">Lowest purchase price</SelectItem>
                  <SelectItem value="volume">Bottle size</SelectItem>
                  <SelectItem value="retailer">Retailer</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Retailer</label>
              <Select value={retailerFilter} onValueChange={setRetailerFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All retailers</SelectItem>
                  {retailersInResults.map((r) => (
                    <SelectItem key={r} value={r}>
                      {retailerLabel(r)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Size</label>
              <Select value={sizeFilter} onValueChange={setSizeFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All sizes</SelectItem>
                  <SelectItem value="200">200 mL</SelectItem>
                  <SelectItem value="375">375 mL</SelectItem>
                  <SelectItem value="700">700 mL</SelectItem>
                  <SelectItem value="750">750 mL</SelectItem>
                  <SelectItem value="1000">1 L</SelectItem>
                  <SelectItem value="1136">1.136 L</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant={exactSize ? "default" : "outline"}
              size="sm"
              onClick={() => setExactSize((v) => !v)}
              disabled={sizeFilter === "all"}
            >
              {exactSize ? "Exact size only ✓" : "Exact size only"}
            </Button>
            <Button
              variant={inStockOnly ? "default" : "outline"}
              size="sm"
              onClick={() => setInStockOnly((v) => !v)}
            >
              {inStockOnly ? "In stock only ✓" : "In stock only"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Retailer</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Size</TableHead>
                <TableHead className="text-right">Price</TableHead>
                <TableHead className="text-right">$ / L</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Checked</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((r) => (
                <ResultRow
                  key={`${r.retailer}-${r.retailer_product_id}`}
                  r={r}
                  isCheapest={r.retailer_product_id === bestPriceId}
                  isBestPpl={r.retailer_product_id === bestPplId}
                />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Cheapest = lowest current purchase price. Best $/L = lowest cost per litre
        across all sizes. Sorted by{" "}
        <span className="font-medium">
          {sortKey === "price_per_litre"
            ? "best $/L"
            : sortKey === "price"
              ? "lowest purchase price"
              : sortKey === "volume"
                ? "bottle size"
                : "retailer"}
        </span>
        .
      </p>
    </div>
  );
}

function ResultRow({
  r,
  isCheapest,
  isBestPpl,
}: {
  r: ProductResult;
  isCheapest: boolean;
  isBestPpl: boolean;
}) {
  return (
    <TableRow>
      <TableCell className="font-medium">{retailerLabel(r.retailer)}</TableCell>
      <TableCell>
        <a
          href={r.url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline text-foreground"
        >
          {r.name}
        </a>
        {!r.location_aware && (
          <span
            className="ml-2 text-xs text-muted-foreground"
            title="This price was not obtained with a specific location context"
          >
            (national)
          </span>
        )}
      </TableCell>
      <TableCell>{formatVolume(r.volume_ml)}</TableCell>
      <TableCell className="text-right tabular-nums">
        <div className="flex flex-col items-end gap-0.5">
          <span className="font-medium">{formatAUD(r.price)}</span>
          {r.on_sale && r.regular_price && (
            <span className="text-xs text-muted-foreground line-through">
              was {formatAUD(r.regular_price)}
            </span>
          )}
        </div>
      </TableCell>
      <TableCell className="text-right tabular-nums">
        {r.price_per_litre != null ? formatAUD(r.price_per_litre) : "—"}
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {isCheapest && <Badge variant="success">Cheapest</Badge>}
          {isBestPpl && <Badge variant="success">Best $/L</Badge>}
          {r.on_sale && <Badge variant="warning">Special</Badge>}
          {!r.available && <Badge variant="destructive">Out of stock</Badge>}
          {!isCheapest && !isBestPpl && r.available && !r.on_sale && (
            <Badge variant="outline">{retailerLabel(r.retailer)}</Badge>
          )}
        </div>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground">
        {new Date(r.observed_at).toLocaleTimeString()}
      </TableCell>
    </TableRow>
  );
}

function ErrorAlert({
  errors,
  resultsCount,
}: {
  errors: { retailer: string; message: string }[];
  resultsCount?: number;
}) {
  const failed = errors.map((e) => retailerLabel(e.retailer)).join(", ");
  return (
    <Alert variant="warning">
      <AlertTitle>Some retailers could not be searched</AlertTitle>
      <AlertDescription>
        {failed}
        {resultsCount != null && resultsCount > 0
          ? ` could not be searched. Results from other retailers are still shown.`
          : ` could not be searched.`}
      </AlertDescription>
    </Alert>
  );
}