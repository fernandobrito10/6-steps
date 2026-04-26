export interface Actor {
  id: number;
  name: string;
  popularity: number;
  profile_path: string | null;
}

export interface Movie {
  id: number;
  title: string;
  title_pt: string | null;
  year: number | null;
  popularity: number;
  poster_path: string | null;
}

export interface Step {
  actor: Actor;
  via_movie: Movie | null;
}

export type SSEEvent =
  | { type: "start" }
  | { type: "resolving" }
  | { type: "resolved"; actor_a: Actor; actor_b: Actor }
  | { type: "expand"; side: "A" | "B"; frontier_size: number; next_depth: number }
  | { type: "result"; path: Step[]; hops: number }
  | { type: "no_path"; max_depth: number }
  | { type: "error"; message: string };
