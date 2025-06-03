<template>
  <div class="line-chart" ref="chartContainer">
    <div v-if="!data || data.length === 0" class="no-data">
      暂无数据
    </div>
    <div v-else-if="visibleData && visibleData.length < 2 && data.length >=2" class="not-enough-data">
      当前视图中数据点不足，请尝试调整视图范围或缩放
    </div>
  </div>
</template>

<script>
export default {
  name: 'LineChart',
  props: {
    viewportStart: { type: Number, required: true },
    viewportEnd: { type: Number, required: true },
    data: { type: Array, required: true },
    height: { type: Number, default: 350 },
    lineColor: { type: String, default: 'rgba(64, 158, 255, 1)' },
    fillColor: { type: String, default: 'rgba(64, 158, 255, 0.1)' },
    lineWidth: { type: Number, default: 2 },
    pointRadius: { type: Number, default: 4 },
    showGrid: { type: Boolean, default: true },
    smooth: { type: Boolean, default: true },
    episodeBoundaries: { type: Array, default: () => [] },
    yAxisMin: { type: Number, default: null },
    yAxisMax: { type: Number, default: null },
    yAxisLabel: { type: String, default: '' },
    colorPoints: { type: Boolean, default: false },
    getPointColor: { type: Function, default: null },
    tooltipFormatter: { type: Function, default: null }
  },
  data() {
    return {
      // chart: null, // chart 变量似乎未使用，可以移除
      observer: null,
      visibleData: [],
      // hoveredPoint: null, // hoveredPoint 变量似乎未使用，可以移除
      // stats: { max: 0, average: 0, total: 0 }, // stats 变量似乎未使用，可以移除
      // activePoint: null, // activePoint 变量似乎未使用，可以移除
      resizeTimeoutId: null,
      isDrawing: false, // 防止并发绘制
    };
  },
  watch: {
    viewportStart: 'requestRedraw',
    viewportEnd: 'requestRedraw',
    data: {
      deep: true,
      handler: 'requestRedraw'
    },
    height: 'requestRedraw',
    lineColor: 'requestRedraw',
    // 监听其他可能影响图表外观的 props
  },
  mounted() {
    this.updateVisibleDataAndDraw(); // 初始绘制
    this.setupResizeListener();
  },
  beforeUnmount() {
    this.cleanupResizeListener();
  },
  methods: {
    setupResizeListener() {
      if (this.$refs.chartContainer) {
        try {
          this.observer = new ResizeObserver(this.handleResize);
          this.observer.observe(this.$refs.chartContainer);
        } catch (err) {
          console.error('Failed to create ResizeObserver:', err);
          // Fallback for browsers that might not support ResizeObserver or if an error occurs
          window.addEventListener('resize', this.handleResize);
        }
      } else {
        // If chartContainer is not yet available, retry or fallback
        window.addEventListener('resize', this.handleResize);
      }
    },
    cleanupResizeListener() {
      if (this.observer && this.$refs.chartContainer) {
        try {
          this.observer.unobserve(this.$refs.chartContainer);
          this.observer.disconnect();
        } catch (err) {
          // console.warn('Error disconnecting observer:', err);
        }
      }
      if (this.resizeTimeoutId) {
        cancelAnimationFrame(this.resizeTimeoutId);
      }
      window.removeEventListener('resize', this.handleResize);
    },
    handleResize() {
      if (this.resizeTimeoutId) {
        cancelAnimationFrame(this.resizeTimeoutId);
      }
      this.resizeTimeoutId = requestAnimationFrame(() => {
        if (this.$refs.chartContainer && !this.isDrawing) {
          this.drawChart();
        }
      });
    },
    requestRedraw() {
        this.updateVisibleData();
        // Debounce drawing slightly to avoid rapid redraws if multiple props change
        if (this.redrawDebounceTimer) clearTimeout(this.redrawDebounceTimer);
        this.redrawDebounceTimer = setTimeout(() => {
             this.drawChart();
        }, 50); // 50ms debounce
    },
    updateVisibleDataAndDraw() {
      this.updateVisibleData();
      this.$nextTick(() => { // Ensure DOM is updated for clientWidth
        this.drawChart();
      });
    },
    updateVisibleData() {
      if (!this.data || typeof this.viewportStart !== 'number' || typeof this.viewportEnd !== 'number') {
        this.visibleData = [];
        return;
      }
      this.visibleData = this.data
        .filter(item => item && typeof item.start === 'number' && item.start >= this.viewportStart && item.start <= this.viewportEnd)
        .sort((a, b) => a.start - b.start);
    },
    // initChart() { // Renamed to updateVisibleDataAndDraw for clarity
    //   this.updateVisibleDataAndDraw();
    // },
    setViewport(start, end) {
      if (typeof start === 'number' && typeof end === 'number' && start < end) {
        // console.log(`LineChart.setViewport called, but viewport is prop-driven. Consider direct prop update.`);
        // This component receives viewportStart and viewportEnd as props.
        // Direct manipulation (`this._viewportStart`) bypasses Vue's reactivity.
        // The parent component should update these props to change the viewport.
        // If this method is truly needed for internal control, ensure it doesn't conflict with props.
        // For now, assuming props are the source of truth, this method might not be needed
        // or should emit an event to the parent.
      }
    },
    drawChart() {
      if (this.isDrawing) return;
      this.isDrawing = true;

      const container = this.$refs.chartContainer;
      if (!container || !container.clientWidth) { // Ensure container is ready and has width
        this.isDrawing = false;
        return;
      }

      const noDataEl = container.querySelector('.no-data');
      const notEnoughDataEl = container.querySelector('.not-enough-data');

      if (noDataEl) noDataEl.style.display = 'none';
      if (notEnoughDataEl) notEnoughDataEl.style.display = 'none';

      if (!this.data || this.data.length === 0) {
        if (noDataEl) noDataEl.style.display = 'flex';
        this.isDrawing = false;
        return;
      }

      if (this.visibleData.length < 2 && this.data.length >=2) { // Show "not enough" only if total data has at least 2 points
        if (notEnoughDataEl) notEnoughDataEl.style.display = 'flex';
        // Do not return here, allow drawing single point if necessary or just axes
        // For a line chart, it's better to not draw if less than 2 visible points
        const oldSvg = container.querySelector('svg');
        if (oldSvg) oldSvg.remove(); // Clear previous chart
        this.isDrawing = false;
        return;
      }
       if (this.visibleData.length < 2 && this.data.length < 2) { // If total data is less than 2, treat as no data
        if (noDataEl) noDataEl.style.display = 'flex';
        this.isDrawing = false;
        return;
      }


      const oldSvg = container.querySelector('svg');
      if (oldSvg) oldSvg.remove();

      const width = container.clientWidth;
      const height = this.height;
      const margin = { top: 30, right: 30, bottom: 50, left: 60 }; // Increased left margin for Y-axis labels
      const chartWidth = width - margin.left - margin.right;
      const chartHeight = height - margin.top - margin.bottom;

      if (chartWidth <= 0 || chartHeight <= 0) { // Prevent drawing if dimensions are invalid
          this.isDrawing = false;
          return;
      }

      const currentViewportDuration = this.viewportEnd - this.viewportStart;
      if (currentViewportDuration <= 0) { // Avoid division by zero
          this.isDrawing = false;
          return;
      }
      const xScale = chartWidth / currentViewportDuration;

      const mergedData = this.mergeDataPoints(this.visibleData); // Removed unused params
      if (mergedData.length === 0) { // If after merging, no data, treat as no data
          if (noDataEl) noDataEl.style.display = 'flex';
          this.isDrawing = false;
          return;
      }
       if (mergedData.length < 2) { // If after merging, less than 2 points, can't draw line
          if (notEnoughDataEl) notEnoughDataEl.style.display = 'flex';
          this.isDrawing = false;
          return;
      }


      let yValues = mergedData.map(d => d.value);
      let effectiveMaxY = this.yAxisMax !== null ? this.yAxisMax : Math.max(...yValues, 0); // Ensure max is at least 0
      let effectiveMinY = this.yAxisMin !== null ? this.yAxisMin : Math.min(...yValues, 0); // Ensure min is at most 0

      if (effectiveMaxY === effectiveMinY) { // Avoid flat line if all values are same
        effectiveMaxY = effectiveMaxY + 1;
        if (effectiveMinY > 0) effectiveMinY = Math.max(0, effectiveMinY -1); // ensure min is not negative if not needed
      }
       if (effectiveMaxY <= effectiveMinY) { // if yAxisMin > yAxisMax or data is outside range
           effectiveMaxY = effectiveMinY + 1; // ensure a valid range
       }


      const valueRange = effectiveMaxY - effectiveMinY;
      const yScale = chartHeight / (valueRange > 0 ? valueRange : 1);

      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('width', width);
      svg.setAttribute('height', height);
      svg.setAttribute('class', 'line-chart-svg');
      container.appendChild(svg);

      const chartGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      chartGroup.setAttribute('transform', `translate(${margin.left}, ${margin.top})`);
      svg.appendChild(chartGroup);

      if (this.showGrid) {
        this.drawGrid(chartGroup, chartWidth, chartHeight, effectiveMaxY, effectiveMinY);
      }
      this.drawXAxis(chartGroup, chartWidth, chartHeight, xScale);
      this.drawLineAndArea(chartGroup, chartWidth, chartHeight, xScale, yScale, effectiveMaxY, effectiveMinY, mergedData);
      this.drawDataPoints(chartGroup, xScale, yScale, chartHeight, effectiveMaxY, effectiveMinY, mergedData);
      // this.drawStats(chartGroup, chartWidth, chartHeight, effectiveMaxY, effectiveMinY); // Stats are now part of tooltip
      this.setupHoverInteraction(chartGroup, xScale, yScale, chartHeight, chartWidth, margin, effectiveMaxY, effectiveMinY, mergedData);
      
      this.isDrawing = false;
    },
    drawGrid(chartGroup, width, height, maxValue, minValue) {
      const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      gridGroup.setAttribute('class', 'grid-lines');

      const gridCount = 5;
      const gridStep = height / gridCount;
      
      if (this.yAxisLabel) {
        const yAxisLabelElem = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yAxisLabelElem.setAttribute('transform', `rotate(-90)`);
        yAxisLabelElem.setAttribute('x', -(height / 2));
        yAxisLabelElem.setAttribute('y', -margin.left + 15); // Position relative to chartGroup
        yAxisLabelElem.setAttribute('font-size', '12');
        yAxisLabelElem.setAttribute('text-anchor', 'middle');
        yAxisLabelElem.setAttribute('fill', 'rgba(0,0,0,0.7)');
        yAxisLabelElem.textContent = this.yAxisLabel;
        gridGroup.appendChild(yAxisLabelElem);
      }

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

        const value = minValue + (maxValue - minValue) * (1 - i / gridCount);
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', -8); // Adjusted for increased left margin
        text.setAttribute('y', y + 4);
        text.setAttribute('font-size', '11');
        text.setAttribute('text-anchor', 'end');
        text.setAttribute('fill', 'rgba(0,0,0,0.6)');
        text.textContent = value.toFixed(Math.abs(value) < 1 && Math.abs(value) > 0 ? 2 : (Math.abs(value) >=1 && Math.abs(value) < 10 ? 1 : 0) ); // Dynamic precision
        gridGroup.appendChild(text);
      }
      chartGroup.appendChild(gridGroup);
    },
    drawXAxis(chartGroup, width, height, xScale) {
      const axisGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      axisGroup.setAttribute('class', 'x-axis');
      axisGroup.setAttribute('transform', `translate(0, ${height})`);

      const axisLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      axisLine.setAttribute('x1', 0);
      axisLine.setAttribute('y1', 0);
      axisLine.setAttribute('x2', width);
      axisLine.setAttribute('y2', 0);
      axisLine.setAttribute('stroke', 'rgba(0,0,0,0.3)');
      axisLine.setAttribute('stroke-width', '1');
      axisGroup.appendChild(axisLine);

      const viewportDurationMs = this.viewportEnd - this.viewportStart;
      let tickCount = Math.min(10, Math.max(2, Math.floor(width / 80))); // Dynamic tick count based on width
      
      if (viewportDurationMs <= 60 * 1000 * 5) { // Less than 5 minutes, more ticks
          tickCount = Math.min(10, Math.max(2, Math.floor(width / 60)));
      }


      for (let i = 0; i <= tickCount; i++) {
        const x = (width / tickCount) * i;
        const time = this.viewportStart + (viewportDurationMs / tickCount) * i;

        const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        tick.setAttribute('x1', x);
        tick.setAttribute('y1', 0);
        tick.setAttribute('x2', x);
        tick.setAttribute('y2', 5);
        tick.setAttribute('stroke', 'rgba(0,0,0,0.3)');
        axisGroup.appendChild(tick);

        if (i % Math.max(1, Math.floor(tickCount / 5)) === 0 || i === tickCount || tickCount <=5 ) { // Show labels more sparsely for many ticks
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', 18);
            text.setAttribute('font-size', '11');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', 'rgba(0,0,0,0.6)');
            text.textContent = this.formatTime(time);
            axisGroup.appendChild(text);
        }
      }
      chartGroup.appendChild(axisGroup);
    },
    drawLineAndArea(chartGroup, width, height, xScale, yScale, maxValue, minValue, mergedData) {
      if (mergedData.length < 2) return;
      const pathGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      pathGroup.setAttribute('class', 'path-group');

      let linePath = '';
      let areaPath = '';
      const valueOffset = minValue; // Use effectiveMinY for y calculation

      mergedData.forEach((point, index) => {
        const x = (point.start - this.viewportStart) * xScale;
        const y = height - (point.value - valueOffset) * yScale;

        if (index === 0) {
          linePath += `M ${x.toFixed(2)} ${y.toFixed(2)}`;
          areaPath += `M ${x.toFixed(2)} ${height} L ${x.toFixed(2)} ${y.toFixed(2)}`;
        } else {
          if (this.smooth) {
            const prevPoint = mergedData[index - 1];
            const prevX = (prevPoint.start - this.viewportStart) * xScale;
            const prevY = height - (prevPoint.value - valueOffset) * yScale;
            const cpX1 = prevX + (x - prevX) / 2; // Simplified control points for smoother curve
            linePath += ` S ${cpX1.toFixed(2)} ${prevY.toFixed(2)}, ${x.toFixed(2)} ${y.toFixed(2)}`;
            areaPath += ` S ${cpX1.toFixed(2)} ${prevY.toFixed(2)}, ${x.toFixed(2)} ${y.toFixed(2)}`;
          } else {
            linePath += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
            areaPath += ` L ${x.toFixed(2)} ${y.toFixed(2)}`;
          }
        }
        if (index === mergedData.length - 1) {
          areaPath += ` L ${x.toFixed(2)} ${height} Z`;
        }
      });

      const areaElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      areaElement.setAttribute('d', areaPath);
      areaElement.setAttribute('fill', this.fillColor);
      pathGroup.appendChild(areaElement);

      const lineElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      lineElement.setAttribute('d', linePath);
      lineElement.setAttribute('fill', 'none');
      lineElement.setAttribute('stroke', this.lineColor);
      lineElement.setAttribute('stroke-width', this.lineWidth);
      lineElement.setAttribute('stroke-linecap', 'round');
      lineElement.setAttribute('stroke-linejoin', 'round');
      pathGroup.appendChild(lineElement);
      chartGroup.appendChild(pathGroup);
    },
    drawDataPoints(chartGroup, xScale, yScale, chartHeight, maxValue, minValue, mergedData) {
      const pointsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      pointsGroup.setAttribute('class', 'data-points');
      const valueOffset = minValue;

      mergedData.forEach(point => {
        const x = (point.start - this.viewportStart) * xScale;
        const y = chartHeight - (point.value - valueOffset) * yScale;

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', this.pointRadius);

        let pointFillColor = 'white';
        let pointStrokeColor = this.lineColor;
        if (this.colorPoints && this.getPointColor) {
          try {
            const customColor = this.getPointColor(point); // point here is a mergedData point
            if (customColor) {
              pointFillColor = customColor;
              pointStrokeColor = customColor;
            }
          } catch (err) { console.error('Error in getPointColor:', err); }
        }
        circle.setAttribute('fill', pointFillColor);
        circle.setAttribute('stroke', pointStrokeColor);
        circle.setAttribute('stroke-width', this.lineWidth / 2 || 1); // Smaller stroke for points
        circle.classList.add('data-point');

        // Store original data for tooltip. `point` is already the merged data point.
        // If tooltipFormatter needs fields not in mergedData, pass original data from parent.
        // For now, we assume `point` (mergedData item) has enough info or `tooltipFormatter` handles it.
        circle.dataset.pointData = JSON.stringify(point);


        pointsGroup.appendChild(circle);
      });
      chartGroup.appendChild(pointsGroup);
    },
    mergeDataPoints(dataToMerge) { // Renamed param for clarity
        if (!dataToMerge || dataToMerge.length === 0) return [];
        // For a line chart showing sentiment score over time,
        // merging might not be desired if each data point is unique (e.g., per minute score).
        // If data is already "per minute" or desired granularity, no merge needed.
        // This implementation assumes data might be denser and need aggregation.
        // If data is already at the correct granularity, just return it sorted.
        // The original mergeDataPoints was for bar-like data where multiple points fall into one "bar".
        // For a line chart, if data is [{start: time1, value: score1}, {start: time2, value: score2}],
        // and these are unique time points, no merging is needed.

        // If your `formattedSentimentData` is already in the form of:
        // [{ start: segment_start_time, value: mapped_sentiment_score, originalScore: ..., ...}, ...]
        // where each `start` is unique for a segment, then merging is not necessary.
        // We will just return the data sorted.
        return [...dataToMerge].sort((a, b) => a.start - b.start);

        // If merging by minute interval is still desired (e.g., if input `data` is very dense):
        /*
        const minuteInterval = 60000;
        const minuteGroups = {};
        dataToMerge.forEach(point => {
            const minuteTimestamp = Math.floor(point.start / minuteInterval) * minuteInterval;
            if (!minuteGroups[minuteTimestamp]) {
            minuteGroups[minuteTimestamp] = { start: minuteTimestamp, values: [], originalPoints: [] };
            }
            minuteGroups[minuteTimestamp].values.push(point.value);
            minuteGroups[minuteTimestamp].originalPoints.push(point); // Store original point
        });
        return Object.values(minuteGroups).map(group => {
            const avgValue = group.values.reduce((sum, val) => sum + val, 0) / group.values.length;
            return {
            start: group.start,
            value: avgValue,
            // Include other relevant data from originalPoints if needed by tooltipFormatter
            // For example, if all original points in this group have the same sentiment:
            sentiment: group.originalPoints[0]?.sentiment,
            originalScore: group.originalPoints.reduce((sum, p) => sum + (p.originalScore || 0), 0) / group.originalPoints.length, // Average original score
            danmaku_count: group.originalPoints.reduce((sum, p) => sum + (p.danmaku_count || 0), 0), // Sum of danmaku counts
            };
        }).sort((a, b) => a.start - b.start);
        */
    },
    // drawStats method can be removed as stats are now part of the interactive tooltip
    setupHoverInteraction(chartGroup, xScale, yScale, height, width, margin, maxValue, minValue, mergedData) {
      if (mergedData.length === 0) return;

      const hoverGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      hoverGroup.setAttribute('class', 'hover-elements');
      hoverGroup.style.display = 'none';

      const vLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      vLine.setAttribute('y1', 0);
      vLine.setAttribute('y2', height);
      vLine.setAttribute('stroke', 'rgba(0,0,0,0.4)');
      vLine.setAttribute('stroke-width', '1');
      vLine.setAttribute('stroke-dasharray', '3,3');
      hoverGroup.appendChild(vLine);

      const hoverPointCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      hoverPointCircle.setAttribute('r', this.pointRadius + 2); // Slightly larger
      // Fill/stroke will be set based on closestPoint
      hoverPointCircle.setAttribute('stroke', 'white');
      hoverPointCircle.setAttribute('stroke-width', '2');
      hoverGroup.appendChild(hoverPointCircle);

      const tooltipRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      tooltipRect.setAttribute('rx', '4');
      tooltipRect.setAttribute('ry', '4');
      tooltipRect.setAttribute('fill', 'rgba(0, 0, 0, 0.75)'); // Darker tooltip
      tooltipRect.setAttribute('stroke', 'rgba(255,255,255,0.5)');
      tooltipRect.setAttribute('stroke-width', '1');
      // Width/Height/X/Y set dynamically
      hoverGroup.appendChild(tooltipRect);

      // Tooltip text lines (up to 4 lines for flexibility)
      const ttTextLines = [];
      for (let i = 0; i < 4; i++) {
          const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          textEl.setAttribute('font-size', '12');
          textEl.setAttribute('fill', 'white');
          textEl.style.display = 'none'; // Hide initially
          hoverGroup.appendChild(textEl);
          ttTextLines.push(textEl);
      }

      chartGroup.appendChild(hoverGroup);

      const svg = chartGroup.ownerSVGElement;
      svg.addEventListener('mousemove', (event) => {
        const rect = svg.getBoundingClientRect();
        const mouseX = event.clientX - rect.left - margin.left;
        if (mouseX < 0 || mouseX > width) { // If outside chart bounds
            hoverGroup.style.display = 'none';
            return;
        }

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

          vLine.setAttribute('x1', pointX);
          vLine.setAttribute('x2', pointX);

          hoverPointCircle.setAttribute('cx', pointX);
          hoverPointCircle.setAttribute('cy', pointY);
          // Set hover point color based on data point
          let pointColor = this.lineColor;
          if (this.colorPoints && this.getPointColor) {
              try { pointColor = this.getPointColor(closestPoint) || this.lineColor; }
              catch (e) { /* ignore */ }
          }
          hoverPointCircle.setAttribute('fill', pointColor);


          let tooltipContent = [];
          if (this.tooltipFormatter && typeof this.tooltipFormatter === 'function') {
            const formatted = this.tooltipFormatter(closestPoint);
            // Assuming formatter returns an object like { title: "...", lines: ["line1", "line2"] }
            // or simply a multi-line string
            if (typeof formatted === 'string') {
                tooltipContent = formatted.split('\n');
            } else if (formatted && Array.isArray(formatted.lines)) {
                if(formatted.title) tooltipContent.push(formatted.title);
                tooltipContent.push(...formatted.lines);
            } else if (formatted && formatted.value){ // For the simple {title, value} case
                tooltipContent.push(formatted.title || (this.yAxisLabel || "数据"));
                tooltipContent.push(formatted.value);
                 const episodeInfo = this.getEpisodeInfoForTimestamp(closestPoint.start);
                 if (episodeInfo) tooltipContent.push(`分集: ${episodeInfo}`);

            } else { // Fallback
                tooltipContent.push(this.yAxisLabel || "数据");
                tooltipContent.push(`${this.yAxisLabel || '值'}: ${closestPoint.value.toFixed(2)}`);
                tooltipContent.push(`时间: ${this.formatTime(closestPoint.start)}`);
            }
          } else { // Default tooltip
            tooltipContent.push(this.yAxisLabel || "数据");
            tooltipContent.push(`${this.yAxisLabel || '值'}: ${closestPoint.value.toFixed(2)}`);
            tooltipContent.push(`时间: ${this.formatTime(closestPoint.start)}`);
            const episodeInfo = this.getEpisodeInfoForTimestamp(closestPoint.start);
            if (episodeInfo) tooltipContent.push(`分集: ${episodeInfo}`);
          }
          
          let maxTextWidth = 0;
          ttTextLines.forEach((textEl, i) => {
              if (i < tooltipContent.length) {
                  textEl.textContent = tooltipContent[i];
                  textEl.style.display = 'block';
                  // Rough text width calculation
                  const tempSvgForTextMeasure = svg.cloneNode(false); // Use a temporary SVG for measurement
                  tempSvgForTextMeasure.style.visibility = 'hidden';
                  document.body.appendChild(tempSvgForTextMeasure);
                  const tempText = textEl.cloneNode(true);
                  tempSvgForTextMeasure.appendChild(tempText);
                  maxTextWidth = Math.max(maxTextWidth, tempText.getComputedTextLength ? tempText.getComputedTextLength() : (tooltipContent[i].length * 7)); // Fallback for length
                  document.body.removeChild(tempSvgForTextMeasure);

                  if (i === 0) { // First line (title) bold
                      textEl.setAttribute('font-weight', 'bold');
                  } else {
                      textEl.removeAttribute('font-weight');
                  }

              } else {
                  textEl.style.display = 'none';
              }
          });

          const padding = 8;
          const lineHeight = 16;
          const rectWidth = maxTextWidth + 2 * padding;
          const rectHeight = tooltipContent.length * lineHeight + 2 * padding - (tooltipContent.length > 0 ? (lineHeight - 12) : 0) ; // Adjust for font-size 12

          let rectX = pointX + 15;
          let rectY = pointY - rectHeight / 2;

          if (rectX + rectWidth > width) rectX = pointX - rectWidth - 15;
          if (rectX < 0) rectX = 5;
          if (rectY < 0) rectY = 5;
          if (rectY + rectHeight > height) rectY = height - rectHeight - 5;
          
          tooltipRect.setAttribute('x', rectX);
          tooltipRect.setAttribute('y', rectY);
          tooltipRect.setAttribute('width', rectWidth);
          tooltipRect.setAttribute('height', rectHeight);

          ttTextLines.forEach((textEl, i) => {
              if (i < tooltipContent.length) {
                  textEl.setAttribute('x', rectX + padding);
                  textEl.setAttribute('y', rectY + padding + i * lineHeight + 10); // +10 for text-anchor middle-ish
              }
          });

          hoverGroup.style.display = 'block';
        } else {
          hoverGroup.style.display = 'none';
        }
      });

      svg.addEventListener('mouseleave', () => {
        hoverGroup.style.display = 'none';
      });
    },
    getEpisodeInfoForTimestamp(timestampMs) { // Helper for tooltip
        if (!this.episodeBoundaries || this.episodeBoundaries.length === 0) {
            return null; // No episode info if boundaries not provided
        }
        const timestampSec = timestampMs / 1000;
        for (const boundary of this.episodeBoundaries) {
            const startSec = boundary.start_time_sec || 0;
            const endSec = boundary.end_time_sec || Infinity;
            if (timestampSec >= startSec && timestampSec < endSec) {
                return `P${boundary.page_id || '?'}`;
            }
        }
        return '整体视图'; // Or null if only specific episode info is wanted
    },
    formatTime(milliseconds) {
      if (milliseconds === null || milliseconds === undefined) return '--:--';
      const totalSeconds = Math.floor(milliseconds / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;

      if (hours > 0) {
        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      } else {
        return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
    },
  }
};
</script>

<style scoped>
.line-chart {
  width: 100%;
  height: 100%; /* Ensure it tries to fill parent if parent has defined height */
  min-height: 300px; /* Fallback min-height */
  overflow: hidden;
  position: relative;
  background-color: #ffffff; /* Cleaner background */
  border-radius: 8px; /* Consistent border radius */
  /* box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); */ /* Softer shadow */
  padding: 10px; /* Reduced padding, more space for chart */
  /* margin-top: 20px; */ /* Margin should be controlled by parent */
  /* margin-bottom: 20px; */
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
  color: #909399; /* Standard Element Plus secondary text color */
  font-size: 14px; /* Standard font size */
  background-color: #f9f9f9; /* Light background for these messages */
  border-radius: 8px; /* Match parent */
  padding: 20px;
  text-align: center;
}

/* SVG elements are styled via JavaScript, but some base styles can be here */
:deep(.line-chart-svg) {
  display: block; /* Remove extra space below SVG */
  user-select: none; /* Prevent text selection on chart */
}

:deep(.line-path) {
  /* transition: stroke-width 0.1s ease-out; */ /* Transitions can be slow on complex charts */
  stroke-linecap: round;
  stroke-linejoin: round;
}

:deep(.area-path) {
  /* transition: opacity 0.1s ease-out; */
}

:deep(.data-point) {
  /* transition: r 0.1s ease-out, stroke-width 0.1s ease-out; */
  cursor: crosshair; /* Indicate hoverability */
}
/*
:deep(.data-point:hover) { // Hover effects are now handled by JS for the 'active' point
  r: 6;
  stroke-width: 3;
}
*/

:deep(.x-axis .tick text), :deep(.grid-lines text) {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

:deep(.hover-elements text) {
    pointer-events: none; /* Ensure text doesn't block mouse events on underlying elements */
}
</style>