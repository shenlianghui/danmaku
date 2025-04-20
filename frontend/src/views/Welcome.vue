<template>
  <div class="welcome-container">
    <!-- 添加动画弹幕背景 -->
    <div class="danmaku-background">
      <span v-for="(item, index) in danmakuItems" :key="index" 
        :style="{ 
          color: item.color, 
          fontSize: item.size + 'px', 
          opacity: item.opacity,
          top: item.top + '%',
          '--duration': item.duration + 's',
          '--delay': item.delay + 's'
        }" 
        class="danmaku-item danmaku-animation">
        {{item.text}}
      </span>
    </div>
    
    <div class="welcome-content slide-up">
      <el-card shadow="hover" class="welcome-card">
        <div class="content">
          <div class="logo-container">
            <div class="logo-animation pulse-animation">
              <BilibiliLogo style="width: 60px; height: 60px;" />
            </div>
          </div>
          <h1 class="title text-primary">弹幕分析系统</h1>
          <p class="subtitle">探索视频互动的海洋</p>
          
          <p class="description">
            本系统提供强大的 Bilibili 弹幕数据分析工具，包括关键词提取、情感分析、
            互动热点识别等功能，让您轻松掌握观众反馈和视频热点。
          </p>
          
          <div class="feature-cards">
            <div class="feature-card card-float">
              <el-icon class="feature-icon"><Download /></el-icon>
              <h3>高效爬取</h3>
              <p>便捷获取弹幕数据</p>
            </div>
            <div class="feature-card card-float">
              <el-icon class="feature-icon"><DataAnalysis /></el-icon>
              <h3>深度分析</h3>
              <p>多维度数据洞察</p>
            </div>
            <div class="feature-card card-float">
              <el-icon class="feature-icon"><PieChart /></el-icon>
              <h3>可视呈现</h3>
              <p>直观数据展示</p>
            </div>
          </div>
          
          <div class="actions">
            <el-button type="primary" size="large" @click="goToLogin" class="btn-login">
              <el-icon><User /></el-icon> 登录
            </el-button>
            <el-button type="success" size="large" @click="goToRegister" class="btn-register">
              <el-icon><UserFilled /></el-icon> 注册
            </el-button>
          </div>
          
          <!-- 调试部分保留但默认隐藏 -->
          <div class="debug-section" v-if="isDebugMode && showDebug">
            <el-divider>调试选项</el-divider>
            <el-button size="small" @click="checkSystemStatus">检查系统状态</el-button>
            <p v-if="systemStatus" class="debug-info">
              <strong>系统状态:</strong> {{ systemStatus }}
            </p>
            <p v-if="csrfStatus" class="debug-info">
              <strong>CSRF Token:</strong> {{ csrfStatus }}
            </p>
          </div>
          
          <div class="footer">
            <p>©2023 弹幕分析系统 - 探索视频互动新体验</p>
            <span class="debug-trigger" v-if="isDebugMode" @click="toggleDebug">·</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'
import { 
  Download, 
  DataAnalysis, 
  PieChart, 
  User, 
  UserFilled 
} from '@element-plus/icons-vue'
import { BilibiliLogo } from '@/assets/icons'

const router = useRouter()
const authStore = useAuthStore()

// 调试模式相关
const isDebugMode = computed(() => process.env.NODE_ENV === 'development')
const systemStatus = ref('')
const csrfStatus = ref('')
const showDebug = ref(false)

// 随机弹幕数据
const danmakuItems = ref([])

// 生成随机弹幕数据
onMounted(() => {
  generateDanmaku()
  
  // 如果已经登录，重定向到仪表盘
  if (authStore.isAuthenticated) {
    router.push({ name: 'Dashboard' })
  }
})

const generateDanmaku = () => {
  const texts = [
    '这个视频太棒了！', '哈哈哈笑死我了', '前方高能', '技术太厉害了', 
    '已经三连了', '这部分好感人', '这个分析系统真不错', '数据可视化很直观',
    '弹幕分析好用', '支持UP主', '学到了很多', '信息量很大', '6666666',
    '这个弹幕分析工具真棒', '弹幕海洋', '高能预警', '前方核能', '2333333'
  ]
  
  const colors = [
    'var(--primary-color)', 
    'var(--secondary-color)', 
    'var(--primary-light)', 
    'var(--secondary-light)', 
    '#ff9900', 
    '#66dd99', 
    '#ff6600', 
    '#9966ff', 
    '#ff4400', 
    '#44bbff'
  ]
  
  danmakuItems.value = Array(25).fill().map(() => {
    return {
      text: texts[Math.floor(Math.random() * texts.length)],
      color: colors[Math.floor(Math.random() * colors.length)],
      size: Math.floor(Math.random() * 6) + 14, // 14-20px
      opacity: (Math.random() * 0.4 + 0.4).toFixed(2), // 0.4-0.8
      top: Math.floor(Math.random() * 80) + 10, // 10%-90%
      duration: Math.floor(Math.random() * 10) + 10, // 10-20s
      delay: Math.floor(Math.random() * 5) // 0-5s
    }
  })
}

const goToLogin = () => {
  router.push({ name: 'Login' })
}

const goToRegister = () => {
  router.push({ name: 'Register' })
}

// 调试切换
const toggleDebug = () => {
  showDebug.value = !showDebug.value
}

// 调试功能 - 检查系统状态
const checkSystemStatus = async () => {
  try {
    // 检查CSRF令牌
    const csrfResponse = await axios.get('/api/accounts/csrf/', { 
      withCredentials: true 
    })
    csrfStatus.value = csrfResponse.status === 200 ? '有效' : '无效'
    
    // 检查后端API状态
    const apiTest = await axios.get('/api/videos/', { 
      withCredentials: true,
      params: { limit: 1 }
    })
    
    systemStatus.value = '系统正常'
  } catch (error) {
    systemStatus.value = `系统异常: ${error.message}`
    csrfStatus.value = '获取失败'
    console.error('系统状态检查错误:', error)
  }
}
</script>

<style scoped>
.welcome-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #141e30 0%, #243b55 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

/* 动画弹幕背景 */
.danmaku-background {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  overflow: hidden;
  z-index: 0;
}

.danmaku-item {
  position: absolute;
  white-space: nowrap;
  left: 100%;
  font-weight: bold;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  letter-spacing: 0.5px;
  pointer-events: none;
}

.welcome-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1000px;
}

.welcome-card {
  width: 100%;
  border-radius: var(--border-radius-large);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: var(--shadow-large);
  border: none;
  overflow: hidden;
  transition: var(--transition-bounce);
}

.welcome-card:hover {
  transform: translateY(-8px) scale(1.01);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.6);
}

.content {
  padding: 40px;
  text-align: center;
}

.logo-container {
  display: flex;
  justify-content: center;
  margin-bottom: 30px;
}

.logo-animation {
  width: 90px;
  height: 90px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-primary);
  overflow: hidden;
}

.title {
  font-size: 36px;
  font-weight: 800;
  margin: 0 0 10px;
  background: linear-gradient(to right, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 20px;
  color: var(--grey-600);
  margin-top: 0;
  margin-bottom: 30px;
}

.description {
  font-size: 16px;
  line-height: 1.6;
  color: var(--grey-600);
  max-width: 700px;
  margin: 0 auto 40px;
}

.feature-cards {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

.feature-card {
  background: white;
  border-radius: var(--border-radius-base);
  padding: 25px;
  width: 200px;
  box-shadow: var(--shadow-base);
  text-align: center;
}

.feature-icon {
  font-size: 36px;
  color: var(--primary-color);
  margin-bottom: 15px;
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary-color) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.feature-card h3 {
  font-size: 18px;
  margin: 0 0 10px;
  color: var(--grey-700);
}

.feature-card p {
  font-size: 14px;
  color: var(--grey-500);
  margin: 0;
}

.actions {
  margin-top: 40px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.btn-login, .btn-register {
  min-width: 120px;
  border-radius: var(--border-radius-base);
  transition: var(--transition-bounce);
}

.btn-login {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.btn-login:hover {
  transform: translateY(-3px);
  background: var(--primary-dark);
  border-color: var(--primary-dark);
  box-shadow: var(--shadow-primary);
}

.btn-register {
  background: var(--secondary-color);
  border-color: var(--secondary-color);
}

.btn-register:hover {
  transform: translateY(-3px);
  background: var(--secondary-dark);
  border-color: var(--secondary-dark);
  box-shadow: var(--shadow-secondary);
}

.debug-section {
  margin-top: 30px;
  padding: 15px;
  background-color: var(--grey-100);
  border-radius: var(--border-radius-base);
  text-align: left;
}

.debug-info {
  font-size: 14px;
  color: var(--grey-600);
  margin: 10px 0;
}

.footer {
  margin-top: 30px;
  color: var(--grey-500);
  font-size: 14px;
}

.debug-trigger {
  cursor: pointer;
  display: inline-block;
  padding: 10px;
  user-select: none;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .content {
    padding: 30px 20px;
  }
  
  .feature-cards {
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }
  
  .feature-card {
    width: 100%;
    max-width: 280px;
  }
  
  .actions {
    flex-direction: column;
    align-items: center;
  }
  
  .btn-login, .btn-register {
    width: 100%;
  }
  
  .title {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 18px;
  }
}
</style>
  