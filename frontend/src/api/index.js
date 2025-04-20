import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true
});

// 添加响应拦截器
api.interceptors.response.use(
  response => response, // 直接返回响应
  error => {
    // 统一处理错误
    console.error('API请求错误:', error);
    
    // 如果响应存在，则提取有用的错误信息
    if (error.response) {
      // 服务器返回了错误状态码
      console.error('状态码:', error.response.status);
      console.error('响应数据:', error.response.data);
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('请求已发送但无响应');
    } else {
      // 设置请求时发生错误
      console.error('请求配置错误:', error.message);
    }
    
    // 继续抛出错误，让调用者可以进行后续处理
    return Promise.reject(error);
  }
);

// 获取CSRF令牌的函数
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// 添加请求拦截器，自动添加CSRF令牌
api.interceptors.request.use(
  config => {
    // 对POST, PUT, PATCH, DELETE请求添加CSRF令牌
    if (['post', 'put', 'patch', 'delete'].includes(config.method)) {
      const csrfToken = getCookie('csrftoken');
      if (csrfToken) {
        // 使用X-CSRFToken头，与Django默认配置一致
        config.headers['X-CSRFToken'] = csrfToken;
        console.log('添加CSRF令牌:', csrfToken.substring(0, 5) + '...');
      } else {
        console.warn('未找到CSRF令牌!');
      }
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 视频相关API
export const videoApi = {
  // 获取视频列表
  getVideos(params) {
    // 如果没有明确指定user参数，默认添加user=current
    const queryParams = { ...params };
    if (!queryParams.user) {
      queryParams.user = 'current';
    }
    return api.get('/videos/', { params: queryParams });
  },
  
  // 获取视频详情
  getVideo(id) {
    return api.get(`/videos/${id}/`);
  },
  
  // 按BV号获取视频
  getVideoByBvid(bvid) {
    // 检查bvid是否有效
    if (!bvid || bvid === 'undefined') {
      console.error('getVideoByBvid: 无效的BVID参数');
      return Promise.reject(new Error('无效的视频BVID'));
    }
    
    console.log(`通过BVID查询视频: ${bvid}`);
    
    // 确保在查询视频时考虑当前用户
    return api.get('/videos/', { params: { bvid, user: 'current' } })
      .then(response => {
        const videos = response.data.results;
        if (videos && videos.length > 0) {
          console.log(`成功找到视频: ${videos[0].title}`);
          return { data: videos[0] };
        }
        // 如果当前用户没有这个视频，可能是新视频或者是其他用户的视频
        console.error(`未找到视频: BVID=${bvid}`);
        throw new Error('未找到视频');
      });
  },
  
  // 获取视频弹幕
  getVideoDanmakus(id, params) {
    const queryParams = { ...params, user: 'current' };
    return api.get(`/videos/${id}/danmakus/`, { params: queryParams });
  },
  
  // 爬取视频弹幕
  crawlVideoDanmakus(id) {
    return api.post(`/videos/${id}/crawl/`);
  },
  
  // 获取当前用户的视频列表
  getMyVideos(params) {
    const queryParams = { ...params, user: 'current' };
    return api.get('/videos/my_videos/', { params: queryParams });
  },
  
  // 获取当前用户的任务列表
  getMyTasks(params) {
    const queryParams = { ...params };
    if (!queryParams.page) queryParams.page = 1;
    if (!queryParams.page_size) queryParams.page_size = 10;
    queryParams.user = 'current';
    return api.get('/tasks/my_tasks/', { params: queryParams });
  }
};

// 弹幕爬取任务API
export const taskApi = {
  // 获取任务列表
  getTasks(params) {
    // 确保参数中包含分页信息和用户信息
    const queryParams = { ...params };
    if (!queryParams.page) queryParams.page = 1;
    if (!queryParams.page_size) queryParams.page_size = 10;
    if (!queryParams.user) queryParams.user = 'current';
    
    console.log('API调用参数:', queryParams);
    return api.get('/tasks/', { params: queryParams });
  },
  
  // 创建爬取任务
  createTask(videoUrl, cookieStr) {
    const data = { video_url: videoUrl };
    if (cookieStr) {
      data.cookie_str = cookieStr;
    }
    return api.post('/tasks/create_task/', data);
  }
};

// 弹幕分析API
export const analysisApi = {
  // 获取分析结果列表
  getAnalyses(videoId = null, type = null) {
    let params = {};
    // 确保只有在videoId有效时才添加bvid参数
    if (videoId && videoId !== 'undefined') {
      params.bvid = videoId;
      console.log(`获取BVID=${videoId}的分析结果`);
    } else {
      console.log('获取所有分析结果');
    }
    
    if (type) params.type = type;
    
    return api.get('/analyses/', { params });
  },
  
  // 开始分析
  analyze(bvid, type = null, options = {}) {
    // 确保bvid不为空
    if (!bvid) {
      console.error('分析失败: bvid参数为空');
      return Promise.reject(new Error('视频BVID不能为空'));
    }
    
    // 默认参数
    let data = { 
      bvid, 
      max_processing_time: options.max_processing_time || 300,
      force_simple: options.force_simple || false
    };
    
    if (type) data.type = type;
    
    console.log('发送分析请求:', data);
    
    // 为情感分析设置更长的超时时间
    const requestConfig = {
      timeout: type === 'sentiment' ? 180000 : 60000 // 情感分析3分钟，其他1分钟
    };
    
    return api.post('/analyses/analyze/', data, requestConfig)
      .then(response => {
        console.log('分析成功，响应数据:', response.data);
        return response;
      })
      .catch(error => {
        console.error('分析失败:', error);
        if (error.response) {
          console.error('错误响应状态:', error.response.status);
          console.error('错误响应详情:', error.response.data);
        }
        return Promise.reject(error);
      });
  },
  
  // 获取关键词列表
  getKeywords(videoId) {
    return api.get('/keywords/', { params: { bvid: videoId } });
  },
  
  // 获取情感分析结果
  getSentiments(videoId) {
    return api.get('/sentiments/', { params: { bvid: videoId } });
  }
};

export default {
  videoApi,
  taskApi,
  analysisApi
}; 