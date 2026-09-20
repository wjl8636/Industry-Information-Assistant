/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { createContext } from 'react'
import { createBrowserRouter } from 'react-router-dom'

export const RouterContext = createContext<
  ReturnType<typeof createBrowserRouter>
>(null as any)
