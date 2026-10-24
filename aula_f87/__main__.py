"""Entry point: ``aula-f87-control [gui|status|set|sleep|music|repair] ...``.

Without a command it opens the window: the GTK 4 app on Linux, the Tkinter
app on Windows/macOS (or on Linux with ``gui --tk`` / when GTK is missing).
"""

import argparse
import sys
import threading
import time

from . import __version__, device
from .effects import EFFECTS, SIDE_MODES, battery_text, effect_info

STYLE_NAMES = ("bars", "meter", "rainbow", "pulse")  # same order as music.STYLES


def _effect_id(text):
    if text.isdigit():
        return int(text)
    for e in EFFECTS:
        if e.name.startswith(text) or (e.en and e.en.lower().startswith(text.lower())):
            return e.id
    raise argparse.ArgumentTypeError(f"未知的效果名称 {text!r}")


def _color(text):
    text = text.lstrip("#")
    if len(text) != 6:
        raise argparse.ArgumentTypeError("use RRGGBB")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def gui_main(force_tk=False, background=False):
    """Open the window: GTK 4 on Linux when available, otherwise Tkinter.

    background: start with only the top-bar icon (GTK app on Linux)."""
    if sys.platform.startswith("linux") and not force_tk:
        try:
            from .gui import main as gtk_main
        except (ImportError, ValueError):  # PyGObject / GTK 4 / libadwaita missing
            pass
        else:
            return gtk_main(background=background)
    from .gui_tk import main as tk_main
    return tk_main()


def _sleep_text(minutes):
    return "从不（背光常亮）" if minutes == 0 else f"空闲 {minutes:g} 分钟后"


def _print_state(kb, state):
    info = effect_info(state.effect)
    color = "彩虹" if state.colorful else "#%02x%02x%02x" % state.color
    print(f"键盘：      {kb.description}")
    print(f"效果：      {info.name}（{state.effect}）")
    print(f"颜色：      {color}")
    print(f"亮度：      {state.brightness}/4   速度：{state.speed}/4")
    side = SIDE_MODES[state.side] if state.side < len(SIDE_MODES) else state.side
    print(f"侧灯：      {side}")
    print(f"休眠：      {_sleep_text(state.sleep)}")
    battery = kb.read_battery()
    print(f"电量：      {battery_text(battery, kb.link.label == 'USB 线缆', kb.last_battery())}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aula-f87-control")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--background", action="store_true",
                        help="以后台托盘图标方式启动（登录时使用）")
    sub = parser.add_subparsers(dest="cmd")
    g = sub.add_parser("gui", help="打开窗口（默认）")
    g.add_argument("--tk", action="store_true", help="在 Linux 上也使用 Tkinter 窗口")
    sub.add_parser("status", help="显示当前灯光状态")
    s = sub.add_parser("set", help="修改灯光")
    s.add_argument("--effect", type=_effect_id, help="效果名称或编号，如 静态、呼吸、3")
    s.add_argument("--color", type=_color, help="RRGGBB 格式的颜色")
    s.add_argument("--rainbow", action="store_true")
    s.add_argument("--brightness", type=int, choices=range(5))
    s.add_argument("--speed", type=int, choices=range(5))
    s.add_argument("--side", type=int, choices=range(len(SIDE_MODES)))
    z = sub.add_parser("sleep", help="背光关闭时机：'never' 或空闲分钟数")
    z.add_argument("when", help="never，或分钟数，如 1、5、10、30")
    m = sub.add_parser("music", help="让背光跟随播放的音频律动（Ctrl+C 停止）")
    m.add_argument("--style", choices=STYLE_NAMES, default="bars",
                   help="bars: 低音红/中音黄/高音绿; meter: 按高度绿-黄-红")
    m.add_argument("--sensitivity", type=float, default=1.0, help="0.2-2，越大条越高")
    m.add_argument("--brightness", type=float, default=1.0, help="0.1-1")
    m.add_argument("--follow", default="all",
                   help="响应对象：all，或 bass,vocals,beat 的逗号组合")
    m.add_argument("--seconds", type=float, help="达到该时长后自动停止")
    sub.add_parser("repair", help="恢复键盘上次正常的设置"
                                  "（当键盘无法输入或灯光乱闪时使用）")
    args = parser.parse_args(argv)

    if args.cmd in (None, "gui"):
        return gui_main(force_tk=getattr(args, "tk", False), background=args.background)
    if args.cmd == "music":
        follow = [part.strip().lower() for part in args.follow.split(",") if part.strip()]
        unknown = [part for part in follow if part not in ("all", "bass", "vocals", "beat")]
        if unknown:
            print(f"未知的 --follow 取值：{', '.join(unknown)}（可用 all, bass, vocals, beat）",
                  file=sys.stderr)
            return 2
        args.follow = tuple(part for part in follow if part != "all")

    try:
        kb = device.connect()
    except device.DeviceError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.cmd == "music":
        return _music(kb, args)
    if args.cmd == "repair":
        try:
            used = kb.repair()
            print(f"已恢复键盘的{used}。")
            _print_state(kb, kb.read_lighting())
        except (device.DeviceError, OSError) as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        finally:
            kb.close()
        return 0
    if args.cmd == "sleep":
        try:
            minutes = 0.0 if args.when.lower() in ("never", "off", "0") else float(args.when)
        except ValueError:
            print("请使用 'never' 或分钟数。", file=sys.stderr)
            kb.close()
            return 2
    try:
        state = kb.read_lighting()
        if args.cmd == "sleep":
            kb.set_sleep(minutes)
            state = kb.read_lighting()
        if args.cmd == "set":
            for name in ("effect", "color", "brightness", "speed", "side"):
                if getattr(args, name) is not None:
                    setattr(state, name, getattr(args, name))
            if args.color is not None or args.rainbow:
                state.colorful = args.rainbow
            kb.apply_lighting(state)
            state = kb.read_lighting()
        _print_state(kb, state)
    except device.DamagedSettings as exc:
        print(f"错误：{exc}\n请运行：aula-f87-control repair", file=sys.stderr)
        return 1
    except (device.DeviceError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    finally:
        kb.close()
    return 0


def _music(kb, args):
    from .music import MusicError, MusicSync

    failure = []
    done = threading.Event()

    def on_error(exc):
        failure.append(exc)
        done.set()

    try:
        sync = MusicSync(kb.link, on_error=on_error)
    except MusicError as exc:
        print(exc, file=sys.stderr)
        kb.close()
        return 1
    sync.style = STYLE_NAMES.index(args.style)
    sync.sensitivity = min(2.0, max(0.2, args.sensitivity))
    sync.brightness = min(1.0, max(0.1, args.brightness))
    sync.follow = args.follow
    print(f"音乐律动已在 {kb.description} 上启动。按 Ctrl+C 停止。")
    start = time.monotonic()
    try:
        done.wait(args.seconds)
    except KeyboardInterrupt:
        pass
    sync.stop()
    kb.close()
    elapsed = time.monotonic() - start
    print(f"已停止，共运行 {elapsed:.0f} 秒（{sync.frames / max(elapsed, 0.001):.1f} 帧/秒）。")
    if failure:
        print(f"错误：{failure[0]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
