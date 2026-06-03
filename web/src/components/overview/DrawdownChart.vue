<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { EquityPoint } from '@/types'

const props = defineProps<{
  data: EquityPoint[]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const option = computed(() => {
  const dates = props.data.map((d) => d.date)
  const drawdowns = props.data.map((d) => +(d.drawdown * 100).toFixed(2))

  return {
    backgroundColor: 'transparent',
    grid: { top: 40, right: 20, bottom: 40, left: 70 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#0f3460',
      borderColor: '#67c23a',
      textStyle: { color: '#e0e0e0' },
      formatter: (params: Array<{ axisValue: string; value: number }>) => {
        const p = params[0]
        return `${p.axisValue}<br/>回撤: ${p.value}%`
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
      max: 0,
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 11, formatter: (v: number) => `${v}%` },
      splitLine: { lineStyle: { color: '#0f3460', type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        data: drawdowns,
        itemStyle: { color: '#67c23a' },
        barMaxWidth: 4,
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
  <el-card class="chart-card">
    <template #header>
      <span class="chart-title">回撤分析</span>
    </template>
    <v-chart ref="chartRef" :option="option" autoresize style="height: 220px" />
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
