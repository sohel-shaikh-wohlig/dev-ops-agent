import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Terminal, AlertCircle, Loader2 } from "lucide-react";

interface Props {
    prNumber: number;
}

export function WebSocketResponseView({ prNumber }: Props) {
    const [status, setStatus] = useState<"connecting" | "connected" | "error" | "closed">("connecting");
    const [latestData, setLatestData] = useState<any>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Construct Dynamic WebSocket URL
        const baseUrl = import.meta.env.VITE_API_BASE_URL;
        const wsBaseUrl = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://");
        const socketUrl = `${wsBaseUrl}/ws/pr-status/${prNumber}`;

        console.log(`Connecting to WebSocket: ${socketUrl}`);

        // Initialize WebSocket connection
        const socket = new WebSocket(socketUrl);
        ws.current = socket;

        socket.onopen = () => {
            console.log("WebSocket connected");
            setStatus("connected");
            setLogs(prev => [...prev, "Connected to server..."]);
        };

        socket.onmessage = (event) => {
            console.log("Message received:", event.data);
            try {
                const data = JSON.parse(event.data);
                // Check if it looks like our expected data structure
                if (data && typeof data === 'object' && 'plan_status' in data) {
                    setLatestData(data);
                } else {
                    // It might be a plain log message
                    setLogs(prev => [...prev, event.data]);
                }
            } catch (e) {
                // Not JSON, treat as plain text log
                setLogs(prev => [...prev, event.data]);
            }
        };

        socket.onerror = (error) => {
            console.error("WebSocket error:", error);
            setStatus("error");
            setLogs(prev => [...prev, "Error connecting to server."]);
        };

        socket.onclose = () => {
            console.log("WebSocket disconnected");
            if (status !== "error") {
                setStatus("closed");
                setLogs(prev => [...prev, "Connection closed."]);
            }
        };

        return () => {
            socket.close();
        };
    }, [prNumber]);

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center gap-2">
                    <Terminal className="w-6 h-6 text-primary" />
                    <CardTitle>Terraform Provisioning Status (PR #{prNumber})</CardTitle>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    Status:
                    <span className={`font-medium ${status === "connected" ? "text-green-500" :
                            status === "error" ? "text-red-500" :
                                "text-yellow-500"
                        }`}>
                        {status.toUpperCase()}
                    </span>
                    {status === "connecting" && <Loader2 className="h-3 w-3 animate-spin" />}
                </div>

                {latestData && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 border rounded-lg bg-muted/10">
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground uppercase">PR Number</span>
                            <div className="font-semibold text-lg">#{latestData.pr_number}</div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground uppercase">State</span>
                            <div className={`font-semibold capitalize ${latestData.state === 'open' ? 'text-green-600' : 'text-gray-600'
                                }`}>{latestData.state}</div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground uppercase">Approved</span>
                            <div className={`font-semibold ${latestData.approved ? 'text-green-600' : 'text-yellow-600'
                                }`}>{latestData.approved ? 'Yes' : 'No'}</div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground uppercase">Plan Status</span>
                            <div className="font-medium">{latestData.plan_status}</div>
                        </div>
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground uppercase">Apply Status</span>
                            <div className="font-medium">{latestData.apply_status}</div>
                        </div>
                        <div className="space-y-1 md:col-span-2 lg:col-span-3">
                            <span className="text-xs font-medium text-muted-foreground uppercase">Last Comment</span>
                            <div className="text-sm p-2 bg-muted rounded">{latestData.last_comment}</div>
                        </div>
                    </div>
                )}

                <div className="space-y-2">
                    <h3 className="text-sm font-medium">Raw Logs</h3>
                    <div className="bg-black/90 text-green-400 p-4 rounded-md font-mono text-xs md:text-sm h-[300px] overflow-y-auto shadow-inner border border-gray-800">
                        {logs.length === 0 ? (
                            <div className="text-gray-500 italic">No logs yet...</div>
                        ) : (
                            logs.map((msg, idx) => (
                                <div key={idx} className="whitespace-pre-wrap break-words border-b border-gray-800/50 pb-1 mb-1 last:border-0">
                                    <span className="text-gray-500 select-none mr-2">[{new Date().toLocaleTimeString()}]</span>
                                    {msg}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {status === "error" && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Connection Error</AlertTitle>
                        <AlertDescription>
                            Failed to connect to the provisioning server. Please check your connection or try again later.
                        </AlertDescription>
                    </Alert>
                )}
            </CardContent>
        </Card>
    );
}
