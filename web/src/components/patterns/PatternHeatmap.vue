<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { PatternCell } from '@/types'

const props = defineProps<{
  cells: PatternCell[]
  accelerationLevel: number
}>()

const emit = defineEmits<{
  cellClick: [f: number, m: number, a: number, fd: number, md: number, ad: number]
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

const filteredCells = computed(() =>
  props.cells.filter((c) => c.a === props.accelerationLevel)
)

const option = computed(() => {
  const momentumLabels = ['大跌', '平盘', '大涨']
  const forceLabels = ['卖压', '均衡', '买压']
  const maxCount = Math.max(...filteredCells.value.map((c) => c.count), 1)

  const data = filteredCells.value.map((c) => ({
    value: [c.m, c.f, +(c.mfe_mae_ratio).toFixed(2)],
    itemStyle: {
      opacity: Math.max(0.2, c.count / maxCount),
    },
    extra: { ...c },
  }))

  return {
    backgroundColor: 'transparent',
    grid: { top: 30, right: 20, bottom: 40, left: 60 },
    tooltip: {
      backgroundColor: '#0f3460',
      borderColor: '#f56c6c',
      textStyle: { color: '#e0e0e0', fontSize: 12 },
      formatter: (p: { data: { value: [number, number, number]; extra: PatternCell } }) => {
        const { extra: c } = p.data
        return [
          `力量[${c.f}] 动量[${c.m}] 加速[${c.a}]`,
          `delta: 力[${c.fd}] 动[${c.md}] 加[${c.ad}]`,
          `MFE/MAE: ${c.mfe_mae_ratio.toFixed(2)}`,
          `胜率: ${(c.win_rate * 100).toFixed(1)}%`,
          `期望值: ${(c.expected_value * 100).toFixed(3)}%`,
          `MFE中位: ${(c.median_mfe * 100).toFixed(2)}%`,
          `MAE中位: ${(c.median_mae * 100).toFixed(2)}%`,
          `样本: ${c.count}`,
        ].join('<br/>')
      },
    },
    xAxis: {
      type: 'category',
      data: momentumLabels,
      name: '动量',
      nameTextStyle: { color: '#8899aa', fontSize: 11 },
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: forceLabels,
      name: '力量',
      nameTextStyle: { color: '#8899aa', fontSize: 11 },
      axisLine: { lineStyle: { color: '#0f3460' } },
      axisLabel: { color: '#8899aa', fontSize: 10 },
    },
    visualMap: {
      show: false,
      min: 0,
      max: 4,
      inRange: {
        color: ['#3d1a1a', '#5a2d2d', '#666633', '#2d5a2d', '#1a5a1a'],
      },
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: {
          show: true,
          fontSize: 10,
          color: '#fff',
          formatter: (p: { data: { value: [number, number, number] } }) => `${p.data.value[2]}`,
        },
        emphasis: {
          itemStyle: { shadowBlur: 8, shadowColor: 'rgba(103,194,58,0.5)' },
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

function onChartClick(params: unknown) {
  const p = params as { data: { extra: PatternCell } }
  if (p?.data?.extra) {
    const c = p.data.extra
    emit('cellClick', c.f, c.m, c.a, c.fd, c.md, c.ad)
  }
}
</script>

<template>
  <div class="heatmap-wrapper">
    <div class="heatmap-label">加速档 {{ accelerationLevel }}</div>
    <v-chart
      ref="chartRef"
      :option="option"
      autoresize
      style="height: 280px; width: 100%"
      @click="onChartClick"
    />
  </div>
</template>

<style scoped>
.heatmap-wrapper {
  flex: 1;
  min-width: 0;
  background-color: #16213e;
  border: 1px solid #0f3460;
  border-radius: 4px;
  padding: 8px;
}

.heatmap-label {
  font-size: 12px;
  color: #a0cfff;
  text-align: center;
  margin-bottom: 4px;
}
</style>
