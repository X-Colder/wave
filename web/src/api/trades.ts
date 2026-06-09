import client from './client'
import type { TradesData } from '@/types'

export function fetchTrades(params: Record<string, string | number>) {
  return client.get<TradesData>('/trades', { params })
}
