/**
 * Markdown 渲染工具
 * marked + highlight.js + DOMPurify
 */
import { marked } from 'marked'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import 'highlight.js/styles/github.css'

// 配置 marked
marked.setOptions({
  // GFM、自动换行
  gfm: true,
  breaks: true,
})

// 通过自定义渲染器接入代码高亮
const renderer = new marked.Renderer()
renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
  let highlighted = ''
  try {
    if (lang && hljs.getLanguage(lang)) {
      highlighted = hljs.highlight(text, { language: lang, ignoreIllegals: true }).value
    } else {
      highlighted = hljs.highlightAuto(text).value
    }
  } catch {
    highlighted = escapeHtml(text)
  }
  const langClass = lang ? `language-${lang}` : ''
  return `<pre class="hljs"><code class="${langClass}">${highlighted}</code></pre>`
}
marked.use({ renderer })

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

/**
 * 把 markdown 字符串渲染成安全的 html
 */
export function renderMarkdown(md: string): string {
  if (!md) return ''
  // marked 同步模式下返回 string
  const html = marked.parse(md, { async: false }) as string
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'rel'],
  })
}
