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
        <aside className="w-64 bg-card border-r border-border flex flex-col transition-colors duration-200">
            <div className="p-6 border-b border-border">
                <img
                    src="https://cdn.prod.website-files.com/67c8393507c6a7eae2efd881/6880aa06d83a6427ccf875ad_allvest%20logo%201.svg"
                    alt="Allvest Logo"
                    className="h-8 w-auto"
                />
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
                                        ? "bg-accent text-accent-foreground"
                                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                )
                            }
                        >
                            <Icon className="w-5 h-5" />
                            <span>{item.name}</span>
                        </NavLink>
                    );
                })}
            </nav>
            <div className="p-4 border-t border-border">
                <div className="flex items-center gap-3 px-4 py-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-sm">
                        U
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-semibold text-foreground">User</p>
                        <p className="text-xs text-muted-foreground">Admin</p>
                    </div>
                </div>
            </div>
        </aside>
    );
}
