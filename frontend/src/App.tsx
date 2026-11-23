import { useEffect, useState } from "react";
import { api, type EventItem, type Me, UnauthorizedError } from "./api";

type State =
  | { kind: "loading" }
  | { kind: "logged-out" }
  | { kind: "error"; message: string }
  | { kind: "ready"; me: Me; events: EventItem[] };

const dateFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    Promise.all([api.me(), api.events()])
      .then(([me, events]) => setState({ kind: "ready", me, events }))
      .catch((err: unknown) =>
        setState(
          err instanceof UnauthorizedError
            ? { kind: "logged-out" }
            : { kind: "error", message: err instanceof Error ? err.message : String(err) },
        ),
      );
  }, []);

  async function toggle(event: EventItem, itemId: number, done: boolean) {
    if (state.kind !== "ready") return;
    try {
      const updated = await api.toggleItem(event.id, itemId, done);
      setState({ ...state, events: state.events.map((e) => (e.id === updated.id ? updated : e)) });
    } catch (err) {
      setState({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <main className="page">
      <header className="top">
        <h1>EventOps</h1>
        {state.kind === "ready" && (
          <span className="who">
            {state.me.username} · {state.me.role ?? "no role"}
          </span>
        )}
      </header>

      {state.kind === "loading" && <p className="muted">Loading events…</p>}

      {state.kind === "logged-out" && (
        <p>
          You need to sign in first. <a href="/admin/login/?next=/">Sign in</a>
        </p>
      )}

      {state.kind === "error" && <p className="error">Something went wrong: {state.message}</p>}

      {state.kind === "ready" && state.events.length === 0 && (
        <p className="muted">No events yet. Create one from the admin or the API.</p>
      )}

      {state.kind === "ready" && (
        <ul className="events">
          {state.events.map((event) => (
            <li key={event.id} className="card">
              <div className="card-head">
                <div>
                  <h2>{event.title}</h2>
                  <p className="muted">
                    {event.speaker} · {dateFormat.format(new Date(event.starts_at))}
                  </p>
                </div>
                <span className={event.is_ready ? "badge ok" : "badge"}>
                  {event.is_ready ? "Ready to go live" : `${event.readiness_percent}% ready`}
                </span>
              </div>
              <div className="bar" aria-hidden>
                <div style={{ width: `${event.readiness_percent}%` }} />
              </div>
              <ul className="checklist">
                {event.checklist.map((item) => (
                  <li key={item.id}>
                    <label>
                      <input
                        type="checkbox"
                        checked={item.done}
                        onChange={(e) => toggle(event, item.id, e.target.checked)}
                      />
                      <span className={item.done ? "done" : undefined}>{item.label}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
