/**
 * Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
 * 未经授权，禁止转售或仿制。
 */

import styles from './source.module.scss'

export default function Source(props: {
  list: API.ChatItem['search_results']
}) {
  const { list } = props

  return (
    <div className={styles['source__list']}>
      {list?.map((source) => (
        <a
          className={styles['source__item']}
          key={source.id}
          href={source.url}
          target="_blank"
        >
          <img className={styles['icon']} src={source.siteIcon} />
          <div className={styles['info']}>
            <span className={styles['host']}>{source.host}</span>
            <span className={styles['name']} title={source.name}>
              {source.name}
            </span>
          </div>
        </a>
      ))}
    </div>
  )
}
