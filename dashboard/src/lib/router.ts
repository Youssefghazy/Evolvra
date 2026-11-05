import { useEffect, useState } from "react";

export type Route = { view: string; id?: string };

const ALIASES: Record<string, string> = { overview: "home", roster: "agents", agent: "agent" };

export function parse(hash: string): Route {
  const [raw = "", id] = hash.replace(/^#\/?/, "").split("/");
  const view = ALIASES[raw] ?? (raw || "home");
  return { view, id: id ? decodeURIComponent(id) : undefined };
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parse(location.hash));
  useEffect(() => {
    const on = () => { setRoute(parse(location.hash)); window.scrollTo({ top: 0 }); };
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  return route;
}

export const href = {
  home: "#/", agents: "#/agents", missions: "#/missions", evolutions: "#/evolutions",
  agent: (slug: string) => `#/agent/${encodeURIComponent(slug)}`,
  mission: (id: string) => `#/missions/${encodeURIComponent(id)}`,
};
