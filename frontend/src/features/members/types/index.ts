export interface Member {
    id: number;
    name: string;
    age: number;
    // Augmented fields (generated from API data)
    roles: string[];
    location: string;
    locationFlag: string;
    status: 'Active' | 'Pending' | 'Deleted';
    recentActivity: string;
    tasks: number;
}
