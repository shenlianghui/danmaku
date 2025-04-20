/**
 * 日期格式化工具
 * 确保在整个应用中使用统一的日期格式
 */

/**
 * 将日期格式化为中国标准时间（东八区）
 * @param {string|Date} date - 需要格式化的日期
 * @param {boolean} includeTime - 是否包含时间，默认为true
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, includeTime = true) {
  if (!date) return 'N/A';
  
  const dateObj = new Date(date);
  
  // 选项根据是否包含时间而变化
  const options = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Asia/Shanghai' // 东八区
  };
  
  // 如果需要包含时间
  if (includeTime) {
    Object.assign(options, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false // 24小时制
    });
    
    return dateObj.toLocaleString('zh-CN', options);
  }
  
  // 仅日期
  return dateObj.toLocaleDateString('zh-CN', options);
}

/**
 * 将日期格式化为相对时间（例如：3分钟前，2小时前等）
 * @param {string|Date} date - 需要格式化的日期
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(date) {
  if (!date) return 'N/A';
  
  const dateObj = new Date(date);
  const now = new Date();
  
  const diffMs = now - dateObj;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) {
    return '刚刚';
  } else if (diffMin < 60) {
    return `${diffMin}分钟前`;
  } else if (diffHour < 24) {
    return `${diffHour}小时前`;
  } else if (diffDay < 30) {
    return `${diffDay}天前`;
  } else {
    // 超过30天就显示完整日期
    return formatDate(date, false);
  }
} 