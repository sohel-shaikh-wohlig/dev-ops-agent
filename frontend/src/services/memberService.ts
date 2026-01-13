import type { Member } from '@/types/member';

const API_URL = 'https://dummyjson.com/c/770d-fe9c-4cba-ad30';

// Deterministic data generation based on member ID
const ROLES_OPTIONS = [
    ['Designer', 'Admin'],
    ['Editor', 'Tester'],
    ['Editor', 'Analyst'],
    ['Admin', 'Analyst'],
    ['Admin', 'Scrum Master'],
    ['Admin', 'Support'],
    ['Designer', 'Analyst'],
    ['Support', 'Developer'],
];

const LOCATIONS = [
    { name: 'South Korea', flag: '🇰🇷' },
    { name: 'Germany', flag: '🇩🇪' },
    { name: 'Russia', flag: '🇷🇺' },
    { name: 'France', flag: '🇫🇷' },
    { name: 'Australia', flag: '🇦🇺' },
    { name: 'Spain', flag: '🇪🇸' },
    { name: 'Malaysia', flag: '🇲🇾' },
    { name: 'United States', flag: '🇺🇸' },
];

const STATUSES: Array<'Active' | 'Pending' | 'Deleted'> = ['Active', 'Pending', 'Deleted'];

const RECENT_ACTIVITIES = [
    '3 days ago',
    '2 days ago',
    'Week ago',
    '2 weeks ago',
    'Month ago',
];

// Deterministic augmentation function
function augmentMember(member: { id: number; name: string; age: number }): Member {
    const id = member.id;

    return {
        ...member,
        roles: ROLES_OPTIONS[id % ROLES_OPTIONS.length],
        location: LOCATIONS[id % LOCATIONS.length].name,
        locationFlag: LOCATIONS[id % LOCATIONS.length].flag,
        status: STATUSES[id % STATUSES.length],
        recentActivity: RECENT_ACTIVITIES[id % RECENT_ACTIVITIES.length],
        tasks: 20 + (id * 7) % 100, // Generate task count between 20-120
    };
}

export async function fetchMembers(): Promise<Member[]> {
    try {
        const response = await fetch(API_URL);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: Array<{ id: number; name: string; age: number }> = await response.json();

        // Augment each member with additional fields
        return data.map(augmentMember);
    } catch (error) {
        console.error('Error fetching members:', error);
        throw error;
    }
}
