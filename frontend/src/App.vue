<template>
  <div class="app-container">
    <!-- 使用 v-if 判断是否显示 Header/Footer/Main 布局 -->
    <el-container v-if="!isWelcomePage">
      <el-header class="app-header">
        <!-- Logo 点击跳转到 Dashboard -->
        <div class="logo" @click="goToDashboard">
          <BilibiliLogo class="logo-icon" />
          <h1>B站弹幕分析系统</h1>
        </div>
        <el-menu
          :default-active="activeMenuIndex"
          class="el-menu-demo"
          mode="horizontal"
          router
          style="flex-grow: 1;"
        >
          <!-- 导航链接使用自定义图标 -->
          <el-menu-item index="/dashboard">
            <el-icon><HomeFilled /></el-icon> 首页
          </el-menu-item>
          <el-menu-item index="/videos">
            <el-icon><VideoPlay /></el-icon> 视频管理
          </el-menu-item>
          <el-menu-item index="/crawler">
            <el-icon><Download /></el-icon> 弹幕爬取
          </el-menu-item>
          <el-menu-item index="/my-tasks">
            <el-icon><List /></el-icon> 我的任务
          </el-menu-item>
          <el-menu-item index="/analysis">
            <el-icon><DataAnalysis /></el-icon> 弹幕分析
          </el-menu-item>
        </el-menu>

        <!-- 用户信息区域 -->
        <div class="user-info">
          <template v-if="authStore.isAuthenticated">
            <el-dropdown @command="handleCommand" trigger="click">
              <span class="el-dropdown-link">
                <el-avatar :size="32" class="user-avatar">
                  {{ authStore.user ? authStore.user.username.substring(0, 1).toUpperCase() : 'U' }}
                </el-avatar>
                <span class="username">{{ authStore.user ? authStore.user.username : '用户' }}</span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 个人资料
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button type="primary" @click="goToLogin" class="login-btn">
              <el-icon><User /></el-icon> 登录
            </el-button>
            <el-button @click="goToRegister" class="register-btn">
              <el-icon><Plus /></el-icon> 注册
            </el-button>
          </template>
        </div>
      </el-header>

      <el-main class="app-main fade-in">
        <!-- 使用 transition 组件添加动画 -->
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>

      <el-footer class="app-footer">
        <div class="footer-content">
          <div class="footer-links">
            <a href="https://www.bilibili.com" target="_blank">B站官网</a>
            <a href="#">关于我们</a>
            <a href="#">帮助中心</a>
            <a href="#">联系我们</a>
          </div>
          <p class="copyright">© {{ new Date().getFullYear() }} B站弹幕分析系统 - 基于 Python, Django, Vue.js 开发</p>
        </div>
      </el-footer>
    </el-container>

    <!-- 如果是 Welcome 页面，则直接渲染 router-view -->
    <router-view v-else />
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue' // 添加 onMounted
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, HomeFilled, VideoPlay, Download, List, DataAnalysis, User, SwitchButton, Plus } from '@element-plus/icons-vue'
import { BilibiliLogo } from '@/assets/icons'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenuIndex = ref('/dashboard') // 默认激活 dashboard

// 判断当前是否是欢迎页
const isWelcomePage = computed(() => route.name === 'Welcome')

// 添加 onMounted 钩子来处理初始化
onMounted(async () => {
  console.log('App mounted, current route path:', route.path, ', name:', route.name);
  // 打印出路由器状态，看是否正确初始化
  console.log('Router history state:', router.currentRoute.value);
  
  // 确保CSRF令牌已设置
  try {
    console.log('Attempting to fetch CSRF token...');
    const response = await axios.get('/api/accounts/csrf/', { 
      withCredentials: true,
      // 添加调试信息
      headers: {
        'Debug-Timestamp': new Date().toISOString()
      }
    });
    console.log('CSRF token response:', response.status, response.statusText);
    authStore.setCsrfReady(true);
    console.log('Auth store csrfReady set to:', authStore.csrfReady);
  } catch (error) {
    console.error('Failed to refresh CSRF token. Error:', error);
    console.error('Error details:', error.response || 'No response data');
    authStore.setCsrfReady(false);
  }
  
  // 检查cookie，看看是否正确设置
  console.log('Current cookies:', document.cookie);
  
  // 如果初始路由不是 Welcome，再检查认证状态
  if (route.name !== 'Welcome') {
    console.log('Not on welcome page, checking auth status');
    // 打印auth状态
    console.log('Auth state:', authStore.isAuthenticated, 'User:', authStore.user);
  }
})

// 监听路由变化来更新激活的菜单项
watch(
  () => route.path,
  (newPath) => {
    if (newPath.startsWith('/dashboard')) {
      activeMenuIndex.value = '/dashboard'
    } else if (newPath.startsWith('/videos')) {
      activeMenuIndex.value = '/videos'
    } else if (newPath.startsWith('/crawler')) {
      activeMenuIndex.value = '/crawler'
    } else if (newPath.startsWith('/my-tasks')) {
      activeMenuIndex.value = '/my-tasks'
    } else if (newPath.startsWith('/analysis')) {
      activeMenuIndex.value = '/analysis'
    } else {
       // 对于非菜单项的受保护页面，可以不改变激活状态或根据逻辑设置
       // activeMenuIndex.value = ''; // 或者保持上一个状态
    }
  },
  { immediate: true }
)

// 处理下拉菜单命令
const handleCommand = async (command) => {
  if (command === 'logout') {
    await handleLogout()
  } else if (command === 'profile') {
    router.push({ name: 'Profile' })
  }
}

// 处理登出
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await authStore.logout()
    ElMessage.success('已退出登录')
    // 登出后跳转到欢迎页
    router.push({ name: 'Welcome' })
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('退出登录失败')
      console.error(err)
    }
  }
}

// 跳转方法
const goToLogin = () => {
  router.push({ name: 'Login' })
}
const goToRegister = () => {
  router.push({ name: 'Register' })
}
const goToDashboard = () => {
  // 仅当未认证时点击 Logo 才跳转到欢迎页，否则跳转到 Dashboard
  if (authStore.isAuthenticated) {
      router.push({ name: 'Dashboard' })
  } else {
      router.push({ name: 'Welcome' })
  }
}

</script>

<style>
/* 全局样式在theme.css中定义，这里只保留App组件特定的样式 */
.app-container {
  width: 100%;
  min-height: 100vh;
}

.el-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: white;
  color: var(--grey-700);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-light);
  padding: 0 24px;
  height: 64px !important;
  position: sticky;
  top: 0;
  z-index: 1000;
}

.logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  margin-right: 40px;
  transition: var(--transition-base);
}

.logo:hover {
  transform: scale(1.05);
}

.logo-icon {
  color: var(--primary-color);
  font-size: 28px;
  margin-right: 8px;
}

.logo h1 {
  font-size: 20px;
  color: var(--primary-color);
  margin: 0;
  font-weight: 600;
}

.el-menu--horizontal.el-menu {
  border-bottom: none;
  height: 64px;
}

.el-menu--horizontal > .el-menu-item {
  height: 64px;
  line-height: 64px;
}

.user-info {
  display: flex;
  align-items: center;
}

.el-dropdown-link {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 5px 10px;
  border-radius: 20px;
  transition: var(--transition-base);
}

.el-dropdown-link:hover {
  background-color: var(--grey-100);
}

.user-avatar {
  background-color: var(--primary-color);
  margin-right: 8px;
}

.username {
  margin: 0 5px;
  color: var(--grey-700);
}

.login-btn {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.login-btn:hover, .login-btn:focus {
  background-color: var(--primary-dark);
  border-color: var(--primary-dark);
}

.register-btn {
  margin-left: 8px;
}

.app-main {
  padding: 20px;
  flex: 1;
  min-height: calc(100vh - 64px - 60px);
  background-color: var(--grey-100);
}

.app-footer {
  height: auto !important;
  padding: 20px;
  background-color: var(--grey-700);
  color: white;
}

.footer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.footer-links {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}

.footer-links a {
  color: var(--grey-200);
  text-decoration: none;
  transition: var(--transition-base);
}

.footer-links a:hover {
  color: white;
  text-decoration: underline;
}

.copyright {
  font-size: 14px;
  color: var(--grey-400);
  margin: 0;
}

@media (max-width: 768px) {
  .logo h1 {
    display: none;
  }
  
  .username {
    display: none;
  }
  
  .app-header {
    padding: 0 10px;
  }
}
</style>