/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { RouterProvider } from 'react-router-dom'
import { RouterContext } from './context'
import { router } from './routes'

export function Router() {
  return (
    <RouterContext.Provider value={router as any}>
      <RouterProvider router={router} />
    </RouterContext.Provider>
  )
}
