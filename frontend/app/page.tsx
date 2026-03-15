import Link from "next/link";

export default function Home() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold mb-4">SwissChess</h1>
      <p className="text-gray-600 mb-8 text-lg">
        Swiss-system chess tournament management platform
      </p>
      <div className="flex gap-4 justify-center">
        <Link
          href="/dashboard"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition"
        >
          My Tournaments
        </Link>
        <Link
          href="/login"
          className="border border-gray-300 px-6 py-3 rounded-lg font-medium hover:bg-gray-100 transition"
        >
          Sign In
        </Link>
      </div>
    </div>
  );
}
