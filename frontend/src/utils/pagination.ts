/**
 * 分页拉取的唯一入口。
 *
 * 后端 `backend/apps/utils/pagination.py` 会把 `page_size` 夹到 `MAX_PAGE_SIZE`（100）。
 * 所以「我要全部」**不能**靠写一个更大的数字来表达 —— 那个数字会被静默夹紧，
 * 表现为下拉框少几项、导出少几千行，而且全程不报错。要全部就必须翻页。
 *
 * `PAGE_SIZE` 与后端 `MAX_PAGE_SIZE` 必须相等，由
 * `backend/apps/utils/tests/test_frontend_pagination_contract.py` 盯着，别单独改一边。
 */

/** 单页条数上限，与后端 `MAX_PAGE_SIZE` 对齐。 */
export const PAGE_SIZE = 100

/** 翻页次数上限：后端 `total` 万一撒谎，不至于把自己翻死。 */
export const MAX_PAGES = 50

/** 分页接口的返回体（响应拦截器已剥掉 `{code,msg,data}` 信封）。 */
export interface PagePayload<T> {
  results: T[]
  total: number
  page: number
  page_size: number
}

export interface AllPages<T> {
  items: T[]
  /**
   * 该接口**本来就没分页**，原样返回的就是全部 —— 不是失败，也无需翻页。
   * 有这种形态是因为仓库里还留着一批继承 DRF 默认 `list` 的 ViewSet。
   */
  unpaginated: boolean
  /** 翻到 MAX_PAGES 还没拿全。调用方**必须**把这件事说出来，不许静默。 */
  truncated: boolean
  /** 实际请求了几次。 */
  pages: number
}

/** 分页接口返回 `{results,...}`；没分页的接口返回裸数组。两种都要认。 */
export function unwrapResults<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[]
  const results = (payload as PagePayload<T> | null)?.results
  if (Array.isArray(results)) return results
  return []
}

/**
 * 翻页拿全。
 *
 * @param fetchPage 接收 `(page, pageSize)`，返回一页的原始响应
 * @param options   `pageSize` 默认 `PAGE_SIZE`；`maxPages` 默认 `MAX_PAGES`
 */
export async function fetchAllPages<T>(
  fetchPage: (page: number, pageSize: number) => Promise<unknown>,
  options: { pageSize?: number; maxPages?: number } = {}
): Promise<AllPages<T>> {
  const pageSize = options.pageSize ?? PAGE_SIZE
  const maxPages = options.maxPages ?? MAX_PAGES
  const items: T[] = []

  let page = 1
  for (;;) {
    const payload = await fetchPage(page, pageSize)

    if (Array.isArray(payload)) {
      // 没分页的接口：一次就是全部。继续翻页只会把同一批数据重复累加。
      items.push(...(payload as T[]))
      return { items, unpaginated: true, truncated: false, pages: page }
    }

    const batch = unwrapResults<T>(payload)
    items.push(...batch)

    // 拿不满一页就说明到底了。
    if (batch.length < pageSize) {
      return { items, unpaginated: false, truncated: false, pages: page }
    }
    if (page >= maxPages) {
      return { items, unpaginated: false, truncated: true, pages: page }
    }
    page += 1
  }
}
