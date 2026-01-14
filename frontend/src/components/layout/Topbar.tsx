import { Search, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";

export function Topbar() {
    return (
        <header className="h-16 bg-background border-b border-border flex items-center justify-between px-6 shadow-sm transition-colors duration-200">
            <div className="flex items-center gap-4 flex-1 max-w-2xl">
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search deployments..."
                        className="w-full pl-10 pr-4 py-2 bg-secondary/50 border border-border rounded-lg text-sm font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent focus:bg-background transition-all placeholder:text-muted-foreground"
                    />
                </div>
            </div>
            <div className="flex items-center gap-3">
                <ModeToggle />
                <Button variant="ghost" size="icon" className="relative hover:bg-accent hover:text-accent-foreground">
                    <Bell className="w-5 h-5 text-muted-foreground" />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-destructive rounded-full"></span>
                </Button>
            </div>
        </header>
    );
}
