<template>
  <div class="crawler-container">
    <el-card class="crawler-card">
      <template #header>
        <div class="card-header">
          <h2>弹幕爬取</h2>
          <el-button type="primary" @click="beforeAddTask">添加任务</el-button>
        </div>
      </template>
      
      <el-table 
        :data="tasks" 
        style="width: 100%" 
        v-loading="loading"
      >
        <el-table-column prop="id" label="任务ID" width="80"></el-table-column>
        <el-table-column prop="video_title" label="视频标题" min-width="200"></el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ getStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="danmaku_count" label="弹幕数量" width="100"></el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="scope">
            <span>{{ formatDate(scope.row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="完成时间" width="180">
          <template #default="scope">
            <span>{{ formatDate(scope.row.completed_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button 
              size="small" 
              @click="viewVideo(scope.row.video)"
            >
              查看视频
            </el-button>
            <el-button 
              size="small" 
              type="primary" 
              @click="analyzeVideo(scope.row.video)"
              :disabled="scope.row.status !== 'completed'"
            >
              分析弹幕
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="totalTasks"
          :page-size="pageSize"
          :current-page.sync="currentPage"
          @current-change="handlePageChange"
        >
        </el-pagination>
      </div>
    </el-card>
    
    <!-- 添加任务对话框 -->
    <el-dialog
      title="添加爬取任务"
      v-model="dialogVisible"
      width="500px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="视频URL" :rules="[{ required: true, message: '请输入视频URL或BV号', trigger: 'blur' }]">
          <el-input v-model="form.videoUrl" placeholder="请输入B站视频URL或BV号"></el-input>
        </el-form-item>
        <el-form-item label="Cookie">
          <el-input 
            v-model="form.cookieStr" 
            type="textarea" 
            placeholder="可选：输入Cookie以访问会员视频"
            :rows="3"
          ></el-input>
          <div class="form-tip">提示：B站Cookie可在浏览器开发者工具中获取</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitTask" :loading="submitting">
            提交任务
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { taskApi } from '@/api';
import { ElMessage } from 'element-plus';
import axios from 'axios';

export default {
  name: 'DanmakuCrawler',
  data() {
    return {
      tasks: [],
      loading: false,
      totalTasks: 0,
      pageSize: 20,
      currentPage: 1,
      dialogVisible: false,
      form: {
        videoUrl: '',
        cookieStr: ''
      },
      submitting: false,
      csrfReady: false,
      pendingTasks: new Set(), // 存储正在进行中的任务ID
      pollingTimer: null      // 轮询定时器
    }
  },
  mounted() {
    this.ensureCsrf();
  },
  beforeUnmount() {
    // 组件销毁时清除定时器
    this.clearPollingTimer();
  },
  methods: {
    // 确保获取CSRF令牌
    async ensureCsrf() {
      try {
        // 获取CSRF令牌
        const response = await axios.get('/api/accounts/csrf/', { 
          withCredentials: true 
        });
        this.csrfReady = true;
        console.log('已获取CSRF令牌:', response.status);
        
        // 获取令牌后加载任务列表
        this.fetchTasks();
      } catch (error) {
        console.error('获取CSRF令牌失败:', error);
        ElMessage.error('获取CSRF令牌失败，可能影响表单提交');
        // 尽管令牌获取失败，仍然尝试加载任务列表
        this.fetchTasks();
      }
    },
    
    // 在打开对话框前确保CSRF令牌已准备好
    beforeAddTask() {
      if (!this.csrfReady) {
        this.ensureCsrf().then(() => {
          this.dialogVisible = true;
        });
      } else {
        this.dialogVisible = true;
      }
    },
    
    async fetchTasks() {
      this.loading = true;
      console.log(`正在获取第 ${this.currentPage} 页数据，每页 ${this.pageSize} 条`);
      
      try {
        const params = {
          page: this.currentPage,
          page_size: this.pageSize
        };
        
        console.log('发送请求参数:', params);
        const response = await taskApi.getTasks(params);
        console.log('服务器响应:', response.data);
        
        // 检查响应数据结构并提取数据
        if (response.data && response.data.results) {
          // DRF 标准分页格式
          this.tasks = response.data.results;
          this.totalTasks = response.data.count;
          console.log(`获取到 ${this.tasks.length} 条数据，总共 ${this.totalTasks} 条`);
        } else if (Array.isArray(response.data)) {
          // 数组格式
          this.tasks = response.data;
          this.totalTasks = response.data.length;
          console.log(`获取到 ${this.tasks.length} 条数据，不分页`);
        } else {
          // 其他格式
          this.tasks = [];
          this.totalTasks = 0;
          console.error('意外的响应格式:', response.data);
        }
        
        // 检查是否有正在进行中的任务
        this.checkPendingTasks();
      } catch (error) {
        console.error('获取任务列表失败:', error);
        ElMessage.error('获取任务列表失败');
        this.tasks = [];
        this.totalTasks = 0;
      } finally {
        this.loading = false;
      }
    },
    
    // 检查是否有待处理的任务，启动轮询
    checkPendingTasks() {
      // 清空当前pendingTasks集合
      this.pendingTasks.clear();
      
      // 检查当前页的任务，找出处于pending或running状态的任务
      const hasPendingTasks = this.tasks.some(task => {
        if (task.status === 'pending' || task.status === 'running') {
          this.pendingTasks.add(task.id);
          return true;
        }
        return false;
      });
      
      // 如果有待处理任务，启动轮询
      if (hasPendingTasks) {
        this.startPollingTaskStatus();
      } else {
        this.clearPollingTimer();
      }
    },
    
    // 启动轮询检查任务状态
    startPollingTaskStatus() {
      // 先清除之前的定时器
      this.clearPollingTimer();
      
      // 设置新的定时器，每5秒查询一次
      this.pollingTimer = setInterval(async () => {
        if (this.pendingTasks.size === 0) {
          // 如果没有待处理任务，停止轮询
          this.clearPollingTimer();
          return;
        }
        
        try {
          // 重新获取任务列表
          await this.fetchTasks();
        } catch (error) {
          console.error('轮询任务状态失败:', error);
        }
      }, 5000); // 5秒轮询一次
    },
    
    // 清除轮询定时器
    clearPollingTimer() {
      if (this.pollingTimer) {
        clearInterval(this.pollingTimer);
        this.pollingTimer = null;
      }
    },
    
    getStatusType(status) {
      switch (status) {
        case 'completed':
          return 'success';
        case 'running':
          return 'warning';
        case 'pending':
          return 'info';
        case 'failed':
          return 'danger';
        default:
          return 'info';
      }
    },
    
    getStatusText(status) {
      switch (status) {
        case 'pending':
          return '等待中';
        case 'running':
          return '进行中';
        case 'completed':
          return '已完成';
        case 'failed':
          return '失败';
        default:
          return status;
      }
    },
    
    formatDate(dateStr) {
      if (!dateStr) return '-';
      const date = new Date(dateStr);
      return date.toLocaleString();
    },
    
    handlePageChange(page) {
      this.currentPage = page;
      this.fetchTasks();
    },
    
    async submitTask() {
      if (!this.form.videoUrl) {
        ElMessage.warning('请输入视频URL或BV号');
        return;
      }
      
      this.submitting = true;
      try {
        const response = await taskApi.createTask(this.form.videoUrl, this.form.cookieStr);
        ElMessage.success(response.data.message);
        this.dialogVisible = false;
        this.form.videoUrl = '';
        this.form.cookieStr = '';
        // 刷新任务列表
        await this.fetchTasks();
        // 添加任务成功后，确保启动轮询（因为新任务可能是pending状态）
        this.checkPendingTasks();
      } catch (error) {
        console.error('创建任务失败:', error);
        
        // 格式化错误消息
        let errorMessage = '创建任务失败，请检查URL是否正确';
        
        if (error.response) {
          if (error.response.data && error.response.data.message) {
            errorMessage = error.response.data.message;
          } else if (typeof error.response.data === 'string') {
            errorMessage = error.response.data;
          } else if (error.response.status === 403 && error.response.statusText === 'Forbidden') {
            errorMessage = 'CSRF验证失败，请刷新页面后重试';
            // CSRF失败时尝试重新获取令牌
            this.csrfReady = false;
            this.ensureCsrf();
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        ElMessage.error(errorMessage);
      } finally {
        this.submitting = false;
      }
    },
    
    viewVideo(videoId) {
      this.$router.push(`/videos/${videoId}`);
    },
    
    analyzeVideo(videoId) {
      this.$router.push(`/analysis?video=${videoId}`);
    }
  }
}
</script>

<style scoped>
.crawler-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style> 