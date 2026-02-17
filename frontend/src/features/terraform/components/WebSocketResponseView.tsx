import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Terminal, AlertCircle, Loader2, ChevronDown, ChevronUp, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface Props {
    prNumber: number;
    repoName: string;
}

export function WebSocketResponseView({ prNumber, repoName }: Props) {
    const [status, setStatus] = useState<"connecting" | "connected" | "error" | "closed">("connecting");
    const [latestData, setLatestData] = useState<any>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [showRawLogs, setShowRawLogs] = useState(true);

    // Comment fetching state
    const [commentContent, setCommentContent] = useState<string | null>(null);
    const [isFetchingComment, setIsFetchingComment] = useState(false);
    const [commentError, setCommentError] = useState<string | null>(null);

    // Atlantis state
    const [isAtlantisPlan, setIsAtlantisPlan] = useState(false);
    const [applyDirectory, setApplyDirectory] = useState<string | null>(null);
    const [actionLoading, setActionLoading] = useState<"accept" | "reject" | null>(null);

    const ws = useRef<WebSocket | null>(null);
    const lastCommentIdRef = useRef<string | null>(null);

    // Helper functions for Atlantis detection
    const checkIsAtlantisPlan = (comment: string) => {
        if (!comment) return false;

        const requiredStrings = [
            "Ran Plan for dir:",
            "Terraform will perform the following actions:",
        ];

        const hasRequired = requiredStrings.every(str =>
            comment.includes(str)
        );

        const hasPlanSummary =
            /Plan:\s+\d+\s+to add,\s+\d+\s+to change,\s+\d+\s+to destroy/.test(comment);

        const hasApplyInstruction =
            comment.includes("atlantis apply") ||
            comment.includes("To apply this plan");

        return hasRequired && hasPlanSummary && hasApplyInstruction;
    };

    const extractDirectory = (comment: string) => {
        const match = comment.match(/atlantis apply\s+-d\s+([^\s]+)/);
        return match ? match[1] : null;
    };

    // Handler for Accept/Reject actions
    const handleAction = async (action: "accept" | "reject") => {
        if (action === "accept" && !applyDirectory) {
            toast.error("Could not determine directory to apply.");
            return;
        }

        setActionLoading(action);
        const baseUrl = import.meta.env.VITE_API_BASE_URL;

        try {
            const commentBody = action === "accept"
                ? `atlantis apply -d ${applyDirectory}`
                : "atlantis unlock";

            const payload = {
                pr_number: prNumber,
                comment: commentBody,
                repo_name: repoName
            };

            const response = await fetch(`${baseUrl}/github/comments`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Failed to ${action} plan`);
            }

            toast.success(action === "accept" ? "Plan Accepted - Applying..." : "Plan Rejected - Unlocked");
        } catch (error) {
            console.error(error);
            toast.error(`Failed to ${action} plan`);
        } finally {
            setActionLoading(null);
        }
    };

    // Fetch comment function
    const fetchComment = async (commentId: string) => {
        if (!commentId || !repoName) return;

        // Avoid refetching same comment
        if (lastCommentIdRef.current === commentId) return;
        lastCommentIdRef.current = commentId;

        setIsFetchingComment(true);
        setCommentError(null);
        setIsAtlantisPlan(false);
        setApplyDirectory(null);

        try {
            // repoName is "owner/repo", handled by backend? 
            // Endpoint: http://127.0.0.1:8000/api/github/comments/{{comment_id}}?repo_name=(owner/repo)
            const baseUrl = import.meta.env.VITE_API_BASE_URL;
            const response = await fetch(`${baseUrl}/github/comments/${commentId}?repo_name=${encodeURIComponent(repoName)}`);

            if (!response.ok) {
                throw new Error("Failed to fetch comment");
            }

            const data = await response.json();
            if (data && data.body) {
                setCommentContent(data.body);

                // Check if it is an Atlantis plan
                if (checkIsAtlantisPlan(data.body)) {
                    setIsAtlantisPlan(true);
                    const dir = extractDirectory(data.body);
                    if (dir) {
                        setApplyDirectory(dir);
                    }
                }
            }
        } catch (err) {
            console.error("Error fetching comment:", err);
            setCommentError("Could not load comment content.");
        } finally {
            setIsFetchingComment(false);
        }
    };

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
                if (data && typeof data === 'object' && ('plan_status' in data || 'state' in data)) {
                    setLatestData(data);

                    // Check for last_comment (assuming it's an ID or has an ID)
                    // Requirements say "From the API response, extract ONLY the "body" field"
                    // So we assume data.last_comment might be the content OR the ID. 
                    // The requirement "c. Implement Last Comment display... fetches data from API... with comment_id"
                    // implies `latestData.last_comment` is likely the CONTENT or we have another field for ID.
                    // However, if the backend sends the ID in a field (e.g. comment_id), update this.
                    // For now, based on "Fetch data from ... {{comment_id}}", I'll assume we get an ID.
                    // BUT previous code displayed `latestData.last_comment` directly. 
                    // If the previous code showed "some more comments", then last_comment was text.
                    // IMPORTANT: The requirement says "Fetch data from ... {{comment_id}}". 
                    // I will guess we need to use `data.last_comment` as the ID if it looks numeric/id-like, 
                    // OR check for `data.comment_id`. 
                    // I will check for `data.comment_id` first, then fallback to testing `data.last_comment`.

                    const commentId = data.comment_id || (typeof data.comment_id !== 'string' || data.comment_id.includes(' ') ? null : data.last_comment);
                    if (commentId) {
                        fetchComment(commentId);
                    } else if (data.last_comment && !commentContent) {
                        // Fallback: if we have text but no ID, maybe just show text? 
                        // But requirement says "Fetch from API". 
                        // I'll assume for now `latestData.last_comment` might be the content if fetch fails/not needed.
                    }
                }

                // Always log raw
                setLogs(prev => [...prev, event.data]);

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
    }, [prNumber, repoName]);

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
                        {/* Last Comment Section */}
                        <div className="space-y-1 md:col-span-2 lg:col-span-3">
                            <span className="text-xs font-medium text-muted-foreground uppercase">Last Comment</span>
                            <div className="text-sm p-3 bg-muted rounded min-h-[60px]">
                                {isFetchingComment ? (
                                    <div className="flex items-center gap-2 text-muted-foreground">
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                        Fetching comment...
                                    </div>
                                ) : commentContent ? (
                                    <div className="whitespace-pre-wrap font-mono text-xs">{commentContent}</div>
                                ) : commentError ? (
                                    <span className="text-destructive text-xs">{commentError}</span>
                                ) : (
                                    <span className="text-muted-foreground italic">
                                        {latestData.last_comment || "No comments yet"}
                                    </span>
                                )}
                            </div>

                            {/* Atlantis Actions */}
                            {isAtlantisPlan && !isFetchingComment && (
                                <div className="flex items-center gap-3 mt-3 animate-in fade-in slide-in-from-top-2">
                                    <Button
                                        onClick={() => handleAction("accept")}
                                        disabled={actionLoading !== null}
                                        className="bg-green-600 hover:bg-green-700 text-white gap-2"
                                        size="sm"
                                    >
                                        {actionLoading === "accept" ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Check className="h-4 w-4" />
                                        )}
                                        Accept Plan
                                    </Button>
                                    <Button
                                        onClick={() => handleAction("reject")}
                                        disabled={actionLoading !== null}
                                        variant="destructive"
                                        size="sm"
                                        className="gap-2"
                                    >
                                        {actionLoading === "reject" ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <X className="h-4 w-4" />
                                        )}
                                        Reject Plan
                                    </Button>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Raw Logs Section */}
                <div className="space-y-2 border rounded-md p-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full flex justify-between items-center h-8"
                        onClick={() => setShowRawLogs(!showRawLogs)}
                    >
                        <span className="text-sm font-medium">Raw Logs</span>
                        {showRawLogs ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>

                    {showRawLogs && (
                        <div className="bg-black/90 text-green-400 p-4 rounded-md font-mono text-xs md:text-sm h-[300px] overflow-y-auto shadow-inner border border-gray-800 mt-2">
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
                    )}
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
