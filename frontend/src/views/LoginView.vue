<template>
  <div class="login-container">
    <el-card class="login-card" :body-style="{ padding: '30px' }">
      <template #header>
        <div class="card-header">
          <h1>登录</h1>
        </div>
      </template>
      <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-width="80px" status-icon>
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入用户名" 
            :prefix-icon="User"
            @keyup.enter="handleLogin"
            :disabled="locked"
          ></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            type="password" 
            v-model="loginForm.password" 
            placeholder="请输入密码" 
            :prefix-icon="Lock"
            show-password 
            @keyup.enter="handleLogin"
            :disabled="locked"
          ></el-input>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="loginForm.remember_me" :disabled="locked">记住我 (30天)</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" :disabled="locked" round>
            <el-icon class="icon-in-button"><Key /></el-icon> 登录
          </el-button>
          <el-button @click="goToRegister" :disabled="loading || locked" round>
            <el-icon class="icon-in-button"><UserFilled /></el-icon> 注册新账号
          </el-button>
        </el-form-item>
        <div v-if="locked" class="lockout-message">
          <el-alert
            title="登录尝试次数过多"
            type="error"
            description="您的账号已被临时锁定，请稍后再试"
            show-icon
            :closable="false"
          />
        </div>
        <div v-else-if="attemptsLeft < 5 && attemptsLeft > 0" class="attempts-left">
          <el-alert
            :title="`您还有 ${attemptsLeft} 次登录尝试机会`"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>
        <div v-if="error && !locked" class="error-message">
          <el-alert
            :title="error"
            type="error"
            show-icon
            :closable="false"
          />
        </div>
      </el-form>
      <div class="login-options">
        <router-link to="/forgot-password" class="forgot-password">忘记密码?</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { User, Lock, Key, UserFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const loginForm = reactive({
  username: '',
  password: '',
  remember_me: false
})

const loginRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度至少为3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少为8个字符', trigger: 'blur' }
  ],
})

const loading = ref(false)
const error = ref('')
const locked = ref(false)
const attemptsLeft = ref(5)

// 组件加载时，检查认证状态
onMounted(async () => {
  // 如果已经登录，直接跳转到仪表盘
  if (authStore.isAuthenticated) {
    router.push({ name: 'Dashboard' })
    return
  }
  
  // 检查是否有来自store的错误
  if (authStore.error) {
    error.value = authStore.error
  }
  
  // 获取CSRF令牌
  try {
    await getCsrfToken()
  } catch (err) {
    console.error('Failed to get CSRF token:', err)
  }
})

// 获取CSRF令牌
const getCsrfToken = async () => {
  try {
    const response = await axios.get('/api/accounts/csrf/', { withCredentials: true })
    if (response.data && response.data.status === 'success') {
      authStore.setCsrfReady(true)
    }
  } catch (error) {
    console.error('Failed to get CSRF token:', error)
    ElMessage.error('无法获取安全令牌，请刷新页面重试')
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  // 锁定检查
  if (locked.value) {
    ElMessage.warning('账号已被临时锁定，请稍后再试')
    return
  }
  
  // 等待 CSRF 准备就绪
  if (!authStore.csrfReady) {
    ElMessage.warning('正在初始化安全令牌，请稍候重试')
    try {
      await getCsrfToken()
    } catch (error) {
      console.error('Retry CSRF fetch failed:', error)
    }
    return
  }

  // 添加更多调试信息
  console.log('开始登录流程，CSRF令牌状态:', authStore.csrfReady)
  console.log('当前cookies:', document.cookie)
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      error.value = ''
      attemptsLeft.value = 5 // 重置错误计数
      
      try {
        console.log('发送登录请求，数据:', JSON.stringify({
          username: loginForm.username,
          password: '******', // 密码不记录
          remember_me: loginForm.remember_me
        }))
        
        const result = await authStore.login({
          username: loginForm.username,
          password: loginForm.password,
          remember_me: loginForm.remember_me
        })
        
        console.log('登录结果:', JSON.stringify(result))
        
        if (result.success) {
          ElMessage.success('登录成功')
          router.push({ name: 'Dashboard' })
        } else {
          error.value = result.error || '登录失败'
          if (result.attempts_left !== undefined) {
            attemptsLeft.value = result.attempts_left
          }
          locked.value = result.lockout || false
          
          ElMessage.error(error.value)
        }
      } catch (err) {
        console.error('登录期间发生错误:', err)
        error.value = '登录请求发生错误，请稍后重试'
        ElMessage.error(error.value)
      } finally {
        loading.value = false
      }
    }
  })
}

const goToRegister = () => {
  router.push({ name: 'Register' })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  position: relative;
  overflow: hidden;
}

/* 背景气泡动画 */
.login-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.2'%3E%3Ccircle cx='12' cy='12' r='5'/%3E%3Ccircle cx='50' cy='50' r='3'/%3E%3Ccircle cx='85' cy='25' r='4'/%3E%3Ccircle cx='70' cy='70' r='6'/%3E%3Ccircle cx='25' cy='85' r='5'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  opacity: 0.6;
  z-index: 0;
}

.login-card {
  width: 420px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
}

.login-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.card-header {
  text-align: center;
  position: relative;
}

.card-header h1 {
  color: #409EFF;
  font-size: 28px;
  margin: 0;
  font-weight: 600;
  letter-spacing: 1px;
  background: linear-gradient(135deg, #409EFF 0%, #64B5F6 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.login-options {
  text-align: center;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}

.forgot-password {
  color: #909399;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.3s;
}

.forgot-password:hover {
  color: #409EFF;
  text-decoration: underline;
}

/* 表单相关样式 */
:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-input__inner) {
  border-radius: 8px;
  height: 45px;
  padding-left: 15px;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

:deep(.el-input__inner:focus) {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

:deep(.el-button) {
  height: 45px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #409EFF 0%, #64B5F6 100%);
  border: none;
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.3);
}

:deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(64, 158, 255, 0.4);
}

:deep(.el-button--default) {
  border: 1px solid #dcdfe6;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
}

:deep(.el-button--default:hover) {
  border-color: #c6e2ff;
  color: #409EFF;
  background: white;
}

.lockout-message,
.attempts-left,
.error-message {
  margin-top: 15px;
  border-radius: 8px;
  overflow: hidden;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.login-card {
  animation: fadeIn 0.5s ease-out;
}

/* 响应式调整 */
@media (max-width: 480px) {
  .login-card {
    width: 90%;
    max-width: 380px;
  }
  
  .card-header h1 {
    font-size: 24px;
  }
  
  .el-form-item {
    margin-bottom: 20px;
  }
}

:deep(.icon-in-button) {
  margin-right: 5px;
  font-size: 16px;
  vertical-align: middle;
}
</style> 