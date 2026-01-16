import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import Home from '../views/Home.vue'
import UserProfile from '../views/UserProfile.vue'
import ForgotPassword from '../views/ForgotPassword.vue'

const routes = [
  { path: '/', component: Home, meta: { requiresAuth: true } },
  { path: '/login', component: Login },
  { path: '/forgot-password', component: ForgotPassword },
  { path: '/admin', component: AdminDashboard, meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/profile', component: UserProfile, meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const user = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null
  
  if (to.meta.requiresAuth && !token) {
    next('/login')
    return
  }
  
  if (to.meta.requiresAdmin && user?.role !== 'admin') {
    next('/')
    return
  }
  
  // 管理员访问根路径时，自动跳转到管理后台
  if (to.path === '/' && token && user?.role === 'admin') {
    next('/admin')
    return
  }
  
  if (to.path === '/login' && token) {
    next(user?.role === 'admin' ? '/admin' : '/')
    return
  }
  
  next()
})

export default router
