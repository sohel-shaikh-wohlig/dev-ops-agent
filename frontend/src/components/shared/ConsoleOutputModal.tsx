import { Terminal, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { LogEntry } from "@/features/gitops/services/gitops-service";
import { useEffect, useRef } from "react";

interface ConsoleOutputModalProps {
    open: boolean;
    logs: LogEntry[];
    isLoading: boolean;
    onClose: () => void;
    title?: string;
}

export function ConsoleOutputModal({
    open,
    logs,
    isLoading,
    onClose,
    title = "Console Output",
}: ConsoleOutputModalProps) {
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll logs
    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, open]);

    return (
        <DialogPrimitive.Root open={open}>
            <DialogPrimitive.Portal>
                <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
                <DialogPrimitive.Content className="fixed left-[50%] top-[50%] z-50 grid w-full max-w-4xl translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-0 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg">
                    <div className="flex flex-col h-[80vh]">
                        <div className="flex items-center justify-between px-6 py-4 border-b">
                            <div className="flex items-center gap-2">
                                <Terminal className="h-5 w-5 text-muted-foreground" />
                                <DialogPrimitive.Title className="text-lg font-semibold">
                                    {title}
                                </DialogPrimitive.Title>
                            </div>
                            {/* Close button  */}
                            {!isLoading && (
                                <DialogPrimitive.Close
                                    className="rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
                                    onClick={onClose}
                                >
                                    <span className="sr-only">Close</span>
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        width="24"
                                        height="24"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        className="h-4 w-4"
                                    >
                                        <path d="M18 6 6 18" />
                                        <path d="m6 6 12 12" />
                                    </svg>
                                </DialogPrimitive.Close>
                            )}
                            {isLoading && (
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            )}
                        </div>

                        <div className="flex-1 overflow-hidden p-0 bg-black">
                            <div className="h-full w-full overflow-y-auto p-6 font-mono text-sm text-green-400 space-y-1">
                                {logs.length === 0 && isLoading && (
                                    <div className="text-zinc-500 italic">Starting process...</div>
                                )}
                                {logs.map((log, index) => (
                                    <div key={index} className="break-all whitespace-pre-wrap">
                                        <span className="opacity-50 text-xs mr-2">
                                            [
                                            {new Date(
                                                log.timestamp ? log.timestamp * 1000 : Date.now()
                                            ).toLocaleTimeString()}
                                            ]
                                        </span>
                                        {log.message}
                                    </div>
                                ))}
                                <div ref={logsEndRef} />
                            </div>
                        </div>

                        {!isLoading && (
                            <div className="px-6 py-4 border-t flex justify-end">
                                <Button onClick={onClose}>Close Console</Button>
                            </div>
                        )}
                    </div>
                </DialogPrimitive.Content>
            </DialogPrimitive.Portal>
        </DialogPrimitive.Root>
    );
}
