<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { EquityPoint } from '@/types'

const props = defineProps<{
  data: EquityPoint[]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const option = computed(() => {
  const dates = props.data.map((d) => d.date)
  const equities = props.data.map((d) => d.equity)

  return {
    backgroundColor: 'transparent',
    grid: { top: 40, right: 20, bottom: 60, left: 70 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f3460',
      borderColor: '#409eff',
      textStyle: { color: '#e0e0e0' },
      formatter: (params: Array<{ axisValue: string; value: number }>) => {
        const p = params[0]
        return `${p.axisValue}<br/>净值: ${p.value.toLocaleString()}`
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 11 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 11, formatter: (v: number) => v.toLocaleString() },
      splitLine: { lineStyle: { color: '#0f3460', type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        bottom: 0,
        height: 24,
        borderColor: '#0f3460',
        backgroundColor: '#16213e',
        fillerColor: 'rgba(64,158,255,0.1)',
        handleStyle: { color: '#409eff' },
        textStyle: { color: '#8899aa' },
      },
    ],
    series: [
      {
        type: 'line',
        data: equities,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#409eff', width: 2 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64,158,255,0.3)' },
              { offset: 1, color: 'rgba(64,158,255,0)' },
            ],
          },
        },
      },
    ],
  }
})

function handleResize() {
  chartRef.value?.chart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <el-card class="chart-card">
    <template #header>
      <span class="chart-title">权益曲线</span>
    </template>
    <v-chart ref="chartRef" :option="option" autoresize style="height: 300px" />
  </el-card>
</template>

<style scoped>
.chart-card {
  width: 100%;
}

.chart-title {
  font-size: 14px;
  color: #a0cfff;
  font-weight: 500;
}
</style>
