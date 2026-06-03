<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { MonthlyReturn } from '@/types'

const props = defineProps<{
  data: MonthlyReturn[]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const option = computed(() => {
  const monthSet = new Set<string>()
  const yearSet = new Set<string>()

  props.data.forEach((d) => {
    const [year, month] = d.month.split('-')
    yearSet.add(year)
    monthSet.add(month)
  })

  const years = Array.from(yearSet).sort()
  const months = ['01','02','03','04','05','06','07','08','09','10','11','12']
  const monthLabels = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

  const returnMap = new Map<string, number>()
  props.data.forEach((d) => {
    returnMap.set(d.month, +(d.return * 100).toFixed(2))
  })

  const heatmapData: [number, number, number][] = []
  years.forEach((year, yi) => {
    months.forEach((month, mi) => {
      const key = `${year}-${month}`
      const val = returnMap.get(key) ?? null
      if (val !== null) {
        heatmapData.push([mi, yi, val])
      }
    })
  })

  const allValues = heatmapData.map((d) => d[2])
  const maxAbs = Math.max(...allValues.map(Math.abs), 1)

  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 80, bottom: 40, left: 50 },
    tooltip: {
      backgroundColor: '#0f3460',
      borderColor: '#409eff',
      textStyle: { color: '#e0e0e0' },
      formatter: (p: { data: [number, number, number] }) => {
        const [mi, yi, val] = p.data
        return `${years[yi]}-${months[mi]}<br/>月收益: ${val}%`
      },
    },
    xAxis: {
      type: 'category',
      data: monthLabels,
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'transparent'] } },
    },
    yAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'transparent'] } },
    },
    visualMap: {
      min: -maxAbs,
      max: maxAbs,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#67c23a', '#ffffff', '#f56c6c'],
      },
      textStyle: { color: '#8899aa', fontSize: 10 },
    },
    series: [
      {
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true,
          fontSize: 9,
          color: '#333',
          formatter: (p: { data: [number, number, number] }) => `${p.data[2]}%`,
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' },
        },
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
      <span class="chart-title">月度收益热力图</span>
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
