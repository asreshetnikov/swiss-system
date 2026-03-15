"use client";

import { useEffect, useState } from "react";
import { standings as standingsApi } from "@/lib/api";
import type { StandingRow } from "@/lib/types";

interface Props {
  slug: string;
}

export function StandingsPanel({ slug }: Props) {
  const [rows, setRows] = useState<StandingRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    standingsApi
      .current(slug)
      .then((data) => setRows(data.standings))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <div className="text-gray-500">Loading...</div>;

  if (rows.length === 0) {
    return <p className="text-gray-500">No standings yet — close at least one round.</p>;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-4 py-2 font-medium text-gray-600">#</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">Rating</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">Points</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">W</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">D</th>
            <th className="text-left px-4 py-2 font-medium text-gray-600">L</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.participant_id} className="border-b border-gray-100 last:border-0">
              <td className="px-4 py-2 text-gray-500">{row.rank}</td>
              <td className="px-4 py-2 font-medium">{row.name}</td>
              <td className="px-4 py-2 text-gray-500">{row.rating ?? "—"}</td>
              <td className="px-4 py-2 font-bold">{row.points}</td>
              <td className="px-4 py-2 text-green-700">{row.wins}</td>
              <td className="px-4 py-2 text-blue-700">{row.draws}</td>
              <td className="px-4 py-2 text-red-700">{row.losses}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
