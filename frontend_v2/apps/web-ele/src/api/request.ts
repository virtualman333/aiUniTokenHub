/**
 * API 请求层 - 适配 uniTokenHub 后端
 * 后端响应格式: { code, msg, data }
 * code >= 200 && < 300 表示成功，返回 data
 */
import type { HttpResponse } from '@vben/request';

import { useAppConfig } from '@vben/hooks';
import { preferences } from '@vben/preferences';
import {
  RequestClient,
} from '@vben/request';
import { useAccessStore } from '@vben/stores';

import Cookies from 'js-cookie';

import { ElMessage } from 'element-plus';
import { useAuthStore } from '#/store';

// 使用环境变量配置 baseURL
const apiURL = (import.meta.env as Record<string, string>).VITE_GLOB_API_URL || '/api';

function createRequestClient(baseURL: string) {
  const client = new RequestClient({
    baseURL,
  });

  /**
   * 重新认证逻辑 - 401 时清除 token 跳转登录页
   */
  async function doReAuthenticate() {
    console.warn('Access token is invalid or expired.');
    const accessStore = useAccessStore();
    const authStore = useAuthStore();
    accessStore.setAccessToken(null);
    Cookies.remove('token');
    Cookies.remove('userRole');
    if (
      preferences.app.loginExpiredMode === 'modal' &&
      accessStore.isAccessChecked
    ) {
      accessStore.setLoginExpired(true);
    } else {
      await authStore.logout();
    }
  }

  function formatToken(token: null | string) {
    return token ? `Bearer ${token}` : null;
  }

  // 请求头处理 - 从 Cookie 读取 token
  client.addRequestInterceptor({
    fulfilled: async (config) => {
      const token = Cookies.get('token');
      if (token) {
        config.headers.Authorization = formatToken(token);
      }
      return config;
    },
  });

  // 响应数据解构 - 适配后端 { code, msg, data } 格式
  client.addResponseInterceptor<HttpResponse>({
    fulfilled: (response) => {
      const responseData = response.data;

      // 检查是否为统一响应格式 { code, msg, data }
      if (
        responseData &&
        typeof responseData === 'object' &&
        'code' in responseData &&
        'data' in responseData
      ) {
        const { code, data, msg } = responseData;
        if (code >= 200 && code < 300) {
          return data;
        }
        // 业务错误，抛出错误信息
        const error = new Error(msg || '操作失败') as Error & {
          response: typeof response;
          code: number;
        };
        error.response = response;
        error.code = code;
        throw error;
      }
      // 非统一格式，直接返回原数据
      return responseData;
    },
  });

  // 401 token 过期处理
  client.addResponseInterceptor({
    fulfilled: undefined,
    rejected: async (error) => {
      if (error?.response?.status === 401) {
        await doReAuthenticate();
      }
      return Promise.reject(error);
    },
  });

  // 通用错误提示
  client.addResponseInterceptor({
    fulfilled: undefined,
    rejected: (error) => {
      // 尝试从后端响应中提取错误信息
      const responseData = error?.response?.data ?? {};
      const errorMessage =
        responseData?.msg ||
        responseData?.detail ||
        responseData?.error ||
        responseData?.message ||
        '';
      if (errorMessage && errorMessage !== error.message) {
        ElMessage.error(errorMessage);
      } else if (!error?.response?.status || error.response.status >= 500) {
        ElMessage.error(errorMessage || '网络异常，请稍后重试');
      }
      return Promise.reject(error);
    },
  });

  return client;
}

export const requestClient = createRequestClient(apiURL);

/** 不带认证信息的请求客户端（用于登录等公开接口） */
export const baseRequestClient = new RequestClient({ baseURL: apiURL });
