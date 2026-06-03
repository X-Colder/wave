import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchPatterns, fetchPatternDetail } from '@/api/patterns'
import type { PatternCell, PatternDetail } from '@/types'

export const usePatternsStore = defineStore('patterns', () => {
  const cells = ref<PatternCell[]>([])
  const selectedDetail = ref<PatternDetail | null>(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const res = await fetchPatterns()
      cells.value = res.data.cells
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载模式数据失败'
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(f: number, m: number, a: number, fd: number, md: number, ad: number) {
    detailLoading.value = true
    try {
      const res = await fetchPatternDetail(f, m, a, fd, md, ad)
      selectedDetail.value = res.data
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载模式详情失败'
    } finally {
      detailLoading.value = false
    }
  }

  function clearDetail() {
    selectedDetail.value = null
  }

  return { cells, selectedDetail, loading, detailLoading, error, load, loadDetail, clearDetail }
})
