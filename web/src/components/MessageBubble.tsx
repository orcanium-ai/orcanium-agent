import { Bot, User } from "lucide-react";

interface ChatMessage {
  id?: string;
  session_id: string;
  sender: string;
  content: string;
  timestamp?: string;
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.sender === "user";
  const isAgent = message.sender === "agent" || message.sender === "assistant";

  return (
    <div
      className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""} animate-in fade-in slide-in-from-bottom-2 duration-300`}
    >
      <div
        className={`p-2 rounded-full shrink-0 ${
          isUser
            ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
            : isAgent
              ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
              : "bg-zinc-100 dark:bg-zinc-800 text-neutral-300"
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div
        className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[75%]`}
      >
        {!isUser && (
          <span className="text-[10px] font-semibold text-zinc-500 mb-1 px-1">
            {isAgent ? "Agent" : message.sender}
          </span>
        )}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : isAgent
                ? "bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-sm shadow-sm border border-zinc-200/60 dark:border-zinc-700/50"
                : "bg-zinc-100 dark:bg-zinc-800/50 text-zinc-500 dark:text-neutral-300 italic rounded-tl-sm"
          }`}
        >
          {message.content}
        </div>
        {message.timestamp && (
          <span className="text-[9px] text-neutral-300 mt-1 px-1">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>
    </div>
  );
}
