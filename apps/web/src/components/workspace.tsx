"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { ApiError, debug, getHealth, getFixtures, reproduce, type DebugReport, type Evidence, type Health, type Fixture } from "@/lib/api";

type Result = { kind: "debug"; data: DebugReport; httpStatus: number } | { kind: "reproduce"; data: Evidence; httpStatus: number };
type State = {
  health: Health | null; healthError: string | null; checking: boolean; refresh: () => Promise<void>;
  pending: "debug" | "reproduce" | null; result: Result | null; error: string | null;
  fixtures: Fixture[]; fixture: Fixture | undefined; fixturesLoading: boolean; fixturesError: string | null;
  selectFixture: (id: Fixture["fixture_id"]) => void; refreshFixtures: () => Promise<void>;
  run: (kind: "debug" | "reproduce", description?: string) => Promise<void>;
};
const Context = createContext<State | null>(null);
export function Workspace({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [pending, setPending] = useState<State["pending"]>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [selectedId, setSelectedId] = useState<Fixture["fixture_id"] | "">("");
  const [fixturesLoading, setFixturesLoading] = useState(true);
  const [fixturesError, setFixturesError] = useState<string | null>(null);
  const fixture = fixtures.find((item) => item.fixture_id === selectedId) ?? fixtures[0];
  const locked = useRef(false);
  async function refresh() {
    setChecking(true);
    try { setHealth((await getHealth()).data); setHealthError(null); }
    catch (e) { setHealth(null); setHealthError(e instanceof ApiError ? e.message : "Health check failed."); }
    finally { setChecking(false); }
  }
  async function refreshFixtures() {
    setFixturesLoading(true);
    try { setFixtures((await getFixtures()).data.fixtures); setFixturesError(null); }
    catch { setFixtures([]); setFixturesError("Could not load approved fixtures. Check the backend connection and version."); }
    finally { setFixturesLoading(false); }
  }
  function selectFixture(id: Fixture["fixture_id"]) {
    if (!locked.current && fixtures.some((item) => item.fixture_id === id)) setSelectedId(id);
  }
  useEffect(() => {
    let active = true;
    void getHealth().then(({ data }) => { if (active) { setHealth(data); setHealthError(null); } })
      .catch((e) => { if (active) { setHealth(null); setHealthError(e instanceof ApiError ? e.message : "Health check failed."); } })
      .finally(() => { if (active) setChecking(false); });
    void getFixtures().then(({ data }) => { if (active) { setFixtures(data.fixtures); setFixturesError(null); } })
      .catch(() => { if (active) setFixturesError("Could not load approved fixtures. Check the backend connection and version."); })
      .finally(() => { if (active) setFixturesLoading(false); });
    return () => { active = false; };
  }, []);
  async function run(kind: "debug" | "reproduce", description = "") {
    if (locked.current || !fixture || fixturesLoading) return;
    locked.current = true; setPending(kind); setError(null); setResult(null);
    try {
      if (kind === "debug") setResult({ kind, ...await debug({ fixture_id: fixture.fixture_id, bug_description: description }) });
      else setResult({ kind, ...await reproduce(fixture.fixture_id) });
    } catch (e) { setError(e instanceof ApiError ? e.message : "The request could not be completed."); }
    finally { setPending(null); locked.current = false; }
  }
  return <Context.Provider value={{ health, healthError, checking, refresh, pending, result, error, run,
    fixtures, fixture, fixturesLoading, fixturesError, selectFixture, refreshFixtures }}>{children}</Context.Provider>;
}
export function useWorkspace() {
  const state = useContext(Context);
  if (!state) throw new Error("Workspace provider missing");
  return state;
}
