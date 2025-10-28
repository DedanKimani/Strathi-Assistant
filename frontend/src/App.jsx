import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import Inbox from "./components/StrathyInbox";
import Categories from "./components/Categories"; // ✅ make sure this import is correct
// import Escalations from "./components/Escalations";
// import Settings from "./components/Settings";

function App() {
  return (
    <Router>
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard adminName="Faith" />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/categories" element={<Categories />} /> {/* ✅ Add this */}
            {/* <Route path="/escalations" element={<Escalations />} />
            <Route path="/settings" element={<Settings />} /> */}
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
