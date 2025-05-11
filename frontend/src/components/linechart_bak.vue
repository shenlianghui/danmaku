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
      // 是否使用自定义颜色的数据点
      colorPoints: {
        type: Boolean,
        default: false
      },
      // 获取数据点颜色的函数
      getPointColor: {
        type: Function,
        default: () => '#409EFF'
      },
      // 自定义工具提示格式化函数
      tooltipFormatter: {
        type: Function,
        default: null
      },
      // Y轴最小值
      yAxisMin: {
        type: Number,
        default: null
      },
      // Y轴最大值
      yAxisMax: {
        type: Number,
        default: null
      },
      // Y轴标签
      yAxisLabel: {
        type: String,
        default: ''
      }
    },
    data() {
      return {
        chart: null,
        observer: null,
        visibleData: [],
        hoveredPoint: null,
        hoverTimeout: null,
        resizeTimeout: null,
        originalErrorHandler: null, // 保存原始的错误处理函数
        _errorHandler: null,        // 保存错误处理函数引用
        eventHandlers: {            // 保存事件处理函数引用
          mousemove: null,
          mouseleave: null
        }
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
      
      // 添加全局错误处理来捕获ResizeObserver错误
      if (typeof window !== 'undefined') {
        // 保存原始的错误处理函数
        this.originalErrorHandler = window.onerror;
        
        // 添加更彻底的ResizeObserver错误处理
        const errorHandler = (event) => {
          if (event && event.message && 
              typeof event.message === 'string' && 
              (event.message.includes('ResizeObserver loop') || 
               event.message.includes('ResizeObserver Loop'))) {
            event.stopImmediatePropagation();
            event.stopPropagation();
            event.preventDefault();
            console.warn('[LineChart] Ignored ResizeObserver error');
            return true;
          }
        };
        
        // 添加事件监听
        window.addEventListener('error', errorHandler, true);
        window.addEventListener('unhandledrejection', errorHandler, true);
        
        // 保存引用以便清理
        this._errorHandler = errorHandler;
        
        // 自定义错误处理函数
        window.onerror = (message, source, lineno, colno, error) => {
          if (message && typeof message === 'string' && 
              message.includes('ResizeObserver') && 
              message.includes('loop')) {
            // 忽略ResizeObserver循环通知错误
            console.warn('Ignored ResizeObserver error:', message);
            return true; // 阻止错误继续传播
          }
          
          // 对于其他错误，使用原始的错误处理函数
          if (this.originalErrorHandler) {
            return this.originalErrorHandler(message, source, lineno, colno, error);
          }
          return false;
        };
      }
      
      // 添加ResizeObserver以便在容器大小变化时重绘图表
      try {
        this.observer = new ResizeObserver(entries => {
          // 使用防抖方式处理重绘，避免频繁调用
          if (this.resizeTimeout) {
            cancelAnimationFrame(this.resizeTimeout);
          }
          
          // 使用requestAnimationFrame代替setTimeout，更适合视觉更新
          this.resizeTimeout = requestAnimationFrame(() => {
            try {
              if (this.$refs.chartContainer) {
                this.drawChart();
              }
            } catch (err) {
              console.error('Error in ResizeObserver callback:', err);
            }
          });
        });
        
        // 确保元素存在再添加观察
        if (this.$refs.chartContainer) {
          this.observer.observe(this.$refs.chartContainer);
        }
      } catch (err) {
        console.error('Failed to create ResizeObserver:', err);
      }
    },
    beforeUnmount() {
      // 清理全局错误处理
      if (typeof window !== 'undefined') {
        if (this.originalErrorHandler) {
          window.onerror = this.originalErrorHandler;
        }
        
        if (this._errorHandler) {
          window.removeEventListener('error', this._errorHandler, true);
          window.removeEventListener('unhandledrejection', this._errorHandler, true);
        }
      }
      
      // 停止观察以防内存泄漏
      if (this.observer) {
        try {
          if (this.$refs.chartContainer) {
            this.observer.unobserve(this.$refs.chartContainer);
          }
          this.observer.disconnect();
        } catch (err) {
          console.error('Error disconnecting observer:', err);
        }
      }
      
      // 清理事件监听器
      try {
        const container = this.$refs.chartContainer;
        if (container) {
          const overlay = container.querySelector('.hover-overlay');
          if (overlay) {
            if (this.eventHandlers.mousemove) {
              overlay.removeEventListener('mousemove', this.eventHandlers.mousemove);
            }
            if (this.eventHandlers.mouseleave) {
              overlay.removeEventListener('mouseleave', this.eventHandlers.mouseleave);
            }
          }
        }
      } catch (err) {
        console.error('Error removing event listeners:', err);
      }
      
      // 清理所有可能的定时器
      if (this.hoverTimeout) {
        cancelAnimationFrame(this.hoverTimeout);
      }
      
      // 清理可能存在的resize定时器
      if (this.resizeTimeout) {
        cancelAnimationFrame(this.resizeTimeout);
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
        const maxValue = Math.max(...mergedData.map(d => d.value));
        const minValue = Math.min(...mergedData.map(d => d.value));
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
          const value = Math.round(maxValue - i * valueStep);
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', -5);
          text.setAttribute('y', y + 4); // 调整垂直位置以对齐网格线
          text.setAttribute('font-size', '11');
          text.setAttribute('text-anchor', 'end');
          text.setAttribute('fill', 'rgba(0,0,0,0.6)');
          text.textContent = value;
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
        const pointsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        pointsGroup.setAttribute('class', 'data-points');
        
        mergedData.forEach(d => {
          // 计算点的位置
          const x = (d.start - this.viewportStart) * xScale;
          const y = chartHeight - (d.value - minValue) * yScale;
          
          // 创建点
          const point = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          point.setAttribute('cx', x);
          point.setAttribute('cy', y);
          point.setAttribute('r', this.pointRadius);
          
          // 如果启用了颜色点并且提供了getPointColor函数，则使用它
          if (this.colorPoints && typeof this.getPointColor === 'function') {
            point.setAttribute('fill', this.getPointColor(d));
          } else {
            point.setAttribute('fill', this.lineColor);
          }
          
          point.setAttribute('stroke', 'white');
          point.setAttribute('stroke-width', '1');
          point.setAttribute('class', 'data-point');
          point.setAttribute('data-value', d.value);
          point.setAttribute('data-time', d.start);
          
          // 存储原始数据点
          point.__data__ = d;
          
          pointsGroup.appendChild(point);
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
      
      setupHoverInteraction(chartGroup, xScale, yScale, chartHeight, chartWidth, margin, maxValue, minValue, mergedData) {
        const container = this.$refs.chartContainer;
        if (!container) return;
        
        const svg = container.querySelector('svg');
        if (!svg) return;
        
        // 创建悬停区域
        const overlay = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        overlay.setAttribute('width', chartWidth);
        overlay.setAttribute('height', chartHeight);
        overlay.setAttribute('fill', 'transparent');
        overlay.setAttribute('class', 'hover-overlay');
        chartGroup.appendChild(overlay);
        
        // 创建工具提示元素
        const tooltip = document.createElement('div');
        tooltip.classList.add('line-chart-tooltip');
        tooltip.style.position = 'absolute';
        tooltip.style.display = 'none';
        tooltip.style.backgroundColor = 'rgba(0,0,0,0.75)';
        tooltip.style.color = 'white';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '12px';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.zIndex = '1000';
        container.appendChild(tooltip);
        
        // 创建提示线
        const guideLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        guideLine.setAttribute('x1', 0);
        guideLine.setAttribute('y1', 0);
        guideLine.setAttribute('x2', 0);
        guideLine.setAttribute('y2', chartHeight);
        guideLine.setAttribute('stroke', 'rgba(0,0,0,0.3)');
        guideLine.setAttribute('stroke-width', '1');
        guideLine.setAttribute('stroke-dasharray', '3,3');
        guideLine.style.display = 'none';
        chartGroup.appendChild(guideLine);
        
        // 使用变量保存上一次的hover位置信息，避免重复渲染
        let lastX = -1;
        let lastHoveredPoint = null;
        let isProcessingHover = false; // 防止多次处理
        
        // 鼠标移动事件处理函数
        const handleMouseMove = (event) => {
          if (isProcessingHover) return; // 如果正在处理，则跳过
          
          // 防止频繁触发
          if (this.hoverTimeout) {
            cancelAnimationFrame(this.hoverTimeout);
          }
          
          isProcessingHover = true;
          
          this.hoverTimeout = requestAnimationFrame(() => {
            try {
              const rect = svg.getBoundingClientRect();
              const x = event.clientX - rect.left - margin.left;
              
              // 如果鼠标位置和上次相同，则不处理
              if (x === lastX) {
                isProcessingHover = false;
                return;
              }
              lastX = x;
              
              if (x < 0 || x > chartWidth) {
                guideLine.style.display = 'none';
                tooltip.style.display = 'none';
                isProcessingHover = false;
                return;
              }
              
              // 显示指导线
              guideLine.setAttribute('x1', x);
              guideLine.setAttribute('x2', x);
              guideLine.style.display = 'block';
              
              // 计算鼠标位置对应的时间
              const time = this.viewportStart + (x / xScale);
              
              // 找到最接近的数据点
              const closestPoint = this.findClosestPoint(time, mergedData);
              
              // 如果最接近的点与上次相同，则不重新渲染
              if (closestPoint && lastHoveredPoint && 
                  closestPoint.start === lastHoveredPoint.start && 
                  closestPoint.value === lastHoveredPoint.value) {
                isProcessingHover = false;
                return;
              }
              lastHoveredPoint = closestPoint;
              
              if (closestPoint) {
                this.hoveredPoint = closestPoint;
                
                try {
                  // 高亮显示最接近的点 - 简化操作以提高性能
                  const points = chartGroup.querySelectorAll('.data-point');
                  const targetPoint = Array.from(points).find(p => {
                    return p.__data__ && p.__data__.start === closestPoint.start && p.__data__.value === closestPoint.value;
                  });
                  
                  if (targetPoint) {
                    // 重置所有点
                    points.forEach(p => {
                      p.setAttribute('r', this.pointRadius);
                      p.setAttribute('stroke-width', '1');
                    });
                    
                    // 只高亮目标点
                    targetPoint.setAttribute('r', this.pointRadius * 1.5);
                    targetPoint.setAttribute('stroke-width', '2');
                  }
                } catch (err) {
                  console.error('Error highlighting point:', err);
                }
                
                // 更新工具提示内容和位置
                try {
                  if (this.tooltipFormatter && typeof this.tooltipFormatter === 'function') {
                    tooltip.innerHTML = this.tooltipFormatter(closestPoint);
                  } else {
                    tooltip.innerHTML = `
                      <div>时间: ${this.formatTime(closestPoint.start)}</div>
                      <div>数值: ${closestPoint.value}</div>
                    `;
                  }
                  
                  // 工具提示位置
                  tooltip.style.left = `${event.clientX + 15}px`;
                  tooltip.style.top = `${event.clientY - 20}px`;
                  tooltip.style.display = 'block';
                } catch (err) {
                  console.error('Error updating tooltip:', err);
                  tooltip.style.display = 'none';
                }
              } else {
                this.hoveredPoint = null;
                tooltip.style.display = 'none';
              }
            } catch (err) {
              console.error('Error in hover interaction:', err);
            } finally {
              isProcessingHover = false;
            }
          });
        };
        
        // 鼠标离开事件处理函数
        const handleMouseLeave = () => {
          if (this.hoverTimeout) {
            cancelAnimationFrame(this.hoverTimeout);
          }
          
          this.hoveredPoint = null;
          lastHoveredPoint = null;
          lastX = -1;
          guideLine.style.display = 'none';
          tooltip.style.display = 'none';
          
          // 重置点的样式
          try {
            const points = chartGroup.querySelectorAll('.data-point');
            points.forEach(p => {
              p.setAttribute('r', this.pointRadius);
              p.setAttribute('stroke-width', '1');
            });
          } catch (err) {
            console.error('Error resetting data points:', err);
          }
        };
        
        // 添加事件监听器
        try {
          // 移除先前添加的事件监听器(如果存在)
          if (this.eventHandlers.mousemove) {
            overlay.removeEventListener('mousemove', this.eventHandlers.mousemove);
          }
          if (this.eventHandlers.mouseleave) {
            overlay.removeEventListener('mouseleave', this.eventHandlers.mouseleave);
          }
          
          // 保存新的事件处理函数引用，以便能在beforeUnmount中移除
          this.eventHandlers.mousemove = handleMouseMove;
          this.eventHandlers.mouseleave = handleMouseLeave;
          
          // 添加新的事件监听器
          overlay.addEventListener('mousemove', this.eventHandlers.mousemove);
          overlay.addEventListener('mouseleave', this.eventHandlers.mouseleave);
        } catch (err) {
          console.error('Error adding event listeners:', err);
        }
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