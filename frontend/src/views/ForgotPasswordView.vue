<template>
  <div class="forgot-password-container">
    <el-card class="forgot-password-card" :body-style="{ padding: '30px' }">
      <template #header>
        <div class="card-header">
          <h1>重置密码</h1>
        </div>
      </template>
      
      <!-- 第一步：输入邮箱 -->
      <div v-if="step === 1">
        <p class="instruction">请输入您注册时使用的电子邮箱地址，我们将向该邮箱发送重置密码的链接。</p>
        <el-form ref="emailFormRef" :model="formData" :rules="emailRules" label-width="80px" status-icon>
          <el-form-item label="邮箱" prop="email">
            <el-input 
              v-model="formData.email" 
              placeholder="请输入您的邮箱"
              prefix-icon="el-icon-message"
            ></el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="requestReset" :loading="loading" round>
              发送重置链接
            </el-button>
            <el-button @click="goToLogin" :disabled="loading" round>
              返回登录
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 第二步：邮件已发送 -->
      <div v-else-if="step === 2" class="success-step">
        <el-result 
          icon="success" 
          title="重置链接已发送!" 
          sub-title="请检查您的邮箱，按照邮件中的指引完成密码重置"
        >
          <template #extra>
            <div class="extra-content">
              <p>没有收到邮件？请检查垃圾邮件文件夹，或者</p>
              <el-button type="primary" @click="step = 1" round>重新发送</el-button>
              <el-button @click="goToLogin" round>返回登录</el-button>
            </div>
          </template>
        </el-result>
      </div>
      
      <!-- 显示错误信息 -->
      <div v-if="error && step === 1" class="error-message">
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const step = ref(1)
const loading = ref(false)
const error = ref('')
const emailFormRef = ref(null)

// 表单数据
const formData = reactive({
  email: ''
})

// 验证规则
const emailRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] }
  ]
}

// 请求密码重置
const requestReset = async () => {
  if (!emailFormRef.value) return
  
  await emailFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      error.value = ''
      
      try {
        const response = await axios.post('/api/accounts/password-reset/', {
          email: formData.email
        })
        
        // 不管用户是否存在，都显示相同的成功信息（安全措施）
        if (response.data && response.data.status === 'success') {
          // 前进到下一步
          step.value = 2
          
          // 仅开发环境：如果返回了重置URL，则可以直接跳转
          if (process.env.NODE_ENV === 'development' && response.data.reset_url) {
            console.log('开发环境重置链接:', response.data.reset_url)
          }
        } else {
          throw new Error('请求失败')
        }
      } catch (err) {
        console.error('Password reset request error:', err)
        error.value = '请求发送失败，请稍后重试'
        ElMessage.error(error.value)
      } finally {
        loading.value = false
      }
    }
  })
}

// 返回登录页面
const goToLogin = () => {
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.forgot-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;
  background-image: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.forgot-password-card {
  width: 450px;
  border-radius: 8px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.forgot-password-card:hover {
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

.success-step {
  padding: 20px 0;
  text-align: center;
}

.extra-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.extra-content p {
  margin-bottom: 15px;
  color: #606266;
}

.error-message {
  margin-top: 20px;
}
</style> 