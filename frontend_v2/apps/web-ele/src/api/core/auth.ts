import { baseRequestClient, requestClient } from '#/api/request';

export namespace AuthApi {
  /** 登录接口参数 */
  export interface LoginParams {
    username?: string;
    password?: string;
  }

  /** 登录接口返回值 - 适配后端 { token, user } 格式 */
  export interface LoginResult {
    token: string;
    user: UserInfo;
  }

  /** 用户基本信息 */
  export interface UserInfo {
    id: number;
    username: string;
    email?: string;
    role: string;
    balance?: number;
    avatar?: string;
    [key: string]: any;
  }
}

/**
 * 用户登录 - POST /users/auth/login/
 * 返回 { token, user }
 */
export async function loginApi(data: AuthApi.LoginParams) {
  return requestClient.post<AuthApi.LoginResult>('/users/auth/login/', data);
}

/**
 * 用户注册 - POST /users/auth/register/
 * 返回 { token, user }
 */
export async function registerApi(data: Record<string, any>) {
  return requestClient.post<AuthApi.LoginResult>('/users/auth/register/', data);
}

/**
 * 发送邮箱验证码 - POST /users/auth/send_email_code/
 */
export async function sendEmailCodeApi(data: { email: string; purpose?: string }) {
  return baseRequestClient.post('/users/auth/send_email_code/', data);
}

/**
 * 发送重置密码验证码 - POST /users/auth/password/reset/send_code/
 */
export async function sendResetCodeApi(data: { email: string }) {
  return baseRequestClient.post('/users/auth/password/reset/send_code/', data);
}

/**
 * 重置密码 - POST /users/auth/password/reset/confirm/
 */
export async function resetPasswordApi(data: {
  email: string;
  email_code: string;
  new_password: string;
}) {
  return baseRequestClient.post('/users/auth/password/reset/confirm/', data);
}

/**
 * 退出登录 - 清除本地状态即可（后端无 logout 接口）
 */
export async function logoutApi() {
  // 后端使用 JWT/Cookie 方式，前端清除本地存储即可
  return Promise.resolve();
}
