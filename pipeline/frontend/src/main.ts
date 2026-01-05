import { createApp } from 'vue'
import App from './App.vue'

// Vue DevUI
import DevUI from 'vue-devui'
import 'vue-devui/style.css'
import '@devui-design/icons/icomoon/devui-icon.css'

// Vue Data UI
import { VueUiRadar, VueUiDonut, VueUiSparkline, VueUiGauge, VueUiXy } from 'vue-data-ui'
import 'vue-data-ui/style.css'

// App theme overrides (must be loaded after library styles)
import './assets/main.css'

const app = createApp(App)

app.use(DevUI)
app.component('VueUiRadar', VueUiRadar)
app.component('VueUiDonut', VueUiDonut)
app.component('VueUiSparkline', VueUiSparkline)
app.component('VueUiGauge', VueUiGauge)
app.component('VueUiXy', VueUiXy)

app.mount('#app')
