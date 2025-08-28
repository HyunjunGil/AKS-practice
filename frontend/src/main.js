import Vue from 'vue'
import App from './App.vue'

// OpenTelemetry 초기화 (간단한 버전)
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-http'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base'
import { trace } from '@opentelemetry/api'

// OpenTelemetry 설정
const provider = new WebTracerProvider()
const exporter = new OTLPTraceExporter({
  url: 'http://grafana.20.249.154.255.nip.io:4318/v1/traces',
  headers: {},
})

provider.addSpanProcessor(new BatchSpanProcessor(exporter))
provider.register()

// 기본 tracer 생성
const tracer = trace.getTracer('frontend-app')

// 페이지 로드 시 기본 span 생성
document.addEventListener('DOMContentLoaded', () => {
  const span = tracer.startSpan('page_load')
  span.setAttribute('page.url', window.location.href)
  span.setAttribute('page.title', document.title)
  span.end()
})

Vue.config.productionTip = false

new Vue({
  render: h => h(App),
}).$mount('#app') 