<script setup lang="ts">
/** Empty page shell for out-of-scope modules M04-M20 (scope lock):
 * navigation entry + placeholder only; zero business logic. */
import { useRoute } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'

const route = useRoute()
</script>

<template>
  <div class="stub-wrap">
    <div class="card stub-card">
      <span class="stub-icon"><AppIcon name="lock" :size="20" /></span>
      <h1 class="text-h4">{{ route.meta.stubName }} ({{ route.meta.stubId }})</h1>
      <p class="text-sm stub-text">
        This capability is part of the platform module map but is not implemented in this
        release. Its API surface answers <code>501 Not Implemented</code>.
      </p>
    </div>
  </div>
</template>

<style scoped>
.stub-wrap {
  display: flex;
  justify-content: center;
  padding-top: var(--space-section-sm);
}
.stub-card {
  width: min(520px, 100%);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-sm);
}
.stub-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--rounded-md);
  background: var(--color-tint-gray);
  color: var(--color-charcoal);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.stub-text {
  color: var(--color-steel);
}
code {
  background: var(--color-surface);
  border-radius: var(--rounded-xs);
  padding: 1px 6px;
  font-size: 13px;
}
</style>
