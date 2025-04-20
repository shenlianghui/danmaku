<template>
  <div class="reset-password-container">
    <el-card class="reset-password-card" :body-style="{ padding: '30px' }">
      <template #header>
        <div class="card-header">
          <h1>设置新密码</h1>
        </div>
      </template>
      
      <!-- 加载中状态 -->
      <div v-if="loading && !verificationComplete" class="loading-state">
        <el-skeleton :rows="4" animated />
        <div class="loading-text">正在验证重置链接...</div>
      </div>
      
      <!-- 链接无效 -->
      <div v-else-if="invalidLink" class="invalid-link">
        <el-result 
          icon="error" 
          title="链接无效或已过期" 
          sub-title="请重新申请密码重置"
        >
          <template #extra>
            <el-button type="primary" @click="goToForgotPassword" round>
              请求新的重置链接
            </el-button>
          </template>
        </el-result>
      </div>
      
      <!-- 设置新密码表单 -->
      <div v-else-if="!resetSuccess">
        <p class="instruction">请设置您的新密码</p>
        
        <el-alert
          title="密码要求: 至少8个字符，包含数字、字母和特殊字符"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />
        
        <el-form ref="passwordFormRef" :model="formData" :rules="passwordRules" label-width="100px" status-icon>
          <el-form-item label="新密码" prop="password">
            <el-input 
              type="password" 
              v-model="formData.password" 
              placeholder="请输入新密码" 
              prefix-icon="el-icon-lock"
              show-password
            ></el-input>
          </el-form-item>
          <el-form-item label="确认密码" prop="password2">
            <el-input 
              type="password" 
              v-model="formData.password2" 
              placeholder="请再次输入新密码" 
              prefix-icon="el-icon-lock"
              show-password
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="resetPassword" :loading="loading" round>
              重置密码
            </el-button>
            <el-button @click="goToLogin" :disabled="loading" round>
              返回登录
            </el-button>
          </el-form-item>
        </el-form>
        
        <!-- 错误信息 -->
        <div v-if="error" class="error-message">
          <el-alert
            :title="error"
            type="error"
            show-icon
            :closable="false"
          />
        </div>
      </div>
      
      <!-- 重置成功 -->
      <div v-else class="success-state">
        <el-result 
          icon="success" 
          title="密码重置成功!" 
          sub-title="您的密码已重置，现在可以使用新密码登录了"
        >
          <template #extra>
            <el-button type="primary" @click="goToLogin" round>
              前往登录
            </el-button>
          </template>
        </el-result>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const error = ref('')
const passwordFormRef = ref(null)
const invalidLink = ref(false)
const resetSuccess = ref(false)
const verificationComplete = ref(false)

// 表单数据
const formData = reactive({
  password: '',
  password2: '',
  uid: '',
  token: ''
})

// 密码验证规则
const passwordRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要8个字符', trigger: 'blur' },
    { pattern: /(?=.*[0-9])/, message: '密码必须包含至少一个数字', trigger: 'blur' },
    { pattern: /(?=.*[a-zA-Z])/, message: '密码必须包含至少一个字母', trigger: 'blur' },
    { pattern: /(?=.*[!@#$%^&*])/, message: '密码必须包含至少一个特殊字符', trigger: 'blur' }
  ],
  password2: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== formData.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

// 组件加载时验证令牌
onMounted(() => {
  // 从URL获取UID和Token
  const uid = route.query.uid
  const token = route.query.token
  
  if (!uid || !token) {
    invalidLink.value = true
    verificationComplete.value = true
    return
  }
  
  // 存储到表单数据中
  formData.uid = uid
  formData.token = token
  
  // 这里可以添加后端验证令牌的逻辑
  // 为简化起见，我们只做基本检查
  verificationComplete.value = true
})

// 重置密码
const resetPassword = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      error.value = ''
      
      try {
        const response = await axios.post('/api/accounts/password-reset/confirm/', {
          uid: formData.uid,
          token: formData.token,
          password: formData.password,
          password2: formData.password2
        })
        
        if (response.data && response.data.status === 'success') {
          resetSuccess.value = true
          ElMessage.success('密码重置成功')
        } else {
          throw new Error(response.data?.error || '重置失败')
        }
      } catch (err) {
        console.error('Password reset error:', err)
        if (err.response?.data?.error) {
          error.value = err.response.data.error
        } else {
          error.value = '重置密码失败，请稍后重试'
        }
        ElMessage.error(error.value)
      } finally {
        loading.value = false
      }
    }
  })
}

// 导航函数
const goToLogin = () => {
  router.push({ name: 'Login' })
}

const goToForgotPassword = () => {
  router.push({ name: 'ForgotPassword' })
}
</script>

<style scoped>
.reset-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
  background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.reset-password-card {
  width: 450px;
  border-radius: 8px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.reset-password-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
}

.card-header {
  text-align: center;
  padding: 15px 0;
}

.card-header h1 {
  margin: 0;
  font-size: 24px;
  color: #409EFF;
}

.instruction {
  margin-bottom: 25px;
  color: #606266;
  text-align: center;
}

.el-form-item {
  margin-bottom: 25px;
}

.el-button {
  width: 45%;
  margin-right: 10px;
}

.loading-state {
  padding: 20px 0;
}

.loading-text {
  text-align: center;
  margin-top: 20px;
  color: #909399;
}

.success-state, .invalid-link {
  padding: 20px 0;
  text-align: center;
}

.error-message {
  margin-top: 20px;
}
</style> 