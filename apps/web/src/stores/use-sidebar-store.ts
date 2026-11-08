import { create } from "zustand"

interface SidebarState {
  // User sidebar collapse state
  isUserCollapsed: boolean
  toggleUserSidebar: () => void
  setUserCollapsed: (collapsed: boolean) => void

  // Admin sidebar collapse state
  isAdminCollapsed: boolean
  toggleAdminSidebar: () => void
  setAdminCollapsed: (collapsed: boolean) => void

  // Backward compatibility
  isOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (isOpen: boolean) => void

  activeChatId: string | null
  setActiveChatId: (id: string | null) => void
}

export const useSidebarStore = create<SidebarState>((set) => ({
  isUserCollapsed: false,
  toggleUserSidebar: () =>
    set((state) => ({
      isUserCollapsed: !state.isUserCollapsed,
      isOpen: state.isUserCollapsed,
    })),
  setUserCollapsed: (collapsed: boolean) => set({ isUserCollapsed: collapsed, isOpen: !collapsed }),

  isAdminCollapsed: false,
  toggleAdminSidebar: () => set((state) => ({ isAdminCollapsed: !state.isAdminCollapsed })),
  setAdminCollapsed: (collapsed: boolean) => set({ isAdminCollapsed: collapsed }),

  // Legacy compatibility mappings
  isOpen: true,
  toggleSidebar: () =>
    set((state) => ({
      isOpen: !state.isOpen,
      isUserCollapsed: state.isOpen,
    })),
  setSidebarOpen: (isOpen: boolean) => set({ isOpen, isUserCollapsed: !isOpen }),

  activeChatId: null,
  setActiveChatId: (id: string | null) => set({ activeChatId: id }),
}))
