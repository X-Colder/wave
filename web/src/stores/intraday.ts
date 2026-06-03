import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchIntradayDates, fetchIntradayData } from '@/api/intraday'
import type { IntradayData } from '@/types'

export const useIntradayStore = defineStore('intraday', () => {
  const dates = ref<string[]>([])
  const data = ref<IntradayData | null>(null)
  const selectedDate = ref<string>('')
  const datesLoading = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadDates() {
    datesLoading.value = true
    error.value = null
    try {
      const res = await fetchIntradayDates()
      dates.value = (res.data as any).dates ?? res.data
      if (dates.value.length > 0 && !selectedDate.value) {
        selectedDate.value = dates.value[dates.value.length - 1]
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载日期列表失败'
    } finally {
      datesLoading.value = false
    }
  }

  async function loadData(date: string) {
    selectedDate.value = date
    loading.value = true
    error.value = null
    try {
      const res = await fetchIntradayData(date)
      data.value = res.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载日内数据失败'
    } finally {
      loading.value = false
    }
  }

  return { dates, data, selectedDate, datesLoading, loading, error, loadDates, loadData }
})
