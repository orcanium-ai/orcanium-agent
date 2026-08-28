import { useState, useCallback } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { ToastContainer } from "./components/ToastContainer";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import LoginPage from "./pages/LoginPage";
import { SessionsPage } from "./pages/SessionsPage";

import { ChatPage } from "./pages/ChatPage";
import { AgentsPage } from "./pages/AgentsPage";
import { ModelsPage } from "./pages/ModelsPage";
import { SkillsPage } from "./pages/SkillsPage";
import { TasksPage } from "./pages/TasksPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { ToolsPage } from "./pages/ToolsPage";
import { MCPPage } from "./pages/MCPPage";
import { ChannelsPage } from "./pages/ChannelsPage";
import { ConfigPage } from "./pages/ConfigPage";
import { KeysPage } from "./pages/KeysPage";
import { SystemPage } from "./pages/SystemPage";
import { LogsPage } from "./pages/LogsPage";
import { DocumentationPage } from "./pages/DocsPage";

// Auth Guard

function ProtectedRoute() {
  const { loading, status } = useAuth();

  // While checking auth, show a brief loading state
  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-[#171717]">
        <div className="text-sm text-zinc-500">Loading...</div>
      </div>
    );
  }

  // Not authenticated → redirect to login
  if (!status || !status.authenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

// Dashboard Layout

function DashboardLayout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const handleMobileClose = useCallback(() => setMobileSidebarOpen(false), []);
  const handleMenuClick = useCallback(() => setMobileSidebarOpen(true), []);

  return (
    <div className="flex h-dvh max-h-dvh min-h-0 overflow-hidden bg-[#171717]">
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onMobileClose={handleMobileClose}
      />
      <div className="flex min-w-0 min-h-0 flex-1 flex-col overflow-hidden">
        <Topbar onMenuClick={handleMenuClick} />
        <main className="flex-1 overflow-y-auto">
          <div className="w-full min-w-0 pb-8">
            <Outlet />
          </div>
        </main>
      </div>
      <ToastContainer />
    </div>
  );
}

// Route Configs

const routeConfigs = [
  { path: "chat", element: <ChatPage /> },
  { path: "sessions", element: <SessionsPage /> },
  { path: "agents", element: <AgentsPage /> },
  { path: "models", element: <ModelsPage /> },
  { path: "skills", element: <SkillsPage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "knowledge", element: <KnowledgePage /> },
  { path: "tools", element: <ToolsPage /> },
  { path: "mcp", element: <MCPPage /> },
  { path: "channels", element: <ChannelsPage /> },
  { path: "config", element: <ConfigPage /> },
  { path: "keys", element: <KeysPage /> },
  { path: "system", element: <SystemPage /> },
  { path: "logs", element: <LogsPage /> },
  { path: "documentation", element: <DocumentationPage /> },
];

// App

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public login page */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected dashboard routes */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/chat" replace />} />
              {routeConfigs.map((route) => (
                <Route
                  key={route.path}
                  path={route.path}
                  element={route.element}
                />
              ))}
            </Route>
          </Route>

          {/* Catch-all → redirect to dashboard */}
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
