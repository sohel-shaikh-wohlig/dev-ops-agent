import { Search, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Topbar() {
    return (
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shadow-sm">
            <div className="flex items-center gap-4 flex-1 max-w-2xl">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search deployments..."
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm font-medium text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent focus:bg-white transition-all placeholder:text-gray-400"
                    />
                </div>
            </div>
            <div className="flex items-center gap-3">
                <Button variant="ghost" size="icon" className="relative hover:bg-gray-100">
                    <Bell className="w-5 h-5 text-gray-600" />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full"></span>
                </Button>
            </div>
        </header>
    );
}
