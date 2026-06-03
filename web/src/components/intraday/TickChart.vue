<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { TickPoint } from '@/types'

const props = defineProps<{
  ticks: TickPoint[]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const tradingTimes = computed(() => {
  return props.ticks
    .filter((t) => {
      const time = t.time.slice(11, 16)
      return time < '11:30' || time >= '13:00'
    })
    .map((t) => t.time.slice(11, 16))
})

const filteredPrices = computed(() => {
  return props.ticks
    .filter((t) => {
      const time = t.time.slice(11, 16)
      return time < '11:30' || time >= '13:00'
    })
    .map((t) => t.price)
})

const filteredVolumes = computed(() => {
  return props.ticks
    .filter((t) => {
      const time = t.time.slice(11, 16)
      return time < '11:30' || time >= '13:00'
    })
    .map((t) => t.volume)
})

const option = computed(() => {
  const times = tradingTimes.value
  const prices = filteredPrices.value
  const volumes = filteredVolumes.value
  const priceMin = prices.length ? Math.min(...prices) * 0.999 : 0
  const priceMax = prices.length ? Math.max(...prices) * 1.001 : 100

  return {
    backgroundColor: 'transparent',
    grid: [
      { top: 30, right: 20, bottom: '35%', left: 70 },
      { top: '68%', right: 20, bottom: 30, left: 70 },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: '#0f3460',
      borderColor: '#409eff',
      textStyle: { color: '#e0e0e0', fontSize: 11 },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    xAxis: [
      {
        type: 'category',
        data: times,
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#0f3460' } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: 'category',
        data: times,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#0f3460' } },
        axisLabel: { color: '#8899aa', fontSize: 10 },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: priceMin,
        max: priceMax,
        axisLine: { lineStyle: { color: '#0f3460' } },
        axisLabel: { color: '#8899aa', fontSize: 10 },
        splitLine: { lineStyle: { color: '#0f3460', type: 'dashed' } },
      },
      {
        type: 'value',
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#0f3460' } },
        axisLabel: { color: '#8899aa', fontSize: 10 },
        splitLine: { lineStyle: { color: '#0f3460', type: 'dashed' } },
      },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        bottom: 4,
        height: 18,
        borderColor: '#0f3460',
        backgroundColor: '#16213e',
        fillerColor: 'rgba(64,158,255,0.1)',
        handleStyle: { color: '#409eff' },
        textStyle: { color: '#8899aa', fontSize: 9 },
      },
    ],
    series: [
      {
        type: 'line',
        data: prices,
        xAxisIndex: 0,
        yAxisIndex: 0,
        symbol: 'none',
        lineStyle: { color: '#409eff', width: 1.5 },
        smooth: false,
        name: '价格',
      },
      {
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: 'rgba(64,158,255,0.5)' },
        name: '成交量',
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
  <el-card class="tick-card">
    <template #header>
      <span class="chart-title">Tick 价格 & 成交量</span>
    </template>
    <v-chart ref="chartRef" :option="option" autoresize style="height: 420px" />
  </el-card>
</template>

<style scoped>
.tick-card {
  width: 100%;
}

.chart-title {
  font-size: 14px;
  color: #a0cfff;
  font-weight: 500;
}
</style>
