"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function Nav() {
  const { user, logout, loading } = useAuth();

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-bold text-lg text-blue-700">
          SwissChess
        </Link>
        <div className="flex items-center gap-4">
          {loading ? null : user ? (
            <>
              <Link
                href="/dashboard"
                className="text-gray-600 hover:text-gray-900 text-sm"
              >
                My Tournaments
              </Link>
              <span className="text-gray-400 text-sm">{user.email}</span>
              <button
                onClick={() => logout()}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900">
                Sign in
              </Link>
              <Link
                href="/register"
                className="bg-blue-600 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-700"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
