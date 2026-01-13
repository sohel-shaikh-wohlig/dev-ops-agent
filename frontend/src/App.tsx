import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import MemberManagement from "./components/MemberManagement";
import { Dashboard } from "./components/dashboard/Dashboard";

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Topbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/members" element={<main className="flex-1 overflow-y-auto"><MemberManagement /></main>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
