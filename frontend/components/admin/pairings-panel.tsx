"use client";

import { useEffect, useState } from "react";
import { rounds as roundsApi, tournaments as tournamentApi } from "@/lib/api";
import type { Pairing, Round, Tournament } from "@/lib/types";

interface Props {
  slug: string;
  tournament: Tournament;
  onTournamentUpdate: (t: Tournament) => void;
}

const RESULT_LABELS: Record<string, string> = {
  PENDING: "Pending",
  WHITE_WIN: "1-0 (White wins)",
  BLACK_WIN: "0-1 (Black wins)",
  DRAW: "½-½ (Draw)",
  BYE: "Bye",
  FORFEIT: "Forfeit",
};

export function PairingsPanel({ slug, tournament, onTournamentUpdate }: Props) {
  const [roundList, setRoundList] = useState<Round[]>([]);
  const [currentRound, setCurrentRound] = useState<Round | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const isRunning = tournament.status === "RUNNING";

  useEffect(() => {
    roundsApi
      .list(slug)
      .then((rounds) => {
        setRoundList(rounds);
        if (rounds.length > 0) {
          const latest = rounds[rounds.length - 1];
          fetchRound(latest.number);
        } else {
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, [slug]);

  const fetchRound = async (number: number) => {
    setLoading(true);
    try {
      const r = await roundsApi.getPairings(slug, number);
      setCurrentRound(r);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setError("");
    setGenerating(true);
    try {
      const round = await roundsApi.generate(slug);
      setRoundList((prev) => [...prev, round]);
      setCurrentRound(round);
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to generate round");
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async () => {
    if (!currentRound) return;
    setError("");
    try {
      await roundsApi.publish(slug, currentRound.number);
      setCurrentRound((r) => r ? { ...r, status: "PUBLISHED" } : r);
      setRoundList((prev) =>
        prev.map((r) => (r.number === currentRound.number ? { ...r, status: "PUBLISHED" } : r))
      );
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to publish round");
    }
  };

  const handleClose = async () => {
    if (!currentRound) return;
    setError("");
    try {
      await roundsApi.close(slug, currentRound.number);
      setCurrentRound((r) => r ? { ...r, status: "CLOSED" } : r);
      setRoundList((prev) =>
        prev.map((r) => (r.number === currentRound.number ? { ...r, status: "CLOSED" } : r))
      );
      // Refresh tournament to update status if finished
      const updated = await tournamentApi.get(slug);
      onTournamentUpdate(updated);
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to close round");
    }
  };

  const handleResult = async (pairing: Pairing, result: string) => {
    if (!currentRound) return;
    try {
      const updated = await roundsApi.setResult(slug, currentRound.number, pairing.id, { result });
      setCurrentRound((r) =>
        r
          ? {
              ...r,
              pairings: r.pairings?.map((p) => (p.id === pairing.id ? updated : p)),
            }
          : r
      );
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  const canGenerate =
    isRunning &&
    (roundList.length === 0 ||
      roundList[roundList.length - 1]?.status === "CLOSED");

  const lastRound = roundList[roundList.length - 1];
  const allRoundsGenerated = roundList.length >= tournament.num_rounds;

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      {/* Round navigation */}
      {roundList.length > 0 && (
        <div className="flex gap-1 mb-4">
          {roundList.map((r) => (
            <button
              key={r.id}
              onClick={() => fetchRound(r.number)}
              className={`px-3 py-1 text-sm rounded border ${
                currentRound?.number === r.number
                  ? "border-blue-600 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:bg-gray-50"
              }`}
            >
              Rd {r.number}
              {r.status === "CLOSED" && " ✓"}
              {r.status === "DRAFT" && " (draft)"}
            </button>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {canGenerate && !allRoundsGenerated && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {generating ? "Generating..." : `Generate Round ${roundList.length + 1}`}
          </button>
        )}
        {currentRound?.status === "DRAFT" && isRunning && (
          <button
            onClick={handlePublish}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
          >
            Publish Round
          </button>
        )}
        {currentRound?.status === "PUBLISHED" && isRunning && (
          <button
            onClick={handleClose}
            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 text-sm"
          >
            Close Round
          </button>
        )}
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {!currentRound && roundList.length === 0 && (
        <p className="text-gray-500">
          {isRunning
            ? "No rounds yet. Click \"Generate Round 1\" to start."
            : "Tournament must be RUNNING to manage rounds."}
        </p>
      )}

      {currentRound && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <h3 className="font-semibold">Round {currentRound.number}</h3>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                currentRound.status === "CLOSED"
                  ? "bg-green-100 text-green-700"
                  : currentRound.status === "PUBLISHED"
                  ? "bg-blue-100 text-blue-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {currentRound.status}
            </span>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Board</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">White</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Black</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">Result</th>
                </tr>
              </thead>
              <tbody>
                {currentRound.pairings?.map((p) => (
                  <tr key={p.id} className="border-b border-gray-100 last:border-0">
                    <td className="px-4 py-2 text-gray-500">{p.board_number}</td>
                    <td className="px-4 py-2">
                      {p.is_bye ? (
                        <span className="text-gray-500 italic">BYE</span>
                      ) : (
                        <>
                          {p.white_name}
                          {p.white_seed && (
                            <span className="text-gray-400 ml-1">(#{p.white_seed})</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {!p.is_bye && (
                        <>
                          {p.black_name}
                          {p.black_seed && (
                            <span className="text-gray-400 ml-1">(#{p.black_seed})</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {p.is_bye ? (
                        <span className="text-gray-500">BYE</span>
                      ) : currentRound.status === "PUBLISHED" ? (
                        <select
                          value={p.result}
                          onChange={(e) => handleResult(p, e.target.value)}
                          className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="PENDING">Pending</option>
                          <option value="WHITE_WIN">1-0 White wins</option>
                          <option value="BLACK_WIN">0-1 Black wins</option>
                          <option value="DRAW">½-½ Draw</option>
                          <option value="FORFEIT">Forfeit</option>
                        </select>
                      ) : (
                        <span className={p.result === "PENDING" ? "text-gray-400" : "font-medium"}>
                          {RESULT_LABELS[p.result] || p.result}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
