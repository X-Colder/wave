import client from './client'
import type { IntradayData } from '@/types'

export function fetchIntradayDates() {
  return client.get<string[]>('/intraday/dates')
}

export function fetchIntradayData(date: string) {
  return client.get<IntradayData>(`/intraday/${date}`)
}
