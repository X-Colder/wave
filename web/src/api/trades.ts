import client from './client'
import type { TradesData, PageQuery } from '@/types'

export function fetchTrades(params: PageQuery) {
  return client.get<TradesData>('/trades', { params })
}
