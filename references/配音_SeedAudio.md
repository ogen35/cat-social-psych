# 配音：LibTV Seed Audio 1.0

**用户定的（2026-11-07 指定，2026-11-09 重申）：配音一律用 LibTV 里的 Seed Audio 1.0（`seed-audio-1.0` 音频节点），提示词用 V1 写法，参考音频用角色库登记的声音样本节点。**

- LibTV MCP 连不上（会话里没有 LibTV 工具、要重新授权）：停下来告诉用户「LibTV 要在交互会话里用 /mcp 重新授权」，等授权好再配。不要自己改用豆包直连或别的 TTS。
- `libtv_voice.py direct`（同模型直连豆包语音接口）只在用户明确说「用豆包直连」时才用；第 31 期就是在 LibTV 断开时用它配的，用户随后要求以后都走 LibTV。
- 片子里的台词写法、字数、语速设置见 `references/Vox版工作流.md`「film.py 设置」。


- 每个角色的声音样本（`角色库/<角色>/声音样本.wav`）已经传到 LibTV，节点登记在 `角色.json` 的 `libtv_voice`：大比 `a-qoIRhwm1An`、胜利 `a-qWBZrRJELN`、大宝 `a-hIiTmHbwN5`、旁白 `a-YLIoCxjn5V`（项目 `55630bcc61e34037b599b51aadb333e8`）。
- 提示词是用户听过三版后选的 V1 写法：「完全复刻样本：同一个嗓音、同样的音高、<角色特点>；不要改变音调，不要播音腔」＋语气（「但嗓音和音高还是样本里那样」）＋「一字不差地念：……不要增加、删减或改动任何字」。不额外降调。

```sh
python3 $S/scripts/libtv_voice.py plan <集目录>      # 每句的提示词、参考节点、params、idempotencyKey → build/tts/配音单.json
# 逐句：create_node(nodeType='audio', model='seed-audio-1.0', left=[参考节点], prompt=…, params=…, run=true, idempotencyKey=idem)
# 等完成后用 read_node 拿 url（data.url[0]）
F="uv run -q --with numpy --with faster-whisper --with opencc-python-reimplemented --with pypinyin --with sherpa-onnx python $S/scripts/libtv_voice.py"
$F fetch <集目录> <句id>=<url> [<句id>=<url> ...]   # 下载、whisper 按拼音核字、量声纹、裁头尾和长停顿，写进缓存
python3 $S/scripts/libtv_voice.py status <集目录>
```

- `fetch` 标 🟡 的句子要重新生成，换一个 idempotencyKey（`idem` 后面加 `-2`）。三种情况会标黄：
  - 念错字，包括多念：大宝样本里的口头禅「我不」偶尔会漏进句尾；
  - 最后一个字被截断；
  - 声纹相似度低于 0.70。2026-11-07 实测：同一个角色 0.78–0.88，不同角色 0.07–0.44。
- 情绪写得太强，音调会变高（胜利、大比试过高 2 个半音）。语气写短、写具体。
- **取音频地址**：一批提交多句后，任务完成了，画布节点却常常还显示「生成中」（`url` 为空）。对每个任务调一次 `task_status(task_id)`，结果就会回写到画布；之后再用 `read_node` 拿 `data.url[0]`。
- **句尾多说一截**：Seed Audio 偶尔念完稿子还继续说，常常是参考样本里的话漏了出来。`fetch` 会按 whisper 的逐字时间自动剪掉，并打印「✂」。剪完还对不上的才需要重新生成。
- **成功率参考**（第 27b 期，28 句）：
  - 一次通过 13 句；
  - 剪尾后通过 4 句；
  - 重新生成 10 句。重生成的原因：漏字、念错、句尾截断、声纹低于 0.70。胜利（东北口音、情绪重）的声纹最容易偏低。
- `build_pixel` 看到 `VOICE='libtv'` 只读这个缓存，缺句会直接报错，不会出无声片。
- **语速**：Seed Audio 平均每秒只念 3.5 个字，句中停顿也多；第 27b 期原样拼起来有 115 秒。
  - film.py 写 `VOICE_TEMPO = 1.25`：用 atempo 整体加速，只变快、不变调。
  - 再写 `VOICE_MAX_GAP = 0.4`：句中停顿最长 0.4 秒。
  - 再把 `GAP` 设成 0.2。
  - 这样大约每秒 4.6 个字，28 句约 87 秒。这一步是本地处理，不用重新生成。
- **慢句单独加速**：film.py 写 `VOICE_MIN_RATE = 4.6`。整集按 `VOICE_TEMPO` 加速后，还慢于每秒 4.6 字的句子再单独加速，最多再快 1.25 倍。大宝的「懒洋洋」「慢慢说」语气每秒只念 2.9–3.5 字，第 29 期因此拖到 102 秒，加上这一条后是 89.7 秒。
- **文本审核**：台词里有「恐怖袭击」这类词，Seed Audio 会直接失败（`task_status` 报 `demo text audit failed`）。按书换成中性说法（第 30 期改成「九一一事件」），再重新生成。
- **太短的句子容易串话**：「会吃亏的。」这种四五个字的句子，两次都多念了半句或念两遍。台词至少写到八九个字（「会吃亏的，而且是大亏。」）。
- **「声音越来越小」「心虚」这类语气会把声纹压低**（胜利只有 0.65–0.68）。换成「心虚，干笑」这种还保持原来嗓门的写法。
- **whisper 常见误报**（不用重新生成）：把「两百三十」写成 230、「九一一」写成 911（核字表里已把「两」当「二」）；剪掉句尾多说的部分之后，常报「最后一个字被截断」，用 `silencedetect` 看原始音频结尾有没有静音就知道。
