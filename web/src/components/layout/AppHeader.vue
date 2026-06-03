<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { Fold } from '@element-plus/icons-vue'

const emit = defineEmits<{
  toggleSidebar: []
}>()

const route = useRoute()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    overview: '总览仪表盘',
    patterns: '模式分析',
    trades: '交易明细',
    intraday: '日内查看器',
  }
  return titles[route.name as string] ?? 'Wave'
})
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <el-button
        class="toggle-btn"
        :icon="Fold"
        circle
        @click="emit('toggleSidebar')"
      />
      <h1 class="page-title">{{ pageTitle }}</h1>
    </div>
    <div class="header-right">
      <span class="system-name">量化交易模式匹配分析系统</span>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 56px;
  background-color: #16213e;
  border-bottom: 1px solid #0f3460;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle-btn {
  background-color: transparent !important;
  border-color: #0f3460 !important;
  color: #8899aa !important;
}

.toggle-btn:hover {
  border-color: #409eff !important;
  color: #409eff !important;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #e0e0e0;
}

.system-name {
  font-size: 12px;
  color: #8899aa;
}
</style>
