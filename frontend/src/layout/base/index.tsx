/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { Footer } from './footer'
import './index.scss'
import { Nav } from './nav'

export function BaseLayout({ children }: { children?: React.ReactNode }) {
  return (
    <div className="base-layout">
      <div className="base-layout__sidebar">
        <div className="base-layout__sidebar-main scrollbar-style">
          <Nav />

          <Footer />
        </div>
      </div>

      <div className="base-layout__content">{children}</div>
    </div>
  )
}
