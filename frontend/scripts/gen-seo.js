#!/usr/bin/env node
/**
 * 按 `seo/site.js` 生成 `public/robots.txt` 与 `public/sitemap.xml`。
 *
 *   node scripts/gen-seo.js        # 写盘
 *   node scripts/gen-seo.js --check # 只比对，不写盘（`check-seo.js` 里那块也是这么做的）
 *
 * 为什么要生成而不是手写：这两份文件此前是手抄的，抄完就和路由表脱钩了 ——
 * 实测 sitemap 提交了三个 robots.txt 明确 Disallow 的 URL，而没有任何东西觉得不对。
 * 同一份「哪些页要收录」写在四处的必然结果就是互相矛盾。
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { robotsTxt, sitemapXml } from '../seo/site.js'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** [相对路径, 内容] —— 产物清单只此一份，`check-seo.js` 也从这里取 */
export const ARTIFACTS = [
  ['public/robots.txt', robotsTxt()],
  ['public/sitemap.xml', sitemapXml()]
]

export function main(argv = process.argv.slice(2)) {
  const checkOnly = argv.includes('--check')
  let changed = 0
  for (const [rel, content] of ARTIFACTS) {
    const file = path.join(ROOT, rel)
    const before = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : null
    if (before === content) {
      console.log(`  = ${rel}（已是最新）`)
      continue
    }
    if (checkOnly) {
      console.log(`  ! ${rel} 与 seo/site.js 不一致`)
      changed++
      continue
    }
    fs.writeFileSync(file, content, 'utf8')
    console.log(`  ${before === null ? '+' : '~'} ${rel}`)
    changed++
  }
  if (checkOnly) {
    console.log(changed ? `\n${changed} 个产物与唯一来源不一致 —— 跑 node scripts/gen-seo.js 重新生成`
      : '\n产物与 seo/site.js 一致')
    return changed ? 1 : 0
  }
  console.log(changed ? `\n已更新 ${changed} 个产物` : '\n产物已是最新，无需改动')
  return 0
}

// 只在本文件被直接执行时干活（被 import 时不写盘）
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  process.exit(main())
}
