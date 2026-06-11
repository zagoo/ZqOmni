/** Frontend entrypoint — wires Pinia, mounts the JWT/silent-refresh
 * interceptors on the generated client, then the router. */
import { createApp } from 'vue'
import App from '@/App.vue'
import '@/assets/styles.css'
import { router } from '@/router'
import { pinia } from '@/store'
import { useAuthStore } from '@/store/auth'

const app = createApp(App)
app.use(pinia)

const auth = useAuthStore(pinia)
auth.mountInterceptors(() => {
  router.push({ path: '/login' })
})

app.use(router)
app.mount('#app')
