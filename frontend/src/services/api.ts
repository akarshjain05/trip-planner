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

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function(resolve, reject) {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token;
          return api(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        isRefreshing = false;
        localStorage.removeItem("access_token");
        if (window.location.pathname !== "/login") window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh?refresh_token=${refreshToken}`);
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        api.defaults.headers.common['Authorization'] = 'Bearer ' + data.access_token;
        originalRequest.headers['Authorization'] = 'Bearer ' + data.access_token;
        processQueue(null, data.access_token);
        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (window.location.pathname !== "/login") window.location.href = "/login";
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
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

export const reorderActivities = (tripId: string, dayId: string, activityIds: string[]) =>
  api.put(`/trips/${tripId}/itinerary/days/${dayId}/activities/reorder`, { activity_ids: activityIds }).then((r) => r.data);

export const fetchAdminStats = () => api.get("/admin/stats").then((r) => r.data);

// --- Agent Runs ---
export const getAgentRun = (runId: string) => api.get(`/agent-runs/${runId}`).then((r) => r.data);
