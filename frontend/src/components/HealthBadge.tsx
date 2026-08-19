import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function HealthBadge() {
  const [status, setStatus] = useState<"ok" | "down" | "loading">("loading");
  useEffect(() => {
    let alive = true;
    fetchHealth()
      .then((h) => alive && setStatus(h.status === "ok" ? "ok" : "down"))
      .catch(() => alive && setStatus("down"));
    return () => {
      alive = false;
    };
  }, []);
  if (status === "loading") return <Badge variant="outline">connecting…</Badge>;
  if (status === "down") return <Badge variant="destructive">API down</Badge>;
  return <Badge variant="success">API ok</Badge>;
}