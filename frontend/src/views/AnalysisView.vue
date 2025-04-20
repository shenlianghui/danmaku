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
            <!-- <div class="sentiment-timeline" ref="sentimentTimelineChart"></div> -->
            <div class="sentiment-timeline">情感时间线图表待替换</div>
            
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
        <el-card style="height: 650px; overflow: hidden;"> <!-- 增加高度，设置overflow控制 -->
          <div class="result-header">
            <h2>时间线分析 {{ currentEpisode ? `(P${currentEpisode})` : '(整体)' }}</h2>
            <div v-if="currentEpisode !== null" class="return-link">
              <el-button type="text" @click="returnToOverallView">
                <i class="el-icon-back"></i> 返回整体视图
              </el-button>
            </div>
            <div v-else class="view-controls">
              <el-button type="text" @click="showFullTimeline" title="显示全部时间线">
                <i class="el-icon-full-screen"></i> 显示完整视频
              </el-button>
            </div>
          </div>

          <!-- 添加分P导航 -->
          <div class="episode-navigation" v-if="episodeBoundaries && episodeBoundaries.length > 1">
            <el-radio-group v-model="currentEpisode" size="small" @change="handleEpisodeChange">
              <el-radio-button :label="null">整体</el-radio-button>
              <el-radio-button 
                v-for="boundary in episodeBoundaries" 
                :key="boundary.page_id" 
                :label="boundary.page_id"
              >P{{ boundary.page_id }}</el-radio-button>
            </el-radio-group>
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

          <div v-else-if="timelineSummary && timelineItems" style="height: 560px;"> <!-- 增加内容区域高度 -->
            <!-- 使用 vue-timeline-chart 组件 -->
            <Timeline
              v-if="Array.isArray(timelineItems) && timelineItems.length > 0"
              :items="[]" 
              :markers="Array.isArray(timelineMarkers) ? timelineMarkers : []"
              :groups="[{id: 'danmaku', label: '弹幕密度'}]"
              :viewport-min="0"
              :viewport-max="video.duration ? video.duration * 1000 : timelineViewport.max"
              :initial-viewport-start="timelineViewport.min"
              :initial-viewport-end="timelineViewport.max"
              :min-viewport-duration="1000 * 5"  
              :max-viewport-duration="video.duration ? video.duration * 1000 * 1.2 : 1000 * 60 * 60 * 24" 
              renderTimestampLabel="custom"
              :scales="getCustomScales()"
              :minTimestampWidth="60"
              @clickTimeline="handleClickTimeline"
              @clickMarker="handleClickMarker"
              @changeViewport="handleViewportChange"
              style="height: 100%; border: 1px solid #ebeef5; border-radius: 4px;"
              class="timeline-chart-container"
              ref="timelineChart"
            >
              <!-- 自定义时间戳标签 -->
              <template #timestamp="{ timestamp, scale }">
                {{ formatCustomTimestamp(timestamp, scale) }}
              </template>
              
              <!-- 使用自定义图表替代Timeline组件的条形图 -->
              <template #items-danmaku="{ viewportStart, viewportEnd }">
                <LineChart 
                  :viewportStart="viewportStart" 
                  :viewportEnd="viewportEnd" 
                  :data="formattedTimelineData"
                  :height="400" 
                  :lineColor="'rgba(64, 158, 255, 0.9)'"
                  :fillColor="'rgba(64, 158, 255, 0.1)'"
                  :lineWidth="2"
                  :pointRadius="4"
                  :smooth="true"
                  :showGrid="true"
                  :episodeBoundaries="episodeBoundaries"
                />
              </template>

              <!-- 自定义 Marker 显示 -->
              <template #marker-label="{ marker }">
                <span 
                  class="marker-label"
                  :style="{
                    fontSize: '12px',
                    color: marker.cssVariables && marker.cssVariables['--marker-color'] ? marker.cssVariables['--marker-color'] : '#333',
                    writingMode: 'vertical-lr',
                    textOrientation: 'mixed',
                    padding: '2px',
                    fontWeight: 'bold'
                  }"
                >{{ marker.label }}</span>
              </template>
            </Timeline>

            <div v-else class="no-data-message">
              <el-alert
                title="没有足够的时间线数据点"
                      type="warning"
                show-icon
                :closable="false"
              >
                <p>当前视图没有足够的数据可供展示。这可能是因为：</p>
                <ul>
                  <li>该视频的弹幕数量很少</li>
                  <li>数据尚未加载完成</li>
                  <li>当前分P没有弹幕</li>
                </ul>
              </el-alert>
                        </div>
             
             <div class="chart-info" v-if="Array.isArray(timelineItems) && timelineItems.length > 0">
                 <p v-if="currentEpisode === null && episodeBoundaries && episodeBoundaries.length > 1">
                   点击图表中时间点可查看该时间所在分集的详细信息。
                 </p>
                 <p v-else-if="currentEpisode === null">
                    视频弹幕整体时间线分布。
                  </p>
                   <p v-else>
                 当前查看: P{{ currentEpisode }}。
                   </p>
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
            <!-- <div class="user-distribution-chart" ref="userDistributionChart"></div> -->
            <div class="user-distribution-chart">用户分布图表待替换</div>
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
import WordCloud from 'wordcloud';
import { videoApi, analysisApi } from '@/api';
import { Timeline } from 'vue-timeline-chart';
import 'vue-timeline-chart/style.css';
import LineChart from '@/components/LineChart.vue';

export default {
  name: 'AnalysisView',
  components: { Timeline, LineChart },
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
      
      // 情感分析结果
      sentimentResult: null,
      sentimentAnalysisTime: null,
      sentimentSegments: [],
      sentimentSummary: {},
      sentimentColors: [
        { color: '#f56c6c', percentage: 33 },
        { color: '#e6a23c', percentage: 66 },
        { color: '#67c23a', percentage: 100 }
      ],
      
      // 时间线分析相关
      timelineLoading: false,
      timelineError: null,
      timelineSummary: { 
          timeline: [], 
          peaks: [], 
          episode_boundaries: [],
          total_count: 0
      },
      episodeBoundaries: [],
      currentEpisode: null,
      timelineViewport: {
          min: 0,
          max: 0,
      },
      
      // 用户分析结果
      userResult: null,
      userAnalysisTime: null,
      userSummary: {},
      
      // 新增的变量
      selectedAnalysisOptions: ['emotion', 'keyword', 'topic', 'timeline'],
      showTimelineAnalysis: true,
      peakTimes: [],
      danmakuData: [],
      apiBaseUrl: process.env.VUE_APP_API_BASE_URL,
      showAllEpisodes: false,
      currentViewport: null
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
            
            // 确保segments数组存在 (用于下方可能的表格渲染)
            this.sentimentSegments = Array.isArray(this.sentimentResult.segments) ? 
              this.sentimentResult.segments.map((item, index) => ({...item, row: index})) : [];
              
            // 从 sentiment_counts 和 visualization.percentages 构建 sentimentSummary
            if (this.sentimentResult.sentiment_counts && this.sentimentResult.visualization) {
              const counts = this.sentimentResult.sentiment_counts;
              const percentages = this.sentimentResult.visualization.percentages || {};
              this.sentimentSummary = {
                positive_segments: counts.positive || 0,
                neutral_segments: counts.neutral || 0,
                negative_segments: counts.negative || 0,
                positive_percentage: percentages.positive || 0,
                neutral_percentage: percentages.neutral || 0,
                negative_percentage: percentages.negative || 0,
                dominant: this.sentimentResult.visualization.dominant || 'neutral',
                score_level: this.sentimentResult.visualization.score_level || 'neutral'
              };
            } else {
              // 如果缺少必要数据，则设为空对象
              this.sentimentSummary = {};
              console.warn("情感分析结果缺少 sentiment_counts 或 visualization 数据");
            }
            
            this.$nextTick(() => {
              // this.renderSentimentTimeline();
            });
          }
          
          // 处理时间线分析
          const timelineAnalysis = analyses.find(a => a.analysis_type === 'timeline');
          if (timelineAnalysis && timelineAnalysis.result_json) {
            console.log("原始时间线数据:", timelineAnalysis.result_json); // Debugging
            this.timelineSummary = timelineAnalysis.result_json;
            
            // 确认数据结构有效
            if (this.timelineSummary.timeline && Array.isArray(this.timelineSummary.timeline)) {
                console.log(`时间线数据点数量: ${this.timelineSummary.timeline.length}`);
            } else {
                console.warn("无效的时间线数据结构:", this.timelineSummary);
            }
            
            // 确保边界数据存在
            this.episodeBoundaries = this.timelineSummary.episode_boundaries || [];
            console.log(`分P边界数量: ${this.episodeBoundaries.length}`);
            
            // 重置为整体视图
            this.currentEpisode = null;

            // 初始化视口范围 (整体视图)
            this.updateTimelineViewport();
            console.log("视口范围:", this.timelineViewport);

            // 确保数据存在再进行下一步操作
            if (!this.timelineSummary.timeline) {
                 this.timelineSummary.timeline = [];
            }
            if (!this.timelineSummary.peaks) {
                 this.timelineSummary.peaks = [];
            }
          } else {
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
              // this.renderUserDistributionChart();
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
    updateTimelineViewport() {
      try {
        if (this.currentEpisode === null) {
          // 整体视图 - 使用视频实际时长
          const videoDurationMs = this.video && this.video.duration ? this.video.duration * 1000 : 0;
          
          if (videoDurationMs > 0) {
            // 使用视频实际时长
            this.timelineViewport = {
              min: 0,
              max: videoDurationMs
            };
            console.log(`使用视频实际时长设置视口: ${this.formatDuration(videoDurationMs)}`);
          } else if (this.episodeBoundaries && this.episodeBoundaries.length > 0) {
            // 备选：使用所有分P长度总和
            const lastBoundary = this.episodeBoundaries[this.episodeBoundaries.length - 1];
            if (lastBoundary && typeof lastBoundary.end_time_sec === 'number') {
              this.timelineViewport = {
                min: 0,
                max: lastBoundary.end_time_sec * 1000
              };
              console.log(`使用分P总长度设置视口: ${this.formatDuration(lastBoundary.end_time_sec * 1000)}`);
            } else {
              // 如果无法确定，使用默认值
              this.timelineViewport = { min: 0, max: 600 * 1000 }; // 10分钟
            }
          } else {
            // 默认10分钟
            this.timelineViewport = { min: 0, max: 600 * 1000 };
          }
      } else {
          // 分P视图 - 使用当前分P的实际长度
          const boundary = this.episodeBoundaries.find(b => b.page_id === this.currentEpisode);
          if (boundary && typeof boundary.duration_sec === 'number' && boundary.duration_sec > 0) {
            const durationMs = boundary.duration_sec * 1000;
            this.timelineViewport = {
              min: 0, // 相对时间从0开始
              max: durationMs
            };
            console.log(`更新分P ${this.currentEpisode} 视口: ${this.formatDuration(durationMs)}`);
          } else {
            console.error(`无法找到分P ${this.currentEpisode} 的有效边界信息`);
            // 使用默认值
            this.timelineViewport = { min: 0, max: 600 * 1000 }; // 10分钟
          }
        }
      } catch (error) {
        console.error('更新视口时出错:', error);
        this.timelineViewport = { min: 0, max: 600 * 1000 }; // 默认10分钟
      }
    },
    handleClickTimeline(event) {
        console.log('Timeline clicked:', event);
        if (!event || typeof event.timestamp !== 'number') {
            console.log('无效的时间线点击事件');
        return;
      }

        // 我们已经在整体视图中，尝试查找这个时间点对应的分P
        if (this.currentEpisode === null && this.episodeBoundaries && this.episodeBoundaries.length > 0) {
            const clickTimestampMs = event.timestamp;
            const clickTimestampSec = clickTimestampMs / 1000; // 转换为秒
            
            console.log(`点击时间戳: ${clickTimestampSec}秒 (${this.formatDuration(clickTimestampMs)})`);

            // 查找包含该时间点的分P
             for (const boundary of this.episodeBoundaries) {
                const startSec = boundary.start_time_sec || 0;
                const endSec = boundary.end_time_sec || 0;
                
                // 检查时间点是否在这个分P范围内
                if (clickTimestampSec >= startSec && clickTimestampSec <= endSec) {
                    console.log(`找到匹配的分P: ${boundary.page_id}, 范围: ${startSec}-${endSec}秒`);
                    this.switchEpisode(boundary.page_id);
        return;
      }
            }
            
            console.log("点击位置未匹配到任何分P");
        } else if (this.currentEpisode !== null) {
            // 如果已经在查看某个分P，点击事件可以返回到整体视图
            console.log("在分P视图中点击，返回整体视图");
            this.returnToOverallView();
        }
    },
    handleClickMarker(marker) {
        console.log('Marker clicked:', marker);
        // 可以在这里实现点击峰值标记点的交互，例如跳转到对应时间
        if (marker && marker.timestamp) {
            // 可以将视口中心移动到标记点时间
            // this.timelineViewport = { ...this.timelineViewport, center: marker.timestamp }; // vue-timeline-chart 可能不支持 center 属性，需要查看文档
        }
    },
    switchEpisode(pageId) {
        if (!pageId || !Array.isArray(this.episodeBoundaries)) {
            console.error(`无效的分P ID: ${pageId} 或边界数据不是数组`);
        return;
      }

        const targetBoundary = this.episodeBoundaries.find(b => b.page_id === pageId);
        if (!targetBoundary) {
            console.error(`找不到分P ${pageId} 的边界信息`);
            this.$message.warning(`无法切换到分P ${pageId}`);
        return;
      }

        if (this.currentEpisode === pageId) return;

        console.log(`切换到分P ${pageId}, 时间范围: ${targetBoundary.start_time_sec}s - ${targetBoundary.end_time_sec}s`);
        this.currentEpisode = pageId;

        // 计算边界
        const startMs = targetBoundary.start_time_sec * 1000;
        const endMs = targetBoundary.end_time_sec * 1000;
        
        // 设置视口范围，确保分P数据居中
        this.timelineViewport = {
            min: startMs,
            max: endMs
        };
        
        // 在下一个tick后，确保UI完成更新再执行居中操作
        this.$nextTick(() => {
            if (this.$refs.timelineChart) {
                // 如果组件有setViewport方法，直接调用
                if (typeof this.$refs.timelineChart.setViewport === 'function') {
                    this.$refs.timelineChart.setViewport(startMs, endMs);
                }
            }
        });
        
        console.log("更新后的视口范围:", this.timelineViewport);
    },
    returnToOverallView() {
      if (this.currentEpisode === null) return;
      
      console.log("返回整体视图");
      
      // 使用视频总时长设置视口
      const videoDurationMs = this.video && this.video.duration ? this.video.duration * 1000 : 0;
      let totalDurationMs = videoDurationMs;
      
      if (videoDurationMs <= 0 && this.episodeBoundaries && this.episodeBoundaries.length > 0) {
        // 备选：如果没有视频时长，使用最后一个分P的结束时间
        const lastBoundary = this.episodeBoundaries[this.episodeBoundaries.length - 1];
        if (lastBoundary && typeof lastBoundary.end_time_sec === 'number') {
          totalDurationMs = lastBoundary.end_time_sec * 1000;
        } else {
          totalDurationMs = 600 * 1000; // 默认10分钟
        }
      }
      
      // 先设置currentEpisode为null，这样会触发相关UI更新
      this.currentEpisode = null;
      
      // 设置整体视口
      this.timelineViewport = {
        min: 0,
        max: totalDurationMs
      };
      
      console.log(`设置整体视口: 0 - ${this.formatDuration(totalDurationMs)}`);
      
      // 确保在DOM更新后执行视口调整
      this.$nextTick(() => {
        if (this.$refs.timelineChart) {
          console.log("尝试调用setViewport...");
          // vue-timeline-chart组件的setViewport方法
          if (typeof this.$refs.timelineChart.setViewport === 'function') {
            try {
              this.$refs.timelineChart.setViewport(0, totalDurationMs);
              console.log("成功设置视口:", 0, totalDurationMs);
            } catch (error) {
              console.error("设置视口失败:", error);
            }
          } else {
            console.warn("Timeline组件没有setViewport方法");
            
            // 备选方案：尝试直接修改Timeline的props
            const timelineComponent = this.$refs.timelineChart;
            if (timelineComponent) {
              // 可能需要通过修改Timeline组件的内部状态来触发更新
              if (typeof timelineComponent.updateViewport === 'function') {
                timelineComponent.updateViewport(0, totalDurationMs);
                console.log("使用updateViewport方法更新视口");
              }
            }
          }
        } else {
          console.warn("找不到$refs.timelineChart引用");
        }
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

        // 返回的数据格式需要匹配 timelineMarkers 的计算属性需求
      return currentEpisodePeaks.map(peak => {
        const relative_time_sec = Math.max(0, (peak.time || 0) - startTimeSec);
        return {
               timestamp: relative_time_sec * 1000, // 需要毫秒时间戳
               count: peak.count, // 保留 count
               label: `峰值: ${peak.count}`, // 给 marker 一个标签
               // color: '#f56c6c' // 可以在 timelineMarkers 计算属性中设置
        };
      });
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
              // this.renderSentimentTimeline();
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
              // this.renderUserDistributionChart();
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
        this.currentEpisode = null; // 分析完成后回到整体视图

        // 初始化或更新视口
        this.updateTimelineViewport();

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
    },
    getHeatColor(count) {
        // 热力图颜色范围从蓝色(少)到红色(多)
        if (count <= 0) return 'rgba(220, 220, 220, 0.5)'; // 灰色，无弹幕
        
        // 颜色阈值
        const thresholds = [
            { count: 1, color: 'rgba(0, 128, 255, 0.6)' },    // 蓝色
            { count: 5, color: 'rgba(0, 200, 255, 0.7)' },    // 浅蓝色
            { count: 10, color: 'rgba(0, 255, 200, 0.7)' },   // 青色
            { count: 20, color: 'rgba(0, 255, 0, 0.7)' },     // 绿色
            { count: 50, color: 'rgba(255, 255, 0, 0.7)' },   // 黄色
            { count: 100, color: 'rgba(255, 128, 0, 0.8)' },  // 橙色
            { count: 200, color: 'rgba(255, 0, 0, 0.8)' },    // 红色
            { count: 500, color: 'rgba(255, 0, 128, 0.9)' },  // 紫红色
        ];
        
        // 找到适合的颜色
        for (const threshold of thresholds) {
            if (count < threshold.count) {
                return threshold.color;
            }
        }
        
        // 如果超过最高阈值，返回最高级别的颜色
        return 'rgba(255, 0, 255, 0.9)'; // 紫色，非常多的弹幕
    },
    logTimelineDataToConsole() {
      console.log('时间线数据:', this.timelineSummary);
      console.log('时间线项目:', this.timelineItems);
      console.log('时间线标记:', this.timelineMarkers);
    },
    handleViewportChange(viewport) {
      console.log('视口变化:', viewport);
      // 保存当前视口状态
      if (viewport && typeof viewport.start === 'number' && typeof viewport.end === 'number') {
        this.currentViewport = {
          start: viewport.start,
          end: viewport.end,
          duration: viewport.end - viewport.start
        };
        
        console.log(`保存当前视口: ${this.formatDuration(viewport.start)} - ${this.formatDuration(viewport.end)}`);
        
        // 如果是整体视图，也更新timelineViewport
        if (this.currentEpisode === null) {
          this.timelineViewport = {
            min: viewport.start,
            max: viewport.end
          };
        }
      }
    },
    formatCustomTimestamp(timestamp, scale) {
      // 根据不同的scale.unit选择不同的时间格式
      if (scale.unit === 'minutes') {
        // 分钟级别的时间戳
        return this.formatDuration(timestamp);
      } else if (scale.unit === 'seconds') {
        // 秒级别的时间戳，只显示分:秒
        const totalSeconds = Math.floor(timestamp / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      } else {
        // 其他级别，使用默认格式
        return this.formatDuration(timestamp);
      }
    },
    getCustomScales() {
      // 根据视频长度返回适当的时间刻度
      const duration = this.video.duration || 0; // 秒
      
      if (duration <= 0) {
        // 默认刻度
        return [
          { unit: 'seconds', steps: [5, 15, 30] },
          { unit: 'minutes', steps: [1, 5, 10] },
        ];
      }
      
      if (duration < 600) { // 小于10分钟
        return [
          { unit: 'seconds', steps: [5, 15, 30] },
          { unit: 'minutes', steps: [1, 2] },
        ];
      } else if (duration < 3600) { // 小于1小时
        return [
          { unit: 'seconds', steps: [30] },
          { unit: 'minutes', steps: [1, 5, 10] },
        ];
      } else { // 大于1小时
        return [
          { unit: 'minutes', steps: [1, 5, 10, 30] },
          { unit: 'hours', steps: [1] },
        ];
      }
    },
    handleEpisodeChange(pageId) {
      if (pageId === null) {
        this.returnToOverallView();
      } else if (pageId !== this.currentEpisode) {
        this.switchEpisode(pageId);
      }
    },
    showFullTimeline() {
      // 显示完整视频时间线
      console.log("显示完整视频时间线");
      
      const videoDurationMs = this.video && this.video.duration ? this.video.duration * 1000 : 0;
      let totalDurationMs = videoDurationMs;
      
      if (totalDurationMs <= 0 && this.episodeBoundaries && this.episodeBoundaries.length > 0) {
        // 如果没有视频时长，使用最后一个分P的结束时间
        const lastBoundary = this.episodeBoundaries[this.episodeBoundaries.length - 1];
        if (lastBoundary && typeof lastBoundary.end_time_sec === 'number') {
          totalDurationMs = lastBoundary.end_time_sec * 1000;
        } else {
          totalDurationMs = 600 * 1000; // 默认10分钟
        }
      }
      
      if (totalDurationMs <= 0) {
        this.$message.warning('无法确定视频时长');
        return;
      }
      
      // 设置视口
      console.log(`设置全局视口: 0 - ${this.formatDuration(totalDurationMs)}`);
      
      this.$nextTick(() => {
        if (this.$refs.timelineChart) {
          if (typeof this.$refs.timelineChart.setViewport === 'function') {
            try {
              this.$refs.timelineChart.setViewport(0, totalDurationMs);
              console.log("成功设置全局视口");
              
              // 同时更新timelineViewport
              this.timelineViewport = {
                min: 0,
                max: totalDurationMs
              };
            } catch (error) {
              console.error("设置全局视口失败:", error);
              this.$message.error('设置视口失败');
            }
          } else {
            console.warn("Timeline组件没有setViewport方法");
            this.$message.warning('无法设置视口');
          }
        }
      });
    }
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
    },
    timelineItems() {
        try {
            // 确保我们有有效的时间线数据
            if (!this.timelineSummary || !this.timelineSummary.timeline) {
                console.warn('无效的时间线数据');
                return [];
            }
            
            if (!Array.isArray(this.timelineSummary.timeline)) {
                console.warn('时间线数据不是数组格式');
                return [];
            }
            
            // 过滤掉没有时间或计数为零的记录
            const validTimeline = this.timelineSummary.timeline.filter(item => 
                item && typeof item.time === 'number' && item.count > 0
            );
            
            console.log(`有效时间线数据: ${validTimeline.length}条记录`);
            
            // 返回适合 vue-timeline-chart 的数据格式
            return validTimeline.map(item => {
                const startMs = (item.time || 0) * 1000; // 后端返回的是秒，转换为毫秒
                const endMs = startMs + 1000; // 每个点代表1秒
                const count = item.count || 0;
                
                return {
                    id: `item-${item.page_id || 0}-${item.time || 0}`,
                    type: 'range', // vue-timeline-chart要求指定类型
                    start: startMs,
                    end: endMs,
                    value: count, // 用于自定义渲染
                    title: `时间: ${this.formatDuration(startMs)}\n弹幕数: ${count}`,
                    cssVariables: {
                        '--item-background': this.getHeatColor(count),
                    }
                };
            });
        } catch (error) {
            console.error('生成时间线项目时出错:', error);
            return [];
        }
    },
    timelineMarkers() {
        try {
            const markers = [];
            
            // 添加分P边界标记
            if (Array.isArray(this.episodeBoundaries) && this.episodeBoundaries.length > 0) {
              // 在整体视图中显示分P边界
              if (this.currentEpisode === null) {
                this.episodeBoundaries.forEach((boundary, index) => {
                  if (typeof boundary.start_time_sec === 'number') {
                    // 添加分P起始标记
                    markers.push({
                      id: `page-start-${boundary.page_id}`,
                      type: 'point',
                      timestamp: boundary.start_time_sec * 1000,
                      label: `P${boundary.page_id}`,
                      title: `分P${boundary.page_id}开始`,
                      cssVariables: {
                        '--marker-background': '#409EFF',
                        '--marker-color': '#fff'
                      }
                    });
                  }
                });
              }
            }
            
            // 添加峰值标记
            if (Array.isArray(this.timelineSummary?.peaks) && this.timelineSummary.peaks.length > 0) {
              // 筛选当前分P的峰值，或在整体视图中显示全部峰值
              let peaksToShow = this.timelineSummary.peaks;
              
              if (this.currentEpisode !== null) {
                // 只显示当前分P的峰值
                peaksToShow = peaksToShow.filter(peak => peak.page_id === this.currentEpisode);
                
                // 使用原始时间，不再计算相对时间
                peaksToShow.forEach(peak => {
                  if (typeof peak.time === 'number' && peak.count > 0) {
                    markers.push({
                      id: `peak-${peak.page_id}-${peak.time}`,
                      type: 'point',
                      timestamp: peak.time * 1000, // 使用原始时间（毫秒）
                      label: `${peak.count}`,
                      title: `峰值: ${peak.count}条弹幕 (${this.formatDuration(peak.time * 1000)})`,
                      cssVariables: {
                        '--marker-background': '#E6A23C',
                        '--marker-color': '#333'
                      }
                    });
                  }
                });
              } else {
                // 在整体视图中显示所有峰值
                // 仅显示前N个最高峰值，避免太多标记导致拥挤
                const topPeaks = [...peaksToShow]
                  .sort((a, b) => b.count - a.count)
                  .slice(0, 10); // 最多显示10个峰值
                
                topPeaks.forEach(peak => {
                  if (typeof peak.time === 'number' && peak.count > 0) {
                    markers.push({
                      id: `peak-${peak.page_id}-${peak.time}`,
                      type: 'point',
                      timestamp: peak.time * 1000,
                      label: `${peak.count}`,
                      title: `峰值: ${peak.count}条弹幕 (${this.formatDuration(peak.time * 1000)})`,
                      cssVariables: {
                        '--marker-background': '#E6A23C',
                        '--marker-color': '#333'
                      }
                    });
                  }
                });
              }
            }
            
            // 修改时间间隔标记逻辑，使用绝对时间
            if (this.currentEpisode !== null) {
              const boundary = this.episodeBoundaries.find(b => b.page_id === this.currentEpisode);
              if (boundary && typeof boundary.duration_sec === 'number' && boundary.duration_sec > 0) {
                const startTimeSec = boundary.start_time_sec || 0;
                const endTimeSec = boundary.end_time_sec || 0;
                const durationSec = boundary.duration_sec;
                const intervalSec = durationSec > 300 ? 60 : 30; // 根据分P长度决定间隔
                
                for (let timeSec = startTimeSec + intervalSec; timeSec < endTimeSec; timeSec += intervalSec) {
                  markers.push({
                    id: `time-${timeSec}`,
                    type: 'point',
                    timestamp: timeSec * 1000, // 使用绝对时间（毫秒）
                    label: this.formatDuration(timeSec * 1000),
                    cssVariables: {
                      '--marker-background': 'rgba(144, 147, 153, 0.3)', // 浅灰色
                      '--marker-color': '#606266'
                    }
                  });
                }
              }
            }
            
            return markers;
        } catch (error) {
            console.error('生成时间线标记时出错:', error);
            return [];
        }
    },
    formattedTimelineData() {
      if (!this.timelineSummary || !Array.isArray(this.timelineSummary.timeline)) {
        return [];
      }
      
      let timelineData = this.timelineSummary.timeline;
      
      // 如果是查看某个特定分P，需要筛选该分P的数据
      if (this.currentEpisode !== null) {
        const boundary = this.episodeBoundaries.find(b => b.page_id === this.currentEpisode);
        if (!boundary) return [];
        
        // 筛选当前分P的数据点
        timelineData = timelineData.filter(item => item.page_id === this.currentEpisode);
        
        // 返回原始时间数据，不再减去起始时间
        return timelineData.map(item => ({
          start: item.time * 1000, // 保持原始时间（毫秒）
          value: item.count || 0
        }));
      }
      
      // 整体视图，直接转换
      return timelineData.map(item => ({
        start: item.time * 1000, // 转换为毫秒
        value: item.count || 0
      }));
    }
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.handleTimelineResize);
  },
  // 添加侦听器
  watch: {
    currentEpisode(newValue, oldValue) {
      if (newValue !== oldValue) {
        console.log(`分P切换: ${oldValue} -> ${newValue}`);
        // 确保视图更新
        this.$nextTick(() => {
          if (this.$refs.timelineChart && newValue !== null) {
            const boundary = this.episodeBoundaries.find(b => b.page_id === newValue);
            if (boundary) {
              const startMs = boundary.start_time_sec * 1000;
              const endMs = boundary.end_time_sec * 1000;
              // 更新视口
              if (typeof this.$refs.timelineChart.setViewport === 'function') {
                this.$refs.timelineChart.setViewport(startMs, endMs);
              }
            }
          }
        });
      }
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

/* 为 vue-timeline-chart 添加一些基本样式 */
.vue-timeline-chart {
  font-family: Avenir, Helvetica, Arial, sans-serif;
}

/* 覆盖一些默认样式或添加自定义样式 (如果需要) */
.vue-timeline-chart .marker .label {
  font-size: 10px;
  color: #333;
}

/* 处理无数据消息 */
.no-data-message {
  margin: 20px 0;
}

.no-data-message .el-alert {
  margin-bottom: 10px;
}

.no-data-message ul {
  margin: 5px 0;
  padding-left: 20px;
}

.no-data-message li {
  margin: 3px 0;
}

.debug-info {
  margin: 20px 0;
  padding: 10px;
  background: #f8f9fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.debug-info h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.debug-info p {
  margin: 5px 0;
}

.debug-info .el-button {
  margin-top: 10px;
}

.timeline-container {
  margin-top: 20px;
}

.episode-navigation {
  margin-bottom: 15px;
  display: flex;
  justify-content: center;
}

.chart-info {
  margin-top: 15px;
  text-align: center;
  color: #606266;
  font-size: 14px;
}

/* 确保折线图在组件中正确显示 */
:deep(.vue-timeline-chart .group-items) {
  overflow: visible !important;
}

:deep(.vue-timeline-chart) {
  --marker-label-color: #333;
  --timestamp-label-color: #333;
}

.debug-info h5 {
  margin-top: 10px;
  margin-bottom: 5px;
}

.debug-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.debug-col {
  flex: 1;
  min-width: 200px;
}

.debug-data-sample {
  margin-top: 10px;
  border-top: 1px dashed #ddd;
  padding-top: 10px;
}

.debug-buttons {
  margin-top: 15px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

/* 增强时间线和折线图显示效果 */
.timeline-chart-container {
  --group-items-height: 450px !important; /* 增加高度 */
  --group-header-height: 40px;
  --navigation-height: 50px;
  margin: 0 !important;
  padding: 0 !important;
  background-color: transparent !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  max-height: 550px !important;
}

/* 添加分P切换组 */
.episode-navigation {
  margin: 10px 0;
  text-align: center;
}

/* 确保卡片内容溢出控制 */
.el-card__body {
  height: calc(100% - 60px);
  overflow-y: auto;
}

/* 修复no-data-message样式 */
.no-data-message {
  margin: 20px auto;
  max-width: 90%;
}

/* 添加返回顶部按钮 */
.return-to-top {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 99;
}

.timeline-line-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 550px;
}

.timeline-container {
  width: 100%;
  height: 250px;
  position: relative;
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 10px;
}

.line-chart-container {
  width: 100%;
  height: 250px;
  position: relative;
  background-color: #f5f7fa;
  border-radius: 4px;
  padding: 10px;
}

.vue-timeline-chart :deep(.group) {
  height: 60px;
}

.vue-timeline-chart :deep(.group-label) {
  font-size: 14px;
  font-weight: bold;
}

.vue-timeline-chart :deep(.group-item) {
  height: 35px;
  transition: transform 0.2s, opacity 0.2s;
}

.vue-timeline-chart :deep(.group-item:hover) {
  transform: scale(1.05);
  opacity: 0.9;
}

.vue-timeline-chart :deep(.marker) {
  opacity: 0.7;
  transition: opacity 0.2s, transform 0.2s;
}

.vue-timeline-chart :deep(.marker:hover) {
  opacity: 1;
  transform: scale(1.1);
}

.vue-timeline-chart :deep(.timestamp) {
  font-weight: normal;
  font-size: 12px;
}

.no-data-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #909399;
  font-size: 14px;
}

.line-chart-wrapper {
  width: 100%;
  height: 280px;
  margin: 20px 0;
  padding: 10px;
  border-radius: 8px;
  background-color: var(--el-fill-color-lighter);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.line-chart-wrapper:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.current-view-info {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 10px;
}

.chart-actions {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.peak-tag {
  cursor: pointer;
  margin-right: 10px;
  font-weight: bold;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
}

.peak-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.peak-tag .el-icon {
  margin-right: 4px;
}

.marker-tag {
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
}

.marker-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background-color: var(--el-color-info-light-5);
}

.marker-tag .el-icon {
  margin-right: 4px;
}

.view-controls {
  display: flex;
  align-items: center;
}

.view-controls .el-button {
  margin-left: 10px;
}
</style> 