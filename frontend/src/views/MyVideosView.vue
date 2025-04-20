<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的视频</span>
          <div class="header-actions">
            <el-tooltip content="爬取新视频" placement="top">
              <el-button type="primary" :icon="Plus" @click="showCrawlDialog" />
            </el-tooltip>
            <el-tooltip content="刷新列表" placement="top">
              <el-button type="info" :icon="Refresh" @click="fetchMyVideos" :loading="loading" />
            </el-tooltip>
          </div>
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
        <el-table-column label="操作" width="210" align="center" fixed="right">
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
            <el-tooltip content="重新爬取" placement="top">
              <el-button :icon="RefreshRight" size="small" type="warning" circle @click="crawlAgain(scope.row)"/>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" v-if="totalVideos > pageSize">
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

    <!-- 爬取新视频对话框 -->
    <el-dialog
      title="爬取新视频"
      v-model="crawlDialogVisible"
      width="500px"
    >
      <el-form :model="crawlForm" ref="crawlFormRef" label-width="100px">
        <el-form-item label="视频URL" prop="video_url" :rules="[{ required: true, message: '请输入B站视频URL', trigger: 'blur' }]">
          <el-input v-model="crawlForm.video_url" placeholder="输入B站视频链接，例如：https://www.bilibili.com/video/BV1xx411c7mD"></el-input>
        </el-form-item>
        <el-form-item label="Cookie" prop="cookie">
          <el-input 
            v-model="crawlForm.cookie" 
            type="textarea" 
            placeholder="可选：输入Cookie以访问会员视频"
            :rows="3"
          ></el-input>
          <div class="form-tip">提示：B站Cookie可在浏览器开发者工具中获取</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="crawlDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitCrawl" :loading="crawling">开始爬取</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Refresh, 
  ChatDotRound, 
  DataLine, 
  InfoFilled, 
  RefreshRight,
  Plus
} from '@element-plus/icons-vue'
import { videoApi } from '@/api'

const router = useRouter()

const videos = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const totalVideos = ref(0)

// 爬取相关
const crawlDialogVisible = ref(false)
const crawlForm = ref({
  video_url: '',
  cookie: ''
})
const crawlFormRef = ref(null)
const crawling = ref(false)

// 获取当前用户的视频
const fetchMyVideos = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    // 使用专门的API端点获取当前用户的视频
    const response = await videoApi.getMyVideos(params)
    videos.value = response.data.results || []
    totalVideos.value = response.data.count || 0
  } catch (error) {
    console.error('获取视频列表失败:', error)
    ElMessage.error('获取视频列表失败，请检查网络连接')
    videos.value = []
    totalVideos.value = 0
  } finally {
    loading.value = false
  }
}

// 分页处理
const handlePageChange = (page) => {
  currentPage.value = page
  fetchMyVideos()
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

// 查看视频详情
const viewVideo = (video) => {
  router.push(`/videos/${video.id}`)
}

// 查看弹幕
const viewDanmaku = (video) => {
  router.push(`/danmaku/${video.id}`)
}

// 分析弹幕
const analyzeDanmaku = (video) => {
  if (video.bvid) {
    router.push(`/analysis/${video.bvid}`)
  } else {
    ElMessage.warning('缺少视频 BV 号，无法跳转到分析页面')
  }
}

// 显示爬取对话框
const showCrawlDialog = () => {
  crawlForm.value = {
    video_url: '',
    cookie: ''
  }
  crawlDialogVisible.value = true
}

// 提交爬取请求
const submitCrawl = async () => {
  if (!crawlFormRef.value) return
  
  await crawlFormRef.value.validate(async (valid) => {
    if (valid) {
      crawling.value = true
      try {
        const response = await videoApi.createCrawlTask({
          video_url: crawlForm.value.video_url,
          cookie: crawlForm.value.cookie || null
        })
        
        ElMessage.success(`已开始爬取: ${response.data.message}`)
        crawlDialogVisible.value = false
        
        // 延迟刷新列表，等待爬取任务启动
        setTimeout(() => {
          fetchMyVideos()
        }, 2000)
      } catch (error) {
        console.error('爬取请求失败:', error)
        ElMessage.error(error.response?.data?.message || '爬取请求失败')
      } finally {
        crawling.value = false
      }
    }
  })
}

// 重新爬取
const crawlAgain = async (video) => {
  try {
    await ElMessageBox.confirm(
      '确定要重新爬取该视频的弹幕吗？这可能会覆盖现有数据。',
      '确认操作',
      {
        confirmButtonText: '确定爬取',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    crawling.value = true
    try {
      const response = await videoApi.crawlVideoDanmakus(video.id)
      ElMessage.success(response.data.message || '爬取任务已创建')
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '创建爬取任务失败')
    } finally {
      crawling.value = false
    }
  } catch {
    // 用户取消，不做任何操作
  }
}

// 初始化
onMounted(() => {
  fetchMyVideos()
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

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style> 