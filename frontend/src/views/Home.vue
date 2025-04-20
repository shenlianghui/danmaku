<template>
  <div class="home-container">
    <!-- 欢迎区域 -->
    <el-row :gutter="20" class="welcome-section">
      <el-col :span="24">
        <el-card shadow="never">
          <h2>欢迎使用 B站弹幕分析系统!</h2>
          <p>在这里，您可以爬取 Bilibili 视频的弹幕数据，并进行深入分析。</p>
          <!-- 这里可以放一些统计数据，如果后端支持 -->
          <!--
          <el-descriptions title="系统概览" :column="3" border>
            <el-descriptions-item label="已收录视频">{{ stats.videoCount || '-' }}</el-descriptions-item>
            <el-descriptions-item label="总弹幕数">{{ stats.danmakuCount || '-' }}</el-descriptions-item>
            <el-descriptions-item label="进行中任务">{{ stats.runningTasks || '-' }}</el-descriptions-item>
          </el-descriptions>
          -->
        </el-card>
      </el-col>
    </el-row>

    <!-- 功能入口 -->
    <el-row :gutter="20" class="feature-section">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="goTo('/videos')">
          <div class="feature-content">
            <el-icon :size="40" color="#409EFF"><VideoCamera /></el-icon>
            <h3>视频管理</h3>
            <p>查看和管理已爬取的视频列表。</p>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="goTo('/crawler')">
          <div class="feature-content">
            <el-icon :size="40" color="#67C23A"><Download /></el-icon>
            <h3>弹幕爬取</h3>
            <p>根据视频链接爬取最新的弹幕数据。</p>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="goTo('/my-tasks')">
          <div class="feature-content">
            <el-icon :size="40" color="#909399"><List /></el-icon>
            <h3>我的任务</h3>
            <p>查看和管理您创建的爬取任务。</p>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="feature-card" @click="goTo('/analysis')">
          <div class="feature-content">
            <el-icon :size="40" color="#E6A23C"><DataLine /></el-icon>
            <h3>弹幕分析</h3>
            <p>对视频弹幕进行情感、关键词等分析。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { VideoCamera, Download, DataLine, List } from '@element-plus/icons-vue'
// import { getSystemStats } from '@/api' // 假设有获取统计数据的 API

const router = useRouter()

// 假设的统计数据
// const stats = ref({
//   videoCount: 0,
//   danmakuCount: 0,
//   runningTasks: 0
// })
// const loadingStats = ref(false)

// onMounted(async () => {
//   loadingStats.value = true;
//   try {
//     const response = await getSystemStats();
//     stats.value = response.data;
//   } catch (error) {
//     console.error("Failed to load system stats:", error);
//   } finally {
//     loadingStats.value = false;
//   }
// });

const goTo = (path) => {
  router.push(path)
}

</script>

<style scoped>
.home-container {
  padding: 30px;
}

.welcome-section {
  margin-bottom: 30px;
}

.welcome-section h2 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.8em;
  font-weight: 600;
}

.welcome-section p {
  color: #606266;
  line-height: 1.6;
}

.el-card {
  border: none; /* 移除卡片边框，更简洁 */
}

.feature-section {
  margin-bottom: 30px;
}

.feature-card {
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  height: 100%; /* 让卡片等高 */
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--el-box-shadow-light);
}

.feature-content {
  text-align: center;
  padding: 20px 10px;
}

.feature-content .el-icon {
  margin-bottom: 15px;
}

.feature-content h3 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 1.2em;
}

.feature-content p {
  color: #909399;
  font-size: 0.9em;
  line-height: 1.5;
}

/* 响应式调整卡片间距 */
@media (max-width: 768px) {
  .feature-section .el-col {
    margin-bottom: 20px;
  }
}

</style> 