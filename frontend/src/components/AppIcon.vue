<script setup lang="ts">
/** Single outline icon family (Rule 8.14 / ARCHITECTURE §2.4): Lucide icons
 * via 'lucide-vue-next'. 16px in nav/toolbars, 20px in content; stroke-based,
 * never mixed families. Keys map the app's semantic icon names to Lucide
 * components so call sites stay stable. */
import { computed, type Component } from 'vue'
import {
  Activity, Bell, Box, BrainCircuit, Building, Check, ChevronDown, ChevronLeft,
  ChevronRight, CircleCheck, Clipboard, Cog, Cpu, Database, Ellipsis, Factory,
  Film, Flag, Folder, Gauge, Info, Key, Layers, Link, List, Lock, LogOut, Map,
  Maximize, Orbit, PanelLeft, Plus, RefreshCw, Search, Server, Settings, Shapes,
  Share2, Shield, SlidersHorizontal, Tag, Trash2, TriangleAlert, Upload, User,
  Users, Workflow, X,
} from 'lucide-vue-next'

const props = withDefaults(defineProps<{ name: string; size?: 16 | 20 | 24 }>(), { size: 16 })

const ICONS: Record<string, Component> = {
  'panel-left': PanelLeft,
  search: Search,
  settings: Settings,
  bell: Bell,
  user: User,
  'chevron-down': ChevronDown,
  'chevron-right': ChevronRight,
  'chevron-left': ChevronLeft,
  plus: Plus,
  x: X,
  logout: LogOut,
  building: Building,
  server: Server,
  folder: Folder,
  users: Users,
  key: Key,
  shield: Shield,
  list: List,
  clipboard: Clipboard,
  flag: Flag,
  upload: Upload,
  film: Film,
  tag: Tag,
  database: Database,
  map: Map,
  cpu: Cpu,
  activity: Activity,
  box: Box,
  'check-circle': CircleCheck,
  check: Check,
  alert: TriangleAlert,
  workflow: Workflow,
  gauge: Gauge,
  layers: Layers,
  factory: Factory,
  orbit: Orbit,
  'brain-circuit': BrainCircuit,
  cog: Cog,
  shapes: Shapes,
  refresh: RefreshCw,
  trash: Trash2,
  link: Link,
  info: Info,
  lock: Lock,
  share: Share2,
  fullscreen: Maximize,
  dots: Ellipsis,
  sliders: SlidersHorizontal,
}

const icon = computed<Component>(() => ICONS[props.name] ?? Info)
</script>

<template>
  <component :is="icon" :size="props.size" :stroke-width="1.6" aria-hidden="true" />
</template>
