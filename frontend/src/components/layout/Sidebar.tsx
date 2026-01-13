import { Server, GitBranch, Workflow, Settings, Users } from "lucide-react";
import { cn } from "@/lib/utils";

import { NavLink } from "react-router-dom";

const navItems = [
    { name: "Clusters", icon: Server, href: "/" },
    { name: "Members", icon: Users, href: "/members" },
    { name: "Repositories", icon: GitBranch, href: "/repositories" },
    { name: "Pipelines", icon: Workflow, href: "/pipelines" },
    { name: "Settings", icon: Settings, href: "/settings" },
];

export function Sidebar() {

    return (
        <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
            <div className="p-6 border-b border-gray-200">
                <h1 className="text-2xl font-bold text-[#2a75ff]">
                    GitOps
                </h1>
                <p className="text-sm text-gray-500 mt-1">Automation Dashboard</p>
            </div>
            <nav className="flex-1 p-4 space-y-1">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                        <NavLink
                            key={item.name}
                            to={item.href}
                            className={({ isActive }) =>
                                cn(
                                    "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 font-medium text-sm",
                                    isActive
                                        ? "bg-[#eff6ff] text-[#2a75ff]"
                                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                                )
                            }
                        >
                            <Icon className="w-5 h-5" />
                            <span>{item.name}</span>
                        </NavLink>
                    );
                })}
            </nav>
            <div className="p-4 border-t border-gray-200">
                <div className="flex items-center gap-3 px-4 py-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-sm">
                        U
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-semibold text-gray-900">User</p>
                        <p className="text-xs text-gray-500">Admin</p>
                    </div>
                </div>
            </div>
        </aside>
    );
}
