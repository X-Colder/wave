<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useIntradayStore } from '@/stores/intraday'
import TickChart from '@/components/intraday/TickChart.vue'
import FeatureOverlay from '@/components/intraday/FeatureOverlay.vue'
import SignalMarkers from '@/components/intraday/SignalMarkers.vue'

const store = useIntradayStore()

onMounted(async () => {
  await store.loadDates()
  if (store.selectedDate) {
    await store.loadData(store.selectedDate)
  }
})

watch(
  () => store.selectedDate,
  (date) => {
    if (date) store.loadData(date)
  },
)

function onDateChange(date: string) {
  store.selectedDate = date
}
</script>

<template>
  <div class="intraday-view">
    <el-card class="date-selector-card">
      <div class="date-row">
        <span class="date-label">选择日期</span>
        <el-select
          v-model="store.selectedDate"
          placeholder="选择交易日"
          size="small"
          style="width: 160px"
          :loading="store.datesLoading"
          @change="onDateChange"
        >
          <el-option
            v-for="d in store.dates"
            :key="d"
            :label="d"
            :value="d"
          />
        </el-select>
        <span class="date-count">共 {{ store.dates.length }} 个交易日</span>
      </div>
    </el-card>

    <div v-if="store.loading" class="loading-overlay">
      <el-icon class="is-loading" size="32"><Loading /></el-icon>
      <span>加载日内数据...</span>
    </div>

    <template v-else-if="store.data">
      <TickChart :ticks="store.data.ticks" />
      <FeatureOverlay :features="store.data.features" />
      <SignalMarkers :signals="store.data.signals" />
    </template>

    <div v-else-if="!store.datesLoading" class="empty-state">
      <el-icon size="40"><Calendar /></el-icon>
      <p>请选择一个交易日查看日内数据</p>
    </div>

    <div v-if="store.error" class="error-state">
      <el-icon size="24"><Warning /></el-icon>
      <p>{{ store.error }}</p>
    </div>
  </div>
</template>

<style scoped>
.intraday-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.date-selector-card :deep(.el-card__body) {
  padding: 12px 20px;
}

.date-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-label {
  font-size: 13px;
  color: #8899aa;
}

.date-count {
  font-size: 12px;
  color: #8899aa;
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 300px;
  color: #8899aa;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 300px;
  color: #8899aa;
}

.error-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  font-size: 13px;
}
</style>
