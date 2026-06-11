<script setup lang="ts">
/** Single outline icon family (Rule 8.14): 16px in nav/toolbars, 20px in
 * content. Stroke-based paths; never mix families. */
const props = withDefaults(defineProps<{ name: string; size?: 16 | 20 | 24 }>(), { size: 16 })

const PATHS: Record<string, string> = {
  'panel-left': 'M3 4h18v16H3zM9 4v16',
  search: 'M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14zM21 21l-4.8-4.8',
  settings:
    'M12 9a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.5-2.4 1a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.6a7 7 0 0 0-2 1.2l-2.4-1-2 3.5 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.5 2.4-1a7 7 0 0 0 2 1.2L10 21h4l.5-2.6a7 7 0 0 0 2-1.2l2.4 1 2-3.5-2-1.5c.1-.4.1-.8.1-1.2z',
  bell: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0',
  user: 'M12 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8zM4 21c0-4 3.6-6 8-6s8 2 8 6',
  'chevron-down': 'M6 9l6 6 6-6',
  'chevron-right': 'M9 6l6 6-6 6',
  'chevron-left': 'M15 6l-6 6 6 6',
  plus: 'M12 5v14M5 12h14',
  x: 'M6 6l12 12M18 6L6 18',
  logout: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  building: 'M4 21V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v16M4 21h16M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1',
  server: 'M3 5h18v6H3zM3 13h18v6H3zM7 8h.01M7 16h.01',
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
  users:
    'M9 5a4 4 0 1 1 0 8 4 4 0 0 1 0-8zM2 21c0-3.5 3-5.5 7-5.5s7 2 7 5.5M17 6a3.5 3.5 0 0 1 0 7M22 21c0-2.7-1.6-4.4-4-5.1',
  key: 'M15 3a6 6 0 1 1-5.6 8.1L3 17.5V21h3.5l1-1.5h2l1-2 1.5-1A6 6 0 0 1 15 3zM16.5 7.5h.01',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  clipboard:
    'M9 3h6a1 1 0 0 1 1 1v2H8V4a1 1 0 0 1 1-1zM16 5h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h3',
  flag: 'M4 21V4s1.5-1 4-1 4 2 7 2 5-1 5-1v11s-2 1-5 1-4-2-7-2-4 1-4 1',
  upload: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
  film: 'M4 4h16v16H4zM4 9h16M4 15h16M9 4v16M15 4v16',
  tag: 'M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z M8 8h.01',
  database: 'M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  map: 'M9 4L3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14',
  cpu: 'M8 8h8v8H8zM5 5h14v14H5zM12 2v3M12 19v3M2 12h3M19 12h3',
  activity: 'M3 12h4l3 8 4-16 3 8h4',
  box: 'M12 3l9 5v8l-9 5-9-5V8zM3 8l9 5 9-5M12 13v8',
  'check-circle': 'M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zM8.5 12l2.5 2.5 5-5',
  alert: 'M12 3l10 17H2zM12 10v4M12 17.5h.01',
  workflow: 'M4 4h6v6H4zM14 14h6v6h-6zM10 7h7v7',
  gauge: 'M12 5a9 9 0 0 1 9 9h-4M12 5a9 9 0 0 0-9 9h4M12 5v0M12 14l4-4',
  layers: 'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 17l9 5 9-5',
  refresh: 'M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6',
  trash: 'M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6',
  link: 'M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1',
  info: 'M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zM12 8h.01M12 11v5',
  lock: 'M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1zM8 11V7a4 4 0 1 1 8 0v4',
  share: 'M18 5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM6 9.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM18 14a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM8.3 10.8l7.4-3.6M8.3 13.2l7.4 3.6',
  fullscreen: 'M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5',
  dots: 'M5 12h.01M12 12h.01M19 12h.01',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
}
</script>

<template>
  <svg
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[props.name] ?? PATHS.info" />
  </svg>
</template>
