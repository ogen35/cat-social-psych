// 每个字体文件注册成独立 family（文件名去扩展名），用法：ctx.font = '96px "PuHui-Heavy"'
// 从 huashu-art-motion 提取时只保留 Vox 竖屏片段用到的字体（许可见同目录 LICENSES.md / OFL.txt）。
window.FONT_FACES = [
  // 中文黑体：family 名沿用 PuHui-*（引擎代码里的引用不用改），文件是思源黑体 Noto Sans SC（OFL 1.1）的 GB2312 子集
  {family:'PuHui-Medium', url:'lib/fonts/NotoSansSC-500.woff'},
  {family:'PuHui-Bold', url:'lib/fonts/NotoSansSC-700.woff'},
  {family:'PuHui-Heavy', url:'lib/fonts/NotoSansSC-800.woff'},
  {family:'PuHui-Black', url:'lib/fonts/NotoSansSC-900.woff'},
  // 霞鹜文楷（OFL 1.1）：手写感，用于猫爪批注
  {family:'LXGWWenKai-500', url:'lib/fonts/LXGWWenKai-500.woff'},
  // 数字
  {family:'Anton-400', url:'lib/fonts/Anton-400.woff'},
];
