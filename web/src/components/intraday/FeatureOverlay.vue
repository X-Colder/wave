<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { FeaturePoint } from '@/types'

const props = defineProps<{
  features: FeaturePoint[]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const filteredFeatures = computed(() => {
  return props.features.filter((f) => {
    const time = f.time.slice(11, 16)
    return time < '11:30' || time >= '13:00'
  })
})

const option = computed(() => {
  const times = filteredFeatures.value.map((f) => f.time.slice(11, 16))
  const f1 = filteredFeatures.value.map((f) => f.short_slope)
  const f2 = filteredFeatures.value.map((f) => f.long_slope)

  return {
    backgroundColor: 'transparent',
    grid: { top: 30, right: 100, bottom: 40, left: 60 },
    legend: {
      right: 0,
      top: 20,
      textStyle: { color: '#8899aa', fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f3460',
      borderColor: '#409eff',
      textStyle: { color: '#e0e0e0', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
      splitLine: { lineStyle: { color: '#0f3460', type: 'dashed' } },
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: '短期斜率',
        type: 'line',
        data: f1,
        step: 'end',
        symbol: 'none',
        lineStyle: { color: '#409eff', width: 1.5 },
      },
      {
        name: '长期斜率',
        type: 'line',
        data: f2,
        step: 'end',
        symbol: 'none',
        lineStyle: { color: '#e6a23c', width: 1.5 },
      },
    ],
  }
})

function handleResize() {
  chartRef.value?.chart?.resize()
}

onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<template>
  <el-card class="feature-card">
    <template #header>
      <span class="chart-title">特征值（5分钟）</span>
    </template>
    <v-chart ref="chartRef" :option="option" autoresize style="height: 180px" />
  </el-card>
</template>

<style scoped>
.feature-card {
  width: 100%;
}

.chart-title {
  font-size: 14px;
  color: #a0cfff;
  font-weight: 500;
}
</style>
