# GitOps Automation Dashboard

A modern, Metronic-themed dashboard for managing GitOps workflows built with React 19, Vite, TypeScript, and Tailwind CSS.

## Features

- 🎨 **Metronic-inspired Design** - Clean, professional light theme
- 📊 **Real-time Updates** - Simulated deployment status changes every 5 seconds
- 🎯 **Type-safe** - Full TypeScript implementation
- 🎭 **Modern UI** - Shadcn/ui components with Lucide React icons
- 📱 **Responsive** - Works on desktop and tablet devices

## Tech Stack

- **React 19** - Latest React with improved performance
- **Vite** - Fast build tool and dev server
- **TypeScript** - Type safety and better DX
- **Tailwind CSS v4** - Utility-first CSS framework
- **Shadcn/ui** - High-quality, accessible components
- **Lucide React** - Beautiful, consistent icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── layout/          # Sidebar, Topbar
│   ├── dashboard/       # DeploymentCard, StatusBadge
│   └── ui/              # Shadcn/ui components
├── hooks/               # useGitOpsData
├── types/               # TypeScript interfaces
├── lib/                 # Utilities
├── App.tsx              # Main app component
└── index.css            # Global styles & theme
```

## Features Overview

### Dashboard View
- **Sidebar Navigation** - Clusters, Repositories, Pipelines, Settings
- **Search Functionality** - Quick search across deployments
- **Deployment Cards** - Grid layout showing:
  - Deployment name and namespace
  - Status badges (Healthy, Progressing, Degraded)
  - Cluster information
  - Sync status
  - Last sync time

### Mock Data
The dashboard uses a custom `useGitOpsData` hook that:
- Provides 10 sample deployments
- Simulates real-time status updates every 5 seconds
- Includes loading states

## Design System

### Colors
- **Primary:** `#2a75ff` (Vibrant Blue)
- **Background:** `#f9fafb` (Light Gray)
- **Cards:** `#ffffff` (White)
- **Text:** `#1f2937` (Dark Gray)

### Status Colors
- **Healthy:** Light green background with dark green text
- **Progressing:** Light blue background with dark blue text
- **Degraded:** Light red background with dark red text

## License

MIT

## Author

Built with ❤️ for GitOps automation
