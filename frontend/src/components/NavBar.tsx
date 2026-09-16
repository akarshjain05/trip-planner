import { useThemeStore } from "../store/themeStore";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export function NavBar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useThemeStore();

  return (
    <header className="border-b border-border bg-bg/90 backdrop-blur sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#C9A24B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="6" cy="19" r="3"></circle>
            <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"></path>
            <circle cx="18" cy="5" r="3"></circle>
          </svg>
          <span className="font-display text-lg tracking-wide text-text group-hover:text-accent transition-colors">
            Itinero
          </span>
        </Link>

        <nav className="flex items-center gap-6 text-sm">
          <button 
            onClick={toggleTheme}
            className="text-text-faint hover:text-text-muted transition-colors"
            title="Toggle Theme" aria-label="Toggle Theme"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          {user ? (
            <>
              <Link to="/admin" className="text-text-muted hover:text-text transition-colors">
                Admin
              </Link>
              <Link to="/trips" className="text-text-muted hover:text-text transition-colors">
                My trips
              </Link>
              <Link
                to="/trips/new"
                className="px-4 py-1.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors"
              >
                Plan a trip
              </Link>
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="text-text-faint hover:text-text-muted transition-colors"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-text-muted hover:text-text transition-colors">
                Sign in
              </Link>
              <Link
                to="/register"
                className="px-4 py-1.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors"
              >
                Get started
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
