/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { AxiosResponse } from 'axios'

export class ResponseError extends Error {
  response: AxiosResponse<any> | undefined

  constructor(message: string, response?: AxiosResponse<any>) {
    super(message)
    this.response = response
  }
}
