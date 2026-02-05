import { useState, useEffect } from "react";
import { useLocation, NavLink } from "react-router-dom";
import {
  Server,
  PieChart,
  File as FileIcon,
  Rocket,
  Github,
  Sliders,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type NavItem = {
  name: string;
  icon: LucideIcon;
  href?: string;
  children?: {
    name: string;
    icon: LucideIcon;
    href: string;
  }[];
};

const navItems: NavItem[] = [
  { name: "Dashboard", icon: PieChart, href: "/" },
  { name: "ArgoCD", icon: Server, href: "/argocd" },
  { name: "ConfigMap", icon: FileIcon, href: "/configmap" },
  {
    name: "Deploy",
    icon: Rocket,
    children: [
      { name: "GitHub", icon: Github, href: "/deploy/github" },
      { name: "Variables", icon: Sliders, href: "/deploy/variables" },
    ],
  },
];

export function Sidebar() {
  const location = useLocation();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (location.pathname.startsWith("/deploy")) {
      setExpanded((prev) => ({ ...prev, Deploy: true }));
    }
  }, [location.pathname]);

  const toggleExpand = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

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

          if (item.children) {
            const isExpanded = expanded[item.name];
            const isChildActive = item.children.some(
              (child) => child.href === location.pathname,
            );

            return (
              <div key={item.name}>
                <button
                  onClick={() => toggleExpand(item.name)}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all duration-200 font-medium text-sm",
                    isChildActive
                      ? "text-foreground bg-accent/50"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-5 h-5" />
                    <span>{item.name}</span>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                {isExpanded && (
                  <div className="pl-4 mt-1 space-y-1">
                    {item.children.map((child) => {
                      const ChildIcon = child.icon;
                      return (
                        <NavLink
                          key={child.name}
                          to={child.href}
                          className={({ isActive }) =>
                            cn(
                              "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 font-medium text-sm",
                              isActive
                                ? "bg-accent text-accent-foreground"
                                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                            )
                          }
                        >
                          <ChildIcon className="w-4 h-4" />
                          <span>{child.name}</span>
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          }

          return (
            <NavLink
              key={item.name}
              to={item.href!}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 font-medium text-sm",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
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
