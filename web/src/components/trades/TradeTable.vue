<script setup lang="ts">
import type { Trade } from '@/types'

defineProps<{
  trades: Trade[]
  loading: boolean
  total: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  pageChange: [page: number]
  sortChange: [sort: { prop: string; order: string }]
}>()

function formatTime(t: string) {
  return t.replace('T', ' ').slice(5, 16)
}

const directionMap: Record<string, { label: string; color: string }> = {
  up: { label: '涨势', color: '#f56c6c' },
  down: { label: '跌势', color: '#67c23a' },
  pullback: { label: '回调', color: '#e6a23c' },
  bounce: { label: '反弹', color: '#909399' },
  neutral: { label: '中性', color: '#8899aa' },
}

function onSortChange(s: { prop: string; order: string }) {
  emit('sortChange', s)
}

function onPageChange(p: number) {
  emit('pageChange', p)
}
</script>

<template>
  <div class="trade-table-wrapper">
    <el-table
      :data="trades"
      v-loading="loading"
      stripe
      size="small"
      style="width: 100%"
      @sort-change="onSortChange"
    >
      <el-table-column prop="time" label="时间" sortable="custom" min-width="100">
        <template #default="{ row }">{{ formatTime(row.time) }}</template>
      </el-table-column>
      <el-table-column label="方向" width="65">
        <template #default="{ row }">
          <span :style="{ color: directionMap[row.direction]?.color || '#8899aa', fontWeight: 600 }">
            {{ directionMap[row.direction]?.label || row.direction }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="55">
        <template #default="{ row }">
          <span :style="{ color: row.position_delta > 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
            {{ row.position_delta > 0 ? '加' : '减' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="仓位" width="100">
        <template #default="{ row }">
          <span class="text-muted">{{ row.position_before.toFixed(0) }}%</span>
          <span style="color:#8899aa"> → </span>
          <span style="font-weight:600">{{ row.position_after.toFixed(0) }}%</span>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="65">
        <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="信号" width="60">
        <template #default="{ row }">
          <span :style="{ color: row.signal_score > 0 ? '#f56c6c' : row.signal_score < 0 ? '#67c23a' : '#8899aa', fontWeight: 600 }">
            {{ row.signal_score > 0 ? '+' : '' }}{{ row.signal_score.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="pnl" label="盈亏" sortable="custom" width="90">
        <template #default="{ row }">
          <span v-if="row.position_delta < 0" :class="row.pnl >= 0 ? 'text-profit' : 'text-loss'" style="font-weight:600">
            {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl.toFixed(0) }}
          </span>
          <span v-else class="text-muted" style="font-size:11px">
            佣{{ Math.abs(row.pnl).toFixed(0) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="资金" width="75">
        <template #default="{ row }">
          <span class="text-muted">{{ (row.capital_after / 1000).toFixed(1) }}k</span>
        </template>
      </el-table-column>
      <el-table-column label="后高" width="65">
        <template #default="{ row }">
          <span v-if="row.high_after" class="text-profit">{{ row.high_after.toFixed(2) }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="high_after_pct" label="遗留%" width="65" sortable="custom">
        <template #default="{ row }">
          <span v-if="row.high_after_pct != null && row.high_after_pct > 0" class="text-profit">
            +{{ row.high_after_pct.toFixed(1) }}%
          </span>
          <span v-else-if="row.high_after_pct != null" class="text-muted">
            {{ row.high_after_pct.toFixed(1) }}%
          </span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="距高tick" width="70">
        <template #default="{ row }">
          <span v-if="row.ticks_to_high != null" class="text-muted">{{ row.ticks_to_high }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        background
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<style scoped>
.trade-table-wrapper { display: flex; flex-direction: column; gap: 16px; }
.pagination-bar { display: flex; justify-content: flex-end; }
.text-muted { color: #8899aa; }
.text-profit { color: #f56c6c; }
.text-loss { color: #67c23a; }
</style>
