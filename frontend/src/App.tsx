import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import { ThemeProvider } from "./components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { DashboardPage } from "@/features/dashboard";
import { ArgoCDPage } from "@/features/argocd";
import { MemberManagement } from "@/features/members";
import { ConfigMapPage } from "@/features/configmap";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
        <div className="flex h-screen bg-background text-foreground">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/argocd" element={<ArgoCDPage />} />
              <Route path="/members" element={<MemberManagement />} />
              <Route path="/configmap" element={<ConfigMapPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
          <Toaster />
        </div>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
