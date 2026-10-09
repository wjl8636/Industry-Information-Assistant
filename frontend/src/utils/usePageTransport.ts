/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import { useMount } from 'ahooks'
import { useState } from 'react'

const tempMap = new Map<PageTransportKey<any>, any>()

// @ts-ignore
export interface PageTransportKey<T> extends Symbol {}

/**
 * 用于页面间数据传输
 * 需要注意的是，仅在组件初始化时有效
 */
export function usePageTransport<T>(key: PageTransportKey<T>) {
  const [data, setData] = useState<T | undefined>(() => tempMap.get(key))

  useMount(() => {
    const tempData = tempMap.get(key)
    setData(tempData)
    tempMap.delete(key)
  })

  return {
    data,
    setData,
  }
}

export function setPageTransport<T>(key: PageTransportKey<T>, data: T) {
  tempMap.set(key, data)
}
