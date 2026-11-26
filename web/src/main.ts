import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './app/App.vue'

createApp(App).use(createPinia()).mount('#app')
