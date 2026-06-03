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

  async function load() {
    loading.value = true
    error.value = null
    try {
      const res = await fetchTrades({ page: page.value, size: size.value })
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

  return { trades, stats, total, loading, error, page, size, load, setPage }
})
