"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  tournaments as tournamentApi,
  rounds as roundsApi,
  standings as standingsApi,
} from "@/lib/api";
import type { Pairing, Round, StandingRow, Tournament } from "@/lib/types";

type Tab = "info" | "rounds" | "standings";

const RESULT_DISPLAY: Record<string, string> = {
  PENDING: "—",
  WHITE_WIN: "1-0",
  BLACK_WIN: "0-1",
  DRAW: "½-½",
  BYE: "BYE",
  FORFEIT: "FF",
};

export default function PublicTournamentPage() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [expandedRound, setExpandedRound] = useState<number | null>(null);
  const [roundDetail, setRoundDetail] = useState<Record<number, Round>>({});
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [standingsRound, setStandingsRound] = useState<number | "current">("current");
  const [closedRounds, setClosedRounds] = useState<Round[]>([]);
  const [tab, setTab] = useState<Tab>("info");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      tournamentApi.get(slug),
      roundsApi.list(slug),
    ])
      .then(([t, r]) => {
        setTournament(t);
        setRounds(r);
        setClosedRounds(r.filter((ro) => ro.status === "CLOSED"));
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const loadRound = async (number: number) => {
    if (roundDetail[number]) {
      setExpandedRound(expandedRound === number ? null : number);
      return;
    }
    const r = await roundsApi.getPairings(slug, number);
    setRoundDetail((prev) => ({ ...prev, [number]: r }));
    setExpandedRound(number);
  };

  const loadStandings = async (roundNum: number | "current") => {
    setStandingsRound(roundNum);
    if (roundNum === "current") {
      const data = await standingsApi.current(slug);
      setStandings(data.standings);
    } else {
      const data = await standingsApi.forRound(slug, roundNum);
      setStandings(data.standings);
    }
  };

  useEffect(() => {
    if (tab === "standings") {
      loadStandings("current");
    }
  }, [tab, slug]);

  if (loading) return <div className="text-gray-500">Loading...</div>;
  if (!tournament) return <div className="text-red-600">Tournament not found</div>;

  const isOwner = user?.email === tournament.owner_email;

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "info", label: "Info" },
    { id: "rounds", label: "Rounds" },
    { id: "standings", label: "Standings" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        {isOwner && (
          <Link
            href={`/tournaments/${slug}/admin`}
            className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700"
          >
            Admin
          </Link>
        )}
      </div>
      <div className="flex items-center gap-2 mb-6">
        <span className="text-sm bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
          {tournament.status}
        </span>
        {tournament.time_control && (
          <span className="text-sm text-gray-500">{tournament.time_control}</span>
        )}
      </div>

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

      {tab === "info" && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          {tournament.description && (
            <p className="text-gray-700 mb-4">{tournament.description}</p>
          )}
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-gray-500">Rounds</dt>
            <dd>{tournament.num_rounds}</dd>
            <dt className="text-gray-500">Time control</dt>
            <dd>{tournament.time_control || "—"}</dd>
            <dt className="text-gray-500">Bye points</dt>
            <dd>{tournament.bye_points}</dd>
            <dt className="text-gray-500">Status</dt>
            <dd>{tournament.status}</dd>
          </dl>
        </div>
      )}

      {tab === "rounds" && (
        <div className="space-y-2">
          {rounds.length === 0 && (
            <p className="text-gray-500">No rounds yet.</p>
          )}
          {rounds
            .filter((r) => r.status !== "DRAFT")
            .map((r) => (
              <div
                key={r.id}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden"
              >
                <button
                  onClick={() => loadRound(r.number)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <span className="font-medium">Round {r.number}</span>
                  <span className="text-sm text-gray-400">
                    {r.status === "CLOSED" ? "Closed ✓" : "Published"}
                  </span>
                </button>

                {expandedRound === r.number && roundDetail[r.number] && (
                  <div className="border-t border-gray-100">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left px-4 py-2 text-gray-600 font-medium">Board</th>
                          <th className="text-left px-4 py-2 text-gray-600 font-medium">White</th>
                          <th className="text-left px-4 py-2 text-gray-600 font-medium">Black</th>
                          <th className="text-left px-4 py-2 text-gray-600 font-medium">Result</th>
                        </tr>
                      </thead>
                      <tbody>
                        {roundDetail[r.number].pairings?.map((p: Pairing) => (
                          <tr key={p.id} className="border-t border-gray-100">
                            <td className="px-4 py-2 text-gray-400">{p.board_number}</td>
                            <td className="px-4 py-2">
                              {p.is_bye ? <em className="text-gray-400">BYE</em> : p.white_name}
                            </td>
                            <td className="px-4 py-2">{!p.is_bye && p.black_name}</td>
                            <td className="px-4 py-2 font-medium">
                              {RESULT_DISPLAY[p.result] || p.result}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      {tab === "standings" && (
        <div>
          {/* Round selector */}
          {closedRounds.length > 0 && (
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm text-gray-500">View after:</span>
              <select
                value={standingsRound === "current" ? "current" : String(standingsRound)}
                onChange={(e) =>
                  loadStandings(e.target.value === "current" ? "current" : Number(e.target.value))
                }
                className="border border-gray-300 rounded px-2 py-1 text-sm"
              >
                <option value="current">Current</option>
                {closedRounds.map((r) => (
                  <option key={r.id} value={String(r.number)}>
                    After Round {r.number}
                  </option>
                ))}
              </select>
            </div>
          )}

          {standings.length === 0 ? (
            <p className="text-gray-500">No standings yet.</p>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">#</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">Pts</th>
                    <th className="text-left px-4 py-2 font-medium text-gray-600">W/D/L</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((row) => (
                    <tr
                      key={row.participant_id}
                      className="border-b border-gray-100 last:border-0"
                    >
                      <td className="px-4 py-2 text-gray-400">{row.rank}</td>
                      <td className="px-4 py-2 font-medium">{row.name}</td>
                      <td className="px-4 py-2 font-bold text-blue-700">{row.points}</td>
                      <td className="px-4 py-2 text-gray-500">
                        {row.wins}/{row.draws}/{row.losses}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
