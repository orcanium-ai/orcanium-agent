import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import {
  TimelineEvent,
  eventIcon,
  eventLabel,
  eventColor,
  formatEventTime,
  fetchEventHistory,
  connectEventStream,
} from "../../services/event.service";

/* ── Props ───────────────────────────────────────────── */

interface Props {
  /** Max events to show in the timeline (default 100) */
  maxEvents?: number;
  /** Polling fallback interval in ms when SSE disconnects (default 5000) */
  fallbackPollMs?: number;
}

/* ── Component ───────────────────────────────────────── */

export function EventTimeline({ maxEvents = 100, fallbackPollMs = 5000 }: Props) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoScroll = useRef(true);

  /* ── Load initial history ──────────────────────────── */
  const loadHistory = useCallback(async () => {
    const res = await fetchEventHistory(maxEvents);
    if (res?.events) {
      setEvents(res.events);
    }
    setLoading(false);
  }, [maxEvents]);

  /* ── Prepend a new event (from SSE) ────────────────── */
  const prependEvent = useCallback(
    (evt: TimelineEvent) => {
      setEvents((prev) => {
        const next = [evt, ...prev];
        return next.slice(0, maxEvents);
      });
    },
    [maxEvents],
  );

  /* ── SSE connection ────────────────────────────────── */
  useEffect(() => {
    loadHistory();

    // Try SSE
    try {
      const es = connectEventStream(prependEvent, () => {
        setLive(false);
      });
      esRef.current = es;

      es.onopen = () => {
        setLive(true);
        // Clear polling fallback if active
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };

      es.onerror = () => {
        setLive(false);
      };
    } catch {
      setLive(false);
    }

    // Fallback polling if SSE fails
    if (!pollRef.current) {
      pollRef.current = setInterval(async () => {
        const res = await fetchEventHistory(1);
        if (res?.events?.length) {
          // Only add if not already in list
          setEvents((prev) => {
            if (prev.some((e) => e.id === res.events[0].id)) return prev;
            return [res.events[0], ...prev].slice(0, maxEvents);
          });
        }
      }, fallbackPollMs);
    }

    return () => {
      if (esRef.current) esRef.current.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadHistory, prependEvent, maxEvents, fallbackPollMs]);

  /* ── Auto-scroll ───────────────────────────────────── */
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop } = containerRef.current;
    autoScroll.current = scrollTop < 50;
  };

  /* ── Render ────────────────────────────────────────── */
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] font-medium text-neutral-300">
          <Activity className="w-3.5 h-3.5" />
          Event Timeline
          {live && (
            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-500">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          )}
        </div>
        <button
          onClick={loadHistory}
          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-stone-100/80 dark:bg-zinc-800/50 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 overflow-y-auto max-h-[400px]"
      >
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-5 h-5 animate-spin text-neutral-300" />
          </div>
        ) : events.length === 0 ? (
          <div className="py-8 text-center">
            <Activity className="w-5 h-5 mx-auto mb-2 text-neutral-300" />
            <p className="text-xs text-neutral-300">No events yet</p>
            <p className="text-[10px] text-neutral-400 mt-1">
              Events appear here as agents process messages.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-200/60 dark:divide-zinc-700/50">
            {events.map((evt) => (
              <div
                key={evt.id}
                className={`flex items-start gap-2.5 px-3 py-2 border-l-2 ${eventColor(evt.event_name)}`}
              >
                <span className="text-xs leading-5 shrink-0">
                  {eventIcon(evt.event_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 truncate">
                      {eventLabel(evt.event_name)}
                    </span>
                    <span className="text-[10px] text-zinc-500 shrink-0 ml-auto">
                      {formatEventTime(evt.timestamp)}
                    </span>
                  </div>
                  {evt.payload?.tool_name && (
                    <p className="text-[10px] text-zinc-500 truncate mt-0.5">
                      {String(evt.payload.tool_name)}
                    </p>
                  )}
                  {evt.payload?.error && (
                    <p className="text-[10px] text-rose-500 truncate mt-0.5">
                      {String(evt.payload.error)}
                    </p>
                  )}
                  <span className="text-[9px] text-zinc-500 uppercase tracking-wider mt-0.5 block">
                    {evt.category}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default EventTimeline;
