import confetti from 'canvas-confetti'

/**
 * 触发一个精美的彩色纸屑礼花筒效果（两边持续喷射）
 * 适合用于支付成功、任务完成等场景
 */
export function fireConfetti() {
  const duration = 3000;
  const end = Date.now() + duration;

  (function frame() {
    // 从左侧发射
    confetti({
      particleCount: 5,
      angle: 60,
      spread: 55,
      origin: { x: 0 },
      colors: ['#26ccff', '#a25afd', '#ff5e7e', '#88ff5a', '#fcff42', '#ffa62d', '#ff36ff']
    });
    // 从右侧发射
    confetti({
      particleCount: 5,
      angle: 120,
      spread: 55,
      origin: { x: 1 },
      colors: ['#26ccff', '#a25afd', '#ff5e7e', '#88ff5a', '#fcff42', '#ffa62d', '#ff36ff']
    });

    if (Date.now() < end) {
      requestAnimationFrame(frame);
    }
  }());
}

/**
 * 触发一次性居中爆发的彩纸效果
 */
export function fireCenterConfetti() {
  confetti({
    particleCount: 150,
    spread: 100,
    origin: { y: 0.6 },
    colors: ['#26ccff', '#a25afd', '#ff5e7e', '#88ff5a', '#fcff42', '#ffa62d', '#ff36ff']
  });
}
