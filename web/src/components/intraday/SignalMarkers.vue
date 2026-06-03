<script setup lang="ts">
import type { Signal } from '@/types'

defineProps<{
  signals: Signal[]
}>()
</script>

<template>
  <el-card class="signal-card">
    <template #header>
      <span class="chart-title">信号记录</span>
    </template>
    <el-table :data="signals" size="small" style="width: 100%" max-height="180">
      <el-table-column label="时间" width="70">
        <template #default="{ row }">{{ row.time.slice(11, 16) }}</template>
      </el-table-column>
      <el-table-column label="类型" width="60">
        <template #default="{ row }">
          <el-tag :type="row.type === 'buy' ? 'success' : 'danger'" size="small">
            {{ row.type === 'buy' ? '买入' : '卖出' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="价格" width="80">
        <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="pattern_id" label="模式ID">
        <template #default="{ row }">
          <span class="text-neutral">{{ row.pattern_id }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.signal-card {
  width: 100%;
}

.chart-title {
  font-size: 14px;
  color: #a0cfff;
  font-weight: 500;
}
</style>
