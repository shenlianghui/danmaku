<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>视频列表</span>
          <el-tooltip content="刷新列表" placement="top">
            <el-button type="primary" :icon="Refresh" circle @click="fetchVideos" :loading="loading" />
          </el-tooltip>
        </div>
      </template>

      <el-table
        :data="videos"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
      >
        <template #empty>
          <el-empty description="暂无视频数据" />
        </template>
        <el-table-column prop="title" label="视频标题" min-width="250" show-overflow-tooltip>
          <template #default="scope">
            <el-link type="primary" @click="viewVideo(scope.row)" :underline="false">
              {{ scope.row.title }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="bvid" label="BV号" width="130"></el-table-column>
        <el-table-column prop="owner" label="UP主" width="150" show-overflow-tooltip></el-table-column>
        <el-table-column prop="danmaku_count" label="弹幕数量" width="100" align="center"></el-table-column>
        <el-table-column label="最后爬取时间" width="170" align="center">
          <template #default="scope">
            {{ formatTime(scope.row.last_crawled) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-tooltip content="查看弹幕" placement="top">
              <el-button :icon="ChatDotRound" size="small" type="primary" circle @click="viewDanmaku(scope.row)"/>
            </el-tooltip>
            <el-tooltip content="弹幕分析" placement="top">
              <el-button :icon="DataLine" size="small" type="success" circle @click="analyzeDanmaku(scope.row)"/>
            </el-tooltip>
             <el-tooltip content="查看详情" placement="top">
              <el-button :icon="InfoFilled" size="small" circle @click="viewVideo(scope.row)"/>
            </el-tooltip>
            <!-- 可以考虑添加删除等操作 -->
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" v-if="totalVideos > pageSize"> <!-- 只有总数大于每页数量时显示分页 -->
        <el-pagination
          background
          layout="total, prev, pager, next, jumper"
          :total="totalVideos"
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
import { Refresh, ChatDotRound, DataLine, InfoFilled } from '@element-plus/icons-vue'
import { videoApi } from '@/api' // 假设 API 路径

const router = useRouter()

const videos = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10) // 每页显示数量
const totalVideos = ref(0)

const fetchVideos = async () => {
  loading.value = true
  try {
    const response = await videoApi.getVideos({ page: currentPage.value, page_size: pageSize.value })
    // 确保返回的数据结构正确
    videos.value = response?.data?.results || []
    totalVideos.value = response?.data?.count || 0
  } catch (error) {
    console.error('获取视频列表失败:', error)
    ElMessage.error( error.response?.data?.detail || '获取视频列表失败')
    videos.value = [] // 出错时清空列表
    totalVideos.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchVideos()
})

const formatTime = (time) => {
  if (!time) return '-'
  // 可以考虑使用更友好的时间格式库，如 dayjs
  try {
    return new Date(time).toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return time // 如果格式化失败，返回原始字符串
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchVideos()
}

const viewVideo = (video) => {
  router.push(`/videos/${video.id}`)
}

const viewDanmaku = (video) => {
  router.push(`/danmaku/${video.id}`)
}

const analyzeDanmaku = (video) => {
  router.push(`/analysis/${video.bvid}`)
}
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
.card-header span {
  font-size: 1.1rem; /* 调整标题字体大小 */
  font-weight: 600;
}

.el-table {
  margin-top: 15px;
}

/* 优化表头样式 */
:deep(.el-table th.el-table__cell) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

/* 修正 show-overflow-tooltip 和 el-link 结合的问题 */
:deep(.el-table .el-table__cell .cell) {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.el-link {
  font-weight: normal; /* 链接文字不需要加粗 */
  font-size: inherit; /* 继承表格字体大小 */
}

.pagination-container {
  margin-top: 25px;
  display: flex;
  justify-content: flex-end; /* 分页居右 */
}

/* 操作按钮间距 */
.el-table-column .el-button + .el-button {
  margin-left: 8px;
}
</style> 