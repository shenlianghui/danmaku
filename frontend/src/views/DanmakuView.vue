<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <el-page-header @back="goBack">
      <template #content>
        <span class="text-large font-600 mr-3"> 弹幕查看: {{ pageTitle }} </span>
      </template>
      <template #extra>
        <div class="header-actions">
          <el-tooltip content="查看视频详情" placement="bottom">
            <el-button :icon="InfoFilled" circle @click="goToVideoDetail" />
          </el-tooltip>
          <el-tooltip content="弹幕分析" placement="bottom">
            <el-button type="success" :icon="DataLine" circle @click="goToAnalysis" />
          </el-tooltip>
        </div>
      </template>
    </el-page-header>

    <!-- 筛选器 -->
    <el-card shadow="never" class="filter-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><Filter /></el-icon> 筛选与排序</span>
        </div>
      </template>
      <el-form :model="filterForm" label-position="top">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="关键词">
              <el-input v-model="filterForm.keyword" placeholder="筛选弹幕内容" clearable @keyup.enter="applyFilter" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="排序方式">
              <el-select v-model="filterForm.ordering" placeholder="选择排序方式" style="width: 100%;" @change="applyFilter">
                <el-option label="视频时间 (升序)" value="progress"></el-option>
                <el-option label="视频时间 (降序)" value="-progress"></el-option>
                <el-option label="发送时间 (升序)" value="send_time"></el-option>
                <el-option label="发送时间 (降序)" value="-send_time"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="8">
             <el-form-item label="操作">
                <el-button type="primary" :icon="Search" @click="applyFilter">筛选</el-button>
                <el-button :icon="Close" @click="resetFilter">重置</el-button>
             </el-form-item>
          </el-col>
          <!-- 时间范围滑块可以放在这里，如果需要的话 -->
          <!-- <el-col :span="24"> ... </el-col> -->
        </el-row>
      </el-form>
    </el-card>

    <!-- 弹幕列表 -->
    <el-card shadow="never" class="danmaku-list-card">
       <template #header>
        <div class="card-header">
          <span><el-icon><ChatDotRound /></el-icon> 弹幕列表 ({{ totalDanmakus }} 条)</span>
          <el-tooltip content="刷新列表" placement="top">
            <el-button :icon="Refresh" circle @click="fetchDanmakus" :loading="loading" />
          </el-tooltip>
        </div>
      </template>
      <el-table
        :data="danmakus"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
        :default-sort="{ prop: 'progress', order: 'ascending' }" 
      >
        <template #empty>
          <el-empty description="当前条件下无弹幕数据" />
        </template>
        <el-table-column prop="progress" label="时间" width="100" sortable="custom" align="center">
          <template #default="scope">
            {{ formatProgress(scope.row.progress) }}
          </template>
        </el-table-column>
        <el-table-column prop="content" label="内容" min-width="300" show-overflow-tooltip></el-table-column>
        <el-table-column prop="send_time" label="发送时间" width="170" sortable="custom" align="center">
          <template #default="scope">
            {{ formatTime(scope.row.send_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="mode" label="模式" width="90" align="center">
          <template #default="scope">
            <el-tag size="small" effect="plain">{{ getDanmakuMode(scope.row.mode) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="颜色" width="90" align="center">
          <template #default="scope">
            <div style="display: flex; align-items: center; justify-content: center;">
              <span
                class="color-block"
                :style="{ backgroundColor: `#${scope.row.color.toString(16).padStart(6, '0')}` }"
              ></span>
              <span style="margin-left: 5px; font-size: 12px;">#{{ scope.row.color.toString(16).padStart(6, '0') }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="font_size" label="字号" width="80" align="center"></el-table-column>
      </el-table>

      <div class="pagination-container" v-if="totalDanmakus > pageSize">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalDanmakus"
          :page-size="pageSize"
          :current-page="currentPage"
          :page-sizes="[20, 50, 100, 200]" 
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          :pager-count="5"
        >
        </el-pagination>
      </div>
    </el-card>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { videoApi } from '@/api' // 假设 API 路径
import {
  Refresh,
  Filter,
  Search,
  Close,
  ChatDotRound,
  InfoFilled,
  DataLine
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

// 状态
const videoId = computed(() => route.params.id)
const video = ref({})
const danmakus = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50) // 默认页大小
const totalDanmakus = ref(0)

const filterForm = reactive({
  keyword: '',
  ordering: 'progress', // 默认按视频时间升序
})

// 计算属性
const pageTitle = computed(() => video.value?.title || '弹幕详情')

// 方法
const goBack = () => {
  // 尝试返回上一页，如果不行则返回视频列表
  if (window.history.length > 1) {
     router.go(-1);
  } else {
     router.push('/videos');
  }
}

const goToVideoDetail = () => {
  router.push(`/videos/${videoId.value}`)
}

const goToAnalysis = () => {
   if (video.value?.bvid) {
    router.push(`/analysis/${video.value.bvid}`)
  } else {
    ElMessage.warning('缺少视频 BV 号，无法跳转到分析页面')
  }
}

const fetchVideoInfo = async () => {
  if (!videoId.value) return
  try {
    const response = await videoApi.getVideo(videoId.value)
    video.value = response?.data || {}
  } catch (error) {
    console.error('获取视频信息失败:', error)
    // ElMessage.error(error.response?.data?.detail || '获取视频信息失败')
  }
}

const fetchDanmakus = async () => {
  if (!videoId.value) return
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      ordering: filterForm.ordering,
      search: filterForm.keyword, // 后端可能使用 search 而非 keyword
      // start: ..., // 如果需要时间范围筛选
      // end: ...
    }
    // 移除空参数
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })

    const response = await videoApi.getVideoDanmakus(videoId.value, params)
    danmakus.value = response?.data?.results || []
    totalDanmakus.value = response?.data?.count || 0
  } catch (error) {
    console.error('获取弹幕数据失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取弹幕数据失败')
    danmakus.value = []
    totalDanmakus.value = 0
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchDanmakus()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1 // 页大小改变时回到第一页
  fetchDanmakus()
}

const applyFilter = () => {
  currentPage.value = 1 // 筛选时回到第一页
  fetchDanmakus()
}

const resetFilter = () => {
  filterForm.keyword = ''
  filterForm.ordering = 'progress'
  currentPage.value = 1
  fetchDanmakus()
}

const formatTime = (time) => {
  if (!time) return '-'
  try {
    return new Date(time).toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return time
  }
}

const formatProgress = (ms) => {
   if (ms === null || ms === undefined) return '-';
   if (ms === 0) return '00:00';
   const totalSeconds = Math.floor(ms / 1000);
   const minutes = Math.floor(totalSeconds / 60);
   const seconds = totalSeconds % 60;
   return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

const getDanmakuMode = (mode) => {
  const modes = { 1: '滚动', 4: '底部', 5: '顶部', 7: '高级', 9: '特殊' }
  return modes[mode] || '未知'
}

// 监听排序变化 (如果使用 el-table 的 sort-change 事件)
// const handleSortChange = ({ prop, order }) => {
//   if (prop) {
//     filterForm.ordering = order === 'descending' ? `-${prop}` : prop;
//     fetchDanmakus();
//   }
// };

// 初始化加载
onMounted(() => {
  fetchVideoInfo() // 先获取视频信息，例如时长用于筛选
  fetchDanmakus()  // 再获取弹幕
})

</script>

<style scoped>
.page-container {
  padding: 20px;
}

.el-page-header {
  margin-bottom: 20px;
}

.header-actions .el-button + .el-button {
  margin-left: 8px;
}

.filter-card, .danmaku-list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header span {
  font-size: 1.1rem;
  font-weight: 600;
}
.card-header .el-icon {
  margin-right: 8px;
  vertical-align: middle;
}

/* 筛选表单项底部留白 */
.el-form--label-top .el-form-item {
  margin-bottom: 18px;
}

.el-table {
  margin-top: 15px;
}

:deep(.el-table th.el-table__cell) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

.color-block {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 1px solid #eee;
  vertical-align: middle;
  border-radius: 3px;
}

.pagination-container {
  margin-top: 25px;
  display: flex;
  justify-content: flex-end;
}
</style> 