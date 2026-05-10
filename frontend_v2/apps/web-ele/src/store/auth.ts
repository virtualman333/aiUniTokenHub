import type { Recordable, UserInfo } from '@vben/types';

import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { DEFAULT_HOME_PATH, LOGIN_PATH } from '@vben/constants';
import { resetAllStores, useAccessStore, useUserStore } from '@vben/stores';

import { ElNotification } from 'element-plus';
import Cookies from 'js-cookie';
import { defineStore } from 'pinia';

import {
  changePasswordApi,
  getUserInfoApi,
  loginApi as loginApiFn,
  logoutApi,
  registerApi as registerApiFn,
} from '#/api/core/auth';
import { $t } from '#/locales';

export const useAuthStore = defineStore('auth', () => {
  const accessStore = useAccessStore();
  const userStore = useUserStore();
  const router = useRouter();

  const loginLoading = ref(false);

  /**
   * 异步处理登录操作
   * @param params 登录表单数据 { username, password }
   * @param onSuccess 成功回调
   */
  async function authLogin(
    params: Recordable<any>,
    onSuccess?: () => Promise<void> | void,
  ) {
    let userInfo: null | UserInfo = null;
    try {
      loginLoading.value = true;
      const { token, user } = await loginApiFn(params);

      if (token && user) {
        // 使用 Cookie 存储 token（与原项目一致）
        Cookies.set('token', token, { expires: 7 });
        Cookies.set('userRole', user.role || '');

        // 将 accessToken 存储到 Vben 的 accessStore
        accessStore.setAccessToken(token);

        // 获取用户详细信息
        userInfo = (await fetchUserInfo()) as UserInfo | null;

        userStore.setUserInfo(userInfo);

        if (accessStore.loginExpired) {
          accessStore.setLoginExpired(false);
        } else {
          await onSuccess?.() ?? router.push(DEFAULT_HOME_PATH);
        }

        ElNotification({
          message: `${$t('authentication.loginSuccessDesc')}: ${userInfo?.realName || user.username}`,
          title: $t('authentication.loginSuccess'),
          type: 'success',
        });
      }
    } finally {
      loginLoading.value = false;
    }

    return { userInfo };
  }

  /**
   * 异步处理注册操作
   */
  async function authRegister(params: Recordable<any>) {
    let userInfo: null | UserInfo = null;
    try {
      loginLoading.value = true;
      const { token, user } = await registerApiFn(params);

      if (token && user) {
        Cookies.set('token', token, { expires: 7 });
        Cookies.set('userRole', user.role || '');
        accessStore.setAccessToken(token);

        userInfo = user as unknown as UserInfo;
        userStore.setUserInfo(userInfo);

        ElNotification({
          message: `注册成功，欢迎 ${user.username}`,
          title: '注册成功',
          type: 'success',
        });
      }
    } finally {
      loginLoading.value = false;
    }

    return { userInfo };
  }

  async function logout(redirect: boolean = true) {
    try {
      await logoutApi();
    } catch {
      // 忽略错误
    }

    // 清除 Cookie 和本地状态
    Cookies.remove('token');
    Cookies.remove('userRole');

    resetAllStores();
    accessStore.setLoginExpired(false);

    await router.replace({
      path: LOGIN_PATH,
      query: redirect
        ? {
            redirect: encodeURIComponent(router.currentRoute.value.fullPath),
          }
        : {},
    });
  }

  /**
   * 获取用户信息 - GET /users/auth/me/
   */
  async function fetchUserInfo() {
    let use