import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  AlertTriangle,
  Settings,
  LogOut,
  Menu,
  Folder,
} from "lucide-react";

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false); // false = expanded by default

  const navItems = [
    { name: "Dashboard", to: "/", icon: LayoutDashboard },
    { name: "Inbox", to: "/inbox", icon: Inbox },
    { name: "Escalations", to: "/escalations", icon: AlertTriangle },
    { name: "Categories", to: "/categories", icon: Folder },
    { name: "Settings", to: "/settings", icon: Settings },
  ];

  return (
    <div
      className={`bg-blue-900 text-white flex flex-col justify-between min-h-screen shadow-lg transition-all duration-300`}
      style={{ width: collapsed ? "4rem" : "15rem" }}
    >
      <div>
        {/* Logo / Title with Hamburger */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-blue-700">
          {!collapsed && <span className="text-xl font-bold">SCES Admin</span>}
          <button
            className="p-1 rounded hover:bg-blue-800"
            onClick={() => setCollapsed(!collapsed)}
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col mt-6 space-y-2">
          {navItems.map(({ name, to, icon: Icon }) => (
            <NavLink
              key={name}
              to={to}
              className={({ isActive }) =>
                `flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  isActive
                    ? "bg-blue-700 text-white shadow-md"
                    : "text-blue-100 hover:bg-blue-800 hover:text-white"
                }`
              }
            >
              <Icon className="w-5 h-5" />
              {!collapsed && <span className="ml-3">{name}</span>}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Logout at Bottom */}
      <div className="px-4 py-4 border-t border-blue-700">
        <button className="flex items-center space-x-2 text-red-300 hover:text-red-500 transition-colors w-full">
          <LogOut className="h-5 w-5" />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </div>
  );
}