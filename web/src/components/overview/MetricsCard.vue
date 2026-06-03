<script setup lang="ts">
defineProps<{
  title: string
  value: string
  subtext?: string
  valueClass?: string
}>()
</script>

<template>
  <el-card class="metrics-card">
    <div class="card-title">{{ title }}</div>
    <div class="card-value" :class="valueClass">{{ value }}</div>
    <div v-if="subtext" class="card-subtext">{{ subtext }}</div>
  </el-card>
</template>

<style scoped>
.metrics-card {
  height: 110px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.metrics-card :deep(.el-card__body) {
  padding: 16px 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.card-title {
  font-size: 12px;
  color: #8899aa;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  font-size: 26px;
  font-weight: 700;
  color: #e0e0e0;
  line-height: 1;
  margin-bottom: 4px;
}

.card-subtext {
  font-size: 11px;
  color: #8899aa;
}
</style>
