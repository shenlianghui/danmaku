import { defineStore } from 'pinia'
import axios from 'axios'

// 获取 CSRF token 的函数
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

// 配置 axios 实例
const apiClient = axios.create({
    baseURL: '/api/accounts/', // 修改为相对路径，依赖于Vue代理
    withCredentials: true,     // 允许跨域请求携带 cookie (用于 session 认证)
    headers: {
        'Content-Type': 'application/json',
    }
});

// 添加请求拦截器，自动添加CSRF令牌
apiClient.interceptors.request.use(
    config => {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
        }
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);

// 导出 apiClient 实例
export { apiClient };

// 持久化存储工具
const STORAGE_KEY = 'auth_user';
const SESSION_EXPIRY_KEY = 'auth_expiry';

const saveToStorage = (user, rememberMe = false) => {
    const expiry = rememberMe 
        ? new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) // 30天
        : new Date(Date.now() + 24 * 60 * 60 * 1000);     // 1天
        
    localStorage.setItem(SESSION_EXPIRY_KEY, expiry.toISOString());
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    console.log('用户数据已保存到localStorage:', user.username);
};

const loadFromStorage = () => {
    const expiry = localStorage.getItem(SESSION_EXPIRY_KEY);
    if (!expiry) return null;
    
    // 检查是否过期
    if (new Date(expiry) < new Date()) {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(SESSION_EXPIRY_KEY);
        return null;
    }
    
    // 从存储中加载用户
    const userJson = localStorage.getItem(STORAGE_KEY);
    if (!userJson) return null;
    
    try {
        return JSON.parse(userJson);
    } catch (e) {
        return null;
    }
};

const clearStorage = () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(SESSION_EXPIRY_KEY);
};

export const useAuthStore = defineStore('auth', {
    state: () => {
        // 初始化时尝试从 localStorage 加载用户信息
        const savedUser = loadFromStorage();
        console.log('从localStorage加载用户数据:', savedUser ? savedUser.username : '无');
        
        return {
            user: savedUser || null,          // 存储用户信息
            isAuthenticated: !!savedUser,     // 是否已认证
            loading: false,                   // 是否加载中
            error: null,                      // 错误信息
            csrfReady: false,                 // CSRF 令牌是否准备就绪
        };
    },
    
    getters: {
        // 获取用户姓名（用于显示）
        fullName: (state) => {
            if (!state.user) return '';
            
            const firstName = state.user.first_name || '';
            const lastName = state.user.last_name || '';
            
            if (firstName || lastName) {
                return `${firstName} ${lastName}`.trim();
            }
            return state.user.username;
        },
        
        // 是否管理员
        isAdmin: (state) => {
            return state.user && state.user.is_staff;
        }
    },
    
    actions: {
        // 设置 CSRF 令牌状态
        setCsrfReady(status) {
            this.csrfReady = status;
        },
        
        // 获取当前用户信息
        async fetchUser() {
            try {
                console.log('执行fetchUser...')
                
                const response = await axios.get('/api/accounts/user/', {
                    withCredentials: true,
                    timeout: 5000
                })
                
                console.log('用户API响应:', response.status)
                
                if (response.data) {
                    this.user = response.data
                    this.isAuthenticated = true
                    // 保存到本地存储
                    saveToStorage(this.user)
                    console.log('用户已认证:', this.user.username)
                    return true
                } else {
                    console.warn('用户API返回空数据')
                    this.clearUserData()
                    return false
                }
            } catch (error) {
                console.error('获取用户数据失败:', error?.response?.status || error.message)
                if (error.response && error.response.status === 401) {
                    console.log('用户未认证，清除用户数据')
                    this.clearUserData()
                }
                if (error.response) {
                    console.error('错误响应数据:', error.response.data)
                }
                return false
            }
        },
        
        // 登录
        async login(credentials) {
            this.loading = true;
            this.error = null;
            
            try {
                const response = await apiClient.post('login/', credentials);
                const data = response.data;
                
                if (data && data.status === 'success') {
                    this.user = data.user;
                    this.isAuthenticated = true;
                    
                    // 保存到本地存储 (可选"记住我")
                    saveToStorage(this.user, credentials.remember_me);
                    
                    return { success: true, user: this.user };
                } else {
                    throw new Error('登录失败');
                }
            } catch (error) {
                this.user = null;
                this.isAuthenticated = false;
                
                // 格式化错误响应
                let errorResponse = { success: false };
                
                if (error.response) {
                    const { data, status } = error.response;
                    
                    // 处理锁定状态 (429)
                    if (status === 429) {
                        errorResponse.lockout = true;
                        errorResponse.error = data.error || '登录尝试次数过多，请稍后再试';
                    }
                    // 处理普通错误
                    else {
                        errorResponse.error = data.error || '登录失败';
                        if (data.attempts_left !== undefined) {
                            errorResponse.attempts_left = data.attempts_left;
                        }
                    }
                } else {
                    errorResponse.error = '登录请求发生错误，请检查网络连接';
                }
                
                this.error = errorResponse.error;
                return errorResponse;
            } finally {
                this.loading = false;
            }
        },
        
        // 注册
        async register(userData) {
            this.loading = true;
            this.error = null;
            
            try {
                const response = await apiClient.post('register/', userData);
                const data = response.data;
                
                if (data && data.status === 'success') {
                    this.user = data.user;
                    this.isAuthenticated = true;
                    
                    // 保存到本地存储
                    saveToStorage(this.user);
                    
                    return { success: true, user: this.user };
                } else {
                    throw new Error('注册失败');
                }
            } catch (error) {
                this.isAuthenticated = false;
                
                // 格式化错误响应
                let errorResponse = { success: false };
                
                if (error.response && error.response.data) {
                    errorResponse.error = error.response.data.error || error.response.data;
                } else {
                    errorResponse.error = '注册失败，请稍后重试';
                }
                
                this.error = errorResponse.error;
                return errorResponse;
            } finally {
                this.loading = false;
            }
        },
        
        // 登出
        async logout() {
            this.loading = true;
            this.error = null;
            
            try {
                const response = await apiClient.post('logout/');
                
                // 无论成功与否，都清除状态
                this.user = null;
                this.isAuthenticated = false;
                clearStorage();
                
                return { success: true };
            } catch (error) {
                this.user = null;
                this.isAuthenticated = false;
                clearStorage();
                
                return { 
                    success: false,
                    error: '登出失败，但已在本地清除登录状态'
                };
            } finally {
                this.loading = false;
            }
        },
        
        // 更新用户资料
        async updateProfile(userData) {
            this.loading = true;
            this.error = null;
            
            try {
                const response = await apiClient.patch('update/', userData);
                const data = response.data;
                
                if (data && data.status === 'success') {
                    this.user = data.user;
                    
                    // 更新本地存储
                    if (this.isAuthenticated) {
                        saveToStorage(this.user);
                    }
                    
                    return { success: true, user: this.user };
                } else {
                    throw new Error('更新资料失败');
                }
            } catch (error) {
                let errorResponse = { success: false };
                
                if (error.response && error.response.data) {
                    errorResponse.error = error.response.data.error || '更新资料失败';
                } else {
                    errorResponse.error = '更新资料请求发生错误';
                }
                
                this.error = errorResponse.error;
                return errorResponse;
            } finally {
                this.loading = false;
            }
        },

        clearUserData() {
            console.log('清除用户数据...')
            this.user = null
            this.isAuthenticated = false
            clearStorage()  // 使用定义好的clearStorage函数，而不是直接操作localStorage
        }
    },
}); 