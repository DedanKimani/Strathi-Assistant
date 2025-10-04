import React, { useEffect, useState } from "react";
import { Mail, AlertTriangle, CheckCircle } from "lucide-react";

const BRAND = {
  red: "#C8102E",
  blue: "#0033A0",
  slate: "#0F172A",
  soft: "#F8FAFC",
};

export default function Dashboard({ adminName = "Faith" }) {
  const [stats, setStats] = useState({
    total: 124,
    replied: 82,
    escalated: 12,
  });

  return (
    <div className="flex flex-col w-full min-h-screen" style={{ background: BRAND.soft }}>
      {/* Top Banner with brand gradient (thinner) */}
      <div
        className="text-white px-8 py-2 flex justify-between items-center shadow-md"
        style={{
          background: `linear-gradient(120deg, ${BRAND.red} 0%, ${BRAND.blue} 100%)`,
        }}
      >
        <div>
          <h1 className="text-2xl font-bold">Welcome, {adminName}</h1>
          <p className="text-sm opacity-90">
            Here’s your SCES Admin overview
          </p>
        </div>
        <Mail className="w-7 h-7 text-white opacity-90" />
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-2xl shadow p-4 border border-blue-200">
            <div className="flex items-center space-x-3">
              <Mail className="text-blue-600" />
              <div>
                <p className="text-gray-600 text-sm">Total Emails</p>
                <h2 className="text-xl font-bold">{stats.total}</h2>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow p-4 border border-green-200">
            <div className="flex items-center space-x-3">
              <CheckCircle className="text-green-600" />
              <div>
                <p className="text-gray-600 text-sm">Replied Emails</p>
                <h2 className="text-xl font-bold">{stats.replied}%</h2>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow p-4 border border-yellow-200">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="text-yellow-600" />
              <div>
                <p className="text-gray-600 text-sm">Escalated Emails</p>
                <h2 className="text-xl font-bold">{stats.escalated}%</h2>
              </div>
            </div>
          </div>
        </div>

        {/* Escalated List */}
        <div className="bg-white rounded-2xl shadow p-4">
          <h3 className="font-semibold text-lg mb-3">🚨 Recently Escalated Emails</h3>
          <div className="space-y-2 text-sm">
            <div className="border-b pb-2">
              <p className="font-medium">Fee Payment Clarification</p>
              <p className="text-gray-500">student1@strathmore.edu</p>
            </div>
            <div>
              <p className="font-medium">Course Registration Issue</p>
              <p className="text-gray-500">student2@strathmore.edu</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
