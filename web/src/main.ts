import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ECharts from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart,
  BarChart,
  HeatmapChart,
  ScatterChart,
} from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkPointComponent,
  MarkLineComponent,
  ToolboxComponent,
} from 'echarts/components'

import App from './App.vue'
import router from './router'
import '@/styles/global.css'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  HeatmapChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkPointComponent,
  MarkLineComponent,
  ToolboxComponent,
])

const app = createApp(App)
const pinia = createPinia()

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.component('v-chart', ECharts)
app.use(pinia)
app.use(router)
app.use(ElementPlus, { size: 'default' })

app.mount('#app')
