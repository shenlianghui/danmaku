<template>
  <div class="analysis-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>弹幕分析</h2>
        </div>
      </template>

      <el-form :model="form" label-width="120px" ref="analysisFormRef">
        <el-form-item label="视频选择" prop="videoId" :rules="[{ required: true, message: '请选择要分析的视频', trigger: 'change' }]">
          <el-select
            v-model="form.videoId"
            placeholder="请选择或搜索要分析的视频"
            filterable
            remote
            :remote-method="searchVideos"
            :loading="loadingVideos"
            style="width: 100%"
            clearable
            @clear="form.videoId = ''"
          >
            <el-option
              v-for="item in videos"
              :key="item.id"
              :label="item.title"
              :value="item.id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="margin-right: 15px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ item.title }}</span>
                <span style="color: #8492a6; font-size: 13px">{{ item.bvid }}</span>
              </div>
            </el-option>
            <template #empty v-if="loadingVideos">
              <div style="text-align: center; padding: 10px;">
                <el-icon class="is-loading"><Loading /></el-icon> 正在加载...
              </div>
            </template>
             <template #empty v-else>
              <div style="text-align: center; padding: 10px;">
                无匹配视频或暂无已爬取视频
              </div>
            </template>
          </el-select>
        </el-form-item>

        <el-form-item label="分析类型" prop="analysisType" :rules="[{ required: true, message: '请选择分析类型', trigger: 'change' }]">
          <el-radio-group v-model="form.analysisType">
            <el-radio value="keyword">关键词分析</el-radio>
            <el-radio value="sentiment">情感分析</el-radio>
            <el-radio value="timeline">时间线分析</el-radio>
            <el-radio value="user">用户分析</el-radio>
            <el-radio value="all">
              <span class="all-analysis">全部分析</span>
              <el-tooltip content="一键执行所有分析项目，可能耗时较长" placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="startAnalysis" :loading="analyzing" :disabled="!form.videoId">
            {{ form.analysisType === 'all' ? '开始全面分析' : '开始分析' }}
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider content-position="center">最近分析记录</el-divider>

      <div v-loading="loadingAnalyses">
        <el-table :data="analyses" style="width: 100%">
          <el-table-column prop="video_title" label="视频标题" min-width="200" show-overflow-tooltip></el-table-column>
          <el-table-column prop="analysis_type" label="分析类型" width="120">
            <template #default="scope">
              <el-tag :type="getAnalysisTypeTag(scope.row.analysis_type)">
                {{ getAnalysisTypeText(scope.row.analysis_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="分析时间" width="180"> <!-- Changed from created_at to updated_at -->
            <template #default="scope">
              {{ formatTime(scope.row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="center">
            <template #default="scope">
              <el-button type="primary" size="small" @click="viewAnalysis(scope.row)">
                查看结果
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="empty-block" v-if="!analyses.length && !loadingAnalyses">
          <el-empty description="暂无分析记录"></el-empty>
        </div>
        <el-pagination
          v-if="totalAnalyses > analysesPageSize"
          style="margin-top: 20px; display: flex; justify-content: center;"
          background
          layout="total, prev, pager, next"
          :total="totalAnalyses"
          :page-size="analysesPageSize"
          :current-page.sync="analysesCurrentPage"
          @current-change="handleAnalysesPageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { videoApi, analysisApi } from '@/api';
import { ElMessage } from 'element-plus';
import { InfoFilled, Loading } from '@element-plus/icons-vue';

export default {
  name: 'DanmakuAnalysis',
  components: {
    InfoFilled,
    Loading,
  },
  data() {
    return {
      form: {
        videoId: '', // Stores the DB ID of the selected video
        analysisType: 'keyword'
      },
      analysisFormRef: null, // For form validation
      videos: [],
      analyses: [],
      loadingVideos: false,
      loadingAnalyses: false,
      analyzing: false,

      analysesCurrentPage: 1,
      analysesPageSize: 10,
      totalAnalyses: 0,
    };
  },
  mounted() {
    this.fetchAnalyses();
    this.fetchRecentVideos(); // Load some initial videos for the dropdown
  },
  methods: {
    async searchVideos(query) {
      if (query) {
        this.loadingVideos = true;
        try {
          // Assuming getVideos can take a search query
          const response = await videoApi.getVideos({ search: query, page_size: 20 }); // limit results
          this.videos = response.data.results || [];
        } catch (error) {
          console.error('搜索视频失败:', error);
          this.videos = [];
        } finally {
          this.loadingVideos = false;
        }
      } else {
        // If query is empty, load recent videos or clear the list
        this.fetchRecentVideos();
      }
    },
    async fetchRecentVideos() {
      this.loadingVideos = true;
      try {
        // Fetch a small number of recent videos for initial display
        const response = await videoApi.getVideos({ page_size: 10, ordering: '-last_crawled' });
        this.videos = response.data.results || [];
      } catch (error) {
        console.error('获取最近视频列表失败:', error);
        this.videos = [];
      } finally {
        this.loadingVideos = false;
      }
    },
    async fetchAnalyses() {
      this.loadingAnalyses = true;
      try {
        const params = {
          page: this.analysesCurrentPage,
          page_size: this.analysesPageSize,
        };
        const response = await analysisApi.getAnalyses(null, null, params);
        const analysisResults = response.data.results || [];
        this.totalAnalyses = response.data.count || 0;

        if (analysisResults.length > 0) {
          // 从分析结果中提取所有唯一的、非空的 BVID
          const bvidSet = new Set(
            analysisResults.map(a => a.video_bvid).filter(bvid => bvid && typeof bvid === 'string' && bvid.trim() !== '')
          );
          const bvidList = Array.from(bvidSet);
          
          const videoDetailsMap = new Map();

          if (bvidList.length > 0) {
            console.log('需要获取标题的BVID列表:', bvidList);
            // 为列表中的每个BVID独立获取视频信息
            // Promise.allSettled 确保即使某个BVID查找失败，其他成功的也能继续
            const videoPromises = bvidList.map(bvid =>
              videoApi.getVideoByBvid(bvid)
                .then(resp => {
                  // 确保 resp 和 resp.data 存在
                  if (resp && resp.data && resp.data.title) {
                    console.log(`成功获取BVID ${bvid} 的标题: ${resp.data.title}`);
                    return { bvid, title: resp.data.title };
                  } else {
                    console.warn(`BVID ${bvid} 的响应数据格式不正确:`, resp);
                    return { bvid, title: `标题加载失败 (${bvid})` };
                  }
                })
                .catch((error) => {
                  console.error(`获取BVID ${bvid} 标题失败:`, error);
                  return { bvid, title: `未知视频 (${bvid})` }; // 错误回退
                })
            );

            // 使用 Promise.allSettled 来处理可能存在的个别API调用失败
            const settledVideoInfos = await Promise.allSettled(videoPromises);
            
            settledVideoInfos.forEach(result => {
              if (result.status === 'fulfilled' && result.value) {
                videoDetailsMap.set(result.value.bvid, result.value.title);
              } else if (result.status === 'rejected') {
                // 理论上 .catch 已经处理了，但以防万一
                console.error('一个getVideoByBvid的Promise被拒绝:', result.reason);
              }
            });
          }
          
          // 更新分析记录，添加正确的视频标题
          this.analyses = analysisResults.map(analysis => ({
            ...analysis,
            video_title: videoDetailsMap.get(analysis.video_bvid) || `标题信息待加载 (${analysis.video_bvid || '未知BVID'})`
          }));

        } else {
          this.analyses = [];
        }
      } catch (error) {
        console.error('获取分析记录失败:', error);
        ElMessage.error('获取分析记录失败');
        this.analyses = [];
        this.totalAnalyses = 0;
      } finally {
        this.loadingAnalyses = false;
      }
    },
    handleAnalysesPageChange(page) {
      this.analysesCurrentPage = page;
      this.fetchAnalyses();
    },
    async startAnalysis() {
      // Validate form first if you have `analysisFormRef` set up for el-form
      // const isValid = await this.$refs.analysisFormRef.validate();
      // if (!isValid) return;

      if (!this.form.videoId) {
        ElMessage.warning('请选择要分析的视频');
        return;
      }

      this.analyzing = true;
      let bvidForAnalysisAndNavigation = '';

      try {
        // 1. Get the video details (including BVID) using the selected database ID
        const videoResponse = await videoApi.getVideo(this.form.videoId);
        const videoToAnalyze = videoResponse.data;

        if (!videoToAnalyze || !videoToAnalyze.bvid) {
          throw new Error('无法获取视频BV号，请确保视频已正确爬取且信息完整。');
        }
        bvidForAnalysisAndNavigation = videoToAnalyze.bvid;

        console.log(`准备分析视频: ${videoToAnalyze.title}, BVID: ${bvidForAnalysisAndNavigation}, 分析类型: ${this.form.analysisType}`);

        const isFullAnalysis = this.form.analysisType === 'all';
        const loadingMessage = isFullAnalysis ? '正在进行全面分析，这可能需要一些时间，请耐心等待...' : '正在进行分析，请稍候...';
        
        ElMessage({
          message: loadingMessage,
          type: 'info',
          duration: isFullAnalysis ? 7000 : 4000, // Longer duration for full analysis message
          showClose: true,
        });

        // 2. Call the analysis API with the correct BVID
        const analysisApiResponse = await analysisApi.analyze(bvidForAnalysisAndNavigation, this.form.analysisType);
        console.log('分析API响应:', analysisApiResponse.data);

        const successMessage = (isFullAnalysis ? '全面分析完成！' : '分析完成！') + (analysisApiResponse.data.cached ? ' (使用了缓存结果)' : '');
        ElMessage.success({message: successMessage, duration: 5000});

        // 3. Navigate directly using the BVID of the video that was targeted.
        if (bvidForAnalysisAndNavigation) {
          console.log(`分析成功，正在跳转到分析结果页面 BVID: ${bvidForAnalysisAndNavigation}`);
          // Add a slight delay for the message to be seen before navigation
          setTimeout(() => {
            this.$router.push(`/analysis/${bvidForAnalysisAndNavigation}`);
          }, 1000);
        } else {
          console.error("无法导航：bvidForAnalysisAndNavigation 为空。");
          ElMessage.error("分析已完成，但无法自动跳转到结果页面。请从下方列表查看。");
          this.fetchAnalyses(); // Refresh list so user can find it
        }
      } catch (error) {
        console.error('分析过程中发生错误:', error);
        let errorMsg = '分析失败，请稍后重试。';
        if (error.response && error.response.data) {
          if (error.response.data.message) {
            errorMsg = `分析失败: ${error.response.data.message}`;
          } else if (typeof error.response.data.error === 'string') {
            errorMsg = `分析失败: ${error.response.data.error}`;
          } else if (typeof error.response.data === 'string') {
             errorMsg = `分析失败: ${error.response.data}`;
          }
        } else if (error.message) {
          errorMsg = error.message.startsWith('无法获取视频BV号') ? error.message : `分析请求错误: ${error.message}`;
        }
        ElMessage.error({message: errorMsg, duration: 5000, showClose: true});
        this.fetchAnalyses(); // Also refresh list on error, in case a partial record was made
      } finally {
        this.analyzing = false;
      }
    },
    viewAnalysis(analysis) {
      if (!analysis || !analysis.video_bvid) {
        ElMessage.error('无法查看分析结果：视频标识符(BVID)缺失。');
        console.error('viewAnalysis - 无效的分析对象或缺少 video_bvid:', analysis);
        return;
      }
      console.log(`从表格查看分析结果，BVID: ${analysis.video_bvid}`);
      this.$router.push(`/analysis/${analysis.video_bvid}`);
    },
    formatTime(time) {
      if (!time) return '-';
      try {
        return new Date(time).toLocaleString('zh-CN', {
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          hour12: false
        });
      } catch (e) {
        return time;
      }
    },
    getAnalysisTypeTag(type) {
      const types = {
        'keyword': 'primary',
        'sentiment': 'success',
        'timeline': 'info',
        'user': 'warning',
        'all': 'danger' // Using danger for 'all' to make it stand out
      };
      return types[type] || 'default';
    },
    getAnalysisTypeText(type) {
      const texts = {
        'keyword': '关键词',
        'sentiment': '情感',
        'timeline': '时间线',
        'user': '用户',
        'all': '全部分析'
      };
      return texts[type] || type.charAt(0).toUpperCase() + type.slice(1);
    }
  }
};
</script>

<style scoped>
.analysis-container {
  max-width: 900px; /* Slightly wider for better layout */
  margin: 20px auto; /* Added top/bottom margin */
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header h2 {
  margin: 0;
  font-size: 1.2rem;
}

.el-form-item {
  margin-bottom: 22px; /* Standardize margin */
}

.el-select {
  width: 100%; /* Make select full width */
}

.el-radio-group {
  display: flex;
  flex-wrap: wrap; /* Allow radios to wrap on smaller screens */
  gap: 10px;
}
.el-radio {
  margin-right: 15px; /* Add some space between radios */
}

.all-analysis {
  margin-right: 5px;
  font-weight: bold;
}

.empty-block {
  margin: 20px 0;
}

.el-divider {
  margin: 30px 0;
}

.el-table {
  margin-top: 15px;
}

:deep(.el-table th.el-table__cell) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}
</style>