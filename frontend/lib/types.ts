export interface User {
  id: number;
  email: string;
  display_name: string;
  date_joined: string;
}

export type TournamentStatus = "DRAFT" | "OPEN" | "RUNNING" | "FINISHED" | "ARCHIVED";

export interface Tournament {
  id: number;
  slug: string;
  name: string;
  description: string;
  time_control: string;
  num_rounds: number;
  bye_points: string;
  status: TournamentStatus;
  is_public: boolean;
  owner_email: string;
  created_at: string;
  updated_at: string;
}

export type ParticipantStatus = "ACTIVE" | "WITHDRAWN" | "DISQUALIFIED";

export interface Participant {
  id: number;
  name: string;
  rating: number | null;
  seed: number | null;
  status: ParticipantStatus;
  created_at: string;
}

export type RoundStatus = "DRAFT" | "PUBLISHED" | "CLOSED";

export type PairingResult =
  | "PENDING"
  | "WHITE_WIN"
  | "BLACK_WIN"
  | "DRAW"
  | "BYE"
  | "FORFEIT";

export interface Pairing {
  id: number;
  board_number: number;
  white: number | null;
  white_name: string | null;
  white_seed: number | null;
  black: number | null;
  black_name: string | null;
  black_seed: number | null;
  result: PairingResult;
  is_bye: boolean;
  note: string;
}

export interface Round {
  id: number;
  number: number;
  status: RoundStatus;
  created_at: string;
  pairings?: Pairing[];
}

export interface StandingRow {
  rank: number;
  participant_id: number;
  name: string;
  rating: number | null;
  seed: number | null;
  points: number;
  wins: number;
  draws: number;
  losses: number;
  byes: number;
  games_played: number;
}

export interface ApiError {
  detail?: string;
  [key: string]: unknown;
}
