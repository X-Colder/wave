import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchTrades } from '@/api/trades'
import type { Trade, TradesStats } from '@/types'

export const useTradesStore = defineStore('trades', () => {
  const trades = ref<Trade[]>([])
  const stats = ref<TradesStats | null>(null)
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const page = ref(1)
  const size = ref(50)
  const sortBy = ref('')
  const sortOrder = ref('desc')

  async function load() {
    loading.value = true
    error.value = null
    try {
      const params: Record<string, string | number> = { page: page.value, size: size.value }
      if (sortBy.value) {
        params.sort_by = sortBy.value
        params.sort_order = sortOrder.value
      }
      const res = await fetchTrades(params)
      trades.value = res.data.trades
      stats.value = res.data.stats
      total.value = res.data.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载交易数据失败'
    } finally {
      loading.value = false
    }
  }

  function setPage(p: number) {
    page.value = p
    load()
  }

  function setSort(field: string, order: string) {
    sortBy.value = field
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
    page.value = 1
    load()
  }

  return { trades, stats, total, loading, error, page, size, sortBy, sortOrder, load, setPage, setSort }
})
