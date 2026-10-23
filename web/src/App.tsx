import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { Sidebar } from "./components/Sidebar";
import { HistoryPage } from "./pages/History";
import { LandingPage } from "./pages/Landing";
import { WorkspacePage } from "./pages/Workspace";
import { ThemeProvider } from "./theme";

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <Sidebar />
      <main className="main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/workspace"
          element={
            <Shell>
              <WorkspacePage />
            </Shell>
          }
        />
        <Route
          path="/workspace/:workId"
          element={
            <Shell>
              <WorkspacePage />
            </Shell>
          }
        />
        <Route
          path="/history"
          element={
            <Shell>
              <HistoryPage />
            </Shell>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ThemeProvider>
  );
}
