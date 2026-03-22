"use client";

import { useEffect, useRef, useState } from "react";
import { rounds as roundsApi, standings as standingsApi } from "@/lib/api";
import type { Pairing, Round, StandingRow } from "@/lib/types";

type RoundResult = {
  result: "1" | "½" | "0" | "+" | "F" | "—";
  color: "W" | "B" | null;
  opponentName: string | null;
  opponentSeed: number | null;
  boardNumber: number;
  is_bye: boolean;
};

type CrossTableRow = StandingRow & {
  roundResults: (RoundResult | null)[];
};

type OpenCell = {
  participantId: number;
  roundIdx: number;
  x: number;
  y: number;
};

function getRoundResult(pairing: Pairing, participantId: number): RoundResult | null {
  if (pairing.white === participantId) {
    if (pairing.is_bye) {
      return {
        result: "+", color: null,
        opponentName: null, opponentSeed: null,
        boardNumber: pairing.board_number, is_bye: true,
      };
    }
    const result =
      pairing.result === "WHITE_WIN" ? "1" :
      pairing.result === "BLACK_WIN" ? "0" :
      pairing.result === "DRAW" ? "½" :
      pairing.result === "FORFEIT" ? "F" : "—";
    return {
      result, color: "W",
      opponentName: pairing.black_name, opponentSeed: pairing.black_seed,
      boardNumber: pairing.board_number, is_bye: false,
    };
  }
  if (pairing.black === participantId) {
    const result =
      pairing.result === "BLACK_WIN" ? "1" :
      pairing.result === "WHITE_WIN" ? "0" :
      pairing.result === "DRAW" ? "½" :
      pairing.result === "FORFEIT" ? "F" : "—";
    return {
      result, color: "B",
      opponentName: pairing.white_name, opponentSeed: pairing.white_seed,
      boardNumber: pairing.board_number, is_bye: false,
    };
  }
  return null;
}

function ColorDot({ color }: { color: "W" | "B" }) {
  return color === "W" ? (
    <span className="inline-block w-2.5 h-2.5 rounded-full border border-gray-500 bg-white flex-shrink-0" />
  ) : (
    <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-800 flex-shrink-0" />
  );
}

function ResultBadge({ result }: { result: RoundResult }) {
  if (result.result === "+") {
    return <span className="text-xs text-gray-500 font-medium">+</span>;
  }
  if (result.result === "—") {
    return <span className="text-gray-300">—</span>;
  }
  const textClass =
    result.result === "1" ? "text-green-700 font-semibold" :
    result.result === "0" ? "text-red-500" :
    result.result === "½" ? "text-blue-600" :
    "text-orange-500";
  return (
    <span className="inline-flex items-center gap-1">
      {result.color && <ColorDot color={result.color} />}
      <span className={textClass}>{result.result}</span>
    </span>
  );
}

const RESULT_LABEL: Record<string, string> = {
  "1": "Win", "½": "Draw", "0": "Loss", "+": "Bye", "F": "Forfeit", "—": "Pending",
};

export function CrossTablePanel({ slug, numRounds }: { slug: string; numRounds: number }) {
  const [rows, setRows] = useState<CrossTableRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [openCell, setOpenCell] = useState<OpenCell | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const [standingsData, roundsList] = await Promise.all([
          standingsApi.current(slug),
          roundsApi.list(slug),
        ]);

        const visibleRounds = (roundsList as Round[]).filter(
          (r) => r.status === "PUBLISHED" || r.status === "CLOSED"
        );

        const pairingsData = await Promise.all(
          visibleRounds.map((r) => roundsApi.getPairings(slug, r.number))
        );

        const resultsByRound = new Map<number, Map<number, RoundResult>>();
        visibleRounds.forEach((round, idx) => {
          const byParticipant = new Map<number, RoundResult>();
          const pairings: Pairing[] = pairingsData[idx].pairings ?? [];
          for (const p of pairings) {
            if (p.white != null) {
              const r = getRoundResult(p, p.white);
              if (r) byParticipant.set(p.white, r);
            }
            if (!p.is_bye && p.black != null) {
              const r = getRoundResult(p, p.black);
              if (r) byParticipant.set(p.black, r);
            }
          }
          resultsByRound.set(round.number, byParticipant);
        });

        const allRoundNumbers = Array.from({ length: numRounds }, (_, i) => i + 1);
        const tableRows: CrossTableRow[] = (standingsData.standings as StandingRow[]).map((row) => ({
          ...row,
          roundResults: allRoundNumbers.map(
            (n) => resultsByRound.get(n)?.get(row.participant_id) ?? null
          ),
        }));

        setRows(tableRows);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug, numRounds]);

  // Close popover on click outside
  useEffect(() => {
    if (!openCell) return;
    const handle = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpenCell(null);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [openCell]);

  const handleCellClick = (
    e: React.MouseEvent,
    participantId: number,
    roundIdx: number,
    result: RoundResult | null
  ) => {
    if (!result || result.result === "—") return;
    if (openCell?.participantId === participantId && openCell?.roundIdx === roundIdx) {
      setOpenCell(null);
      return;
    }
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setOpenCell({ participantId, roundIdx, x: rect.left, y: rect.bottom + 6 });
  };

  if (loading) return <div className="text-gray-500 text-sm">Loading…</div>;
  if (rows.length === 0) return <div className="text-gray-500 text-sm">No data yet.</div>;

  const allRounds = Array.from({ length: numRounds }, (_, i) => i + 1);

  // Find the result for the open popover
  const popoverResult = openCell
    ? rows.find((r) => r.participant_id === openCell.participantId)?.roundResults[openCell.roundIdx] ?? null
    : null;

  return (
    <>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-2 font-medium text-gray-600 w-8">#</th>
                <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
                {allRounds.map((n) => (
                  <th key={n} className="px-3 py-2 font-medium text-gray-600 text-center w-14">
                    R{n}
                  </th>
                ))}
                <th className="px-3 py-2 font-medium text-gray-600 text-center">Pts</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr
                  key={row.participant_id}
                  className={`border-b border-gray-100 last:border-0 ${idx % 2 !== 0 ? "bg-gray-50" : ""}`}
                >
                  <td className="px-4 py-2.5 text-gray-400">{row.rank}</td>
                  <td className="px-4 py-2.5 font-medium">
                    {row.name}
                    {row.seed != null && (
                      <span className="ml-1.5 text-gray-400 text-xs font-normal">#{row.seed}</span>
                    )}
                  </td>
                  {allRounds.map((_, i) => {
                    const result = row.roundResults[i];
                    const isOpen = openCell?.participantId === row.participant_id && openCell?.roundIdx === i;
                    const isClickable = result && result.result !== "—";
                    return (
                      <td
                        key={i}
                        className={`px-3 py-2.5 text-center ${isClickable ? "cursor-pointer" : ""} ${isOpen ? "bg-blue-50" : ""}`}
                        onClick={(e) => handleCellClick(e, row.participant_id, i, result)}
                      >
                        {result ? <ResultBadge result={result} /> : <span className="text-gray-300">—</span>}
                      </td>
                    );
                  })}
                  <td className="px-3 py-2.5 text-center font-bold text-blue-700">
                    {row.points % 1 === 0 ? row.points : row.points.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center gap-4 px-4 py-2 border-t border-gray-100 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full border border-gray-500 bg-white" />
            White
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-800" />
            Black
          </span>
          <span><span className="text-green-700 font-semibold">1</span> win</span>
          <span><span className="text-blue-600">½</span> draw</span>
          <span><span className="text-red-500">0</span> loss</span>
          <span><span className="text-gray-500">+</span> bye</span>
        </div>
      </div>

      {/* Popover — fixed-position to escape overflow:hidden of the scroll container */}
      {openCell && popoverResult && (
        <div
          ref={popoverRef}
          style={{ position: "fixed", left: openCell.x, top: openCell.y, zIndex: 50 }}
          className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-sm w-52"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Round {openCell.roundIdx + 1} · Board {popoverResult.boardNumber}
            </span>
            <button
              onClick={() => setOpenCell(null)}
              className="text-gray-400 hover:text-gray-600 text-base leading-none ml-2"
            >
              ×
            </button>
          </div>

          {popoverResult.is_bye ? (
            <div className="text-gray-600">Bye</div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500 w-14 flex-shrink-0">vs.</span>
                <span className="font-medium text-gray-800 truncate">
                  {popoverResult.opponentName ?? "—"}
                  {popoverResult.opponentSeed != null && (
                    <span className="ml-1 text-gray-400 font-normal text-xs">
                      #{popoverResult.opponentSeed}
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500 w-14 flex-shrink-0">Color</span>
                <span className="inline-flex items-center gap-1">
                  {popoverResult.color && <ColorDot color={popoverResult.color} />}
                  <span className="text-gray-700">{popoverResult.color === "W" ? "White" : "Black"}</span>
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500 w-14 flex-shrink-0">Result</span>
                <span className={
                  popoverResult.result === "1" ? "text-green-700 font-semibold" :
                  popoverResult.result === "0" ? "text-red-500 font-semibold" :
                  popoverResult.result === "½" ? "text-blue-600 font-semibold" :
                  "text-gray-600"
                }>
                  {popoverResult.result} — {RESULT_LABEL[popoverResult.result]}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
