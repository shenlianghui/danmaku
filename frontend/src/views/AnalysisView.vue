<template>
  <div class="analysis-view-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-page-header @back="goBack" :content="videoTitle"></el-page-header>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="video-info">
      <el-col :span="24">
        <el-card>
          <div class="video-info-header">
            <h2>视频信息</h2>
          </div>
          <el-descriptions :column="3" border v-loading="loadingVideo">
            <el-descriptions-item label="视频标题">{{ video.title }}</el-descriptions-item>
            <el-descriptions-item label="BV号">{{ video.bvid }}</el-descriptions-item>
            <el-descriptions-item label="AV号">{{ video.aid }}</el-descriptions-item>
            <el-descriptions-item label="UP主">{{ video.owner }}</el-descriptions-item>
            <el-descriptions-item label="弹幕数量">{{ video.danmaku_count }}</el-descriptions-item>
            <el-descriptions-item label="视频时长">{{ formatDuration(video.duration * 1000) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="analysis-controls">
      <el-col :span="24">
        <el-card>
          <div class="actions-header">
            <h2>分析控制</h2>
          </div>
          <div class="analysis-options">
            <el-checkbox-group v-model="selectedAnalysisOptions">
              <el-checkbox label="emotion">情感分析</el-checkbox>
              <el-checkbox label="keyword">关键词提取</el-checkbox>
              <el-checkbox label="topic">话题聚类</el-checkbox>
              <el-checkbox label="timeline">时间线分析</el-checkbox>
            </el-checkbox-group>
          </div>
          <div class="action-buttons">
            <el-button type="primary" @click="runAllAnalysis" :loading="isAnalyzing" :disabled="!danmakuData || !danmakuData.length || selectedAnalysisOptions.length === 0">一键分析</el-button>
            <el-tooltip content="采用简化模型，处理速度更快" placement="top">
              <el-checkbox v-model="useSimpleMode" class="simple-mode-option">简化模式</el-checkbox>
            </el-tooltip>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 关键词分析 -->
    <el-row :gutter="20" class="analysis-result" v-if="keywordResult">
      <el-col :span="24">
        <el-card>
          <div class="result-header">
            <h2>关键词分析</h2>
            <span class="analysis-time">分析时间: {{ formatTime(keywordAnalysisTime) }}</span>
          </div>
          
          <div class="keyword-charts">
            <div class="word-cloud-container" ref="wordCloudContainer"></div>
            
            <div class="keyword-table-container">
              <el-table :data="processedKeywords" style="width: 100%" max-height="400">
                <el-table-column prop="keyword" label="关键词" width="160"></el-table-column>
                <el-table-column prop="frequency" label="出现次数" width="100"></el-table-column>
                <el-table-column label="权重" width="100">
                  <template #default="{ row }">
                    {{ row && row.weight ? (row.weight * 100).toFixed(2) + '%' : '0%' }}
                  </template>
                </el-table-column>
                <el-table-column label="占比">
                  <template #default="{ row }">
                    <el-progress 
                      :percentage="row && row.weight ? row.weight * 100 : 0" 
                      :color="getRandomColor(row ? row.keyword : '')">
                    </el-progress>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 情感分析 -->
    <el-row :gutter="20" class="analysis-result" v-if="sentimentResult">
      <el-col :span="24">
        <el-card>
          <div class="result-header">
            <h2>情感分析</h2>
            <span class="analysis-time">分析时间: {{ formatTime(sentimentAnalysisTime) }}</span>
          </div>
          
          <div class="sentiment-summary">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card positive-card">
                  <template #header>
                    <div class="summary-header">
                      <span>积极片段</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ sentimentSummary.positive_segments || 0 }}</div>
                    <div class="summary-label">占比 {{ sentimentSummary.positive_percentage || 0 }}%</div>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card neutral-card">
                  <template #header>
                    <div class="summary-header">
                      <span>中性片段</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ sentimentSummary.neutral_segments || 0 }}</div>
                    <div class="summary-label">占比 {{ sentimentSummary.neutral_percentage || 0 }}%</div>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card negative-card">
                  <template #header>
                    <div class="summary-header">
                      <span>消极片段</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ sentimentSummary.negative_segments || 0 }}</div>
                    <div class="summary-label">占比 {{ sentimentSummary.negative_percentage || 0 }}%</div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
          
          <div class="sentiment-charts">
            <div class="sentiment-timeline" ref="sentimentTimelineChart"></div>
            
            <div class="sentiment-table-container">
              <el-table :data="sentimentSegments" style="width: 100%" max-height="400">
                <el-table-column label="时间段" width="180">
                  <template #default="{ row }">
                    {{ formatDuration(row.segment_start) }} - {{ formatDuration(row.segment_end) }}
                  </template>
                </el-table-column>
                <el-table-column prop="sentiment" label="情感" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getSentimentType(row.sentiment)">
                      {{ getSentimentText(row.sentiment) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="score" label="情感得分" width="100">
                  <template #default="{ row }">
                    {{ row.score.toFixed(2) }}
                  </template>
                </el-table-column>
                <el-table-column prop="danmaku_count" label="弹幕数" width="80"></el-table-column>
                <el-table-column label="情感分布">
                  <template #default="{ row }">
                    <el-progress :percentage="getSentimentPercentage(row)" :colors="sentimentColors"></el-progress>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 时间线分析 -->
    <el-row :gutter="20" class="analysis-result" v-if="showTimelineAnalysis">
      <el-col :span="24">
        <el-card>
          <div class="result-header">
            <h2>时间线分析</h2>
            <div v-if="currentEpisode !== null" class="return-link">
              <el-button type="text" @click="returnToOverallView">
                <i class="el-icon-back"></i> 返回整体视图
              </el-button>
            </div>
          </div>

          <div v-if="timelineLoading" class="loading-container">
            <el-skeleton animated :rows="6"></el-skeleton>
          </div>

          <div v-else-if="timelineError" class="error-message">
            <el-alert
              title="获取时间线数据失败"
              type="error"
              :description="timelineError"
              show-icon>
            </el-alert>
          </div>

          <div v-else-if="timelineSummary">
            <div v-if="currentEpisode === null" class="chart-container">
              <div ref="overallTimelineChartContainer" class="chart overall-timeline-chart"></div>
               <div class="chart-info">
                 <p v-if="episodeBoundaries && episodeBoundaries.length > 1">
                   点击图表中不同分集区域可查看该分集详细时间线。
                 </p>
                 <p v-else>
                    视频弹幕整体时间线分布。
                 </p>
               </div>
            </div>

            <div v-show="currentEpisode !== null">
              <div class="chart-container">
                <div ref="timelineChartContainer" class="chart timeline-chart"></div>
                <div class="timeline-info">
                   <p>当前查看: P{{ currentEpisode }}</p>
                   <p v-if="peakTimes && peakTimes.length">
                    弹幕峰值时刻:
                    <el-tag
                      v-for="(peak, index) in peakTimes.slice(0, 5)"
                      :key="index"
                      type="warning"
                      size="small"
                      class="peak-tag">
                      {{ formatDuration(peak.relative_time_sec * 1000) }} ({{ peak.count }}条)
                    </el-tag>
                    <el-tooltip v-if="peakTimes.length > 5" placement="top">
                      <template #content>
                        <div v-for="(peak, index) in peakTimes.slice(5)" :key="index + 5">
                           {{ formatDuration(peak.relative_time_sec * 1000) }} ({{ peak.count }}条)
                        </div>
                      </template>
                      <el-tag size="small" type="info">更多{{ peakTimes.length - 5 }}个...</el-tag>
                    </el-tooltip>
                  </p>
                   <p v-else>
                      当前分集未检测到明显弹幕峰值。
                   </p>
                </div>
              </div>
            </div>
          </div>
              
          <div v-else class="no-data">
            <el-empty description="暂无时间线数据，请先运行分析"></el-empty>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 用户分析 -->
    <el-row :gutter="20" class="analysis-result" v-if="userResult">
      <el-col :span="24">
        <el-card>
          <div class="result-header">
            <h2>用户分析</h2>
            <span class="analysis-time">分析时间: {{ formatTime(userAnalysisTime) }}</span>
          </div>
          
          <div class="user-summary">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card">
                  <template #header>
                    <div class="summary-header">
                      <span>发送弹幕用户数</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ userSummary.total_users || 0 }}</div>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card">
                  <template #header>
                    <div class="summary-header">
                      <span>人均弹幕数</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ userSummary.avg_per_user ? userSummary.avg_per_user.toFixed(2) : 0 }}</div>
                  </div>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="summary-card">
                  <template #header>
                    <div class="summary-header">
                      <span>最高弹幕数</span>
                    </div>
                  </template>
                  <div class="summary-content">
                    <div class="summary-value">{{ userSummary.top_users && userSummary.top_users.length > 0 ? userSummary.top_users[0].count : 0 }}</div>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
          
          <div class="user-distribution">
            <h3>弹幕发送分布</h3>
            <div class="user-distribution-chart" ref="userDistributionChart"></div>
          </div>
          
          <div class="top-users">
            <h3>活跃用户排行</h3>
            <el-table :data="processedTopUsers" style="width: 100%" max-height="400">
              <el-table-column label="用户哈希" width="200">
                <template #default="{ row }">
                  {{ row && row.user_hash }}
                </template>
              </el-table-column>
              <el-table-column prop="count" label="弹幕数" width="100"></el-table-column>
              <el-table-column label="占比">
                <template #default="{ row }">
                  <el-progress 
                    :percentage="processedTopUsers && processedTopUsers.length > 0 && row ? (row.count / processedTopUsers[0].count * 100) : 0" 
                    :color="getRandomColor('user-' + (row ? row.user_hash : ''))">
                  </el-progress>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { videoApi, analysisApi } from '@/api';
import * as echarts from 'echarts';
import WordCloud from 'wordcloud';

export default {
  name: 'AnalysisView',
  data() {
    return {
      bvid: this.$route.params.bvid,
      video: {},
      loadingVideo: false,
      videoTitle: '弹幕分析',
      
      // 分析状态
      isAnalyzing: false,
      useSimpleMode: true,
      
      // 关键词分析结果
      keywordResult: null,
      keywordAnalysisTime: null,
      keywords: [],
      wordCloudChart: null,
      
      // 情感分析结果
      sentimentResult: null,
      sentimentAnalysisTime: null,
      sentimentSegments: [],
      sentimentSummary: {},
      sentimentTimelineChart: null,
      sentimentColors: [
        { color: '#f56c6c', percentage: 33 },
        { color: '#e6a23c', percentage: 66 },
        { color: '#67c23a', percentage: 100 }
      ],
      
      // 时间线分析相关
      timelineLoading: false,
      timelineError: null,
      timelineSummary: null,
      episodeBoundaries: [],
      currentEpisode: null,
      overallTimelineChart: null,
      timelineChart: null,
      
      // 用户分析结果
      userResult: null,
      userAnalysisTime: null,
      userSummary: {},
      userDistributionChart: null,
      
      // 新增的变量
      selectedAnalysisOptions: ['emotion', 'keyword', 'topic', 'timeline'],
      showTimelineAnalysis: true,
      peakTimes: [],
      danmakuData: [],
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL,
      showAllEpisodes: false
    };
  },
  created() {
    // 检查路由参数
    if (!this.$route.params.bvid || this.$route.params.bvid === 'undefined') {
      console.error('无效的路由参数: bvid为空或undefined');
      this.$message.error('无效的视频标识符');
      this.$router.push({ name: 'Home' });
      return;
    }
    
    this.bvid = this.$route.params.bvid;
    console.log(`组件创建，BVID: ${this.bvid}`);
    
    this.fetchVideoInfo();
    this.fetchExistingAnalysis();
  },
  methods: {
    goBack() {
      this.$router.push({ name: 'Home' });
    },
    fetchVideoInfo() {
      // 检查bvid是否存在
      if (!this.bvid || this.bvid === 'undefined') {
        console.error('获取视频信息失败: bvid参数无效');
        this.$message.error('无效的视频标识符');
        return;
      }
      
      this.loadingVideo = true;
      console.log(`获取视频信息, BVID: ${this.bvid}`);
      
      videoApi.getVideoByBvid(this.bvid)
        .then(response => {
          this.video = response.data;
          this.videoTitle = `${this.video.title} - 弹幕分析`;
          console.log(`成功获取视频信息: ${this.video.title}`);
        })
        .catch(error => {
          console.error('获取视频信息失败', error);
          this.$message.error('获取视频信息失败');
        })
        .finally(() => {
          this.loadingVideo = false;
        });
    },
    fetchExistingAnalysis() {
      // 检查bvid是否存在
      if (!this.bvid) {
        console.error('获取分析结果失败: bvid参数为空');
        return;
      }
      
      console.log(`获取视频分析结果, BVID: ${this.bvid}`);
      
      // 获取已有的分析结果
      analysisApi.getAnalyses(this.bvid)
        .then(response => {
          const analyses = response.data.results || [];
          console.log(`获取到${analyses.length}条分析结果`);
          
          // 处理关键词分析
          const keywordAnalysis = analyses.find(a => a.analysis_type === 'keyword');
          if (keywordAnalysis && keywordAnalysis.result_json) {
            this.keywordResult = keywordAnalysis.result_json;
            this.keywordAnalysisTime = keywordAnalysis.updated_at;
            // 确保keywords数组中的每个项都有row属性
            this.keywords = Array.isArray(this.keywordResult) ? this.keywordResult.map((item, index) => {
              return {...item, row: index};
            }) : [];
            this.$nextTick(() => {
              this.renderWordCloud();
            });
          }
          
          // 处理情感分析
          const sentimentAnalysis = analyses.find(a => a.analysis_type === 'sentiment');
          if (sentimentAnalysis && sentimentAnalysis.result_json) {
            this.sentimentResult = sentimentAnalysis.result_json;
            this.sentimentAnalysisTime = sentimentAnalysis.updated_at;
            // 确保segments数组中的每个项都有row属性
            this.sentimentSegments = Array.isArray(this.sentimentResult.segments) ? 
              this.sentimentResult.segments.map((item, index) => ({...item, row: index})) : [];
            this.sentimentSummary = this.sentimentResult.summary || {};
            this.$nextTick(() => {
              this.renderSentimentTimeline();
            });
          }
          
          // 处理时间线分析
          const timelineAnalysis = analyses.find(a => a.analysis_type === 'timeline');
          if (timelineAnalysis && timelineAnalysis.result_json) {
            this.timelineSummary = timelineAnalysis.result_json;
            this.episodeBoundaries = this.timelineSummary.episode_boundaries || [];
            this.currentEpisode = null;
            
            // 确保时间线和高峰数据中的每个项都有row属性和page_id
            if (this.timelineSummary.timeline && Array.isArray(this.timelineSummary.timeline)) {
              this.timelineSummary.timeline = this.timelineSummary.timeline.map((item, index) => ({
                ...item, 
                row: index,
                page_id: item.page_id || 1  // 确保每个项都有page_id
              }));
            }
            
            if (this.timelineSummary.peaks && Array.isArray(this.timelineSummary.peaks)) {
              this.timelineSummary.peaks = this.timelineSummary.peaks.map((item, index) => ({
                ...item, 
                row: index,
                page_id: item.page_id || 1  // 确保每个项都有page_id
              }));
            }
            
            this.$nextTick(() => {
              // 默认渲染整体时间线图
              this.renderOverallTimelineChart();
            });
          } else {
            // 清理旧数据，以防重新运行分析时出错
            this.timelineSummary = null;
            this.episodeBoundaries = [];
            this.currentEpisode = null;
          }
          
          // 处理用户分析
          const userAnalysis = analyses.find(a => a.analysis_type === 'user');
          if (userAnalysis && userAnalysis.result_json) {
            this.userResult = userAnalysis.result_json;
            this.userAnalysisTime = userAnalysis.updated_at;
            this.userSummary = this.userResult || {};
            
            // 确保top_users数组中的每个项都有row属性
            if (this.userSummary.top_users && Array.isArray(this.userSummary.top_users)) {
              this.userSummary.top_users = this.userSummary.top_users.map((item, index) => ({...item, row: index}));
            }
            
            this.$nextTick(() => {
              this.renderUserDistributionChart();
            });
          }
        })
        .catch(error => {
          console.error('获取分析结果失败', error);
          if (error.response && error.response.status === 404) {
            if (error.response.data && error.response.data.detail === "No Video matches the given query.") {
              this.$message.error(`无法找到视频(BVID: ${this.bvid})`);
            } else {
              this.$message.error('无法获取分析结果');
            }
          }
        });
    },
    async runSelectedAnalysis() {
      if (!this.danmakuData || this.danmakuData.length === 0) {
        this.$message.warning('无弹幕数据可分析');
        return;
      }
      
      if (this.selectedAnalysisOptions.length === 0) {
        this.$message.warning('请至少选择一项分析内容');
        return;
      }
      
      this.isAnalyzing = true;
      
      try {
        // 并行执行选中的分析任务
        const analysisPromises = [];
        
        if (this.selectedAnalysisOptions.includes('emotion')) {
          analysisPromises.push(this.runEmotionAnalysis());
        }
        
        if (this.selectedAnalysisOptions.includes('keyword')) {
          analysisPromises.push(this.runKeywordAnalysis());
        }
        
        if (this.selectedAnalysisOptions.includes('topic')) {
          analysisPromises.push(this.runTopicAnalysis());
        }
        
        if (this.selectedAnalysisOptions.includes('timeline')) {
          analysisPromises.push(this.runTimelineAnalysis());
        }
        
        await Promise.all(analysisPromises);
        
        this.$message.success('分析完成');
      } catch (error) {
        console.error('分析过程中出错:', error);
        this.$message.error(`分析失败: ${error.message || '未知错误'}`);
      } finally {
        this.isAnalyzing = false;
      }
    },
    renderWordCloud() {
      if (!this.keywordResult || !this.$refs.wordCloudContainer) return;
      
      const container = this.$refs.wordCloudContainer;
      // 清空容器
      container.innerHTML = '';
      
      // 检查关键词数据是否有效
      const keywords = Array.isArray(this.keywordResult) ? this.keywordResult : [];
      if (keywords.length === 0) {
        console.warn('无法渲染词云：无关键词数据');
        container.innerHTML = '<div style="text-align:center;padding:20px;">无关键词数据</div>';
        return;
      }
      
      // 计算字体大小范围
      const minFontSize = 12;
      const maxFontSize = 60;
      
      // 找到最大权重用于缩放
      let maxWeight = 0;
      keywords.forEach(item => {
        if (item && typeof item.weight === 'number' && item.weight > maxWeight) {
          maxWeight = item.weight;
        }
      });
      
      // 准备词云数据，根据权重计算字体大小
      const words = keywords.map(item => {
        const keyword = item && item.keyword ? item.keyword : '';
        const weight = item && typeof item.weight === 'number' ? item.weight : 0;
        
        // 线性缩放字体大小: map [0, maxWeight] to [minFontSize, maxFontSize]
        // 如果 maxWeight 为 0，则所有字体大小为 minFontSize
        const fontSize = maxWeight > 0 
          ? minFontSize + (weight / maxWeight) * (maxFontSize - minFontSize)
          : minFontSize;
          
        return [keyword, Math.round(fontSize)];
      }).filter(item => item[0]); // 过滤掉没有关键词的项

      if (words.length === 0) {
        console.warn('无法渲染词云：处理后无有效关键词');
        container.innerHTML = '<div style="text-align:center;padding:20px;">无有效关键词数据</div>';
        return;
      }
      
      // 设置词云配置
      const options = {
        list: words,
        gridSize: Math.round(16 * maxFontSize / 60), // 可选：根据最大字体大小调整网格大小
        // weightFactor: 1, // 不再需要固定的 weightFactor，因为我们直接计算了字体大小
        fontFamily: 'Arial, 微软雅黑, sans-serif',
        color: (word, weight, fontSize, distance, theta) => this.getRandomColor(word), // 使用关键词作为颜色种子
        rotateRatio: 0.3, // 减少旋转比例，提高可读性
        rotationSteps: 2,
        backgroundColor: 'transparent',
        drawOutOfBound: false, // 防止词语画出边界
        shrinkToFit: true // 尝试缩小字体以适应容器
      };
      
      try {
        // 渲染词云
        WordCloud(container, options);
      } catch (error) {
        console.error('词云渲染失败:', error);
        container.innerHTML = '<div style="text-align:center;padding:20px;">词云渲染失败</div>';
      }
    },
    renderSentimentTimeline() {
      if (!this.sentimentResult || !this.$refs.sentimentTimelineChart) return;
      
      // 检查sentimentSegments是否存在并且是数组
      if (!this.sentimentSegments || !Array.isArray(this.sentimentSegments) || this.sentimentSegments.length === 0) {
        console.warn('无法渲染情感时间线：数据不完整');
        return;
      }
      
      // 初始化图表
      if (!this.sentimentTimelineChart) {
        this.sentimentTimelineChart = echarts.init(this.$refs.sentimentTimelineChart);
      }
      
      // 准备数据 (时间轴使用毫秒)
      const timeData = this.sentimentSegments.map(s => this.formatDuration(s.segment_start)); // 横轴标签仍用格式化后的时间
      const scoreData = this.sentimentSegments.map(s => s.score);
      const countData = this.sentimentSegments.map(s => s.danmaku_count);
      
      // 设置图表选项
      const option = {
        title: {
          text: '视频情感走势',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            const time = params[0].name;
            const score = params[0].value;
            const count = params[1].value;
            return `时间: ${time}<br/>情感得分: ${score.toFixed(2)}<br/>弹幕数: ${count}`;
          }
        },
        legend: {
          data: ['情感得分', '弹幕数量'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: timeData, // 使用格式化的时间作为x轴标签
          name: '视频时间'
        },
        yAxis: [
          {
            type: 'value',
            name: '情感得分',
            min: -1,
            max: 1,
            interval: 0.5,
            axisLabel: {
              formatter: '{value}'
            }
          },
          {
            type: 'value',
            name: '弹幕数量',
            axisLabel: {
              formatter: '{value}'
            }
          }
        ],
        series: [
          {
            name: '情感得分',
            type: 'line',
            smooth: true,
            emphasis: { focus: 'series' },
            data: scoreData,
            markLine: {
              data: [{ yAxis: 0, lineStyle: { color: '#909399' } }]
            },
            itemStyle: {
              color: function(params) {
                const value = params.value;
                if (value > 0.1) return '#67c23a';
                if (value < -0.1) return '#f56c6c';
                return '#909399';
              }
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(103, 194, 58, 0.2)' },
                  { offset: 0.5, color: 'rgba(144, 147, 153, 0.2)' },
                  { offset: 1, color: 'rgba(245, 108, 108, 0.2)' }
                ]
              }
            }
          },
          {
            name: '弹幕数量',
            type: 'bar',
            emphasis: { focus: 'series' },
            data: countData,
            yAxisIndex: 1
          }
        ]
      };
      
      // 渲染图表
      this.sentimentTimelineChart.setOption(option);
      window.addEventListener('resize', () => {
        if (this.sentimentTimelineChart) {
        this.sentimentTimelineChart.resize();
        }
      });
    },
    renderOverallTimelineChart() {
      if (this.currentEpisode !== null) {
        console.warn("renderOverallTimelineChart called when currentEpisode is not null.");
        return;
      }

      const chartDom = this.$refs.overallTimelineChartContainer;
      if (!chartDom) {
        console.error('找不到整体时间线图表容器 (ref: overallTimelineChartContainer)');
        return;
      }

      if (!this.timelineSummary || !this.timelineSummary.timeline || this.timelineSummary.timeline.length === 0) {
        console.warn('无时间线数据可显示 (Overall)');
        chartDom.innerHTML = '<div style="text-align:center;padding:40px;">暂无时间线数据</div>';
        if (this.overallTimelineChart && !this.overallTimelineChart.isDisposed()) {
          this.overallTimelineChart.dispose();
          this.overallTimelineChart = null;
        }
        return;
      } else {
         chartDom.innerHTML = '';
      }

      if (this.overallTimelineChart) {
        this.overallTimelineChart.dispose();
      }

      try {
        this.overallTimelineChart = echarts.init(chartDom);
      } catch (e) {
        console.error("ECharts (Overall) 初始化失败:", e);
        chartDom.innerHTML = '<div style="text-align:center;padding:40px;">图表初始化失败</div>';
        return;
      }

      const chartData = this.timelineSummary.timeline.map(item => {
          const timestamp_ms = (item.time || 0) * 1000;
          return [timestamp_ms, item.count || 0];
      });

      const markAreaData = (this.episodeBoundaries || []).map((boundary, index) => {
         const colors = ['rgba(92,163,230,0.1)', 'rgba(123,205,118,0.1)', 'rgba(241,159,106,0.1)', 'rgba(230,117,117,0.1)', 'rgba(178,149,218,0.1)'];
         const color = colors[index % colors.length];
         return [
           {
             name: `P${boundary.page_id}`,
             xAxis: (boundary.start_time_sec || 0) * 1000,
             itemStyle: { color: color },
             label: {
                show: true,
                position: 'insideTopLeft',
                formatter: `P${boundary.page_id}`,
                color: '#555',
                fontSize: 10,
                padding: [2, 4]
             },
             page_id: boundary.page_id
           },
           {
             xAxis: (boundary.end_time_sec || 0) * 1000
           }
         ];
      });

      const markPoints = (this.timelineSummary.peaks || []).map(peak => {
         const timestamp_ms = (peak.time || 0) * 1000;
         return {
           value: peak.count,
           xAxis: timestamp_ms,
           yAxis: peak.count,
           name: '峰值',
           symbolSize: 8,
           itemStyle: { color: '#e6a23c' }
         };
       });

      const option = {
        title: {
          text: '视频弹幕整体时间线分布',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: params => {
             const dataPoint = params[0].data;
             const time_ms = dataPoint[0];
             const count = dataPoint[1];
             return `时间点: ${this.formatDuration(time_ms)}<br/>弹幕数: ${count}`;
          }
        },
        grid: { left: '8%', right: '8%', bottom: '15%', containLabel: false },
        xAxis: {
          type: 'time',
          axisLabel: {
            formatter: (value, index) => {
              return this.formatDuration(value);
            }
          },
          name: '视频时间',
          min: 0
        },
        yAxis: { type: 'value', name: '弹幕数量', minInterval: 1 },
        dataZoom: [ { type: 'inside', filterMode: 'weakFilter' }, { type: 'slider', filterMode: 'weakFilter', bottom: '5%' } ],
        series: [
          {
            name: '弹幕数量',
            type: 'line',
            data: chartData,
            smooth: true,
            symbol: 'none',
            areaStyle: { opacity: 0.2 },
            markArea: {
               silent: false,
               data: markAreaData
            },
            markPoint: {
              data: markPoints,
              label: { formatter: '{c}' }
            }
          }
        ]
      };

      this.overallTimelineChart.setOption(option);

      this.overallTimelineChart.off('click');
      this.overallTimelineChart.on('click', params => {
        console.log("Overall chart clicked, Params:", JSON.stringify(params, null, 2));

        let targetPageId = null;

        if (params && params.componentType === 'markArea' && params.data && params.data.page_id) {
           targetPageId = params.data.page_id;
           console.log(`Click detected directly on MarkArea data for page ${targetPageId}`);
         } 
         else if (params && params.componentType === 'markArea' && params.name && params.name.startsWith('P')) {
          try {
            targetPageId = parseInt(params.name.substring(1));
            console.log(`Click detected on MarkArea component (using name) for page ${targetPageId}`);
          } catch (e) {
            console.error("Error parsing pageId from markArea name:", params.name, e);
          }
        }
        else if (params && params.componentType === 'series' && params.value && params.value.length > 0) {
          const clickTimestampMs = params.value[0];
          console.log(`Click detected on series at timestamp ${clickTimestampMs}ms`);
          if (clickTimestampMs !== undefined && this.episodeBoundaries && this.episodeBoundaries.length > 0) {
             const lastBoundary = this.episodeBoundaries[this.episodeBoundaries.length - 1];
             const lastEndTimeMs = (lastBoundary?.end_time_sec ?? 0) * 1000;

             for (const boundary of this.episodeBoundaries) {
                const startMs = (boundary.start_time_sec || 0) * 1000;
                const endMs = (boundary.end_time_sec || 0) * 1000;

                if (clickTimestampMs >= startMs && clickTimestampMs < endMs) {
                   targetPageId = boundary.page_id;
                   console.log(`Timestamp ${clickTimestampMs}ms falls within page ${targetPageId} [${startMs}ms, ${endMs}ms)`);
                   break;
                }
                if (clickTimestampMs === endMs && clickTimestampMs === lastEndTimeMs) {
                     targetPageId = boundary.page_id;
                     console.log(`Timestamp ${clickTimestampMs}ms falls exactly on the end boundary of the last page ${targetPageId}`);
                     break;
                }
             }
             if (targetPageId === null) {
                console.log(`Timestamp ${clickTimestampMs}ms did not fall within any known episode boundary.`);
             }
          } else {
             console.log("Click on series, but timestamp or boundaries are missing.");
          }
        } else {
           console.log("Click was not on a relevant component (MarkArea or Series). Event Params:", params);
        }

        if (targetPageId !== null) {
          this.switchEpisode(targetPageId);
        } else {
           console.log("Could not determine target pageId from click event.");
        }
      });
    },
    renderTimelineChart() {
      if (this.currentEpisode === null) {
        console.warn("renderTimelineChart called when currentEpisode is null.");
        if (this.timelineChart && !this.timelineChart.isDisposed()) {
          this.timelineChart.dispose();
          this.timelineChart = null;
        }
        return;
      }

      const chartDom = this.$refs.timelineChartContainer;
      if (!chartDom) {
        console.error('找不到单集时间线图表容器 (ref: timelineChartContainer)');
        return;
      }

      if (!this.timelineSummary || !this.timelineSummary.timeline || this.timelineSummary.timeline.length === 0) {
        console.warn(`无时间线数据可显示 (Episode ${this.currentEpisode})`);
        chartDom.innerHTML = `<div style="text-align:center;padding:40px;">第${this.currentEpisode}集暂无时间线数据</div>`;
        if (this.timelineChart && !this.timelineChart.isDisposed()) {
          this.timelineChart.dispose();
          this.timelineChart = null;
        }
        return;
      } else {
         chartDom.innerHTML = '';
      }

      if (this.timelineChart) {
        this.timelineChart.dispose();
      }

      try {
        this.timelineChart = echarts.init(chartDom);
      } catch (e) {
        console.error(`ECharts (Episode ${this.currentEpisode}) 初始化失败:`, e);
        chartDom.innerHTML = '<div style="text-align:center;padding:40px;">图表初始化失败</div>';
        return;
      }

      const currentBoundary = (this.episodeBoundaries || []).find(b => b.page_id === this.currentEpisode);
      if (!currentBoundary) {
         console.error(`无法找到第 ${this.currentEpisode} 集的边界信息`);
         chartDom.innerHTML = `<div style="text-align:center;padding:40px;">无法加载第 ${this.currentEpisode} 集数据</div>`;
         return;
      }
      const startTimeSec = currentBoundary.start_time_sec || 0;
      const durationSec = currentBoundary.duration_sec || 0;

      const currentEpisodeTimeline = this.timelineSummary.timeline.filter(item => {
        return item.page_id === this.currentEpisode;
      });

      if (currentEpisodeTimeline.length === 0) {
        console.warn(`第${this.currentEpisode}集过滤后没有时间线数据`);
        chartDom.innerHTML = `<div style="text-align:center;padding:40px;">第${this.currentEpisode}集没有弹幕数据</div>`;
        return;
      }

      const chartData = currentEpisodeTimeline.map(item => {
          const relative_time_ms = Math.max(0, (item.time || 0) - startTimeSec) * 1000;
          return [relative_time_ms, item.count || 0];
      });

      const markPoints = this.getPeaksForCurrentEpisode();

      const option = {
        title: {
          text: `P${this.currentEpisode} 弹幕时间线分布`,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: params => {
             const dataPoint = params[0].data;
             const relative_time_ms = dataPoint[0];
             const count = dataPoint[1];
             return `时间点(相对): ${this.formatDuration(relative_time_ms)}<br/>弹幕数: ${count}`;
          }
        },
        grid: { left: '8%', right: '8%', bottom: '15%', containLabel: false },
        xAxis: {
          type: 'time',
          axisLabel: {
            formatter: (value, index) => {
              return this.formatDuration(value);
            }
          },
          name: '分集内时间',
          min: 0,
          max: durationSec * 1000
        },
        yAxis: { type: 'value', name: '弹幕数量', minInterval: 1 },
        dataZoom: [ { type: 'inside', filterMode: 'weakFilter' }, { type: 'slider', filterMode: 'weakFilter', bottom: '5%' } ],
        series: [
          {
            name: '弹幕数量',
            type: 'line',
            data: chartData,
            smooth: true,
            symbol: 'none',
            areaStyle: { opacity: 0.3 },
            markPoint: {
              data: markPoints,
              symbolSize: 10,
               label: { formatter: '{c}' }
            }
          }
        ]
      };

      this.timelineChart.setOption(option);
    },
    handleTimelineResize() {
      if (this.overallTimelineChart && !this.overallTimelineChart.isDisposed()) {
        this.overallTimelineChart.resize();
      }
      if (this.timelineChart && !this.timelineChart.isDisposed()) {
        this.timelineChart.resize();
      }
      if (this.sentimentTimelineChart && !this.sentimentTimelineChart.isDisposed()) {
        this.sentimentTimelineChart.resize();
      }
      if (this.userDistributionChart && !this.userDistributionChart.isDisposed()) {
        this.userDistributionChart.resize();
      }
    },
    switchEpisode(episodeId) {
       if (!episodeId || !(this.episodeBoundaries || []).some(b => b.page_id === episodeId)) {
          console.error(`无效的分集 ID: ${episodeId}`);
          this.$message.warning(`无法切换到分集 ${episodeId}`);
          return;
       }
       if (this.currentEpisode === episodeId) return;

       console.log(`Switching to episode ${episodeId}`);
       this.currentEpisode = episodeId;

       if (this.overallTimelineChart && !this.overallTimelineChart.isDisposed()) {
          // this.overallTimelineChart.clear();
       }

       this.$nextTick(() => {
         this.renderTimelineChart();
       });
    },
    formatTime(time) {
      if (!time) return '-';
      return new Date(time).toLocaleString();
    },
    formatDuration(milliseconds) {
      const totalSeconds = Math.floor(milliseconds / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      
      if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      } else {
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      }
    },
    getRandomColor(seed) {
      const colors = [
        '#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399',
        '#36CFC9', '#40A9FF', '#9254DE', '#73D13D', '#FF7875'
      ];
      
      if (seed) {
        let hash = 0;
        for (let i = 0; i < seed.length; i++) {
          hash = seed.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
      }
      
      return colors[Math.floor(Math.random() * colors.length)];
    },
    getSentimentType(sentiment) {
      const types = {
        'positive': 'success',
        'neutral': 'info',
        'negative': 'danger'
      };
      return types[sentiment] || 'info';
    },
    getSentimentText(sentiment) {
      const texts = {
        'positive': '积极',
        'neutral': '中性',
        'negative': '消极'
      };
      return texts[sentiment] || '未知';
    },
    getSentimentPercentage(row) {
      if (!row) return 0;
      
      const positive_count = row.positive_count || 0;
      const negative_count = row.negative_count || 0;
      const neutral_count = row.neutral_count || 0;
      
      const total = positive_count + negative_count + neutral_count;
      if (!total) return 0;
      
      if (row.sentiment === 'positive') {
        return (positive_count / total) * 100;
      } else if (row.sentiment === 'negative') {
        return (negative_count / total) * 100;
      } else {
        return (neutral_count / total) * 100;
      }
    },
    shouldShowAnalysisType(type) {
      return this.selectedAnalysisOptions.includes(type);
    },
    getPeaksForCurrentEpisode() {
      if (!this.timelineSummary || !this.timelineSummary.peaks || !Array.isArray(this.timelineSummary.peaks)) {
        console.warn("getPeaksForCurrentEpisode: 峰值数据 (peaks) 不可用");
        return [];
      }
      if (this.currentEpisode === null) {
         console.warn("getPeaksForCurrentEpisode called when currentEpisode is null.");
         return [];
      }
      const currentBoundary = (this.episodeBoundaries || []).find(b => b.page_id === this.currentEpisode);
      if (!currentBoundary) {
         console.error(`获取峰值失败: 无法找到第 ${this.currentEpisode} 集的边界信息`);
         return [];
      }
      const startTimeSec = currentBoundary.start_time_sec || 0;

      const currentEpisodePeaks = this.timelineSummary.peaks.filter(peak => {
        return peak.page_id === this.currentEpisode;
      });

      if (currentEpisodePeaks.length === 0) {
          console.log(`第 ${this.currentEpisode} 集没有峰值数据`);
          return [];
      }

      return currentEpisodePeaks.map(peak => {
        const relative_time_sec = Math.max(0, (peak.time || 0) - startTimeSec);
        const relative_timestamp_ms = relative_time_sec * 1000;
        return {
          value: peak.count,
          xAxis: relative_timestamp_ms,
          yAxis: peak.count,
          name: '峰值',
          itemStyle: { color: '#f56c6c' },
          original_time_sec: peak.time,
          relative_time_sec: relative_time_sec
        };
      });
    },
    returnToOverallView() {
      if (this.currentEpisode === null) return;

      console.log("Returning to overall view");
      this.currentEpisode = null;

      if (this.timelineChart && !this.timelineChart.isDisposed()) {
        // this.timelineChart.clear();
      }

      this.$nextTick(() => {
        this.renderOverallTimelineChart();
      });
    },
    async runEmotionAnalysis() {
      if (!this.danmakuData || this.danmakuData.length === 0) return;
      
      try {
        const response = await fetch(`${this.apiBaseUrl}/analyze/emotion`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            danmaku: this.danmakuData
          }),
        });
        
        if (!response.ok) {
          throw new Error(`情感分析请求失败: ${response.status}`);
        }
        
        const result = await response.json();
        this.sentimentSummary = result;
        
        // 渲染情感分析图表
        this.$nextTick(() => {
          this.renderSentimentTimeline();
        });
      } catch (error) {
        console.error('情感分析错误:', error);
        throw error;
      }
    },
    async runKeywordAnalysis() {
      if (!this.danmakuData || this.danmakuData.length === 0) return;
      
      try {
        const response = await fetch(`${this.apiBaseUrl}/analyze/keywords`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            danmaku: this.danmakuData
          }),
        });
        
        if (!response.ok) {
          throw new Error(`关键词分析请求失败: ${response.status}`);
        }
        
        const result = await response.json();
        this.keywordResult = result;
        this.keywords = Array.isArray(this.keywordResult) ? this.keywordResult.map((item, index) => {
          return {...item, row: index};
        }) : [];
        
        // 渲染关键词云图
        this.$nextTick(() => {
          this.renderWordCloud();
        });
      } catch (error) {
        console.error('关键词分析错误:', error);
        throw error;
      }
    },
    async runTopicAnalysis() {
      if (!this.danmakuData || this.danmakuData.length === 0) return;
      
      try {
        const response = await fetch(`${this.apiBaseUrl}/analyze/topics`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            danmaku: this.danmakuData
          }),
        });
        
        if (!response.ok) {
          throw new Error(`话题分析请求失败: ${response.status}`);
        }
        
        const result = await response.json();
        this.userResult = result;
        this.userAnalysisTime = new Date().toISOString();
        this.userSummary = this.userResult || {};
        
        // 渲染话题分布图
        this.$nextTick(() => {
          this.renderTopicChart();
        });
      } catch (error) {
        console.error('话题分析错误:', error);
        throw error;
      }
    },
    async runTimelineAnalysis() {
      if (!this.danmakuData || this.danmakuData.length === 0) return;
      
      console.log(`运行时间线分析 for ${this.bvid}`);
      this.timelineLoading = true;
      this.timelineError = null;

      try {
        const response = await analysisApi.runTimelineAnalysis(this.bvid, this.useSimpleMode);
        const result = response.data;
        console.log("时间线分析 API 返回:", result);

        this.timelineSummary = result;
        this.episodeBoundaries = result.episode_boundaries || [];

        this.currentEpisode = null;

        this.$nextTick(() => {
          this.renderOverallTimelineChart();
        });
      } catch (error) {
        console.error('时间线分析错误:', error);
        this.timelineError = error.response?.data?.error || error.message || '分析时发生未知错误';
        this.$message.error(`时间线分析失败: ${this.timelineError}`);
      } finally {
        this.timelineLoading = false;
      }
    },
    toggleShowAllEpisodes() {
      this.showAllEpisodes = !this.showAllEpisodes;
    },
    runAllAnalysis() {
      if (!this.bvid) {
        this.$message.error('无效的视频ID');
        return;
      }
      
      const selectedOptions = this.selectedAnalysisOptions;
      
      if (selectedOptions.length === 0) {
        this.$message.warning('请至少选择一项分析内容');
        return;
      }
      
      this.isAnalyzing = true;
      
      this.keywordError = null;
      this.sentimentError = null;
      this.timelineError = null;
      this.userError = null;
      
      const analysisPromises = [];
      
      if (selectedOptions.includes('keyword')) {
        const keywordPromise = analysisApi.runKeywordAnalysis(this.bvid, this.useSimpleMode)
          .then(response => {
            this.keywordResult = response.data;
            this.keywordAnalysisTime = new Date().toISOString();
            this.keywords = Array.isArray(this.keywordResult) ? 
              this.keywordResult.map((item, index) => ({...item, row: index})) : [];
            
            this.$nextTick(() => {
              this.renderWordCloud();
            });
          })
          .catch(error => {
            console.error('关键词分析失败', error);
            this.keywordError = error.message || '分析失败';
          });
        
        analysisPromises.push(keywordPromise);
      }
      
      if (selectedOptions.includes('emotion')) {
        const sentimentPromise = analysisApi.runSentimentAnalysis(this.bvid, this.useSimpleMode)
          .then(response => {
            this.sentimentResult = response.data;
            this.sentimentAnalysisTime = new Date().toISOString();
            this.sentimentSegments = Array.isArray(this.sentimentResult.segments) ? 
              this.sentimentResult.segments.map((item, index) => ({...item, row: index})) : [];
            this.sentimentSummary = this.sentimentResult.summary || {};
            
            this.$nextTick(() => {
              this.renderSentimentTimeline();
            });
          })
          .catch(error => {
            console.error('情感分析失败', error);
            this.sentimentError = error.message || '分析失败';
          });
        
        analysisPromises.push(sentimentPromise);
      }
      
      if (selectedOptions.includes('timeline')) {
        this.timelineLoading = true;
        this.timelineError = null;

        const timelinePromise = this.runTimelineAnalysis();

        const wrappedTimelinePromise = Promise.resolve(timelinePromise)
           .catch(err => {
              console.error("Timeline analysis promise rejected in runAllAnalysis:", err);
           })
           .finally(() => {
           });

        analysisPromises.push(wrappedTimelinePromise);
      }
      
      if (selectedOptions.includes('topic')) {
        const topicPromise = analysisApi.runTopicAnalysis(this.bvid, this.useSimpleMode)
          .then(response => {
            this.userResult = response.data;
            this.userAnalysisTime = new Date().toISOString();
            this.userSummary = this.userResult || {};
            
            if (this.userSummary.top_users && Array.isArray(this.userSummary.top_users)) {
              this.userSummary.top_users = this.userSummary.top_users.map((item, index) => ({...item, row: index}));
            }
            
            this.$nextTick(() => {
              this.renderUserDistributionChart();
            });
          })
          .catch(error => {
            console.error('话题分析失败', error);
            this.userError = error.message || '分析失败';
          });
        
        analysisPromises.push(topicPromise);
      }
      
      Promise.all(analysisPromises)
        .then(() => {
           if (this.keywordError || this.sentimentError || this.timelineError || this.userError) {
              this.$message.warning('部分分析任务失败，请查看详情');
           } else {
              this.$message.success('所有选定分析已完成');
           }
        })
        .catch(error => {
          console.error('Promise.all 在 runAllAnalysis 中出错:', error);
          this.$message.error('分析过程中发生意外错误');
        })
        .finally(() => {
          this.isAnalyzing = false;
        });
    },
    renderUserDistributionChart() {
      if (!this.userResult || !this.$refs.userDistributionChart) return;
      
      if (!this.userSummary || !this.userSummary.user_distribution) {
        console.warn('无法渲染用户分布图表：数据不完整');
        return;
      }
      
      if (!this.userDistributionChart) {
        this.userDistributionChart = echarts.init(this.$refs.userDistributionChart);
      }
      
      const distribution = this.userSummary.user_distribution || {};
      const categories = Object.keys(distribution);
      const data = categories.map(key => distribution[key] || 0);
      
      const option = {
        title: {
          text: '用户弹幕数分布',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          data: categories
        },
        series: [
          {
            name: '弹幕数分布',
            type: 'pie',
            radius: '50%',
            center: ['50%', '60%'],
            data: categories.map(category => ({
              name: category,
              value: distribution[category] || 0
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      };
      
      this.userDistributionChart.setOption(option);
      window.addEventListener('resize', () => {
        if (this.userDistributionChart) {
        this.userDistributionChart.resize();
        }
      });
    },
  },
  computed: {
    peakTimes() {
      if (!this.timelineSummary || !this.timelineSummary.peaks || !Array.isArray(this.timelineSummary.peaks)) {
        return [];
      }
      
      if (this.currentEpisode !== null) {
        const peaksWithRelativeTime = this.getPeaksForCurrentEpisode();
        return peaksWithRelativeTime.sort((a, b) => (b.value || 0) - (a.value || 0));
      } else {
         return this.timelineSummary.peaks
             .map(p => ({ ...p, relative_time_sec: p.time }))
             .sort((a, b) => b.count - a.count);
      }
    },
    processedTopUsers() {
      if (!this.userSummary || !this.userSummary.top_users || !Array.isArray(this.userSummary.top_users)) {
        return [];
      }
      
      return this.userSummary.top_users.map((item, index) => {
        if (!item) return { row: index, user_hash: '未知', count: 0 };
        return { ...item, row: index };
      });
    },
    processedKeywords() {
      if (!this.keywordResult || !Array.isArray(this.keywordResult)) {
        return [];
      }
      
      return this.keywordResult.map((item, index) => {
        if (!item) return { row: index, keyword: '未知', frequency: 0, weight: 0 };
        return { ...item, row: index };
      });
    }
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleTimelineResize);
    if (this.overallTimelineChart) {
      this.overallTimelineChart.dispose();
      this.overallTimelineChart = null;
    }
    if (this.timelineChart) {
      this.timelineChart.dispose();
      this.timelineChart = null;
    }
    if (this.sentimentTimelineChart) {
      this.sentimentTimelineChart.dispose();
      this.sentimentTimelineChart = null;
    }
     if (this.userDistributionChart) {
       this.userDistributionChart.dispose();
       this.userDistributionChart = null;
     }
  }
};
</script>

<style scoped>
.analysis-view-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.video-info, .analysis-controls, .analysis-result {
  margin-top: 20px;
}

.video-info-header, .actions-header, .result-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.analysis-options {
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.analysis-time {
  font-size: 14px;
  color: #909399;
}

.keyword-charts, .sentiment-charts, .timeline-charts {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.word-cloud-container, .sentiment-timeline, .timeline-chart, .user-distribution-chart {
  height: 400px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 20px;
  background-color: #f8f9fa;
}

.keyword-table-container, .sentiment-table-container, .timeline-peaks-container, .top-users {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 20px;
}

.timeline-peaks-container h3, .top-users h3, .user-distribution h3 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 16px;
  color: #606266;
}

.user-distribution {
  margin-top: 20px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 20px;
}

.top-users {
  margin-top: 20px;
}

.sentiment-summary, .timeline-summary, .user-summary {
  margin-bottom: 20px;
}

.summary-card {
  text-align: center;
}

.summary-content {
  padding: 20px 0;
}

.summary-value {
  font-size: 36px;
  font-weight: bold;
  margin-bottom: 10px;
}

.summary-label {
  font-size: 14px;
  color: #909399;
}

.positive-card .summary-value {
  color: #67c23a;
}

.neutral-card .summary-value {
  color: #909399;
}

.negative-card .summary-value {
  color: #f56c6c;
}

@media (min-width: 768px) {
  .keyword-charts, .sentiment-charts, .timeline-charts {
    flex-direction: row;
  }
  
  .word-cloud-container, .sentiment-timeline, .timeline-chart {
    width: 60%;
  }
  
  .keyword-table-container, .sentiment-table-container, .timeline-peaks-container {
    width: 40%;
  }
}

.overall-timeline-chart {
  width: 100%;
  height: 400px;
   border: 1px solid #ebeef5;
   border-radius: 4px;
   padding: 10px;
   background-color: #fff;
   cursor: pointer;
}

.timeline-chart {
  width: 100%;
  height: 400px;
   border: 1px solid #ebeef5;
   border-radius: 4px;
   padding: 10px;
   background-color: #fff;
}

.chart-help-text {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin: 10px 0;
}

.card-buttons {
  float: right;
  margin-top: -5px;
}

.peak-keyword {
  background-color: #f0f9eb;
  color: #67c23a;
  padding: 2px 5px;
  border-radius: 4px;
  margin-left: 5px;
  font-size: 12px;
}

.analysis-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.return-link {
  margin-left: 10px;
}

.chart-container {
  margin: 20px 0;
}

.chart {
  width: 100%;
  height: 400px;
}

.chart-info, .timeline-info {
  margin-top: 10px;
  font-size: 14px;
  color: #606266;
}

.peak-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.loading-container {
  padding: 20px;
}

.error-message {
  margin: 20px 0;
}

.no-data {
  padding: 40px 0;
  text-align: center;
}

.episode-select-prompt {
  margin-top: 20px;
  margin-bottom: 20px;
}

.timeline-info p:last-child {
  margin-top: 8px;
}
</style> 