<template>
  <div class="register-container">
    <el-card class="register-card" :body-style="{ padding: '30px' }">
      <template #header>
        <div class="card-header">
          <h1>注册</h1>
        </div>
      </template>
      <el-steps :active="activeStep" finish-status="success" simple style="margin-bottom: 30px">
        <el-step title="基本信息" :icon="User" />
        <el-step title="密码设置" :icon="Lock" />
        <el-step title="完成" :icon="Check" />
      </el-steps>
      
      <!-- 步骤1: 基本信息 -->
      <div v-if="activeStep === 0" class="step-content">
        <el-form ref="basicFormRef" :model="registerForm" :rules="basicRules" label-width="80px" status-icon>
          <el-form-item label="用户名" prop="username">
            <el-input 
              v-model="registerForm.username" 
              placeholder="请输入用户名"
              :prefix-icon="User"
              @blur="checkUsernameAvailability"
            ></el-input>
            <div v-if="usernameStatus.checked" class="username-feedback" :class="{'success': usernameStatus.available, 'error': !usernameStatus.available}">
              {{ usernameStatus.message }}
            </div>
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input 
              v-model="registerForm.email" 
              placeholder="请输入邮箱"
              :prefix-icon="Message"
            ></el-input>
          </el-form-item>
          <el-form-item label="姓名" prop="first_name">
            <el-input 
              v-model="registerForm.first_name" 
              placeholder="请输入姓名 (可选)"
              :prefix-icon="User"
            ></el-input>
          </el-form-item>
          <el-form-item label="姓氏" prop="last_name">
            <el-input 
              v-model="registerForm.last_name" 
              placeholder="请输入姓氏 (可选)"
              :prefix-icon="UserFilled"
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="goToStep2" :loading="loading" round>
              <el-icon class="icon-in-button"><ArrowRight /></el-icon> 下一步
            </el-button>
            <el-button @click="goToLogin" :disabled="loading" round>
              <el-icon class="icon-in-button"><Back /></el-icon> 已有账户？去登录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 步骤2: 密码设置 -->
      <div v-else-if="activeStep === 1" class="step-content">
        <el-alert
          title="密码要求: 至少8个字符，包含数字、字母和特殊字符(如 @#$%&* 等)"
          description="请确保两次输入的密码完全一致"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
          class="password-alert"
        />
        <el-form ref="passwordFormRef" :model="registerForm" :rules="passwordRules" label-width="80px" status-icon>
          <el-form-item label="密码" prop="password">
            <el-input 
              type="password" 
              v-model="registerForm.password" 
              placeholder="请输入密码" 
              :prefix-icon="Lock"
              show-password
            ></el-input>
          </el-form-item>
          <el-form-item label="确认密码" prop="password2">
            <el-input 
              type="password" 
              v-model="registerForm.password2" 
              placeholder="请再次输入密码" 
              :prefix-icon="Key"
              show-password
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-button @click="activeStep = 0" :disabled="loading" round>
              <el-icon class="icon-in-button"><Back /></el-icon> 上一步
            </el-button>
            <el-button type="primary" @click="handleRegister" :loading="loading" round>
              <el-icon class="icon-in-button"><CirclePlus /></el-icon> 注册
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 步骤3: 注册成功 -->
      <div v-else class="success-step">
        <el-result 
          icon="success" 
          title="注册成功!" 
          sub-title="您的账号已创建并已自动登录"
          class="success-result"
        >
          <template #extra>
            <el-button type="primary" @click="goToDashboard" round class="dashboard-btn">
              <el-icon class="icon-in-button"><HomeFilled /></el-icon> 前往仪表盘
            </el-button>
          </template>
        </el-result>
      </div>
      
      <!-- 错误提示 -->
      <div v-if="error && activeStep < 2" class="error-message">
        <el-alert
          :title="error"
          type="error"
          show-icon
          :closable="false"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { 
  User, 
  UserFilled, 
  Message, 
  Lock, 
  Check, 
  HomeFilled, 
  ArrowRight, 
  Back, 
  CirclePlus,
  Key
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

// 多步骤表单控制
const activeStep = ref(0)
const basicFormRef = ref(null)
const passwordFormRef = ref(null)

// 初始表单数据
const registerForm = reactive({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  password2: '' // 确保字段名称与后端匹配
})

// 监听表单值变化
onMounted(() => {
  // 获取CSRF令牌
  axios.get('/api/accounts/csrf/', { withCredentials: true })
    .then(() => {
      authStore.setCsrfReady(true)
    })
    .catch(error => {
      console.error('Failed to get CSRF token:', error)
    })
})

// 用户名可用状态
const usernameStatus = reactive({
  checked: false,
  available: false,
  message: ''
})

// 检查用户名可用性
const checkUsernameAvailability = async () => {
  if (!registerForm.username || registerForm.username.length < 3) return
  
  try {
    const response = await axios.post('/api/accounts/check-username/', {
      username: registerForm.username
    })
    usernameStatus.checked = true
    usernameStatus.available = response.data.available
    usernameStatus.message = response.data.message
    
    if (!response.data.available) {
      ElMessage.warning(response.data.message)
    }
  } catch (error) {
    console.error('检查用户名失败:', error)
    usernameStatus.checked = false
  }
}

// 前进到密码设置步骤
const goToStep2 = async () => {
  if (!basicFormRef.value) return
  
  await basicFormRef.value.validate(async (valid) => {
    if (valid) {
      // 如果用户名未检查可用性，则检查
      if (registerForm.username && !usernameStatus.checked) {
        await checkUsernameAvailability()
        if (!usernameStatus.available) {
          ElMessage.error('用户名已存在，请更换')
          return
        }
      }
      
      // 前进到下一步
      activeStep.value = 1
    }
  })
}

// 基本信息验证规则
const basicRules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度应在3到30个字符之间', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] }
  ]
})

// 密码验证规则
const passwordRules = reactive({
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要8个字符', trigger: 'blur' },
    { pattern: /(?=.*[0-9])/, message: '密码必须包含至少一个数字', trigger: 'blur' },
    { pattern: /(?=.*[a-zA-Z])/, message: '密码必须包含至少一个字母', trigger: 'blur' },
    { pattern: /(?=.*[!@#$%^&*])/, message: '密码必须包含至少一个特殊字符', trigger: 'blur' }
  ],
  password2: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
})

const loading = ref(false)
const error = ref('')

// 处理注册
const handleRegister = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      error.value = ''
      
      try {
        // 确保CSRF令牌已准备
        if (!authStore.csrfReady) {
          try {
            await axios.get('/api/accounts/csrf/', { withCredentials: true })
            authStore.setCsrfReady(true)
          } catch (csrfError) {
            throw new Error('无法获取安全令牌')
          }
        }
        
        const result = await authStore.register({
          username: registerForm.username,
          email: registerForm.email,
          password: registerForm.password,
          password2: registerForm.password2,
          first_name: registerForm.first_name,
          last_name: registerForm.last_name
        })
        
        if (result.success) {
          ElMessage.success('注册成功')
          activeStep.value = 2
        } else {
          error.value = result.error || '注册失败'
          ElMessage.error(error.value)
        }
      } catch (err) {
        console.error('注册期间发生错误:', err)
        error.value = '注册请求发生错误，请稍后重试'
        ElMessage.error(error.value)
      } finally {
        loading.value = false
      }
    }
  })
}

const goToLogin = () => {
  router.push({ name: 'Login' })
}

const goToDashboard = () => {
  router.push({ name: 'Dashboard' })
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  position: relative;
  overflow: hidden;
}

/* 背景图案 */
.register-container::before {
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

.register-card {
  width: 480px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  position: relative;
  z-index: 1;
  animation: fadeIn 0.5s ease-out;
}

.register-card:hover {
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

/* 步骤条样式 */
:deep(.el-steps) {
  margin-bottom: 25px;
}

:deep(.el-step__title) {
  font-size: 16px;
  font-weight: 500;
}

:deep(.el-step__icon.is-text) {
  border-radius: 50%;
  border: 2px solid #C0C4CC;
}

:deep(.el-step__icon.is-text.is-active) {
  background: linear-gradient(135deg, #409EFF 0%, #64B5F6 100%);
  border-color: #409EFF;
}

:deep(.el-step__line) {
  background-color: #EBEEF5;
}

/* 表单样式 */
.step-content {
  transition: all 0.3s ease;
}

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

/* 用户名反馈 */
.username-feedback {
  margin-top: 5px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  transition: all 0.3s;
}

.username-feedback.success {
  color: #67C23A;
  background-color: rgba(103, 194, 58, 0.1);
}

.username-feedback.error {
  color: #F56C6C;
  background-color: rgba(245, 108, 108, 0.1);
}

/* 密码提示样式 */
.password-alert {
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

:deep(.password-alert .el-alert__title) {
  font-weight: 500;
}

/* 成功结果 */
.success-step {
  padding: 20px 0;
}

:deep(.success-result .el-result__icon .el-icon) {
  color: #67C23A;
}

:deep(.success-result .el-result__title) {
  color: #67C23A;
  font-weight: 600;
}

:deep(.success-result .el-result__subtitle) {
  font-size: 16px;
  color: #606266;
}

.dashboard-btn {
  background: linear-gradient(135deg, #67C23A 0%, #85CE61 100%);
  box-shadow: 0 4px 10px rgba(103, 194, 58, 0.3);
}

.dashboard-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(103, 194, 58, 0.4);
}

/* 错误提示 */
.error-message {
  margin-top: 20px;
  border-radius: 8px;
  overflow: hidden;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 按钮图标 */
:deep(.icon-in-button) {
  margin-right: 5px;
  font-size: 16px;
  vertical-align: middle;
}

/* 响应式调整 */
@media (max-width: 520px) {
  .register-card {
    width: 90%;
    max-width: 420px;
  }
  
  .card-header h1 {
    font-size: 24px;
  }
  
  :deep(.el-steps--simple) {
    padding: 10px 0;
  }
  
  :deep(.el-step__title) {
    font-size: 14px;
  }
}
</style> 