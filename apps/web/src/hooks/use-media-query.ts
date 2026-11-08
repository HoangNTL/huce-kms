"use client"

import { useSyncExternalStore } from "react"

/**
 * useMediaQuery - Track media query match state using React's useSyncExternalStore
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = (callback: () => void) => {
    if (typeof window === "undefined") return () => {}
    const media = window.matchMedia(query)
    media.addEventListener("change", callback)
    return () => media.removeEventListener("change", callback)
  }

  const getSnapshot = () => {
    if (typeof window === "undefined") return false
    return window.matchMedia(query).matches
  }

  const getServerSnapshot = () => false

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
