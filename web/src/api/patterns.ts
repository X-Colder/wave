import client from './client'
import type { PatternsData, PatternDetail } from '@/types'

export function fetchPatterns() {
  return client.get<PatternsData>('/patterns')
}

export function fetchPatternDetail(f: number, m: number, a: number, fd: number, md: number, ad: number) {
  return client.get<PatternDetail>(`/patterns/${f}/${m}/${a}/${fd}/${md}/${ad}`)
}
