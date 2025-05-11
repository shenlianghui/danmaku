<template>
  <div class="line-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="no-data">
      暂无数据
    </div>
    <div v-else-if="visibleData && visibleData.length < 2" class="not-enough-data">
      当前视图中数据点不足，请尝试放大视图
    </div>
  </div>
</template>

<script>
export default {
  name: 'LineChart',
  props: {
    // 视口开始时间（毫秒）
    viewportStart: {
      type: Number,
      required: true
    },
    // 视口结束时间（毫秒）
    viewportEnd: {
      type: Number,
      required: true
    },
    // 数据点数组，预期格式：[{start: 时间戳, value: 数值}, ...]
    data: {
      type: Array,
      required: true
    },
    // 图表高度
    height: {
      type: Number,
      default: 350
    },
    // 线条颜色
    lineColor: {
      type: String,
      default: 'rgba(64, 158, 255, 1)'
    },
    // 填充颜色
    fillColor: {
      type: String,
      default: 'rgba(64, 158, 255, 0.1)'
    },
    // 线条宽度
    lineWidth: {
      type: Number,
      default: 2
    },
    // 数据点半径
    pointRadius: {
      type: Number,
      default: 4
    },
    // 是否显示网格
    showGrid: {
      type: Boolean,
      default: true
    },
    // 是否平滑曲线
    smooth: {
      type: Boolean,
      default: true
    },
    // 分P边界数据
    episodeBoundaries: {
      type: Array,
      default: () => []
    },
    // Y轴最小值（可选）
    yAxisMin: {
      type: Number,
      default: null
    },
    // Y轴最大值（可选）
    yAxisMax: {
      type: Number,
      default: null
    },
    // Y轴标签（可选）
    yAxisLabel: {
      type: String,
      default: ''
    },
    // 是否为数据点着色
    colorPoints: {
      type: Boolean,
      default: false
    },
    // 获取数据点颜色的函数
    getPointColor: {
      type: Function,
      default: null
    },
    // 自定义提示格式化函数
    tooltipFormatter: {
      type: Function,
      default: null
    }
  },
  data() {
    return {
      chart: null,
      observer: null,
      visibleData: [],
      hoveredPoint: null,
      stats: {
        max: 0,
        average: 0,
        total: 0
      },
      activePoint: null,
      resizeTimeout: null  // 添加ResizeTimeout变量，用于防抖处理
    };
  },
  watch: {
    viewportStart() {
      this.updateVisibleData();
      this.drawChart();
    },
    viewportEnd() {
      this.updateVisibleData();
      this.drawChart();
    },
    data: {
      deep: true,
      handler() {
        this.updateVisibleData();
        this.drawChart();
      }
    }
  },
  mounted() {
    this.updateVisibleData();
    this.initChart();
    
    // 添加ResizeObserver以便在容器大小变化时重绘图表
    try {
      this.observer = new ResizeObserver(entries => {
        if (this.resizeTimeout) clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => {
          if (this.$refs.chartContainer) {
            this.drawChart();
          }
        }, 60); // 60ms延迟，避免同步触发
      });
      if (this.$refs.chartContainer) {
        this.observer.observe(this.$refs.chartContainer);
      }
    } catch (err) {
      console.error('Failed to create ResizeObserver:', err);
    }
  },
  beforeUnmount() {
    if (this.observer) {
      try {
        this.observer.disconnect();
      } catch (err) {
        console.error('Error disconnecting observer:', err);
      }
    }
    if (this.resizeTimeout) {
      clearTimeout(this.resizeTimeout);
    }
  },
  methods: {
    updateVisibleData() {
      // 计算可见数据点
      this.visibleData = this.data
        .filter(item => item.start >= this.viewportStart && item.start <= this.viewportEnd)
        .sort((a, b) => a.start - b.start);
    },
    initChart() {
      this.drawChart();
    },
    setViewport(start, end) {
      // 设置视口范围，更新可见数据点并重绘图表
      if (typeof start === 'number' && typeof end === 'number' && start < end) {
        console.log(`LineChart.setViewport(${start}, ${end})`);
        // 更新视口
        this._viewportStart = start;
        this._viewportEnd = end;
        // 更新可见数据
        this.updateVisibleData();
        // 重绘图表
        this.drawChart();
      }
    },
    drawChart() {
      const container = this.$refs.chartContainer;
      if (!container) return;
      
      // 清空容器，保留可能存在的消息元素
      const noData = container.querySelector('.no-data');
      const notEnough = container.querySelector('.not-enough-data');
      if (noData) noData.style.display = 'none';
      if (notEnough) notEnough.style.display = 'none';
      
      // 检查数据
      if (!this.data || this.data.length === 0) {
        if (noData) noData.style.display = 'flex';
        return;
      }
      
      if (this.visibleData.length < 2) {
        if (notEnough) notEnough.style.display = 'flex';
        return;
      }
      
      // 移除旧的SVG
      const oldSvg = container.querySelector('svg');
      if (oldSvg) container.removeChild(oldSvg);
      
      // 获取容器尺寸
      const width = container.clientWidth;
      const height = this.height;
      
      // 计算边距，增加底部边距以显示X轴标签
      const margin = { top: 30, right: 30, bottom: 50, left: 50 };
      const chartWidth = width - margin.left - margin.right;
      const chartHeight = height - margin.top - margin.bottom;
      
      // 计算X轴和Y轴的比例
      const xScale = chartWidth / (this.viewportEnd - this.viewportStart);
      
      // 找出数据的最大值和最小值
      const mergedData = this.mergeDataPoints(this.visibleData, null, xScale);
      let maxValue = Math.max(...mergedData.map(d => d.value));
      let minValue = Math.min(...mergedData.map(d => d.value));
      
      // 使用自定义的Y轴范围（如果提供）
      if (this.yAxisMin !== null) {
        minValue = this.yAxisMin;
      }
      if (this.yAxisMax !== null) {
        maxValue = this.yAxisMax;
      }
      
      const valueRange = maxValue - minValue;
      const yScale = chartHeight / (valueRange > 0 ? valueRange : 1);
      
      // 创建SVG元素
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', width);
      svg.setAttribute('height', height);
      svg.setAttribute('class', 'line-chart-svg');
      container.appendChild(svg);
      
      // 创建图表组，应用边距
      const chartGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      chartGroup.setAttribute('transform', `translate(${margin.left}, ${margin.top})`);
      svg.appendChild(chartGroup);
      
      // 添加网格线
      if (this.showGrid) {
        this.drawGrid(chartGroup, chartWidth, chartHeight, maxValue, minValue);
      }
      
      // 添加X轴
      this.drawXAxis(chartGroup, chartWidth, chartHeight, xScale);
      
      // 添加折线和面积
      this.drawLineAndArea(chartGroup, chartWidth, chartHeight, xScale, yScale, maxValue, minValue, mergedData);
      
      // 添加数据点
      this.drawDataPoints(chartGroup, xScale, yScale, chartHeight, maxValue, minValue, mergedData);
      
      // 添加统计信息
      this.drawStats(chartGroup, chartWidth, chartHeight, maxValue, minValue);
      
      // 添加悬停交互
      this.setupHoverInteraction(chartGroup, xScale, yScale, chartHeight, chartWidth, margin, maxValue, minValue, mergedData);
    },
    
    drawGrid(chartGroup, width, height, maxValue, minValue) {
      // 添加水平网格线
      const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      gridGroup.setAttribute('class', 'grid-lines');
      
      // 计算网格线间隔
      const gridCount = 5;
      const gridStep = height / gridCount;
      const valueStep = (maxValue - minValue) / gridCount;
      
      // 添加Y轴标签（如果提供）
      if (this.yAxisLabel) {
        const yAxisLabelElem = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yAxisLabelElem.setAttribute('transform', `rotate(-90)`);
        yAxisLabelElem.setAttribute('x', -height / 2);
        yAxisLabelElem.setAttribute('y', -35);
        yAxisLabelElem.setAttribute('font-size', '12');
        yAxisLabelElem.setAttribute('text-anchor', 'middle');
        yAxisLabelElem.setAttribute('fill', 'rgba(0,0,0,0.7)');
        yAxisLabelElem.textContent = this.yAxisLabel;
        gridGroup.appendChild(yAxisLabelElem);
      }
      
      // 添加水平网格线
      for (let i = 0; i <= gridCount; i++) {
        const y = i * gridStep;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', 0);
        line.setAttribute('y1', y);
        line.setAttribute('x2', width);
        line.setAttribute('y2', y);
        line.setAttribute('stroke', 'rgba(0,0,0,0.1)');
        line.setAttribute('stroke-width', '1');
        line.setAttribute('stroke-dasharray', '3,3');
        gridGroup.appendChild(line);
        
        // 添加Y轴刻度值
        const value = minValue + (maxValue - minValue) * (1 - i / gridCount);
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', -5);
        text.setAttribute('y', y + 4); // 调整垂直位置以对齐网格线
        text.setAttribute('font-size', '11');
        text.setAttribute('text-anchor', 'end');
        text.setAttribute('fill', 'rgba(0,0,0,0.6)');
        text.textContent = value.toFixed(2);
        gridGroup.appendChild(text);
      }
      
      chartGroup.appendChild(gridGroup);
    },
    
    drawXAxis(chartGroup, width, height, xScale) {
      const axisGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      axisGroup.setAttribute('class', 'x-axis');
      axisGroup.setAttribute('transform', `translate(0, ${height})`);
      
      // X轴线
      const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      axisLine.setAttribute('x1', 0);
      axisLine.setAttribute('y1', 0);
      axisLine.setAttribute('x2', width);
      axisLine.setAttribute('y2', 0);
      axisLine.setAttribute('stroke', 'rgba(0,0,0,0.3)');
      axisLine.setAttribute('stroke-width', '1');
      axisGroup.appendChild(axisLine);
      
      // 计算时间范围（分钟数）
      const totalMinutes = Math.ceil((this.viewportEnd - this.viewportStart) / 60000);
      
      // 确定合适的刻度数量，不超过10个
      const tickCount = Math.min(10, totalMinutes);
      const tickStep = width / tickCount;
      
      for (let i = 0; i <= tickCount; i++) {
        const x = i * tickStep;
        const time = this.viewportStart + (i * (this.viewportEnd - this.viewportStart) / tickCount);
        
        // 刻度线
        const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        tick.setAttribute('x1', x);
        tick.setAttribute('y1', 0);
        tick.setAttribute('x2', x);
        tick.setAttribute('y2', 5);
        tick.setAttribute('stroke', 'rgba(0,0,0,0.3)');
        tick.setAttribute('stroke-width', '1');
        axisGroup.appendChild(tick);
        
        // 时间标签
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', 18);
        text.setAttribute('font-size', '11');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', 'rgba(0,0,0,0.6)');
        text.textContent = this.formatTime(time);
        axisGroup.appendChild(text);
      }
      
      chartGroup.appendChild(axisGroup);
    },
    
    drawLineAndArea(chartGroup, width, height, xScale, yScale, maxValue, minValue, mergedData) {
      if (mergedData.length < 2) return;
      
      // 创建路径组
      const pathGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      pathGroup.setAttribute('class', 'path-group');
      
      // 生成折线路径
      let linePath = '';
      let areaPath = '';
      
      mergedData.forEach((point, index) => {
        const x = (point.start - this.viewportStart) * xScale;
        const y = height - (point.value - minValue) * yScale;
        
        if (index === 0) {
          linePath += `M ${x} ${y}`;
          areaPath += `M ${x} ${height} L ${x} ${y}`;
        } else if (this.smooth && index > 0 && index < mergedData.length) {
          // 使用贝塞尔曲线平滑连接点
          const prevPoint = mergedData[index - 1];
          const prevX = (prevPoint.start - this.viewportStart) * xScale;
          const prevY = height - (prevPoint.value - minValue) * yScale;
          
          const cpX1 = prevX + (x - prevX) / 3;
          const cpX2 = prevX + 2 * (x - prevX) / 3;
          
          linePath += ` C ${cpX1} ${prevY}, ${cpX2} ${y}, ${x} ${y}`;
          areaPath += ` C ${cpX1} ${prevY}, ${cpX2} ${y}, ${x} ${y}`;
        } else {
          linePath += ` L ${x} ${y}`;
          areaPath += ` L ${x} ${y}`;
        }
        
        if (index === mergedData.length - 1) {
          areaPath += ` L ${x} ${height} Z`;
        }
      });
      
      // 创建面积填充
      const areaElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      areaElement.setAttribute('d', areaPath);
      areaElement.setAttribute('fill', this.fillColor);
      areaElement.setAttribute('class', 'area-path');
      pathGroup.appendChild(areaElement);
      
      // 创建折线
      const lineElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      lineElement.setAttribute('d', linePath);
      lineElement.setAttribute('fill', 'none');
      lineElement.setAttribute('stroke', this.lineColor);
      lineElement.setAttribute('stroke-width', this.lineWidth);
      lineElement.setAttribute('class', 'line-path');
      pathGroup.appendChild(lineElement);
      
      chartGroup.appendChild(pathGroup);
    },
    
    drawDataPoints(chartGroup, xScale, yScale, chartHeight, maxValue, minValue, mergedData) {
      // 创建数据点组
      const pointsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      pointsGroup.setAttribute('class', 'data-points');
      
      // 绘制每个数据点
      mergedData.forEach(point => {
        const x = (point.start - this.viewportStart) * xScale;
        const y = chartHeight - (point.value - minValue) * yScale;
        
        // 创建点
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', this.pointRadius);
        
        // 设置填充颜色 - 支持自定义颜色
        let fillColor = 'white';
        let strokeColor = this.lineColor;
        
        if (this.colorPoints && this.getPointColor && typeof this.getPointColor === 'function') {
          try {
            fillColor = this.getPointColor(point) || fillColor;
            strokeColor = fillColor; // 使用相同的颜色作为边框
          } catch (err) {
            console.error('获取数据点颜色失败:', err);
          }
        }
        
        circle.setAttribute('fill', fillColor);
        circle.setAttribute('stroke', strokeColor);
        circle.setAttribute('stroke-width', '2');
        circle.setAttribute('class', 'data-point');
        
        // 添加数据属性用于交互
        circle.setAttribute('data-time', point.start);
        circle.setAttribute('data-value', point.value);
        
        // 计算分钟结束时间
        const endTime = point.start + 60000;
        
        // 添加提示
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        
        // 使用自定义工具提示格式化器（如果提供）
        if (this.tooltipFormatter && typeof this.tooltipFormatter === 'function') {
          title.innerHTML = this.tooltipFormatter(point);
        } else {
          title.textContent = `时间段: ${this.formatTime(point.start)} - ${this.formatTime(endTime)}\n弹幕数: ${point.value}`;
        }
        
        circle.appendChild(title);
        pointsGroup.appendChild(circle);
      });
      
      chartGroup.appendChild(pointsGroup);
    },
    
    mergeDataPoints(data, barWidth, xScale) {
      if (data.length === 0) return [];
      
      // 计算合并的时间间隔 (固定为1分钟 = 60000毫秒)
      const minuteInterval = 60000; // 1分钟 = 60000毫秒
      
      // 按分钟分组
      const minuteGroups = {};
      
      // 对数据按时间排序
      const sortedData = [...data].sort((a, b) => a.start - b.start);
      
      // 按分钟分组
      sortedData.forEach(point => {
        // 将时间戳向下取整到最近的分钟
        const minuteTimestamp = Math.floor(point.start / minuteInterval) * minuteInterval;
        
        if (!minuteGroups[minuteTimestamp]) {
          minuteGroups[minuteTimestamp] = {
            start: minuteTimestamp,
            value: 0,
            count: 0
          };
        }
        
        minuteGroups[minuteTimestamp].value += point.value;
        minuteGroups[minuteTimestamp].count += 1;
      });
      
      // 转换为数组并计算平均值
      const result = Object.values(minuteGroups).map(group => ({
        start: group.start,
        value: group.value, // 保留总和而不是平均值，因为我们需要弹幕总数
        originalValue: group.value,
        count: group.count
      }));
      
      // 按时间排序
      return result.sort((a, b) => a.start - b.start);
    },
    
    drawStats(chartGroup, width, height, maxValue, minValue) {
      // 计算统计信息
      const avgValue = this.visibleData.reduce((sum, d) => sum + d.value, 0) / this.visibleData.length;
      const totalPoints = this.visibleData.length;
      
      // 创建半透明背景
      const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      bgRect.setAttribute('x', width - 120);
      bgRect.setAttribute('y', 5);
      bgRect.setAttribute('width', 115);
      bgRect.setAttribute('height', 65);
      bgRect.setAttribute('fill', 'rgba(255, 255, 255, 0.8)');
      bgRect.setAttribute('rx', '4');
      bgRect.setAttribute('ry', '4');
      bgRect.setAttribute('stroke', 'rgba(0, 0, 0, 0.1)');
      bgRect.setAttribute('stroke-width', '1');
      
      // 添加统计信息文本
      const statsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      statsGroup.setAttribute('class', 'stats');
      statsGroup.appendChild(bgRect);
      
      const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      titleText.setAttribute('x', width - 110);
      titleText.setAttribute('y', 20);
      titleText.setAttribute('font-size', '12');
      titleText.setAttribute('font-weight', 'bold');
      titleText.setAttribute('fill', 'rgba(0,0,0,0.8)');
      titleText.textContent = '数据统计';
      statsGroup.appendChild(titleText);
      
      const maxText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      maxText.setAttribute('x', width - 110);
      maxText.setAttribute('y', 38);
      maxText.setAttribute('font-size', '11');
      maxText.setAttribute('fill', 'rgba(0,0,0,0.7)');
      maxText.textContent = `最大值: ${maxValue}`;
      statsGroup.appendChild(maxText);
      
      const avgText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      avgText.setAttribute('x', width - 110);
      avgText.setAttribute('y', 53);
      avgText.setAttribute('font-size', '11');
      avgText.setAttribute('fill', 'rgba(0,0,0,0.7)');
      avgText.textContent = `平均值: ${Math.round(avgValue * 10) / 10}`;
      statsGroup.appendChild(avgText);
      
      const countText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      countText.setAttribute('x', width - 110);
      countText.setAttribute('y', 68);
      countText.setAttribute('font-size', '11');
      countText.setAttribute('fill', 'rgba(0,0,0,0.7)');
      countText.textContent = `数据点: ${totalPoints}`;
      statsGroup.appendChild(countText);
      
      chartGroup.appendChild(statsGroup);
    },
    
    setupHoverInteraction(chartGroup, xScale, yScale, height, width, margin, maxValue, minValue, mergedData) {
      // 创建悬停线和信息框
      const hoverGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      hoverGroup.setAttribute('class', 'hover-elements');
      hoverGroup.style.display = 'none';
      
      // 垂直线
      const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      vLine.setAttribute('x1', 0);
      vLine.setAttribute('y1', 0);
      vLine.setAttribute('x2', 0);
      vLine.setAttribute('y2', height);
      vLine.setAttribute('stroke', 'rgba(0,0,0,0.4)');
      vLine.setAttribute('stroke-width', '1.5');
      vLine.setAttribute('stroke-dasharray', '3,3');
      hoverGroup.appendChild(vLine);
      
      // 悬停点
      const hoverPoint = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      hoverPoint.setAttribute('r', this.pointRadius + 2);
      hoverPoint.setAttribute('fill', this.lineColor);
      hoverPoint.setAttribute('stroke', 'white');
      hoverPoint.setAttribute('stroke-width', '2');
      hoverGroup.appendChild(hoverPoint);
      
      // 信息框背景 - 调整高度以容纳分P信息
      const infoRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      infoRect.setAttribute('rx', '4');
      infoRect.setAttribute('ry', '4');
      infoRect.setAttribute('fill', 'white');
      infoRect.setAttribute('stroke', 'rgba(0,0,0,0.2)');
      infoRect.setAttribute('stroke-width', '1');
      infoRect.setAttribute('width', '140');
      infoRect.setAttribute('height', '80'); // 增加高度
      infoRect.setAttribute('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))');
      hoverGroup.appendChild(infoRect);
      
      // 标题背景
      const titleBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      titleBg.setAttribute('rx', '4');
      titleBg.setAttribute('ry', '0');
      titleBg.setAttribute('fill', 'rgba(64, 158, 255, 0.9)');
      titleBg.setAttribute('width', '140');
      titleBg.setAttribute('height', '22');
      hoverGroup.appendChild(titleBg);
      
      // 标题文本
      const titleText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      titleText.setAttribute('font-size', '12');
      titleText.setAttribute('font-weight', 'bold');
      titleText.setAttribute('fill', 'white');
      titleText.setAttribute('x', '10');
      titleText.setAttribute('y', '16');
      titleText.textContent = '弹幕数据';
      hoverGroup.appendChild(titleText);
      
      // 时间文本
      const timeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      timeText.setAttribute('font-size', '11');
      timeText.setAttribute('fill', 'rgba(0,0,0,0.7)');
      timeText.setAttribute('x', '10');
      timeText.setAttribute('y', '38');
      hoverGroup.appendChild(timeText);
      
      // 值文本
      const valueText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      valueText.setAttribute('font-size', '14');
      valueText.setAttribute('font-weight', 'bold');
      valueText.setAttribute('fill', 'rgba(0,0,0,0.8)');
      valueText.setAttribute('x', '10');
      valueText.setAttribute('y', '55');
      hoverGroup.appendChild(valueText);
      
      // 添加分P信息文本
      const episodeText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      episodeText.setAttribute('font-size', '11');
      episodeText.setAttribute('fill', 'rgba(0,0,0,0.7)');
      episodeText.setAttribute('x', '10');
      episodeText.setAttribute('y', '72');
      hoverGroup.appendChild(episodeText);
      
      chartGroup.appendChild(hoverGroup);
      
      // 添加鼠标移动事件
      const svg = chartGroup.ownerSVGElement;
      svg.addEventListener('mousemove', (event) => {
        const rect = svg.getBoundingClientRect();
        const mouseX = event.clientX - rect.left - margin.left;
        
        // 找到最近的数据点
        const hoverTime = this.viewportStart + (mouseX / xScale);
        let closestPoint = null;
        let minDistance = Infinity;
        
        for (const point of mergedData) {
          const distance = Math.abs(point.start - hoverTime);
          if (distance < minDistance) {
            minDistance = distance;
            closestPoint = point;
          }
        }
        
        if (closestPoint) {
          const pointX = (closestPoint.start - this.viewportStart) * xScale;
          const pointY = height - (closestPoint.value - minValue) * yScale;
          
          // 将时间戳向下取整到最近的分钟
          const minuteTimestamp = closestPoint.start;
          const endMinuteTimestamp = minuteTimestamp + 60000;
          
          // 查找当前时间点所在的分P
          let episodeInfo = '整体视图';
          if (Array.isArray(this.episodeBoundaries) && this.episodeBoundaries.length > 0) {
            const timestampSec = minuteTimestamp / 1000;
            for (const boundary of this.episodeBoundaries) {
              const startSec = boundary.start_time_sec || 0;
              const endSec = boundary.end_time_sec || 0;
              
              if (timestampSec >= startSec && timestampSec <= endSec) {
                episodeInfo = `分P ${boundary.page_id || '?'}`;
                break;
              }
            }
          }
          
          // 更新垂直线位置
          vLine.setAttribute('x1', pointX);
          vLine.setAttribute('x2', pointX);
          
          // 更新悬停点位置
          hoverPoint.setAttribute('cx', pointX);
          hoverPoint.setAttribute('cy', pointY);
          
          // 更新信息框位置
          let infoX = pointX + 10;
          if (infoX + 140 > width) {
            infoX = pointX - 150;
          }
          
          let infoY = Math.max(10, pointY - 90);
          
          infoRect.setAttribute('x', infoX);
          infoRect.setAttribute('y', infoY);
          
          titleBg.setAttribute('x', infoX);
          titleBg.setAttribute('y', infoY);
          
          // 更新文本内容和位置
          titleText.setAttribute('x', infoX + 10);
          titleText.setAttribute('y', infoY + 16);
          
          timeText.setAttribute('x', infoX + 10);
          timeText.setAttribute('y', infoY + 38);
          timeText.textContent = `时间段: ${this.formatTime(minuteTimestamp)} - ${this.formatTime(endMinuteTimestamp)}`;
          
          valueText.setAttribute('x', infoX + 10);
          valueText.setAttribute('y', infoY + 55);
          valueText.textContent = `弹幕数: ${closestPoint.value}`;
          
          // 更新分P信息
          episodeText.setAttribute('x', infoX + 10);
          episodeText.setAttribute('y', infoY + 72);
          episodeText.textContent = `所在分集: ${episodeInfo}`;
          
          // 显示悬停元素
          hoverGroup.style.display = 'block';
        }
      });
      
      // 鼠标离开时隐藏
      svg.addEventListener('mouseleave', () => {
        hoverGroup.style.display = 'none';
      });
    },
    
    formatTime(milliseconds) {
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
  }
};
</script>

<style scoped>
.line-chart {
  width: 100%;
  height: 100%;
  min-height: 350px;
  overflow: hidden;
  position: relative;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
  padding: 15px;
  margin-top: 20px;
  margin-bottom: 20px;
}

.no-data, .not-enough-data {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #606266;
  font-size: 16px;
  background-color: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
}

:deep(.line-path) {
  transition: stroke-width 0.2s;
  stroke-linecap: round;
  stroke-linejoin: round;
}

:deep(.area-path) {
  transition: opacity 0.2s;
}

:deep(.data-point) {
  transition: r 0.2s, stroke-width 0.2s;
  cursor: pointer;
}

:deep(.data-point:hover) {
  r: 6;
  stroke-width: 3;
}

:deep(.line-chart-svg) {
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.1));
}
</style> 