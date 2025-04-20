<template>
  <div class="profile-container">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="profile-card">
          <template #header>
            <div class="card-header">
              <span>个人资料</span>
            </div>
          </template>
          <div class="user-info">
            <div class="avatar-container">
              <el-avatar :size="100" icon="el-icon-user-solid"></el-avatar>
            </div>
            <h2>{{ user.username }}</h2>
            <p class="user-email">{{ user.email }}</p>
            <p class="user-join-date">加入时间: {{ formatDate(user.date_joined) }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card class="profile-edit-card">
          <template #header>
            <div class="card-header">
              <span>编辑个人资料</span>
            </div>
          </template>
          <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="100px" v-loading="loading">
            <el-form-item label="姓名" prop="first_name">
              <el-input v-model="profileForm.first_name" placeholder="请输入姓名"></el-input>
            </el-form-item>
            <el-form-item label="姓氏" prop="last_name">
              <el-input v-model="profileForm.last_name" placeholder="请输入姓氏"></el-input>
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" placeholder="请输入邮箱"></el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="updateProfile" :loading="submitting">保存修改</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
            <el-alert v-if="message.text" :title="message.text" :type="message.type" show-icon :closable="false" />
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useAuthStore, apiClient } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import axios from 'axios';
import { formatDate } from '@/utils/dateFormatter'; // 导入日期格式化工具

const authStore = useAuthStore();

// 用户信息
const user = computed(() => authStore.user || {});

// 表单数据
const profileFormRef = ref(null);
const profileForm = reactive({
  first_name: '',
  last_name: '',
  email: ''
});

// 表单验证规则
const profileRules = reactive({
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: ['blur', 'change'] }
  ]
});

// 状态管理
const loading = ref(false);
const submitting = ref(false);
const message = reactive({
  text: '',
  type: 'info'
});

// 页面加载时加载用户数据
onMounted(async () => {
  loading.value = true;
  
  if (!authStore.isAuthenticated) {
    // 如果未登录，通过fetchUser尝试获取用户信息
    try {
      await authStore.fetchUser();
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  }
  
  // 如果无法获取用户，message显示错误
  if (!authStore.isAuthenticated) {
    message.text = '无法获取用户信息，请重新登录';
    message.type = 'error';
  } else {
    // 成功获取用户后，填充表单
    profileForm.first_name = user.value.first_name || '';
    profileForm.last_name = user.value.last_name || '';
    profileForm.email = user.value.email || '';
  }
  
  loading.value = false;
});

// 更新用户资料
const updateProfile = async () => {
  if (!profileFormRef.value) return;
  
  await profileFormRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true;
      message.text = '';
      
      try {
        // 使用配置好的 apiClient 实例，它会自动处理 CSRF
        const response = await apiClient.put('update/', profileForm);
        
        // 更新本地存储的用户信息
        authStore.user = response.data.user;
        
        message.text = '个人资料更新成功';
        message.type = 'success';
        ElMessage.success('个人资料已更新');
      } catch (error) {
        console.error('Failed to update profile:', error);
        // 从 apiClient 响应中获取错误信息
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || '更新个人资料失败';
        message.text = errorMessage;
        message.type = 'error';
        ElMessage.error(message.text);
      } finally {
        submitting.value = false;
      }
    }
  });
};

// 重置表单
const resetForm = () => {
  if (profileFormRef.value) {
    profileFormRef.value.resetFields();
    // 重新填充初始数据
    profileForm.first_name = user.value.first_name || '';
    profileForm.last_name = user.value.last_name || '';
    profileForm.email = user.value.email || '';
  }
};
</script>

<style scoped>
.profile-container {
  max-width: 1200px;
  margin: 20px auto;
  padding: 0 20px;
}

.profile-card, .profile-edit-card {
  height: 100%;
}

.card-header {
  font-size: 1.2em;
  font-weight: 500;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.avatar-container {
  margin-bottom: 20px;
}

.user-info h2 {
  margin-top: 0;
  margin-bottom: 10px;
}

.user-email, .user-join-date {
  color: #606266;
  margin: 5px 0;
}

.el-alert {
  margin-top: 20px;
}
</style> 