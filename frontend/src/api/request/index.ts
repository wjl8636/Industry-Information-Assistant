/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { createRequest } from './request'

export const request = createRequest({
  baseURL: import.meta.env.VITE_API_BASE,
  loading: true,
  errorToast: true,
  cancelRepeat: true,
  unwrap: true,
})
