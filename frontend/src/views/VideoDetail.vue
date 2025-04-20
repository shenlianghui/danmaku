<template>
  <div class="page-container fade-in">
    <!-- 页面头部 -->
    <div class="page-header">
      <el-page-header @back="goBack">
        <template #content>
          <span class="page-title"> {{ pageTitle }} </span>
        </template>
        <template #icon>
          <el-icon class="header-icon"><ArrowLeft /></el-icon>
        </template>
      </el-page-header>
    </div>

    <div class="video-detail-layout">
      <!-- 左侧视频信息卡片 -->
      <el-card shadow="hover" class="info-card bilibili-card" v-loading="loading">
        <template #header>
          <div class="card-header">
            <el-icon><VideoPlay /></el-icon>
            <span>视频基本信息</span>
          </div>
        </template>
        
        <template v-if="video.id">
          <div class="video-info">
            <div class="video-thumbnail">
              <img :src="getVideoCover(video.aid)" alt="视频封面" class="video-cover" v-if="video.aid">
              <div class="video-placeholder" v-else>
                <el-icon><Picture /></el-icon>
              </div>
            </div>
            
            <div class="video-meta">
              <h2 class="video-title">{{ video.title }}</h2>
              
              <div class="meta-items">
                <div class="meta-item">
                  <el-icon><VideoCamera /></el-icon>
                  <span>BV号: </span>
                  <el-link :href="`https://www.bilibili.com/video/${video.bvid}`" target="_blank" type="primary">
                    {{ video.bvid }} <el-icon><Link /></el-icon>
                  </el-link>
                </div>
                
                <div class="meta-item" v-if="video.aid">
                  <el-icon><Paperclip /></el-icon>
                  <span>AV号: {{ video.aid }}</span>
                </div>
                
                <div class="meta-item">
                  <el-icon><User /></el-icon>
                  <span>UP主: {{ video.owner }}</span>
                </div>
                
                <div class="meta-item" v-if="video.owner_mid">
                  <el-icon><UserFilled /></el-icon>
                  <span>UP主ID: {{ video.owner_mid }}</span>
                </div>
                
                <div class="meta-item">
                  <el-icon><Timer /></el-icon>
                  <span>视频时长: {{ formatDuration(video.duration) }}</span>
                </div>
                
                <div class="meta-item">
                  <el-icon><ChatDotRound /></el-icon>
                  <span>弹幕数量: {{ video.danmaku_count || 0 }}</span>
                </div>
                
                <div class="meta-item">
                  <el-icon><Calendar /></el-icon>
                  <span>最后爬取: {{ formatTime(video.last_crawled) }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button type="primary" :icon="ChatDotRound" @click="viewDanmaku" class="action-btn">
              查看弹幕
            </el-button>
            <el-button type="success" :icon="DataLine" @click="analyzeDanmaku" class="action-btn">
              弹幕分析
            </el-button>
            <el-button type="warning" :icon="RefreshRight" @click="crawlAgain" 
              :loading="crawling" class="action-btn">
              重新爬取
            </el-button>
          </div>
        </template>
        
        <el-empty v-else-if="!loading" description="未找到视频信息" />
      </el-card>
      
      <!-- 右侧爬取历史卡片 -->
      <el-card shadow="hover" class="history-card bilibili-card" v-loading="loadingTasks">
        <template #header>
          <div class="card-header">
            <el-icon><Tickets /></el-icon>
            <span>爬取历史</span>
          </div>
        </template>
        
        <el-table :data="tasks" style="width: 100%" stripe>
          <template #empty>
            <el-empty description="暂无爬取历史" />
          </template>
          <el-table-column prop="id" label="任务ID" width="80" align="center"></el-table-column>
          <el-table-column label="状态" width="110" align="center">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small" effect="light">
                <el-icon v-if="scope.row.status === 'running'" class="is-loading"><Loading /></el-icon>
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="danmaku_count" label="爬取数量" width="100" align="center">
            <template #default="scope">
              <span class="danmaku-count">{{ scope.row.danmaku_count || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="170" align="center">
            <template #default="scope">
              <span>{{ formatTime(scope.row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="完成时间" min-width="170" align="center">
            <template #default="scope">
              <span>{{ formatTime(scope.row.completed_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200" show-overflow-tooltip>
            <template #default="scope">
              <span v-if="scope.row.error_message" class="error-message">{{ scope.row.error_message }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { videoApi, taskApi } from '@/api'
import {
  ArrowLeft,
  VideoPlay,
  ChatDotRound,
  DataLine,
  RefreshRight,
  Tickets,
  Loading,
  Link,
  Calendar,
  Timer,
  UserFilled,
  Paperclip,
  User,
  Picture,
  VideoCamera
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 视频信息状态
const video = ref({})
const loading = ref(false)
const crawling = ref(false)
const videoId = computed(() => route.params.id)

// 任务列表状态
const tasks = ref([])
const loadingTasks = ref(false)

// 页面标题
const pageTitle = computed(() => video.value?.title || '视频详情')

// 获取视频封面
const getVideoCover = (aid) => {
  if (!aid) return '';
  return `https://images.weserv.nl/?url=https://pic.aixeir.cc/aid/${aid}.jpg&output=webp&q=70`;
}

// 返回上一页
const goBack = () => {
  router.push('/videos')
}

// 获取视频信息
const fetchVideoInfo = async () => {
  if (!videoId.value) return;
  loading.value = true
  try {
    const response = await videoApi.getVideo(videoId.value)
    video.value = response?.data || {}
  } catch (error) {
    console.error('获取视频信息失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取视频信息失败')
    video.value = {} // 清空
  } finally {
    loading.value = false
  }
}

// 获取任务历史
const fetchTasks = async () => {
  if (!videoId.value) return;
  loadingTasks.value = true
  try {
    // 添加user=current参数，明确获取当前用户的任务
    const response = await taskApi.getTasks({ 
      video: videoId.value, 
      page_size: 10,
      user: 'current' // 明确指定只获取当前用户的任务
    })
    tasks.value = response?.data?.results || []
  } catch (error) {
    console.error('获取任务列表失败:', error)
    // 此处不提示错误，避免干扰主信息
    tasks.value = []
  } finally {
    loadingTasks.value = false
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  try {
    return new Date(time).toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return time
  }
}

// 格式化时长
const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds === 0) return '00:00';
  const min = Math.floor(seconds / 60)
  const sec = Math.floor(seconds % 60)
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

// 任务状态样式
const getStatusType = (status) => {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

// 任务状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '进行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return status
  }
}

// 查看弹幕
const viewDanmaku = () => {
  router.push(`/danmaku/${videoId.value}`)
}

// 分析弹幕
const analyzeDanmaku = () => {
  if (video.value?.bvid) {
    router.push(`/analysis/${video.value.bvid}`)
  } else {
    ElMessage.warning('缺少视频 BV 号，无法跳转到分析页面')
  }
}

// 重新爬取
const crawlAgain = async () => {
  try {
    // 显示确认对话框，询问是否需要输入Cookie
    await ElMessageBox.confirm(
      '确定要重新爬取该视频的弹幕吗？这可能会覆盖现有数据。',
      '确认操作',
      {
        confirmButtonText: '确定爬取',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 弹出输入Cookie的对话框
    const { value: cookieStr } = await ElMessageBox.prompt(
      '如需爬取会员视频弹幕，请输入Cookie(可选)',
      'Cookie输入',
      {
        confirmButtonText: '开始爬取',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '可选：输入Cookie以访问会员视频',
        inputValue: '',
        showCancelButton: true,
        inputValidator: (value) => {
          // Cookie是可选的，所以不需要验证
          return true
        }
      }
    )
    
    crawling.value = true
    try {
      // 传递Cookie参数
      const response = await taskApi.createTask(video.value?.bvid || videoId.value, cookieStr)
      ElMessage.success({
        message: response?.data?.message || '已创建新的爬取任务',
        type: 'success',
        duration: 3000
      })
      // 刷新任务列表
      fetchTasks()
      // 延迟一段时间后刷新视频信息（可选）
      setTimeout(() => fetchVideoInfo(), 3000)
    } catch (error) {
      console.error('创建爬取任务失败:', error)
      ElMessage.error(error.response?.data?.message || error.response?.data?.detail || '创建爬取任务失败')
    } finally {
      crawling.value = false
    }
  } catch (err) {
    if (err !== 'cancel') {
      console.error('对话框操作失败:', err)
    }
  }
}

// 初始加载
onMounted(() => {
  fetchVideoInfo()
  fetchTasks()
})

// 监听路由参数变化，重新加载数据
watch(() => route.params.id, (newId) => {
  if (newId) {
    fetchVideoInfo()
    fetchTasks()
  }
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--grey-700);
}

.header-icon {
  margin-right: 8px;
  color: var(--primary-color);
}

.video-detail-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.info-card, .history-card {
  height: fit-content;
}

.card-header {
  display: flex;
  align-items: center;
  color: var(--grey-700);
  font-weight: 600;
}

.card-header .el-icon {
  margin-right: 8px;
  color: var(--primary-color);
}

.video-info {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.video-thumbnail {
  width: 160px;
  height: 100px;
  border-radius: var(--border-radius-small);
  overflow: hidden;
  flex-shrink: 0;
  background-color: var(--grey-200);
}

.video-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: var(--transition-base);
}

.video-cover:hover {
  transform: scale(1.05);
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--grey-400);
  font-size: 30px;
}

.video-meta {
  flex: 1;
}

.video-title {
  margin: 0 0 15px 0;
  color: var(--grey-700);
  font-size: 18px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  color: var(--grey-600);
  font-size: 14px;
}

.meta-item .el-icon {
  margin-right: 6px;
  font-size: 16px;
  color: var(--secondary-color);
}

.action-buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.action-btn {
  transition: var(--transition-base);
}

.action-btn:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-base);
}

.danmaku-count {
  font-weight: 600;
  color: var(--primary-color);
}

.error-message {
  color: var(--danger-color);
}

/* 响应式布局 */
@media (max-width: 992px) {
  .video-detail-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }
  
  .video-info {
    flex-direction: column;
  }
  
  .video-thumbnail {
    width: 100%;
    height: 200px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-btn {
    width: 100%;
  }
}
</style> 