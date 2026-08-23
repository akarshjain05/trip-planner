export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type TripStatus = "draft" | "awaiting_input" | "planning" | "completed" | "failed";

export interface Trip {
  id: string;
  title: string;
  status: TripStatus;
  original_prompt: string;
  created_at: string;
  updated_at: string;
}

export interface TripStatusRead {
  trip_id: string;
  status: TripStatus;
  latest_agent_run_id: string | null;
  awaiting_input: boolean;
  clarifying_question: string | null;
}

export type ActivityType =
  | "flight"
  | "transfer"
  | "meal"
  | "attraction"
  | "hotel_checkin"
  | "hotel_checkout"
  | "free_time"
  | "other";

export interface Activity {
  id: string;
  order_index: number;
  time: string | null;
  activity_type: ActivityType;
  title: string;
  description: string | null;
  location: string | null;
  estimated_cost: number | null;
  duration_minutes: number | null;
  source_ref: string | null;
}

export interface ItineraryDay {
  id: string;
  day_number: number;
  date: string | null;
  title: string | null;
  weather_summary: string | null;
  activities: Activity[];
}

export interface Itinerary {
  id: string;
  version: number;
  status: "draft" | "needs_revision" | "approved";
  total_estimated_cost: number | null;
  currency: string;
  critic_notes: string | null;
  days: ItineraryDay[];
}

export interface BudgetLine {
  category: string;
  estimated_amount: number;
  currency: string;
}

export interface Budget {
  total_budget: number | null;
  currency: string;
  lines: BudgetLine[];
  total_estimated: number;
  remaining: number | null;
}

export interface ResearchSource {
  url: string;
  title: string | null;
  source: string | null;
  extracted_facts: string | null;
  confidence: number;
}

export interface AgentProgressEvent {
  type: string;
  agent: string | null;
  message: string | null;
  payload: Record<string, unknown>;
  ts: number;
}

export interface UserPreferences {
  home_city: string | null;
  currency: string;
  travel_style: string | null;
  budget_range_min: number | null;
  budget_range_max: number | null;
  pace: string | null;
  transportation_preference: string | null;
  hotel_preferences: string[];
  activity_preferences: string[];
  food_preferences: string[];
  favorite_destinations: string[];
  dislikes: string[];
}
