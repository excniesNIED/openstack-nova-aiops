import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'

// Vue DevUI
import DevUI from 'vue-devui'
import 'vue-devui/style.css'
import '@devui-design/icons/icomoon/devui-icon.css'

// Vue Data UI
import { VueUiRadar, VueUiDonut, VueUiSparkline, VueUiGauge, VueUiXy } from 'vue-data-ui'
import 'vue-data-ui/style.css'

const app = createApp(App)

app.use(DevUI)
app.component('VueUiRadar', VueUiRadar)
app.component('VueUiDonut', VueUiDonut)
app.component('VueUiSparkline', VueUiSparkline)
app.component('VueUiGauge', VueUiGauge)
app.component('VueUiXy', VueUiXy)

app.mount('#app')
