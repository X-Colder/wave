<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import client from '@/api/client'

const dates = ref<string[]>([])
const selectedDate = ref('')
const frames = ref<any[]>([])
const summary = ref<any>(null)
const currentFrame = ref(0)
const playing = ref(false)
const speed = ref(100) // ms per frame
let timer: ReturnType<typeof setInterval> | null = null

async function loadDates() {
  const res = await client.get('/intraday/dates')
  dates.value = (res.data as any).dates ?? res.data
}

async function loadPlayback(date: string) {
  selectedDate.value = date
  stop()
  currentFrame.value = 0
  const res = await client.get(`/playback/${date}`)
  frames.value = res.data.frames
  summary.value = res.data.summary
}

function play() {
  if (playing.value) return
  playing.value = true
  timer = setInterval(() => {
    if (currentFrame.value < frames.value.length - 1) {
      currentFrame.value++
    } else {
      stop()
    }
  }, speed.value)
}

function stop() {
  playing.value = false
  if (timer) { clearInterval(timer); timer = null }
}

function reset() {
  stop()
  currentFrame.value = 0
}

function setSpeed(ms: number) {
  speed.value = ms
  if (playing.value) { stop(); play() }
}

const current = computed(() => frames.value[currentFrame.value] || null)

const tradeEvents = computed(() => {
  return frames.value
    .filter((f: any, i: number) => f.event && i <= currentFrame.value)
    .map((f: any) => f)
    .reverse()
})

loadDates()

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="playback-view">
    <div class="controls">
      <el-select v-model="selectedDate" placeholder="选择日期" size="small" style="width:140px" @change="loadPlayback">
        <el-option v-for="d in dates" :key="d" :label="d" :value="d" />
      </el-select>
      <el-button size="small" @click="reset">重置</el-button>
      <el-button size="small" type="primary" @click="playing ? stop() : play()">
        {{ playing ? '暂停' : '播放' }}
      </el-button>
      <span class="speed-label">速度:</span>
      <el-button-group size="small">
        <el-button :type="speed === 200 ? 'primary' : 'default'" @click="setSpeed(200)">慢</el-button>
        <el-button :type="speed === 100 ? 'primary' : 'default'" @click="setSpeed(100)">中</el-button>
        <el-button :type="speed === 30 ? 'primary' : 'default'" @click="setSpeed(30)">快</el-button>
      </el-button-group>
      <span class="frame-info">{{ currentFrame }} / {{ frames.length }}</span>
    </div>

    <el-slider v-model="currentFrame" :max="Math.max(frames.length - 1, 1)" :show-tooltip="false" style="margin: 8px 0" />

    <div class="dashboard" v-if="current">
      <div class="status-row">
        <div class="status-item">
          <span class="label">时间</span>
          <span class="value">{{ current.time }}</span>
        </div>
        <div class="status-item">
          <span class="label">价格</span>
          <span class="value">{{ current.price.toFixed(2) }}</span>
        </div>
        <div class="status-item">
          <span class="label">信号</span>
          <span class="value" :style="{color: current.signal > 0 ? '#f56c6c' : current.signal < 0 ? '#67c23a' : '#8899aa'}">
            {{ current.signal > 0 ? '+' : '' }}{{ current.signal.toFixed(3) }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">仓位</span>
          <span class="value">{{ (current.position * 100).toFixed(0) }}%</span>
        </div>
        <div class="status-item">
          <span class="label">趋势</span>
          <span class="value" :style="{color: current.trend_structure === 'higher_low' ? '#f56c6c' : current.trend_structure === 'lower_low' ? '#67c23a' : '#8899aa'}">
            {{ current.trend_structure === 'higher_low' ? '底抬高' : current.trend_structure === 'lower_low' ? '底降低' : '平' }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">资金</span>
          <span class="value">{{ (current.capital / 1000).toFixed(1) }}k</span>
        </div>
      </div>

      <div v-if="current.event" class="event-flash">
        <span :style="{color: current.event.delta > 0 ? '#f56c6c' : '#67c23a'}">
          {{ current.event.delta > 0 ? '加仓' : '减仓' }} {{ (Math.abs(current.event.delta) * 100).toFixed(0) }}%
          &nbsp; PnL: {{ current.event.pnl >= 0 ? '+' : '' }}{{ current.event.pnl.toFixed(0) }}
        </span>
      </div>
    </div>

    <div class="trade-log" v-if="tradeEvents.length">
      <div class="log-title">交易记录 ({{ tradeEvents.length }}笔)</div>
      <div class="log-list">
        <div v-for="(f, idx) in tradeEvents.slice(0, 20)" :key="idx" class="log-item">
          <span class="log-time">{{ f.time }}</span>
          <span :style="{color: f.event.delta > 0 ? '#f56c6c' : '#67c23a'}">
            {{ f.event.delta > 0 ? '加' : '减' }}{{ (Math.abs(f.event.delta) * 100).toFixed(0) }}%
          </span>
          <span class="log-price">P={{ f.price.toFixed(2) }}</span>
          <span :style="{color: f.event.pnl >= 0 ? '#f56c6c' : '#67c23a'}">
            {{ f.event.pnl >= 0 ? '+' : '' }}{{ f.event.pnl.toFixed(0) }}
          </span>
          <span class="log-signal">sig={{ f.signal > 0 ? '+' : '' }}{{ f.signal.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <div v-if="summary" class="summary-bar">
      开={{ summary.open.toFixed(2) }} 高={{ summary.high.toFixed(2) }} 低={{ summary.low.toFixed(2) }} 收={{ summary.close.toFixed(2) }}
      | 交易{{ summary.total_trades }}笔 日盈亏={{ summary.day_pnl >= 0 ? '+' : '' }}{{ summary.day_pnl.toFixed(0) }}
    </div>
  </div>
</template>

<style scoped>
.playback-view { display: flex; flex-direction: column; gap: 12px; height: 100%; }
.controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.speed-label { font-size: 12px; color: #8899aa; margin-left: 8px; }
.frame-info { font-size: 12px; color: #8899aa; margin-left: auto; }
.dashboard { background: #16213e; border-radius: 8px; padding: 16px; }
.status-row { display: flex; gap: 16px; flex-wrap: wrap; }
.status-item { display: flex; flex-direction: column; gap: 4px; }
.status-item .label { font-size: 11px; color: #8899aa; }
.status-item .value { font-size: 18px; font-weight: 600; color: #e0e0e0; }
.event-flash { margin-top: 12px; padding: 8px 12px; background: #0f3460; border-radius: 4px; font-size: 14px; font-weight: 600; animation: flash 0.3s; }
@keyframes flash { 0% { opacity: 0.3; } 100% { opacity: 1; } }
.trade-log { background: #16213e; border-radius: 8px; padding: 12px; flex: 1; overflow-y: auto; }
.log-title { font-size: 12px; color: #8899aa; margin-bottom: 8px; }
.log-list { display: flex; flex-direction: column; gap: 4px; }
.log-item { display: flex; gap: 10px; font-size: 12px; padding: 4px 0; border-bottom: 1px solid #0f3460; }
.log-time { color: #8899aa; width: 60px; }
.log-price { color: #8899aa; }
.log-signal { color: #8899aa; }
.summary-bar { font-size: 12px; color: #8899aa; padding: 8px; background: #0f3460; border-radius: 4px; }
</style>
