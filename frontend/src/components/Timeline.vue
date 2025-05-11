<template>
  <div class="timeline-container">
    <div v-if="!timelineItems || timelineItems.length === 0" class="no-data">
      <div class="empty-message">暂无时间线数据</div>
    </div>
    
    <template v-else>
      <div class="timeline-chart">
        <LineChart 
          :viewportStart="0" 
          :viewportEnd="getMaxTime()" 
          :data="formattedData"
          :height="450" 
          :lineColor="'rgba(64, 158, 255, 0.9)'"
          :fillColor="'rgba(64, 158, 255, 0.1)'"
          :lineWidth="2"
          :pointRadius="4"
          :smooth="true"
          :showGrid="true"
          ref="lineChart"
        />
      </div>
      
      <div class="timeline-items">
        <div 
          v-for="item in sortedItems" 
          :key="item.id" 
          class="timeline-item"
          @click="handleItemClick(item)"
        >
          <div class="time">{{ formatTime(item.time) }}</div>
          <div class="count">{{ item.count }} 条弹幕</div>
          <div class="preview" @click.stop="previewDanmaku(item)">
            <el-button size="mini" type="text" icon="el-icon-view">预览</el-button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import LineChart from './LineChart.vue';

export default {
  name: 'Timeline',
  components: { LineChart },
  props: {
    timelineItems: {
      type: Array,
      required: true
    },
    summary: {
      type: Object,
      default: () => ({})
    }
  },
  mounted() {
    console.log("Timeline组件已挂载，数据项：", this.timelineItems.length);
    console.log("第一条数据：", this.timelineItems[0]);
  },
  computed: {
    sortedItems() {
      // 按时间排序
      if (!this.timelineItems || this.timelineItems.length === 0) {
        return [];
      }
      return [...this.timelineItems].sort((a, b) => a.time - b.time);
    },
    formattedData() {
      // 转换为LineChart可用的数据格式
      if (!this.timelineItems || this.timelineItems.length === 0) {
        return [];
      }
      return this.timelineItems.map(item => ({
        start: item.time,
        value: item.count
      }));
    }
  },
  methods: {
    getMaxTime() {
      if (!this.timelineItems || this.timelineItems.length === 0) return 600000; // 默认10分钟
      
      // 找出最大时间
      const maxTime = Math.max(...this.timelineItems.map(item => item.time));
      return maxTime + 60000; // 加一分钟作为缓冲
    },
    formatTime(timestamp) {
      if (!timestamp && timestamp !== 0) return "--:--";
      
      // 格式化时间为时:分:秒
      const totalSeconds = Math.floor(timestamp / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      
      if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      } else {
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
      }
    },
    handleItemClick(item) {
      console.log("点击了时间线项目:", item);
      this.$emit('clickTimelineItem', item);
    },
    previewDanmaku(item) {
      console.log("预览弹幕:", item);
      this.$emit('previewDanmaku', item);
    },
    setViewport(start, end) {
      console.log("设置时间线视口:", start, end);
      // 在这里实现视口范围控制的逻辑
      // 由于我们的LineChart没有直接的视口控制，这里可以通过更新组件内部状态实现
      if (this.$refs.lineChart) {
        // 如果LineChart组件有设置视口的方法，可以调用它
        if (typeof this.$refs.lineChart.setViewport === 'function') {
          this.$refs.lineChart.setViewport(start, end);
        }
      }
    }
  }
};
</script>

<style scoped>
.timeline-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  background-color: #fff;
  overflow: hidden;
}

.timeline-chart {
  flex: 2;
  min-height: 300px;
  padding: 10px;
  border-bottom: 1px solid #EBEEF5;
}

.timeline-items {
  flex: 1;
  overflow-y: auto;
  max-height: 250px;
  padding: 0;
}

.timeline-item {
  display: flex;
  align-items: center;
  padding: 8px 15px;
  border-bottom: 1px solid #EBEEF5;
  cursor: pointer;
}

.timeline-item:hover {
  background-color: #f5f7fa;
}

.timeline-item .time {
  width: 100px;
  font-weight: bold;
  color: #303133;
}

.timeline-item .count {
  flex: 1;
  color: #606266;
}

.timeline-item .preview {
  margin-left: 10px;
}

.no-data {
  padding: 20px;
  text-align: center;
  color: #909399;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}

.empty-message {
  font-size: 14px;
  color: #909399;
}
</style>