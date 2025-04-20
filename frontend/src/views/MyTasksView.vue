<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的爬取任务</span>
          <el-tooltip content="刷新列表" placement="top">
            <el-button type="primary" :icon="Refresh" circle @click="fetchMyTasks" :loading="loading" />
          </el-tooltip>
        </div>
      </template>

      <el-table
        :data="tasks"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
      >
        <template #empty>
          <el-empty description="暂无爬取任务" />
        </template>
        <el-table-column label="任务ID" prop="id" width="80" align="center"></el-table-column>
        <el-table-column label="视频标题" min-width="250" show-overflow-tooltip>
          <template #default="scope">
            <el-link type="primary" @click="viewVideo(scope.row.video, scope.row.video_detail)" :underline="false">
              {{ scope.row.video_title || '未知视频' }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="BV号" width="130">
          <template #default="scope">
            {{ scope.row.video_detail ? scope.row.video_detail.bvid : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" size="small" effect="light">
              <el-icon v-if="scope.row.status === 'running'" class="is-loading"><Loading /></el-icon>
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="danmaku_count" label="弹幕数量" width="100" align="center"></el-table-column>
        <el-table-column label="创建时间" width="170" align="center">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="完成时间" width="170" align="center">
          <template #default="scope">
            {{ formatTime(scope.row.completed_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip></el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="scope">
            <el-tooltip content="查看视频" placement="top" v-if="scope.row.video">
              <el-button :icon="InfoFilled" size="small" circle @click="viewVideo(scope.row.video, scope.row.video_detail)"/>
            </el-tooltip>
            <el-tooltip content="查看弹幕" placement="top" v-if="scope.row.video && scope.row.status === 'completed'">
              <el-button :icon="ChatDotRound" size="small" type="primary" circle @click="viewDanmaku(scope.row.video)"/>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" v-if="totalTasks > pageSize">
        <el-pagination
          background
          layout="total, prev, pager, next, jumper"
          :total="totalTasks"
          :page-size="pageSize"
          :current-page="currentPage"
          @current-change="handlePageChange"
          :pager-count="5"
        >
        </el-pagination>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, ChatDotRound, InfoFilled, Loading } from '@element-plus/icons-vue'
import { videoApi, taskApi } from '@/api'

const router = useRouter()

const tasks = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)

// 获取当前用户的任务
const fetchMyTasks = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    // 使用专门的API端点获取当前用户的任务
    const response = await taskApi.getTasks(params)
    console.log('任务数据:', response.data);
    tasks.value = response.data.results || []
    totalTasks.value = response.data.count || 0
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败，请检查网络连接')
    tasks.value = []
    totalTasks.value = 0
  } finally {
    loading.value = false
  }
}

// 分页处理
const handlePageChange = (page) => {
  currentPage.value = page
  fetchMyTasks()
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

// 任务状态样式
const getStatusType = (status) => {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'warning'
    case 'pending': return 'info'
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

// 查看视频详情
const viewVideo = (videoId, videoDetail) => {
  // 如果有视频详情，可以直接导航
  router.push(`/videos/${videoId}`)
}

// 查看弹幕
const viewDanmaku = (videoId) => {
  router.push(`/danmaku/${videoId}`)
}

// 初始化
onMounted(() => {
  fetchMyTasks()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style> 