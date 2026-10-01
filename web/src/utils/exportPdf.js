/**
 * 将 DOM 元素导出为 PDF
 * 原理 = html2canvas 把 DOM 截图成图片（自动处理中文） + jsPDF 拼成多页 A4 PDF
 * 用法：import { exportElementToPdf } from '@/utils/exportPdf'
 *      <div ref="reportRef">报表内容</div>
 *      exportElementToPdf(reportRef.value, '绩效薪酬.pdf')
 */
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

export async function exportElementToPdf(el, filename = '报表.pdf') {
  if (!el) {
    throw new Error('导出失败：找不到目标元素')
  }
  // 隐藏导出按钮本身，避免出现在截图里
  const hideBtns = el.querySelectorAll('[data-pdf-hide]')
  const prevDisplay = []
  hideBtns.forEach((b, i) => {
    prevDisplay[i] = b.style.display
    b.style.display = 'none'
  })
  let canvas
  try {
    canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    })
  } finally {
    hideBtns.forEach((b, i) => { b.style.display = prevDisplay[i] || '' })
  }

  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p', 'mm', 'a4')
  const pageW = pdf.internal.pageSize.getWidth()
  const pageH = pdf.internal.pageSize.getHeight()
  const imgW = pageW - 10 // 左右各 5mm 边距
  const imgH = (canvas.height * imgW) / canvas.width

  let heightLeft = imgH
  let position = 5 // 上边距 5mm
  pdf.addImage(imgData, 'PNG', 5, position, imgW, imgH)
  heightLeft -= (pageH - 10)

  while (heightLeft > 0) {
    position -= (pageH - 10)
    pdf.addPage()
    pdf.addImage(imgData, 'PNG', 5, position, imgW, imgH)
    heightLeft -= (pageH - 10)
  }

  pdf.save(filename)
}

export default exportElementToPdf