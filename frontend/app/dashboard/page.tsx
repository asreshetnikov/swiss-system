"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { tournaments as tournamentApi } from "@/lib/api";
import type { Tournament } from "@/lib/types";

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  OPEN: "bg-blue-100 text-blue-700",
  RUNNING: "bg-green-100 text-green-700",
  FINISHED: "bg-purple-100 text-purple-700",
  ARCHIVED: "bg-gray-200 text-gray-500",
};

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [list, setList] = useState<Tournament[]>([]);
  const [fetching, setFetching] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRounds, setNewRounds] = useState(5);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      tournamentApi
        .list()
        .then(setList)
        .finally(() => setFetching(false));
    }
  }, [user]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setCreating(true);
    try {
      const t = await tournamentApi.create({ name: newName, num_rounds: newRounds });
      router.push(`/tournaments/${t.slug}/admin`);
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to create tournament");
    } finally {
      setCreating(false);
    }
  };

  if (loading || fetching) {
    return <div className="text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Tournaments</h1>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700"
        >
          + New Tournament
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="border border-gray-200 rounded-lg p-4 mb-6 bg-white"
        >
          <h2 className="font-semibold mb-3">New Tournament</h2>
          <div className="flex gap-3 flex-wrap">
            <input
              type="text"
              required
              placeholder="Tournament name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 flex-1 min-w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="number"
              min={1}
              max={20}
              value={newRounds}
              onChange={(e) => setNewRounds(Number(e.target.value))}
              className="border border-gray-300 rounded px-3 py-1.5 w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
              title="Number of rounds"
            />
            <button
              type="submit"
              disabled={creating}
              className="bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        </form>
      )}

      {list.length === 0 ? (
        <p className="text-gray-500">No tournaments yet. Create your first one!</p>
      ) : (
        <div className="space-y-3">
          {list.map((t) => (
            <div
              key={t.id}
              className="border border-gray-200 rounded-lg p-4 bg-white flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{t.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      STATUS_BADGE[t.status] || ""
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
                <p className="text-sm text-gray-500">
                  {t.num_rounds} rounds · {t.time_control || "No time control"}
                </p>
              </div>
              <div className="flex gap-2">
                <Link
                  href={`/tournaments/${t.slug}`}
                  className="text-sm text-gray-600 hover:text-gray-900 border border-gray-200 px-3 py-1 rounded"
                >
                  Public view
                </Link>
                <Link
                  href={`/tournaments/${t.slug}/admin`}
                  className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                >
                  Manage
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
