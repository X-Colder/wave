<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  collapsed: boolean
}>()

const route = useRoute()

const menuItems = [
  { path: '/', name: 'overview', label: '总览仪表盘', icon: 'DataAnalysis' },
  { path: '/patterns', name: 'patterns', label: '模式分析', icon: 'Grid' },
  { path: '/trades', name: 'trades', label: '交易明细', icon: 'List' },
  { path: '/intraday', name: 'intraday', label: '日内查看', icon: 'TrendCharts' },
]
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-logo">
      <span class="logo-icon">W</span>
      <span v-if="!collapsed" class="logo-text">Wave</span>
    </div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in menuItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: route.name === item.name }"
      >
        <el-icon class="nav-icon">
          <component :is="item.icon" />
        </el-icon>
        <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 200px;
  background-color: #16213e;
  border-right: 1px solid #0f3460;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  z-index: 100;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  border-bottom: 1px solid #0f3460;
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #a0cfff;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: #8899aa;
  text-decoration: none;
  border-radius: 0;
  transition: all 0.2s;
  white-space: nowrap;
}

.nav-item:hover {
  background-color: #0f3460;
  color: #e0e0e0;
}

.nav-item.active {
  background-color: #0f3460;
  color: #409eff;
  border-right: 3px solid #409eff;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.nav-label {
  font-size: 14px;
}
</style>
