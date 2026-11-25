/// <reference types="vite/client" />
interface Window { websentinel?: { version: string; platform: string; openTarget: (projectId: number, url: string) => Promise<void> } }
