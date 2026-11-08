#!/usr/bin/env python3
"""配乐与音效：按分镜的情绪（mood）合成背景音乐、按事件放音效。纯代码合成，不用采样，没有版权问题。

  uv run --with numpy --with scipy --with soundfile python audio_fx.py --plan build/音频计划.json --out build/
  uv run --with numpy --with scipy --with soundfile python audio_fx.py --demo <目录>    # 每种配乐、每个音效各出一个试听文件

build_episode.py 会自动生成音频计划并调用本脚本，一般不用手动跑。

音频计划（JSON）：
  total   全片秒数
  beds    [{start, end, mood}]   连续的情绪段；同一情绪的相邻镜头合成一段
  drops   [{t, dur}]             配乐「停」：揭晓前把音乐抽空，让下一记重音更响
  sfx     [{t, name, gain}]      音效：t 是音效「打点」的时刻（riser 在 t 结束，其余在 t 起音）

情绪 → 配乐：悬疑（低频长音＋钟表滴答＋心跳低音＋偶尔的不协和高音）· 紧张（八分音符低音推进＋十六分滴答＋渐亮滤波）·
  轻松（蹑手蹑脚的拨弦＋轻拍）· 平叙（慢钢琴琶音）· 温暖（柔和和弦垫底＋钢琴旋律）。揭晓沿用紧张，反转沿用轻松。
音效：whoosh 嗖 · hit 重击 · boom 低沉轰 · riser 上升蓄力 · ding 叮 · pop 啵 · tick 滴答 · heartbeat 心跳 ·
  glitch 故障 · scratch 唱片急停 · sting 悬疑「当—当—当」。

想用自己的音乐或音效：放进 skill 的 assets/配乐/<情绪>.wav|mp3（会循环铺满那一段）或 assets/音效/<名字>.wav|mp3，
同名文件优先于合成的。抖音上用平台热门 BGM 也可以：成片导出无配乐版（build_episode.py --no-bgm），在抖音里加。
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
import scipy.signal as ss
import soundfile as sf

SR = 48000
SKILL = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- 基础
def tv(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)          # MIDI → Hz
def lp(x, fc, o=2): return ss.sosfilt(ss.butter(o, min(fc, SR / 2 * 0.95), 'low', fs=SR, output='sos'), x)
def hp(x, fc, o=2): return ss.sosfilt(ss.butter(o, fc, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return ss.sosfilt(ss.butter(o, [lo, min(hi, SR / 2 * 0.95)], 'band', fs=SR, output='sos'), x)
def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    a, d, r = int(a * SR), int(d * SR), int(r * SR); h = max(0, n - a - d - r)
    return np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False), np.full(h, s), np.linspace(s, 0, r)])[:n]
def expdec(d, tau): return np.exp(-tv(d) / tau)
def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1; return x / m * peak
def reverb(x, size=1.2, mix=0.25):
    """廉价混响：指数衰减噪声当冲激响应。"""
    ir = rng.standard_normal(int(size * SR)) * np.exp(-tv(size) / (size / 5)); ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
    wet = ss.fftconvolve(x, ir)[:len(x)]
    return x * (1 - mix) + wet * mix * 0.6

def add(bus, sig, t, gain=1.0):
    s = int(round(t * SR))
    if s >= len(bus) or s + len(sig) <= 0: return
    if s < 0: sig = sig[-s:]; s = 0
    sig = sig[:len(bus) - s]; bus[s:s + len(sig)] += sig * gain

# ---------------------------------------------------------------- 乐器
def piano(m, d=1.6, bright=1.0):
    f = hz(m); t = tv(d); x = np.zeros_like(t)
    for k, a in enumerate([1, .5, .28, .16, .09, .05], 1):
        x += a * np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (1.2 + 0.9 * k) / bright)
    return x * np.minimum(1, t / 0.004)

def pluck(m, d=0.35, bright=1.0):
    f = hz(m); t = tv(d); x = np.zeros_like(t)
    for k, a in enumerate([1, .7, .45, .25, .12], 1):
        x += a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (9 + 6 * k) / bright)
    return x * np.minimum(1, t / 0.002)

def pad(ms, d, cutoff=1400):
    t = tv(d); x = np.zeros_like(t)
    for m in ms:
        for det in (-0.06, 0, 0.07):
            f = hz(m + det); x += sum(np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6)) / k for k in (1, 2, 3))
    return lp(x, cutoff) * env_adsr(len(t), a=min(0.8, d / 3), d=0.2, s=0.85, r=min(1.2, d / 3))

def drone(m, d):
    t = tv(d); f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + 1) + 0.3 * np.sin(2 * np.pi * f * 2.003 * t)
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.13 * t)                       # 慢慢起伏
    wind = lp(rng.standard_normal(len(t)), 400) * 0.08
    return (x + wind) * env_adsr(len(t), a=1.0, d=0.1, s=1, r=1.0)

def bass_saw(m, d=0.22):
    f = hz(m); t = tv(d); x = ss.sawtooth(2 * np.pi * f * t) + 0.6 * np.sin(np.pi * f * t)
    return lp(x, 700) * np.exp(-t * 7) * np.minimum(1, t / 0.003)

def kick(f0=110, f1=42, tau=0.22, d=0.45):
    t = tv(d); f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)

def click(f=2600, d=0.03, g=1.0):
    t = tv(d); return bp(rng.standard_normal(len(t)), f * 0.7, f * 1.4) * np.exp(-t / 0.006) * g

def hat(d=0.06):
    t = tv(d); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t / 0.015)

# ---------------------------------------------------------------- 配乐（每种情绪一段可铺满任意时长的床）
def bed_suspense(d):
    """悬疑 72 BPM：D 小调低频长音 ＋ 滴答 ＋ 心跳低音 ＋ 稀疏的低音钢琴动机 ＋ 偶尔的小二度高音。"""
    bus = np.zeros(int(d * SR) + SR); beat = 60 / 72
    add(bus, drone(38, d) * 0.3, 0); add(bus, drone(45, d) * 0.12, 0)
    n = int(d / beat) + 1
    for i in range(n):
        add(bus, click(2400 if i % 2 == 0 else 1900, g=0.55), i * beat)
        if i % 4 == 0: add(bus, kick(70, 40, 0.18) * 0.55, i * beat); add(bus, kick(70, 40, 0.15) * 0.35, i * beat + 0.24)
    motif = [62, 65, 64, 57]
    for j, i in enumerate(range(0, n, 8)):
        for k, m in enumerate(motif): add(bus, piano(m - 12, 2.2, 0.7) * 0.32, (i + k) * beat)
    for i in range(6, n, 16):
        t0 = i * beat; seg = min(4 * beat, d - t0)
        if seg > 0.5: add(bus, (np.sin(2 * np.pi * hz(86) * tv(seg)) + np.sin(2 * np.pi * hz(87) * tv(seg))) * env_adsr(int(seg * SR), a=seg / 2, d=0, s=1, r=seg / 2) * 0.05, t0)
    return reverb(bus[:int(d * SR)], 1.6, 0.3)

def bed_tense(d):
    """紧张 112 BPM：八分音符低音推进 ＋ 十六分滴答 ＋ 底鼓 ＋ 逐渐打开的滤波。"""
    bus = np.zeros(int(d * SR) + SR); e = 60 / 112 / 2
    roots = [38, 38, 41, 36]
    n = int(d / e) + 1
    for i in range(n):
        r = roots[(i // 16) % 4]; add(bus, bass_saw(r if i % 4 != 3 else r + 12, e * 0.9) * 0.6, i * e)
        add(bus, hat() * (0.3 if i % 2 else 0.18), i * e); add(bus, hat() * 0.12, i * e + e / 2)
        if i % 4 == 0: add(bus, kick() * 0.7, i * e)
    add(bus, pad([62, 65, 68], d, 900) * 0.07, 0)                           # 不协和的垫底（减三和弦）
    x = bus[:int(d * SR)]
    ramp = np.linspace(0.75, 1.0, len(x))                                    # 越来越满
    return reverb(x * ramp, 0.9, 0.18)

def bed_light(d):
    """轻松 104 BPM：F 大调「蹑手蹑脚」拨弦 ＋ 轻拍 ＋ 低音拨弦。"""
    bus = np.zeros(int(d * SR) + SR); e = 60 / 104 / 2
    line = [65, 69, 72, 69, 67, 70, 74, 70, 65, 69, 72, 77, 76, 72, 67, 64]
    n = int(d / e) + 1
    for i in range(n):
        if i % 2 == 0: add(bus, pluck(line[(i // 2) % 16], 0.3) * 0.38, i * e)
        if i % 8 == 0: add(bus, pluck([41, 46, 48, 41][(i // 8) % 4], 0.5, 0.6) * 0.5, i * e)
        if i % 8 == 4: add(bus, click(1500, 0.05, 0.5), i * e)
    return reverb(bus[:int(d * SR)], 0.7, 0.15)

def bed_neutral(d):
    """平叙 90 BPM：D 小调慢钢琴琶音（Dm–B♭–F–C）。"""
    bus = np.zeros(int(d * SR) + SR); e = 60 / 90 / 2
    chords = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 48, 53, 57], [48, 55, 60, 64]]
    n = int(d / e) + 1
    for i in range(n):
        ch = chords[(i // 8) % 4]; add(bus, piano(ch[[0, 2, 1, 3, 2, 1, 3, 2][i % 8]], 1.4, 0.8) * 0.3, i * e)
    return reverb(bus[:int(d * SR)], 1.4, 0.3)

def bed_warm(d):
    """温暖 80 BPM：F 大调和弦垫底（F–C–Dm–B♭）＋ 钢琴旋律。"""
    bus = np.zeros(int(d * SR) + SR); bar = 4 * 60 / 80
    chords = [[53, 57, 60], [48, 55, 60], [50, 53, 57], [46, 50, 53]]
    mel = [72, 74, 76, 74, 72, 69, 67, 69]
    n = int(d / bar) + 1
    for i in range(n):
        add(bus, pad(chords[i % 4], bar + 0.6, 1600) * 0.12, i * bar)
        for k in range(2): add(bus, piano(mel[(i * 2 + k) % 8], 1.8) * 0.22, i * bar + k * bar / 2)
    return reverb(bus[:int(d * SR)], 1.8, 0.35)

BEDS = {'悬疑': bed_suspense, '紧张': bed_tense, '揭晓': bed_tense, '轻松': bed_light, '反转': bed_light, '平叙': bed_neutral, '温暖': bed_warm}
BED_RMS_DB = {'悬疑': -24, '紧张': -23, '揭晓': -23, '轻松': -25, '反转': -25, '平叙': -27, '温暖': -26}   # 各情绪床的平均响度：按 RMS 对齐，换情绪不忽大忽小

# ---------------------------------------------------------------- 音效
def sfx_whoosh(d=0.5):
    t = tv(d); n = rng.standard_normal(len(t)); out = np.zeros_like(t)
    for i, (lo, hi) in enumerate([(300, 900), (700, 2000), (1500, 4500)]):
        out += bp(n, lo, hi) * np.sin(np.pi * np.clip(t / d - i * 0.08, 0, 1)) ** 2
    return norm(out, 0.7)

def sfx_hit():
    t = tv(1.2); body = kick(130, 38, 0.3, 1.2)
    crack = lp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.03)
    sub = np.sin(2 * np.pi * 45 * t) * np.exp(-t / 0.5) * 0.6
    return norm(reverb(body + crack * 0.5 + sub, 1.2, 0.25), 0.95)

def sfx_boom():
    t = tv(2.5); body = kick(80, 28, 0.8, 2.5) + np.sin(2 * np.pi * 32 * t) * np.exp(-t / 1.0) * 0.7
    rumble = lp(rng.standard_normal(len(t)), 200) * np.exp(-t / 0.7) * 0.4
    return norm(reverb(body + rumble, 2.0, 0.3), 0.95)

def sfx_riser(d=1.4):
    t = tv(d); f = 180 * (8 ** (t / d)); tone = ss.sawtooth(2 * np.pi * np.cumsum(f) / SR) * 0.3
    noise = hp(rng.standard_normal(len(t)), 800) * (t / d) ** 2 * 0.6
    x = lp(tone, 3000) + noise
    return norm(x * (t / d) ** 2.2, 0.75)

def sfx_ding():
    t = tv(1.6); f = 1318
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dcy) for a, r, dcy in [(1, 1, 2.2), (.45, 2.76, 4), (.25, 5.4, 7), (.12, 8.9, 11)])
    return norm(x * np.minimum(1, t / 0.002), 0.6)

def sfx_pop():
    t = tv(0.12); f = 380 + 700 * (t / 0.12); x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035)
    return norm(x, 0.55)

def sfx_tick(): return norm(click(2600, 0.04), 0.5)

def sfx_heartbeat():
    out = np.zeros(int(0.9 * SR)); add(out, kick(65, 38, 0.12, 0.3), 0); add(out, kick(60, 36, 0.1, 0.3) * 0.7, 0.22)
    return norm(lp(out, 300), 0.85)

def sfx_glitch(d=0.32):
    out = np.zeros(int(d * SR)); t0 = 0
    while t0 < d - 0.02:
        seg = rng.uniform(0.015, 0.05); f = rng.choice([180, 360, 720, 1440, 2880])
        s = ss.square(2 * np.pi * f * tv(seg)) * rng.uniform(0.3, 0.8)
        if rng.random() < 0.4: s = np.round(rng.standard_normal(len(s)) * 4) / 4 * 0.6
        add(out, s, t0); t0 += seg + rng.uniform(0, 0.015)
    return norm(lp(out, 6000), 0.6)

def sfx_scratch(d=0.42):
    t = tv(d); speed = np.sin(2 * np.pi * 3.2 * t) * np.exp(-t / 0.25)
    f = 300 + 900 * np.abs(speed); x = bp(rng.standard_normal(len(t)), 300, 2500) * np.abs(speed) + np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 * np.abs(speed)
    return norm(x, 0.6)

def sfx_sting():
    """悬疑「当—当—当」：低音铜管式三连，最后一声拖长。"""
    out = np.zeros(int(2.6 * SR))
    for i, (m, d) in enumerate([(38, 0.32), (38, 0.32), (37, 1.6)]):
        t = tv(d + 0.6); f = hz(m); x = sum(ss.sawtooth(2 * np.pi * f * (1 + det) * t) for det in (-0.004, 0, 0.005))
        x = lp(x, 900) * env_adsr(len(t), a=0.01, d=0.15, s=0.7, r=0.5) + kick(70, 35, 0.25, d + 0.6) * 0.6
        add(out, x, i * 0.42)
    return norm(reverb(out, 1.8, 0.3), 0.9)

SFX = {'whoosh': sfx_whoosh, 'hit': sfx_hit, 'boom': sfx_boom, 'riser': sfx_riser, 'ding': sfx_ding, 'pop': sfx_pop, 'tick': sfx_tick,
       'heartbeat': sfx_heartbeat, 'glitch': sfx_glitch, 'scratch': sfx_scratch, 'sting': sfx_sting}

# ---------------------------------------------------------------- 用户自带的素材（同名优先）
def load_override(kind, name):
    for ext in ('.wav', '.mp3', '.m4a', '.flac'):
        f = SKILL / 'assets' / kind / (name + ext)
        if f.exists():
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
            return np.frombuffer(raw, np.float32).astype(np.float64)
    return None

def bed(mood, d):
    user = load_override('配乐', mood)
    if user is not None and len(user):
        reps = int(np.ceil(d * SR / len(user))); x = np.tile(user, reps)[:int(d * SR)]
    else:
        x = BEDS.get(mood, bed_neutral)(d)
    rms = np.sqrt(np.mean(x ** 2)) or 1
    x = x * (10 ** (BED_RMS_DB.get(mood, -25) / 20) / rms)
    return np.tanh(x * 1.5) / 1.5                          # 软限幅：偶尔的峰不炸

def sfx(name, **kw):
    user = load_override('音效', name)
    if user is not None and len(user): return norm(user, 0.9)
    if name not in SFX: raise SystemExit(f'不认识的音效 {name}（可用：{" ".join(SFX)}）')
    return SFX[name](**kw)

# ---------------------------------------------------------------- 按计划混
def render(plan, out):
    total = plan['total']; N = int((total + 1) * SR)
    music = np.zeros(N); fx = np.zeros(N)
    xf = 0.6
    for b in plan['beds']:                              # 情绪段之间 0.6 秒交叉淡化
        s, e = b['start'], b['end']; d = e - s + xf
        seg = bed(b['mood'], d)
        fade = np.ones(len(seg)); k = int(xf * SR)
        fade[:k] = np.linspace(0, 1, k) if s > 0 else 1; fade[-k:] = np.linspace(1, 0, k)
        add(music, seg * fade, max(0, s - xf / 2))
    gain = np.ones(N)                                   # 揭晓前抽空：音乐停—悬—砸
    for dp in plan.get('drops', []):
        a, b = int((dp['t'] - dp['dur']) * SR), int(dp['t'] * SR); k = int(0.08 * SR)
        gain[max(0, a):b] = 0
        if a - k > 0: gain[a - k:a] = np.minimum(gain[a - k:a], np.linspace(1, 0, k))
        r = int(0.9 * SR); gain[b:b + r] = np.minimum(gain[b:b + r], np.linspace(0, 1, min(r, N - b)))
    music *= gain
    for ev in plan.get('sfx', []):
        name = ev['name']; s = sfx(name, d=ev['dur']) if name == 'riser' and ev.get('dur') else sfx(name)
        t = ev['t'] - (len(s) / SR if name == 'riser' else 0)
        add(fx, s, t, ev.get('gain', 1.0))
    music = music[:int(total * SR)]; fx = fx[:int(total * SR)]
    sf.write(out / 'bgm.wav', np.stack([music, music], 1).astype(np.float32), SR)
    sf.write(out / 'sfx.wav', np.stack([fx, fx], 1).astype(np.float32), SR)
    print(f'配乐 → {out / "bgm.wav"}  音效 {len(plan.get("sfx", []))} 个 → {out / "sfx.wav"}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan'); ap.add_argument('--out'); ap.add_argument('--demo')
    a = ap.parse_args()
    if a.demo:
        d = Path(a.demo); d.mkdir(parents=True, exist_ok=True)
        for m in ['悬疑', '紧张', '轻松', '平叙', '温暖']: sf.write(d / f'配乐_{m}.wav', bed(m, 12).astype(np.float32), SR)
        for k in SFX: sf.write(d / f'音效_{k}.wav', sfx(k).astype(np.float32), SR)
        print('试听文件 →', d); return
    plan = json.loads(Path(a.plan).read_text()); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    render(plan, out)


if __name__ == '__main__':
    main()
