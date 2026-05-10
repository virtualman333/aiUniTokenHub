import { requestClient } from '#/api/request';

export namespace UserApi {
  /** 用户信息类型 */
  export interface UserInfo {
    id: number;
    username: string;
    email?: string;
    role: string;
    balance?: number;
    is_active?: boolean;
    invite_code?: string;
    created_at?: string;
    [key: string]: any;
  }
}

/**
 * 获取当前用户信息 - GET /users/auth/me/
 */
export async function getUserInfoApi() {
  return requestClient.get<UserApi.UserInfo>('/users/auth/me/');
}

/**
 * 修改密码 - POST /users/auth/change_password/
 */
export async function changePasswordApi(data: {
  old_password: string;
  new_password: string;
}) {
  return requestClient.post('/users/auth/change_password/', data);
}
