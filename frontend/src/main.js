import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// 引入自定义主题和动画样式
import './assets/theme.css'
import './assets/animations.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAuthStore } from './stores/auth'
import axios from 'axios'
// 引入自定义图标
import * as Icons from './assets/icons'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, {
  locale: zhCn
})

// 注册所有图标组件
Object.entries(Icons).forEach(([key, component]) => {
  app.component(key, component)
})

// 初始化应用前获取CSRF令牌
async function initApp() {
  try {
    console.log('开始初始化应用...')
    const authStore = useAuthStore()
    
    // 获取CSRF令牌
    const response = await axios.get('/api/accounts/csrf/', { 
      withCredentials: true,
      timeout: 5000 // 添加超时设置
    })
    console.log('CSRF token response:', response.status, response.statusText)
    
    // 获取令牌后初始化Pinia存储
    authStore.setCsrfReady(true)
    
    // 尝试获取用户信息 - 如果不在存储中，则从API获取
    console.log('尝试获取用户信息...')
    console.log('当前认证状态:', authStore.isAuthenticated ? '已登录' : '未登录')
    
    if (!authStore.isAuthenticated) {
      try {
        const userResult = await authStore.fetchUser()
        console.log('用户信息获取结果:', userResult)
      } catch (userError) {
        console.error('获取用户信息时出错:', userError)
        // 继续执行，不阻止应用挂载
      }
    } else {
      console.log('从本地存储恢复用户:', authStore.user?.username)
    }
    
    console.log('初始化完成，认证状态:', authStore.isAuthenticated ? '已登录' : '未登录')
  } catch (error) {
    console.error('初始化失败:', error?.response?.status || error.message || error)
    if (error.response) {
      console.error('错误响应数据:', error.response.data)
    }
  } finally {
    // 无论成功失败都挂载应用
    console.log('挂载应用到DOM...')
    app.mount('#app')
  }
}

// 开始初始化
initApp() 