export type ProductResult = {
  retailer: string;
  retailer_product_id: string;
  name: string;
  brand: string;
  variant: string | null;
  volume_ml: number | null;
  price: number;
  regular_price: number | null;
  sale_price: number | null;
  price_per_litre: number | null;
  available: boolean;
  on_sale: boolean;
  url: string;
  observed_at: string;
  postcode: string | null;
  store_identifier: string | null;
  location_aware: boolean;
};

export type SearchError = { retailer: string; message: string };

export type SearchResponse = {
  query: string;
  postcode: string | null;
  results: ProductResult[];
  errors: SearchError[];
};

export type Retailer = {
  id: number;
  name: string;
  slug: string;
  base_url: string;
  enabled: boolean;
};

const BASE = ""; // vite proxy rewrites /api → backend root

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export async function searchProducts(
  q: string,
  postcode: string,
  volume_ml?: number,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, postcode });
  if (volume_ml) params.set("volume_ml", String(volume_ml));
  const res = await fetch(`${BASE}/api/search?${params.toString()}`, {
    signal,
    headers: { Accept: "application/json" },
  });
  return jsonOrThrow<SearchResponse>(res);
}

export async function listRetailers(): Promise<Retailer[]> {
  const res = await fetch(`${BASE}/api/retailers`);
  return jsonOrThrow<Retailer[]>(res);
}

export async function fetchHealth(): Promise<{ status: string; db: string; version: string }> {
  const res = await fetch(`${BASE}/api/health`);
  return jsonOrThrow(res);
}