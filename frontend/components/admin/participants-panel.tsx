"use client";

import { useEffect, useState } from "react";
import { participants as participantApi } from "@/lib/api";
import type { Participant, Tournament } from "@/lib/types";

interface Props {
  slug: string;
  tournament: Tournament;
}

export function ParticipantsPanel({ slug, tournament }: Props) {
  const [list, setList] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [rating, setRating] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const canEdit = tournament.status === "DRAFT" || tournament.status === "OPEN";

  useEffect(() => {
    participantApi
      .list(slug)
      .then(setList)
      .finally(() => setLoading(false));
  }, [slug]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setAdding(true);
    try {
      const p = await participantApi.create(slug, {
        name,
        rating: rating ? Number(rating) : undefined,
      });
      setList((prev) => [...prev, p]);
      setName("");
      setRating("");
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to add participant");
    } finally {
      setAdding(false);
    }
  };

  const handleWithdraw = async (id: number) => {
    try {
      const updated = await participantApi.withdraw(slug, id);
      setList((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Remove participant?")) return;
    try {
      await participantApi.remove(slug, id);
      setList((prev) => prev.filter((p) => p.id !== id));
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  };

  if (loading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      {canEdit && (
        <form
          onSubmit={handleAdd}
          className="border border-gray-200 rounded-lg p-4 mb-4 bg-white"
        >
          <h3 className="font-semibold mb-3">Add participant</h3>
          <div className="flex gap-2 flex-wrap">
            <input
              type="text"
              required
              placeholder="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 flex-1 min-w-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="number"
              placeholder="Rating (optional)"
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 w-40 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={adding}
              className="bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {adding ? "Adding..." : "Add"}
            </button>
          </div>
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        </form>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Seed</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Rating</th>
              <th className="text-left px-4 py-2 font-medium text-gray-600">Status</th>
              {canEdit && (
                <th className="text-left px-4 py-2 font-medium text-gray-600">Actions</th>
              )}
            </tr>
          </thead>
          <tbody>
            {list.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  No participants yet
                </td>
              </tr>
            )}
            {list.map((p) => (
              <tr key={p.id} className="border-b border-gray-100 last:border-0">
                <td className="px-4 py-2 text-gray-500">{p.seed ?? "—"}</td>
                <td className="px-4 py-2 font-medium">{p.name}</td>
                <td className="px-4 py-2 text-gray-500">{p.rating ?? "—"}</td>
                <td className="px-4 py-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      p.status === "ACTIVE"
                        ? "bg-green-100 text-green-700"
                        : p.status === "WITHDRAWN"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {p.status}
                  </span>
                </td>
                {canEdit && (
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      {p.status === "ACTIVE" && (
                        <button
                          onClick={() => handleWithdraw(p.id)}
                          className="text-xs text-yellow-600 hover:text-yellow-800"
                        >
                          Withdraw
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(p.id)}
                        className="text-xs text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
