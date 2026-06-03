<script setup lang="ts">
import { ref } from 'vue'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

const collapsed = ref(false)
</script>

<template>
  <div class="app-layout">
    <AppSidebar :collapsed="collapsed" />
    <div class="app-main" :class="{ 'sidebar-collapsed': collapsed }">
      <AppHeader @toggle-sidebar="collapsed = !collapsed" />
      <div class="page-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background-color: #1a1a2e;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 200px;
  transition: margin-left 0.3s ease;
  overflow: hidden;
}

.app-main.sidebar-collapsed {
  margin-left: 64px;
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>
