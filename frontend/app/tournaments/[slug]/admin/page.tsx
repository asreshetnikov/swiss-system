"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { tournaments as tournamentApi } from "@/lib/api";
import type { Tournament } from "@/lib/types";

const TIEBREAK_LABELS: Record<string, string> = {
  buchholz: "Buchholz",
  wins: "Wins",
  head_to_head: "Head-to-head",
};
import { ParticipantsPanel } from "@/components/admin/participants-panel";
import { PairingsPanel } from "@/components/admin/pairings-panel";
import { StandingsPanel } from "@/components/admin/standings-panel";

type Tab = "overview" | "participants" | "pairings" | "standings";

const STATUS_NEXT_ACTION: Record<string, string> = {
  DRAFT: "Add participants, then open registration or start the tournament",
  OPEN: "Add participants, then start the tournament when ready",
  RUNNING: "Generate rounds, enter results, close rounds",
  FINISHED: "Tournament is finished. Archive if needed.",
  ARCHIVED: "Tournament is archived.",
};

const STATUS_TRANSITIONS: Record<string, Array<{ label: string; value: string }>> = {
  DRAFT: [{ label: "Open for Registration", value: "OPEN" }],
  OPEN: [
    { label: "Start Tournament", value: "RUNNING" },
    { label: "Back to Draft", value: "DRAFT" },
  ],
  RUNNING: [{ label: "Finish Tournament", value: "FINISHED" }],
  FINISHED: [{ label: "Archive", value: "ARCHIVED" }],
  ARCHIVED: [],
};

export default function AdminPage() {
  const { slug } = useParams<{ slug: string }>();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [fetching, setFetching] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState("");
  const [tiebreakOrder, setTiebreakOrder] = useState<string[]>([]);
  const [tiebreakSaving, setTiebreakSaving] = useState(false);
  const [tiebreakError, setTiebreakError] = useState("");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  useEffect(() => {
    tournamentApi
      .get(slug)
      .then((t) => {
        setTournament(t);
        setTiebreakOrder(t.tiebreak_order || []);
      })
      .finally(() => setFetching(false));
  }, [slug]);

  const updateTiebreak = (index: number, value: string) => {
    setTiebreakOrder((prev) => {
      const next = [...prev];
      if (value === "") {
        next.splice(index, 1);
      } else {
        next[index] = value;
      }
      return next;
    });
  };

  const saveTiebreaks = async () => {
    setTiebreakError("");
    setTiebreakSaving(true);
    try {
      const updated = await tournamentApi.update(slug, {
        tiebreak_order: tiebreakOrder.filter(Boolean),
      });
      setTournament(updated);
      setTiebreakOrder(updated.tiebreak_order || []);
    } catch (err: unknown) {
      setTiebreakError((err as Error).message || "Failed to save tiebreaks");
    } finally {
      setTiebreakSaving(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    setError("");
    setTransitioning(true);
    try {
      const updated = await tournamentApi.setStatus(slug, newStatus);
      setTournament(updated);
    } catch (err: unknown) {
      setError((err as Error).message || "Status change failed");
    } finally {
      setTransitioning(false);
    }
  };

  if (loading || fetching) return <div className="text-gray-500">Loading...</div>;
  if (!tournament) return <div className="text-red-600">Tournament not found</div>;
  if (tournament.owner_email !== user?.email) {
    return <div className="text-red-600">Access denied</div>;
  }

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "participants", label: "Participants" },
    { id: "pairings", label: "Pairings & Results" },
    { id: "standings", label: "Standings" },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        <span className="text-sm bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          {tournament.status}
        </span>
      </div>
      <p className="text-gray-500 text-sm mb-6">Admin Panel</p>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div>
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
            <h2 className="font-semibold mb-2">Next steps</h2>
            <p className="text-gray-600 text-sm">
              {STATUS_NEXT_ACTION[tournament.status]}
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
            <h2 className="font-semibold mb-3">Tournament details</h2>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-gray-500">Rounds</dt>
              <dd>{tournament.num_rounds}</dd>
              <dt className="text-gray-500">Time control</dt>
              <dd>{tournament.time_control || "—"}</dd>
              <dt className="text-gray-500">Bye points</dt>
              <dd>{tournament.bye_points}</dd>
              <dt className="text-gray-500">Public</dt>
              <dd>{tournament.is_public ? "Yes" : "No"}</dd>
            </dl>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
            <h2 className="font-semibold mb-3">Tiebreak order</h2>
            <p className="text-xs text-gray-500 mb-3">
              Select up to 3 tiebreaks applied after points. Seed is always the final fallback.
            </p>
            <div className="flex gap-2 flex-wrap items-center">
              {[0, 1, 2].map((i) => (
                <select
                  key={i}
                  value={tiebreakOrder[i] || ""}
                  onChange={(e) => updateTiebreak(i, e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">— none —</option>
                  {Object.entries(TIEBREAK_LABELS)
                    .filter(([v]) => v === tiebreakOrder[i] || !tiebreakOrder.includes(v))
                    .map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                </select>
              ))}
              <button
                onClick={saveTiebreaks}
                disabled={tiebreakSaving}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {tiebreakSaving ? "Saving..." : "Save"}
              </button>
            </div>
            {tiebreakError && <p className="text-red-600 text-sm mt-2">{tiebreakError}</p>}
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h2 className="font-semibold mb-3">Status transitions</h2>
            <div className="flex gap-2 flex-wrap">
              {(STATUS_TRANSITIONS[tournament.status] || []).map((t) => (
                <button
                  key={t.value}
                  onClick={() => handleStatusChange(t.value)}
                  disabled={transitioning}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
                >
                  {t.label}
                </button>
              ))}
            </div>
            {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
          </div>
        </div>
      )}

      {tab === "participants" && (
        <ParticipantsPanel slug={slug} tournament={tournament} />
      )}

      {tab === "pairings" && (
        <PairingsPanel
          slug={slug}
          tournament={tournament}
          onTournamentUpdate={setTournament}
        />
      )}

      {tab === "standings" && (
        <StandingsPanel slug={slug} />
      )}
    </div>
  );
}
