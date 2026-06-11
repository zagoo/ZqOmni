<script setup lang="ts">
/**
 * Three-pane app shell (Rule 8): left nav ~256px | fluid center | right
 * config panel ~360px. Left/right are fixed; only the center scrolls. No top
 * app bar. Panels collapse independently; on narrow viewports the right
 * panel becomes a slide-over with backdrop.
 *
 * Slots: nav-header, nav-primary, nav-footer, content-toolbar, content,
 * content-footer, panel-header, panel-body.
 */
import { useMediaQuery } from '@vueuse/core'
import { useShellStore } from '@/store/shell'

const shell = useShellStore()
const isNarrow = useMediaQuery('(max-width: 1023px)')
</script>

<template>
  <div class="app-shell">
    <aside class="shell-nav" :class="{ collapsed: shell.navCollapsed }">
      <div class="nav-header"><slot name="nav-header" /></div>
      <nav class="nav-primary"><slot name="nav-primary" /></nav>
      <div class="nav-spacer" />
      <div class="nav-footer"><slot name="nav-footer" /></div>
    </aside>

    <main class="shell-center">
      <div class="content-toolbar"><slot name="content-toolbar" /></div>
      <div class="content-scroll">
        <div class="content-body"><slot name="content" /></div>
        <div v-if="$slots['content-footer']" class="content-footer">
          <slot name="content-footer" />
        </div>
      </div>
    </main>

    <div
      v-if="shell.panelOpen && isNarrow"
      class="panel-backdrop"
      @click="shell.closePanel()"
    />
    <aside
      v-if="shell.panelOpen"
      class="shell-panel"
      :class="{ slideover: isNarrow }"
    >
      <div class="panel-header"><slot name="panel-header" /></div>
      <div class="panel-body"><slot name="panel-body" /></div>
    </aside>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--color-canvas);
}

/* Left sidebar — fixed, internal flex column with dynamic spacer (Rule 8.4) */
.shell-nav {
  flex: none;
  width: var(--shell-nav-width);
  background: var(--color-surface);
  border-right: 1px solid var(--color-hairline);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 180ms ease, padding 180ms ease;
}
.shell-nav.collapsed {
  width: 0;
  border-right: none;
}
.nav-header {
  flex: none;
  padding: var(--space-sm) var(--space-sm) var(--space-xs);
}
.nav-primary {
  flex: none;
  overflow-y: auto;
  padding: var(--space-xs) var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: 1px;
  max-height: 60vh;
}
.nav-spacer {
  flex: 1;
}
.nav-footer {
  flex: none;
  padding: var(--space-xs) var(--space-sm) var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: 1px;
}

/* Center pane — toolbar fixed, body scrolls */
.shell-center {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.content-toolbar {
  flex: none;
  height: var(--shell-toolbar-height);
  display: flex;
  align-items: center;
  padding: 0 var(--space-md);
  border-bottom: 1px solid var(--color-hairline-soft);
  background: var(--color-canvas);
}
.content-scroll {
  flex: 1;
  overflow-y: auto;
}
.content-body {
  padding: var(--space-xxl) var(--space-xxxl) var(--space-section);
  max-width: 1280px;
}
.content-footer {
  padding: var(--space-md) var(--space-xxxl);
  border-top: 1px solid var(--color-hairline-soft);
}

/* Right configuration panel — pushes content (never overlays) on desktop */
.shell-panel {
  flex: none;
  width: var(--shell-panel-width);
  border-left: 1px solid var(--color-hairline);
  background: var(--color-canvas);
  display: flex;
  flex-direction: column;
}
.panel-header {
  flex: none;
  height: var(--shell-toolbar-height); /* exactly the toolbar height (Rule 8.10) */
  display: flex;
  align-items: center;
  padding: 0 var(--space-md);
  border-bottom: 1px solid var(--color-hairline-soft);
}
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-sm) var(--space-lg) var(--space-xl);
}

/* Narrow viewports: slide-over with backdrop (Rule 8.12) */
.panel-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 15, 15, 0.3);
  z-index: 40;
}
.shell-panel.slideover {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  box-shadow: var(--shadow-modal);
  width: min(var(--shell-panel-width), 92vw);
}
</style>
