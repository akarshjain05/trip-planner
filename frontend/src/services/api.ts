import axios from "axios";
import type {
  Budget,
  Itinerary,
  ResearchSource,
  TokenPair,
  Trip,
  TripStatusRead,
  User,
  UserPreferences,
} from "../types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// --- Auth ---
export const registerUser = (email: string, password: string, fullName?: string) =>
  api.post<TokenPair>("/auth/register", { email, password, full_name: fullName }).then((r) => r.data);

export const loginUser = (email: string, password: string) =>
  api.post<TokenPair>("/auth/login", { email, password }).then((r) => r.data);

export const fetchMe = () => api.get<User>("/auth/me").then((r) => r.data);

// --- Preferences ---
export const fetchPreferences = () => api.get<UserPreferences>("/users/me/preferences").then((r) => r.data);
export const updatePreferences = (payload: Partial<UserPreferences>) =>
  api.put<UserPreferences>("/users/me/preferences", payload).then((r) => r.data);

// --- Trips ---
export const createTrip = (prompt: string) => api.post<Trip>("/trips", { prompt }).then((r) => r.data);
export const listTrips = () => api.get<Trip[]>("/trips").then((r) => r.data);
export const getTrip = (tripId: string) => api.get<Trip>(`/trips/${tripId}`).then((r) => r.data);
export const deleteTrip = (tripId: string) => api.delete(`/trips/${tripId}`);

export const planTrip = (tripId: string, message?: string) =>
  api.post<TripStatusRead>(`/trips/${tripId}/plan`, message ? { message } : undefined).then((r) => r.data);

export const modifyTrip = (tripId: string, message: string) =>
  api.post<TripStatusRead>(`/trips/${tripId}/modify`, { message }).then((r) => r.data);

export const regenerateTrip = (tripId: string) =>
  api.post<TripStatusRead>(`/trips/${tripId}/regenerate`).then((r) => r.data);

export const submitFeedback = (tripId: string, message: string) =>
  api.post(`/trips/${tripId}/feedback`, { message });

export const getTripStatus = (tripId: string) =>
  api.get<TripStatusRead>(`/trips/${tripId}/status`).then((r) => r.data);

export const getItinerary = (tripId: string) =>
  api.get<Itinerary>(`/trips/${tripId}/itinerary`).then((r) => r.data);

export const getBudget = (tripId: string) => api.get<Budget>(`/trips/${tripId}/budget`).then((r) => r.data);

export const getSources = (tripId: string) =>
  api.get<ResearchSource[]>(`/trips/${tripId}/sources`).then((r) => r.data);

export const streamUrl = (tripId: string) => {
  const token = localStorage.getItem("access_token");
  return `${API_BASE}/trips/${tripId}/stream?token=${encodeURIComponent(token ?? "")}`;
};
