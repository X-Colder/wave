<script setup lang="ts">
import { onMounted } from 'vue'
import { useTradesStore } from '@/stores/trades'
import TradeStats from '@/components/trades/TradeStats.vue'
import TradeTable from '@/components/trades/TradeTable.vue'

const store = useTradesStore()

onMounted(() => {
  store.load()
})

function onPageChange(page: number) {
  store.setPage(page)
}

function onSortChange(_sort: { prop: string; order: string }) {
  store.load()
}
</script>

<template>
  <div class="trades-view">
    <TradeStats :stats="store.stats" />

    <el-card>
      <TradeTable
        :trades="store.trades"
        :loading="store.loading"
        :total="store.total"
        :page="store.page"
        :page-size="store.size"
        @page-change="onPageChange"
        @sort-change="onSortChange"
      />
    </el-card>
  </div>
</template>

<style scoped>
.trades-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>
