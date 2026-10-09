/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { AxiosInstance } from 'axios'

export type IRequestPlugin = {
  preinstall?: (instance: AxiosInstance) => void
  install?: (instance: AxiosInstance) => void
  postinstall?: (instance: AxiosInstance) => void
}

export function installPlugins(
  instance: AxiosInstance,
  plugins: IRequestPlugin[],
) {
  plugins
    .slice()
    .reverse()
    .forEach(({ preinstall }) => preinstall?.(instance))
  plugins.forEach(({ install }) => install?.(instance))
  plugins.forEach(({ postinstall }) => postinstall?.(instance))
}
