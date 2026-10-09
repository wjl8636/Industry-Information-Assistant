/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import '@ant-design/v5-patch-for-react-19'
import 'normalize.css'
import { createRoot } from 'react-dom/client'
import './antd.scss'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(<App />)
