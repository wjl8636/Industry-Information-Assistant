/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import axios, { AxiosRequestConfig } from 'axios'
import { authPlugin } from './plugins/auth'
import { errorToastPlugin } from './plugins/error-toast'
import { loadingPlugin } from './plugins/loading'
import { installPlugins } from './plugins/plugin'
import { repeatPlugin } from './plugins/repeat'
import { servicePlugin } from './plugins/service'

export function createRequest(configs: AxiosRequestConfig = {}) {
  const instance = axios.create(configs)

  installPlugins(instance, [
    authPlugin,
    servicePlugin,
    loadingPlugin,
    repeatPlugin,
    errorToastPlugin,
  ])

  return instance
}
