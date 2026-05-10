<script lang="ts" setup>
import type { VbenFormSchema } from '@vben/common-ui';
import type { Recordable } from '@vben/types';

import { computed, markRaw, onBeforeUnmount, ref } from 'vue';

import {
  AuthenticationForgetPassword,
  VbenButton,
  z,
} from '@vben/common-ui';
import { $t } from '@vben/locales';

import { sendResetCodeApi, resetPasswordApi } from '#/api';
import { ElMessage } from 'element-plus';

defineOptions({ name: 'ForgetPassword' });

const loading = ref(false);
const sendingCode = ref(false);
const countdown = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

function startCountdown(seconds: number) {
  countdown.value = seconds;
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      clearInterval(timer!);
      timer = null;
    }
  }, 1000);
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});

const codeBtnText = computed(() => {
  if (countdown.value > 0)
    return $t('authentication.sendText').replace('{0}', String(countdown.value));
  return $t('authentication.sendCode');
});

async function handleSendCode(email: string) {
  sendingCode.value = true;
  try {
    const res = await sendResetCodeApi({ email });
    ElMessage.success('验证码已发送，请查收邮件');
    const wait = Number((res as any)?.resend_seconds) || 60;
    startCountdown(wait);
  } catch (error: any) {
    ElMessage.error(error?.message || '发送失败');
  } finally {
    sendingCode.value = false;
  }
}

const formSchema = computed((): VbenFormSchema[] => {
  return [
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: 'example@example.com',
      },
      fieldName: 'email',
      label: $t('authentication.email'),
      rules: z
        .string()
        .min(1, { message: $t('authentication.emailTip') })
        .email($t('authentication.emailValidErrorTip')),
    },
    {
      component: 'VbenInput',
      componentProps: {
        placeholder: '请输入6位邮箱验证码',
        maxlength: 6,
      },
      fieldName: 'email_code',
      label: '邮箱验证码',
      renderComponentContent: () => ({
        after: () =>
          h(VbenButton, {
            disabled: sendingCode.value || countdown.value > 0,
            loading: sendingCode.value,
            size: 'small',
            onClick() {
              // 通过 formRef 获取 email 值
              const emailEl = document.querySelector(
                '[name="email"] input',
              ) as HTMLInputElement;
              const email = emailEl?.value || '';
              if (!email) {
                ElMessage.warning('请先输入邮箱');
                return;
              }
              handleSendCode(email);
            },
            default: () => codeBtnText.value,
          }),
      }),
      rules: z
        .string()
        .min(1, { message: '请输入邮箱验证码' })
        .length(6, { message: '验证码为6位数字' }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '请输入新密码（至少6位）',
      },
      fieldName: 'password',
      label: '新密码',
      rules: z
        .string()
        .min(6, { message: '密码长度至少为6位' }),
    },
    {
      component: 'VbenInputPassword',
      componentProps: {
        placeholder: '确认新密码',
      },
      dependencies: {
        rules(values) {
          const { password } = values;
          return z
            .string()
            .min(1, { message: '请确认密码' })
            .refine((value) => value === password, {
              message: $t('authentication.confirmPasswordTip'),
            });
        },
        triggerFields: ['password'],
      },
      fieldName: 'confirm_password',
      label: $t('authentication.confirmPassword'),
    },
  ];
});

async function handleSubmit(value: Recordable<any>) {
  loading.value = true;
  try {
    await resetPasswordApi({
      email: value.email,
      email_code: value.email_code,
      new_password: value.password,
    });
    ElMessage.success('密码重置成功，请使用新密码登录');
  } catch (error: any) {
    ElMessage.error(error?.message || '重置密码失败');
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AuthenticationForgetPassword
    :form-schema="formSchema"
    :loading="loading"
    sub-title="输入您的邮箱以接收验证码并重置密码"
    title="忘记密码？"
    @submit="handleSubmit"
  />
</template>
