/** Global app-shell UI state (Rule 8: panes collapse independently). */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useShellStore = defineStore('shell', () => {
  const navCollapsed = ref(false)
  const panelOpen = ref(false)

  function toggleNav() {
    navCollapsed.value = !navCollapsed.value
  }
  function openPanel() {
    panelOpen.value = true
  }
  function closePanel() {
    panelOpen.value = false
  }
  function togglePanel() {
    panelOpen.value = !panelOpen.value
  }

  return { navCollapsed, panelOpen, toggleNav, openPanel, closePanel, togglePanel }
})
