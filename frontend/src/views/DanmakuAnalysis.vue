<template>
  <div class="analysis-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>弹幕分析</h2>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px">
        <el-form-item label="视频选择">
          <el-select 
            v-model="form.videoId" 
            placeholder="请选择要分析的视频" 
            filterable 
            remote
            :remote-method="searchVideos"
            :loading="loadingVideos"
            style="width: 100%"
          >
            <el-option 
              v-for="item in videos" 
              :key="item.id" 
              :label="item.title" 
              :value="item.id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span style="margin-right: 15px">{{ item.title }}</span>
                <span style="color: #8492a6; font-size: 13px">{{ item.bvid }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="分析类型">
          <el-radio-group v-model="form.analysisType">
            <el-radio value="keyword">关键词分析</el-radio>
            <el-radio value="sentiment">情感分析</el-radio>
            <el-radio value="timeline">时间线分析</el-radio>
            <el-radio value="user">用户分析</el-radio>
            <el-radio value="all">
              <span class="all-analysis">全部分析</span>
              <el-tooltip content="一键执行所有分析项目" placement="top">
                <el-icon><InfoFilled /></el-icon>
              </el-tooltip>
            </el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="startAnalysis" :loading="analyzing">
            {{ form.analysisType === 'all' ? '开始全面分析' : '开始分析' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <el-divider content-position="center">最近分析</el-divider>
      
      <div v-loading="loadingAnalyses">
        <el-table :data="analyses" style="width: 100%">
          <el-table-column prop="video_title" label="视频标题" min-width="200"></el-table-column>
          <el-table-column prop="analysis_type" label="分析类型" width="120">
            <template #default="scope">
              <el-tag :type="getAnalysisTypeTag(scope.row.analysis_type)">
                {{ getAnalysisTypeText(scope.row.analysis_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button type="primary" size="small" @click="viewAnalysis(scope.row)">
                查看结果
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="empty-block" v-if="analyses.length === 0 && !loadingAnalyses">
          <el-empty description="暂无分析记录"></el-empty>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
import { videoApi, analysisApi } from '@/api';
import { InfoFilled } from '@element-plus/icons-vue';

export default {
  name: 'DanmakuAnalysis',
  components: {
    InfoFilled
  },
  data() {
    return {
      form: {
        videoId: '',
        analysisType: 'keyword'
      },
      videos: [],
      analyses: [],
      loadingVideos: false,
      loadingAnalyses: false,
      analyzing: false
    };
  },
  mounted() {
    this.fetchAnalyses();
    this.fetchRecentVideos();
  },
  methods: {
    searchVideos(query) {
      if (query) {
        this.loadingVideos = true;
        videoApi.getVideos({ search: query })
          .then(response => {
            this.videos = response.data.results;
          })
          .catch(error => {
            console.error('搜索视频失败:', error);
          })
          .finally(() => {
            this.loadingVideos = false;
          });
      } else {
        this.fetchRecentVideos();
      }
    },
    fetchRecentVideos() {
      this.loadingVideos = true;
      videoApi.getVideos()
        .then(response => {
          this.videos = response.data.results;
        })
        .catch(error => {
          console.error('获取视频列表失败:', error);
        })
        .finally(() => {
          this.loadingVideos = false;
        });
    },
    fetchAnalyses() {
      this.loadingAnalyses = true;
      analysisApi.getAnalyses()
        .then(response => {
          const analysisResults = response.data.results;
          
          // 先保存分析结果
          this.analyses = analysisResults;
          
          // 如果有分析记录，则获取对应的视频标题
          if (analysisResults && analysisResults.length > 0) {
            // 收集所有不重复的视频BVID
            const bvidSet = new Set();
            analysisResults.forEach(analysis => {
              if (analysis.video_bvid) {
                bvidSet.add(analysis.video_bvid);
              }
            });
            
            // 将Set转为数组
            const bvidList = Array.from(bvidSet);
            
            // 为每个BVID获取视频信息
            const videoPromises = bvidList.map(bvid => 
              videoApi.getVideoByBvid(bvid)
                .then(resp => ({ bvid, title: resp.data.title }))
                .catch(() => ({ bvid, title: `未知视频(${bvid})` }))  // 获取失败时设置默认标题
            );
            
            // 等待所有视频信息请求完成
            Promise.all(videoPromises)
              .then(videoInfos => {
                // 创建BVID到标题的映射
                const bvidToTitleMap = {};
                videoInfos.forEach(info => {
                  bvidToTitleMap[info.bvid] = info.title;
                });
                
                // 更新分析记录，添加视频标题
                this.analyses = this.analyses.map(analysis => ({
                  ...analysis,
                  video_title: bvidToTitleMap[analysis.video_bvid] || `未知视频(${analysis.video_bvid})`
                }));
              })
              .catch(error => {
                console.error('获取视频信息失败:', error);
              });
          }
        })
        .catch(error => {
          console.error('获取分析记录失败:', error);
        })
        .finally(() => {
          this.loadingAnalyses = false;
        });
    },
    startAnalysis() {
      if (!this.form.videoId) {
        this.$message.warning('请选择要分析的视频');
        return;
      }
      
      this.analyzing = true;
      
      // 先获取视频信息
      videoApi.getVideo(this.form.videoId)
        .then(response => {
          const video = response.data;
          
          if (!video || !video.bvid) {
            throw new Error('无法获取视频BV号');
          }
          
          console.log(`准备分析视频: ${video.title}, BVID: ${video.bvid}, 分析类型: ${this.form.analysisType}`);
          
          const isFullAnalysis = this.form.analysisType === 'all';
          const message = isFullAnalysis ? '正在进行全面分析，请耐心等待...' : '正在进行分析，请稍候...';
          this.$message({
            message: message,
            type: 'info',
            duration: 3000
          });
          
          // 开始分析
          return analysisApi.analyze(video.bvid, this.form.analysisType);
        })
        .then(response => {
          console.log('分析完成:', response.data);
          const isFullAnalysis = this.form.analysisType === 'all';
          const message = isFullAnalysis ? '全面分析完成' : '分析完成';
          this.$message.success(message);
          this.fetchAnalyses();
          
          // 获取刚刚创建的分析记录，跳转到结果页面
          setTimeout(() => {
            this.fetchAnalyses(); // 再次获取最新的分析结果
            setTimeout(() => {
              const latestAnalysis = this.analyses[0];
              if (latestAnalysis) {
                this.viewAnalysis(latestAnalysis);
              }
            }, 500);
          }, 1000);
        })
        .catch(error => {
          console.error('分析失败:', error);
          
          let errorMsg = '分析失败';
          
          // 尝试提取更详细的错误信息
          if (error.response && error.response.data) {
            if (error.response.data.message) {
              errorMsg = error.response.data.message;
            } else if (typeof error.response.data === 'string') {
              errorMsg = error.response.data;
            }
          } else if (error.message) {
            errorMsg = error.message;
          }
          
          this.$message.error(errorMsg);
        })
        .finally(() => {
          this.analyzing = false;
        });
    },
    viewAnalysis(analysis) {
      // 检查分析对象是否有效
      if (!analysis) {
        console.error('无效的分析对象');
        this.$message.error('无法查看分析结果：数据无效');
        return;
      }
      
      // 检查视频bvid是否存在
      if (!analysis.video_bvid) {
        console.error('分析对象缺少视频BVID:', analysis);
        this.$message.error('无法查看分析结果：无法获取视频标识符');
        return;
      }
      
      console.log(`跳转到分析结果页面，BVID: ${analysis.video_bvid}`);
      this.$router.push(`/analysis/${analysis.video_bvid}`);
    },
    formatTime(time) {
      if (!time) return '-';
      return new Date(time).toLocaleString();
    },
    getAnalysisTypeTag(type) {
      const types = {
        'keyword': 'primary',
        'sentiment': 'success',
        'timeline': 'info',
        'user': 'warning',
        'all': 'danger'
      };
      return types[type] || 'info';
    },
    getAnalysisTypeText(type) {
      const texts = {
        'keyword': '关键词',
        'sentiment': '情感',
        'timeline': '时间线',
        'user': '用户',
        'all': '全部分析'
      };
      return texts[type] || type;
    }
  }
};
</script>

<style scoped>
.analysis-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.empty-block {
  margin: 20px 0;
}

.el-divider {
  margin: 30px 0;
}

.all-analysis {
  margin-right: 5px;
  font-weight: bold;
}
</style>
