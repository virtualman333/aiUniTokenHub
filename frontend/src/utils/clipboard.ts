export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) {
    return false
  }

  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (error) {
      console.warn('Clipboard API failed, trying fallback method:', error)
    }
  }

  return fallbackCopyToClipboard(text)
}

function fallbackCopyToClipboard(text: string): boolean {
  try {
    const textArea = document.createElement('textarea')
    textArea.value = text
    
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    textArea.style.opacity = '0'
    textArea.setAttribute('readonly', '')
    
    document.body.appendChild(textArea)
    textArea.select()
    textArea.setSelectionRange(0, text.length)
    
    const successful = document.execCommand('copy')
    document.body.removeChild(textArea)
    
    return successful
  } catch (error) {
    console.error('Fallback copy failed:', error)
    return false
  }
}
