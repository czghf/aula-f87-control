"""Built-in lighting effects, side-light modes and colour presets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    id: int
    name: str
    speed: bool
    color: bool
    en: str = ""  # English name, kept for the CLI (--effect breathing) and configs


# Effect 18 plus the config "custom" flag shows the stored per-key map
# (confirmed on an F87 Pro; effect 21, used by newer F87 boards, goes dark).
PER_KEY = 18

# Firmware effect numbers. 6, 9 and 14 exist in the OEM table but
# misbehave on this board, so they are left out (as in other open tools).
EFFECTS = (
    Effect(0, "关闭", False, False, "Off"),
    Effect(1, "静态", False, True, "Static"),
    Effect(2, "呼吸", True, True, "Breathing"),
    Effect(3, "彩虹波浪", True, False, "Rainbow wave"),
    Effect(4, "闪烁离去", True, True, "Flash away"),
    Effect(5, "雨滴", True, True, "Raindrops"),
    Effect(7, "涟漪", True, True, "Ripples"),
    Effect(8, "繁星闪烁", True, True, "Twinkling stars"),
    Effect(10, "复古贪吃蛇", True, True, "Retro snake"),
    Effect(11, "霓虹流光", True, True, "Neon stream"),
    Effect(12, "按键响应", True, True, "Reactive (keypress)"),
    Effect(13, "正弦波", True, True, "Sine wave"),
    Effect(15, "旋转风车", True, False, "Rotating windmill"),
    Effect(16, "七彩瀑布", True, False, "Colorful waterfall"),
    Effect(17, "花开", True, False, "Blossoming"),
    Effect(PER_KEY, "自定义逐键", False, False, "Custom per-key"),
)

_BY_ID = {e.id: e for e in EFFECTS}


def effect_info(effect_id):
    return _BY_ID.get(effect_id) or Effect(effect_id, f"效果 {effect_id}", True, True,
                                           f"Effect {effect_id}")


# Lights on the sides of the case (config byte 18; Fn + Right Shift on the keyboard).
# The light bar above the arrow keys (byte 28, Fn + Left Shift) uses the same five
# modes, but the keyboard doesn't reliably apply changes to it from the computer.
SIDE_MODES = ("关闭", "彩虹波浪", "彩虹（整体）", "纯色", "呼吸")

PRESETS = (
    ("红", (255, 0, 0)),
    ("橙", (255, 96, 0)),
    ("黄", (255, 208, 0)),
    ("绿", (0, 255, 0)),
    ("青", (0, 255, 255)),
    ("蓝", (0, 64, 255)),
    ("紫", (140, 0, 255)),
    ("粉", (255, 0, 160)),
    ("白", (255, 255, 255)),
)

# Music sync styles; the index is used by the GUIs and the CLI.
MUSIC_STYLES = ("频谱条", "频谱条（表色）", "频谱条（彩虹）", "节拍脉冲")

# What music sync can follow (key, label). Nothing selected = everything.
MUSIC_FOLLOW = (("bass", "低音"), ("vocals", "人声"), ("beat", "节拍"))
FOLLOW_KEYS = tuple(key for key, _label in MUSIC_FOLLOW)

# "Turn the backlight off after" choices, in minutes (the keyboard stores 30 s steps).
SLEEP_MINUTES = (1, 2, 5, 10, 15, 30, 60)


def sleep_label(minutes):
    return f"{minutes:g} 分钟"


def nearest_sleep_index(minutes):
    return min(range(len(SLEEP_MINUTES)), key=lambda i: abs(SLEEP_MINUTES[i] - minutes))


def battery_text(battery, wired, last=None):
    """Human text for the battery row. battery: Battery or None; last: (percent, time)."""
    if battery is not None:
        return str(battery).capitalize()
    if wired:
        text = "有线连接时不上报电量（由 USB 供电）"
        if last:
            import time
            percent, when = last
            stamp = time.strftime("%H:%M" if time.time() - when < 86400 else "%m月%d日 %H:%M",
                                  time.localtime(when))
            text += f" · 上次 2.4G 读数：{percent}%（{stamp}）"
        return text
    return "未知"
