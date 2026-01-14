import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    useReactTable,
    getCoreRowModel,
    getFilteredRowModel,
    getSortedRowModel,
    getPaginationRowModel,
    flexRender,
    type ColumnDef,
    type SortingState,
    type VisibilityState,
    type ColumnFiltersState,
    type PaginationState,
} from '@tanstack/react-table';
import {
    Search,
    Plus,
    MoreVertical,
    ChevronLeft,
    ChevronRight,
    Columns3,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
    DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from '@/components/ui/sheet';
import type { Member } from '@/types/member';
import { fetchMembers } from '@/services/memberService';
import AddMemberForm from '@/components/AddMemberForm';

export default function MemberManagement() {
    // Data state
    const { data: members = [], isLoading: loading, error } = useQuery({
        queryKey: ['members'],
        queryFn: fetchMembers,
    });

    // Table state
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
    const [globalFilter, setGlobalFilter] = useState('');
    const [pagination, setPagination] = useState<PaginationState>({
        pageIndex: 0,
        pageSize: 10,
    });

    // Filter states
    const [statusFilter, setStatusFilter] = useState('all');
    const [activeUsersOnly, setActiveUsersOnly] = useState(false);

    // Sidebar state
    const [isAddMemberOpen, setIsAddMemberOpen] = useState(false);
    const [editingMember, setEditingMember] = useState<Member | null>(null);



    // Generate initials for avatar
    const getInitials = (name: string) => {
        return name.charAt(0).toUpperCase();
    };

    // Handle actions
    const handleEdit = (member: Member) => {
        setEditingMember(member);
        setIsAddMemberOpen(true);
    };

    const handleCopyId = (id: number) => {
        navigator.clipboard.writeText(id.toString());
        console.log('Copied ID:', id);
    };

    const handleDelete = (member: Member) => {
        console.log('Delete member:', member);
    };

    const handleAddNew = () => {
        setEditingMember(null);
        setIsAddMemberOpen(true);
    };

    // Column definitions
    const columns: ColumnDef<Member>[] = [
        {
            accessorKey: 'name',
            id: 'member',
            header: ({ column }) => {
                return (
                    <button
                        className="flex items-center gap-2 font-semibold text-muted-foreground hover:text-foreground"
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                    >
                        Member
                        {column.getIsSorted() === 'asc' ? (
                            <ArrowUp className="h-4 w-4" />
                        ) : column.getIsSorted() === 'desc' ? (
                            <ArrowDown className="h-4 w-4" />
                        ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                        )}
                    </button>
                );
            },
            cell: ({ row }) => {
                const member = row.original;
                return (
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-sm">
                            {getInitials(member.name)}
                        </div>
                        <div>
                            <div className="font-medium text-foreground capitalize">
                                {member.name}
                            </div>
                            <div className="text-xs text-muted-foreground">
                                {member.tasks} tasks
                            </div>
                        </div>
                    </div>
                );
            },
            enableSorting: true,
            enableHiding: false, // Always visible
        },
        {
            accessorKey: 'roles',
            id: 'roles',
            header: () => <span className="font-semibold text-muted-foreground">Roles</span>,
            cell: ({ row }) => {
                return (
                    <div className="flex gap-2">
                        {row.original.roles.map((role, idx) => (
                            <span
                                key={idx}
                                className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded"
                            >
                                {role}
                            </span>
                        ))}
                    </div>
                );
            },
            enableSorting: false,
        },
        {
            accessorKey: 'location',
            id: 'location',
            header: () => <span className="font-semibold text-gray-700">Location</span>,
            cell: ({ row }) => {
                return (
                    <div className="flex items-center gap-2">
                        <span className="text-lg">{row.original.locationFlag}</span>
                        <span className="text-gray-700">{row.original.location}</span>
                    </div>
                );
            },
            enableSorting: false,
        },
        {
            accessorKey: 'status',
            id: 'status',
            header: ({ column }) => {
                return (
                    <button
                        className="flex items-center gap-2 font-semibold text-muted-foreground hover:text-foreground"
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                    >
                        Status
                        {column.getIsSorted() === 'asc' ? (
                            <ArrowUp className="h-4 w-4" />
                        ) : column.getIsSorted() === 'desc' ? (
                            <ArrowDown className="h-4 w-4" />
                        ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                        )}
                    </button>
                );
            },
            cell: ({ row }) => {
                const status = row.original.status;
                const colorMap = {
                    Active: 'bg-green-100 text-green-700',
                    Pending: 'bg-yellow-100 text-yellow-700',
                    Deleted: 'bg-red-100 text-red-700',
                };
                return (
                    <span className={`px-3 py-1 text-xs font-medium rounded-full ${colorMap[status]}`}>
                        {status}
                    </span>
                );
            },
            enableSorting: true,
        },
        {
            accessorKey: 'age',
            id: 'age',
            header: ({ column }) => {
                return (
                    <button
                        className="flex items-center gap-2 font-semibold text-gray-700 hover:text-gray-900"
                        onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
                    >
                        Age
                        {column.getIsSorted() === 'asc' ? (
                            <ArrowUp className="h-4 w-4" />
                        ) : column.getIsSorted() === 'desc' ? (
                            <ArrowDown className="h-4 w-4" />
                        ) : (
                            <ArrowUpDown className="h-4 w-4 opacity-50" />
                        )}
                    </button>
                );
            },
            cell: ({ row }) => {
                return <span className="text-gray-700">{row.original.age} years</span>;
            },
            enableSorting: true,
        },
        {
            accessorKey: 'recentActivity',
            id: 'recentActivity',
            header: () => <span className="font-semibold text-gray-700">Recent Activity</span>,
            cell: ({ row }) => {
                return <span className="text-gray-700">{row.original.recentActivity}</span>;
            },
            enableSorting: false,
        },
        {
            id: 'actions',
            header: () => <span className="font-semibold text-muted-foreground text-right block">Actions</span>,
            cell: ({ row }) => {
                const member = row.original;
                return (
                    <div className="text-right">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0 hover:bg-accent"
                                >
                                    <MoreVertical className="h-4 w-4 text-muted-foreground" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-40">
                                <DropdownMenuItem
                                    onClick={() => handleEdit(member)}
                                    className="cursor-pointer"
                                >
                                    Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => handleCopyId(member.id)}
                                    className="cursor-pointer"
                                >
                                    Copy ID
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                    onClick={() => handleDelete(member)}
                                    className="cursor-pointer text-red-600 focus:text-red-600"
                                >
                                    Delete
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                );
            },
            enableHiding: false, // Always visible
        },
    ];

    // Initialize table
    const table = useReactTable({
        data: members,
        columns,
        state: {
            sorting,
            columnFilters,
            columnVisibility,
            globalFilter,
            pagination,
        },
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onColumnVisibilityChange: setColumnVisibility,
        onGlobalFilterChange: setGlobalFilter,
        onPaginationChange: setPagination,
        getCoreRowModel: getCoreRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        globalFilterFn: 'includesString',
    });

    // Apply status filter
    useEffect(() => {
        if (statusFilter === 'all') {
            table.getColumn('status')?.setFilterValue(undefined);
        } else {
            table.getColumn('status')?.setFilterValue(statusFilter);
        }
    }, [statusFilter, table]);

    // Apply active users filter
    useEffect(() => {
        if (activeUsersOnly) {
            table.getColumn('status')?.setFilterValue('Active');
            setStatusFilter('Active');
        } else if (statusFilter === 'Active' && !activeUsersOnly) {
            // Only clear if it was set by the toggle
            table.getColumn('status')?.setFilterValue(undefined);
            setStatusFilter('all');
        }
    }, [activeUsersOnly, table]);

    // Update page size when rows per page changes
    useEffect(() => {
        setPagination(prev => ({
            pageIndex: 0,
            pageSize: prev.pageSize,
        }));
    }, []);

    if (loading) {
        return (
            <div className="bg-background p-6">
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center justify-center h-64">
                        <Loader2 className="w-8 h-8 animate-spin text-primary" />
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-background p-6">
                <div className="max-w-7xl mx-auto">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                        {error instanceof Error ? error.message : 'An error occurred'}
                    </div>
                </div>
            </div>
        );
    }

    const totalRows = table.getFilteredRowModel().rows.length;
    const startIndex = table.getState().pagination.pageIndex * pagination.pageSize;
    const endIndex = Math.min(startIndex + pagination.pageSize, totalRows);

    return (
        <div className="bg-background p-6">
            <div className="max-w-7xl mx-auto">
                {/* Page Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-semibold text-foreground">Member Management</h1>
                    <p className="text-sm text-muted-foreground mt-1">Manage your team members and their information</p>
                </div>

                {/* Main Card */}
                <div className="bg-card rounded-xl border border-border shadow-sm">
                    {/* Toolbar */}
                    <div className="p-4 border-b border-border">
                        <div className="flex flex-wrap items-center gap-3">
                            {/* Search Input */}
                            <div className="relative flex-1 min-w-[200px]">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search Members..."
                                    value={globalFilter}
                                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGlobalFilter(e.target.value)}
                                    className="pl-9 h-9 bg-background border-border"
                                />
                            </div>

                            {/* Status Filter */}
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger className="w-[140px] h-9 bg-card border-border">
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All Status</SelectItem>
                                    <SelectItem value="Active">Active</SelectItem>
                                    <SelectItem value="Pending">Pending</SelectItem>
                                    <SelectItem value="Deleted">Deleted</SelectItem>
                                </SelectContent>
                            </Select>

                            {/* Active Users Toggle */}
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-card border border-border rounded-lg">
                                <span className="text-sm text-foreground">Active Users</span>
                                <Switch
                                    checked={activeUsersOnly}
                                    onCheckedChange={setActiveUsersOnly}
                                />
                            </div>

                            {/* Add New Button */}
                            <Button
                                onClick={handleAddNew}
                                className="h-9 bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5"
                            >
                                <Plus className="h-4 w-4" />
                                Add New
                            </Button>

                            {/* Columns Visibility Dropdown */}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="outline"
                                        className="h-9 border-border gap-1.5"
                                    >
                                        <Columns3 className="h-4 w-4" />
                                        Columns
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-48">
                                    <div className="px-2 py-1.5 text-sm font-semibold text-foreground">
                                        Toggle Columns
                                    </div>
                                    <DropdownMenuSeparator />
                                    {table
                                        .getAllColumns()
                                        .filter((column) => column.getCanHide())
                                        .map((column) => {
                                            return (
                                                <DropdownMenuCheckboxItem
                                                    key={column.id}
                                                    className="capitalize cursor-pointer"
                                                    checked={column.getIsVisible()}
                                                    onCheckedChange={(value) => column.toggleVisibility(!!value)}
                                                >
                                                    {column.id === 'recentActivity' ? 'Recent Activity' : column.id}
                                                </DropdownMenuCheckboxItem>
                                            );
                                        })}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </div>

                    {/* Table */}
                    <div className="overflow-x-auto">
                        <Table>
                            <TableHeader>
                                {table.getHeaderGroups().map((headerGroup) => (
                                    <TableRow key={headerGroup.id} className="border-border hover:bg-transparent">
                                        {headerGroup.headers.map((header) => (
                                            <TableHead key={header.id}>
                                                {header.isPlaceholder
                                                    ? null
                                                    : flexRender(
                                                        header.column.columnDef.header,
                                                        header.getContext()
                                                    )}
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                ))}
                            </TableHeader>
                            <TableBody>
                                {table.getRowModel().rows.length > 0 ? (
                                    table.getRowModel().rows.map((row) => (
                                        <TableRow
                                            key={row.id}
                                            className="border-border hover:bg-muted/50"
                                        >
                                            {row.getVisibleCells().map((cell) => (
                                                <TableCell key={cell.id}>
                                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))
                                ) : (
                                    <TableRow>
                                        <TableCell
                                            colSpan={columns.length}
                                            className="h-24 text-center text-muted-foreground"
                                        >
                                            No members found.
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </div>

                    {/* Pagination Footer */}
                    <div className="p-4 border-t border-border">
                        <div className="flex items-center justify-between flex-wrap gap-4">
                            {/* Rows per page */}
                            <div className="flex items-center gap-2">
                                <span className="text-sm text-foreground">Rows per page</span>
                                <Select
                                    value={pagination.pageSize.toString()}
                                    onValueChange={(value: string) => {
                                        setPagination({
                                            pageIndex: 0,
                                            pageSize: Number(value),
                                        });
                                    }}
                                >
                                    <SelectTrigger className="w-[70px] h-8 bg-card border-border">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="10">10</SelectItem>
                                        <SelectItem value="25">25</SelectItem>
                                        <SelectItem value="50">50</SelectItem>
                                        <SelectItem value="100">100</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Page info and navigation */}
                            <div className="flex items-center gap-4">
                                {/* Range text */}
                                <span className="text-sm text-foreground">
                                    {startIndex + 1} - {endIndex} of {totalRows}
                                </span>

                                {/* Page navigation */}
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => table.previousPage()}
                                        disabled={!table.getCanPreviousPage()}
                                        className="h-8 w-8 p-0 hover:bg-accent disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                                    >
                                        <ChevronLeft className="h-4 w-4" />
                                    </Button>

                                    {/* Page numbers */}
                                    {Array.from({ length: Math.min(table.getPageCount(), 5) }, (_, i) => {
                                        const pageNum = i + 1;
                                        const pageIndex = i;
                                        return (
                                            <Button
                                                key={pageNum}
                                                variant={table.getState().pagination.pageIndex === pageIndex ? 'default' : 'ghost'}
                                                size="sm"
                                                onClick={() => table.setPageIndex(pageIndex)}
                                                className={`h-8 w-8 p-0 cursor-pointer ${table.getState().pagination.pageIndex === pageIndex
                                                    ? 'bg-primary hover:bg-primary/90 text-primary-foreground'
                                                    : 'hover:bg-accent'
                                                    }`}
                                            >
                                                {pageNum}
                                            </Button>
                                        );
                                    })}

                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => table.nextPage()}
                                        disabled={!table.getCanNextPage()}
                                        className="h-8 w-8 p-0 hover:bg-accent disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                                    >
                                        <ChevronRight className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Add Member Sheet */}
            <Sheet open={isAddMemberOpen} onOpenChange={setIsAddMemberOpen}>
                <SheetContent className="w-[400px] sm:w-[540px] bg-card p-6">
                    <SheetHeader>
                        <SheetTitle className="text-xl font-semibold text-foreground">
                            {editingMember ? 'Edit Member' : 'New Member'}
                        </SheetTitle>
                    </SheetHeader>
                    <div className="mt-6 flex flex-col h-[calc(100vh-150px)]">
                        <AddMemberForm
                            onClose={() => setIsAddMemberOpen(false)}
                            initialData={editingMember}
                        />
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
}
