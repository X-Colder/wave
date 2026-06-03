<script setup lang="ts">
import type { TradesStats } from '@/types'

defineProps<{
  stats: TradesStats | null
}>()

const dirLabels: Record<string, string> = {
  up: '涨势', down: '跌势', pullback: '回调', bounce: '反弹', neutral: '中性'
}
</script>

<template>
  <div v-if="stats">
    <div class="stats-row">
      <el-card class="stat-card">
        <div class="stat-label">加仓</div>
        <div class="stat-value text-profit">{{ stats.buy_count }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-label">减仓</div>
        <div class="stat-value text-loss">{{ stats.sell_count }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-label">盈利减仓</div>
        <div class="stat-value text-profit">{{ stats.profitable_sells }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-label">亏损减仓</div>
        <div class="stat-value text-loss">{{ stats.losing_sells }}</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-label">实现盈亏</div>
        <div class="stat-value" :class="stats.total_realized_pnl >= 0 ? 'text-profit' : 'text-loss'">
          {{ stats.total_realized_pnl >= 0 ? '+' : '' }}{{ stats.total_realized_pnl.toFixed(0) }}
        </div>
      </el-card>
    </div>
    <div v-if="stats.direction_breakdown" class="direction-row">
      <el-tag
        v-for="(data, dir) in stats.direction_breakdown"
        :key="dir"
        :type="(data as any).pnl >= 0 ? 'danger' : 'success'"
        size="small"
        class="dir-tag"
      >
        {{ dirLabels[dir as string] || dir }}: {{ (data as any).count }}次
        {{ (data as any).pnl >= 0 ? '+' : '' }}{{ (data as any).pnl.toFixed(0) }}
      </el-tag>
    </div>
  </div>
</template>

<style scoped>
.stats-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.stat-card :deep(.el-card__body) { padding: 12px 16px; }
.stat-label { font-size: 12px; color: #8899aa; margin-bottom: 6px; }
.stat-value { font-size: 20px; font-weight: 700; }
.text-profit { color: #f56c6c; }
.text-loss { color: #67c23a; }
.direction-row { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
.dir-tag { font-size: 12px; }
</style>
