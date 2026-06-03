import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchOverview } from '@/api/overview'
import type { OverviewData } from '@/types'

export const useOverviewStore = defineStore('overview', () => {
  const data = ref<OverviewData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const res = await fetchOverview()
      data.value = res.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载总览数据失败'
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, load }
})
