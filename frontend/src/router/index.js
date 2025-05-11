import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
// import Home from '../views/Home.vue' // Home 现在懒加载
const Welcome = () => import('../views/Welcome.vue') // 导入欢迎页

// 懒加载其他视图组件
const HomeDashboard = () => import('../views/Home.vue') // 重命名 Home 为 HomeDashboard
const VideoList = () => import('../views/VideoList.vue')
const VideoDetail = () => import('../views/VideoDetail.vue')
const DanmakuCrawler = () => import('../views/DanmakuCrawler.vue')
const DanmakuAnalysis = () => import('../views/DanmakuAnalysis.vue')
const LoginView = () => import('../views/LoginView.vue')
const RegisterView = () => import('../views/RegisterView.vue')
const DanmakuView = () => import('../views/DanmakuView.vue')
const AnalysisView = () => import('../views/AnalysisView.vue')
const ProfileView = () => import('../views/ProfileView.vue') // 新增个人资料页面
const ForgotPasswordView = () => import('../views/ForgotPasswordView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const MyTasksView = () => import('../views/MyTasksView.vue') // 导入我的任务页面

// 开始日志 - 验证文件是否被加载
console.log('Router file loaded - Step 1');

const routes = [
  {
    path: '/', // 根路径指向欢迎页
    name: 'Welcome',
    component: Welcome,
    meta: { requiresAuth: false } // 公开访问
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterView,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard', // 原来的 Home 移到 /dashboard
    name: 'Dashboard', // 重命名路由
    component: HomeDashboard,
    meta: { requiresAuth: true } // 需要认证
  },
  {
    path: '/videos',
    name: 'Videos',
    component: VideoList,
    meta: { requiresAuth: true }
  },
  {
    path: '/videos/:id',
    name: 'VideoDetail',
    component: VideoDetail,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/crawler',
    name: 'Crawler',
    component: DanmakuCrawler,
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: DanmakuAnalysis,
    meta: { requiresAuth: true }
  },
  {
    path: '/danmaku/:id',
    name: 'DanmakuView',
    component: DanmakuView,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis/:bvid',
    name: 'AnalysisView',
    component: AnalysisView,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { requiresAuth: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPasswordView,
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: ResetPasswordView,
    meta: { requiresAuth: false }
  },
  {
    path: '/my-tasks',
    name: 'MyTasks',
    component: MyTasksView,
    meta: { requiresAuth: true }
  },
  // 可以添加一个 404 页面
  // { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound }
]

console.log('Routes defined - Step 3');

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL || '/'),
  routes
})

console.log('Router created - Step 4');

// 路由守卫 - 添加认证检查
router.beforeEach((to, from, next) => {
  console.log('Router Guard executed for:', to.path);
  const authStore = useAuthStore();
  
  // 特殊处理分析详情页路由，检查bvid参数
  if (to.name === 'AnalysisView') {
    const bvid = to.params.bvid;
    if (!bvid || bvid === 'undefined') {
      console.error('无效的分析路由参数:', to.params);
      // 重定向到分析列表页
      next({ name: 'Analysis' });
      return;
    }
  }

  // 验证用户权限
  if (to.meta.requiresAuth) {
    console.log('访问受保护路由:', to.path, '认证状态:', authStore.isAuthenticated);
    
    // 如果用户未认证但尝试访问需要认证的页面
    if (!authStore.isAuthenticated) {
      console.log('用户未认证，重定向到登录页');
      next({ name: 'Login' });
      return;
    }
  }
  
  next();
})


// 保留原始的 getCookie 函数
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

console.log('Router file fully processed - Step 5');

export default router
