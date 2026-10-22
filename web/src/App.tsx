import { Navigate, Route, Routes } from "react-router-dom";

import { Sidebar } from "./components/Sidebar";
import { HistoryPage } from "./pages/History";
import { StatusPage } from "./pages/Status";
import { WorkspacePage } from "./pages/Workspace";
import { ThemeProvider } from "./theme";

export default function App() {
  return (
    <ThemeProvider>
      <div className="app">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<WorkspacePage />} />
            <Route path="/workspace/:workId" element={<WorkspacePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/status" element={<StatusPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </ThemeProvider>
  );
}
