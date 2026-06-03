<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import type { PatternDetail } from '@/types'

const props = defineProps<{
  detail: PatternDetail
  loading: boolean
}>()

const chartRef = ref<{ chart: { resize: () => void } } | null>(null)

function buildHistogram(data: number[], color: string) {
  if (!data || data.length === 0) return null
  const pctData = data.map((v) => +(v * 100).toFixed(3))
  const bins = 20
  const min = Math.min(...pctData)
  const max = Math.max(...pctData)
  const step = (max - min) / bins || 0.01
  const counts = new Array(bins).fill(0)
  pctData.forEach((v) => {
    const idx = Math.min(Math.floor((v - min) / step), bins - 1)
    counts[idx]++
  })
  const labels = counts.map((_, i) => `${(min + i * step).toFixed(2)}%`)

  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 10, bottom: 30, left: 40 },
    xAxis: { type: 'category' as const, data: labels, axisLabel: { color: '#8899aa', fontSize: 9, rotate: 45 }, axisLine: { lineStyle: { color: '#0f3460' } } },
    yAxis: { type: 'value' as const, axisLabel: { color: '#8899aa', fontSize: 9 }, splitLine: { lineStyle: { color: '#0f3460' } } },
    series: [{ type: 'bar' as const, data: counts, itemStyle: { color }, barMaxWidth: 12 }],
  }
}

const mfeOption = computed(() => buildHistogram(props.detail?.mfe_distribution ?? [], '#f56c6c'))
const maeOption = computed(() => buildHistogram(props.detail?.mae_distribution ?? [], '#67c23a'))

function handleResize() { chartRef.value?.chart?.resize() }
onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<template>
  <el-card class="detail-card">
    <template #header>
      <span class="detail-title">详情</span>
    </template>

    <div v-if="loading" class="detail-loading">
      <el-icon class="is-loading" size="24"><Loading /></el-icon>
    </div>

    <div v-else-if="!detail" class="detail-empty">
      <p>暂无详情数据</p>
    </div>

    <div v-else class="detail-content">
      <div class="stat-grid">
        <div class="stat-item">
          <span class="stat-label">样本量</span>
          <span class="stat-value">{{ detail.count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">胜率</span>
          <span class="stat-value" :class="detail.win_rate >= 0.5 ? 'text-profit' : 'text-loss'">
            {{ (detail.win_rate * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="stat-item">
          <span class="stat-label">均收益</span>
          <span class="stat-value" :class="detail.avg_return >= 0 ? 'text-profit' : 'text-loss'">
            {{ (detail.avg_return * 100).toFixed(3) }}%
          </span>
        </div>
      </div>

      <div v-if="mfeOption" class="chart-section">
        <div class="section-title">MFE 分布</div>
        <v-chart ref="chartRef" :option="mfeOption" autoresize style="height: 140px" />
      </div>
      <div v-if="maeOption" class="chart-section">
        <div class="section-title">MAE 分布</div>
        <v-chart :option="maeOption" autoresize style="height: 140px" />
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.detail-card { height: 100%; }
.detail-card :deep(.el-card__body) { height: calc(100% - 48px); overflow-y: auto; }
.detail-title { font-size: 14px; color: #a0cfff; font-weight: 500; }
.detail-loading, .detail-empty { display: flex; align-items: center; justify-content: center; height: 200px; color: #8899aa; }
.detail-content { display: flex; flex-direction: column; gap: 12px; }
.stat-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
.stat-item { background-color: #0f3460; border-radius: 6px; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 11px; color: #8899aa; }
.stat-value { font-size: 16px; font-weight: 600; color: #e0e0e0; }
.text-profit { color: #f56c6c; }
.text-loss { color: #67c23a; }
.chart-section { margin-top: 4px; }
.section-title { font-size: 12px; color: #8899aa; border-bottom: 1px solid #0f3460; padding-bottom: 4px; margin-bottom: 4px; }
</style>
