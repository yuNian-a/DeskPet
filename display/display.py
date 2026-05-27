"""
成步堂龙一状态显示器 — 用于 Claude Code 的 Hook 系统
基于《逆转裁判》素材，显示成步堂的各种表情动画

状态映射:
    0=BOOT(启动)      → 通常
    1=ANALYZING(思考) → 思考
    2=PROCESSING(处理)→ 集中
    3=EXECUTING(执行) → 异议
    4=SUCCESS(成功)   → 得意
    5=FAILURE(失败)   → 尴尬/冷汗
    6=CRITICAL(严重)  → 绝望
    7=DISPLAY(等待)   → 看纸
    8=IDLE(空闲)      → 通常(眨眼)
"""

import pygame
import json
import os
import sys
import socket
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from PIL import Image
import glob

# ═══════════════════════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════════════════════

SCREEN_W = 596
SCREEN_H = 480
FPS = 30  # GIF 帧率通常在 6-10fps，这里用 30fps 跑游戏循环
TCP_PORT = 19876
CORNER_RADIUS = 0  # 不需要圆角了

# 素材路径 (使用项目内素材)
import os
ASSET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "cbt")

# 背景素材路径
BG_SEAT = os.path.join(ASSET_PATH, "..", "defenseSeat.png")
BG_DESK = os.path.join(ASSET_PATH, "..", "defenseSeatDesk.png")

# 加载背景图片 (全局缓存)
_bg_seat = None
_bg_desk = None

def load_backgrounds():
    """加载背景图片"""
    global _bg_seat, _bg_desk
    try:
        seat = pygame.image.load(BG_SEAT).convert_alpha()
        # 缩放到屏幕大小
        _bg_seat = pygame.transform.scale(seat, (SCREEN_W, SCREEN_H))
        print(f"[display] Loaded defenseSeat.png")
    except Exception as e:
        print(f"[warn] Failed to load defenseSeat.png: {e}")
        _bg_seat = None

    try:
        desk = pygame.image.load(BG_DESK).convert_alpha()
        _bg_desk = pygame.transform.scale(desk, (SCREEN_W, SCREEN_H))
        print(f"[display] Loaded defenseSeatDesk.png")
    except Exception as e:
        print(f"[warn] Failed to load defenseSeatDesk.png: {e}")
        _bg_desk = None

def draw_court_background(screen):
    """绘制法庭背景 (三层: 座位背景 -> CBT -> 桌子前景)"""
    # 最底层：座位背景
    if _bg_seat:
        screen.blit(_bg_seat, (0, 0))
    else:
        # 后备：深蓝灰色背景
        screen.fill((45, 65, 95))

def draw_court_foreground(screen):
    """绘制法庭前景 (桌子，遮挡CBT下半身)"""
    if _bg_desk:
        screen.blit(_bg_desk, (0, 0))

# 状态到文件名前缀的映射
STATE_ASSETS = {
    0: "cbt1-通常-1",    # BOOT
    1: "cbt1-思考",      # ANALYZING
    2: "cbt1-通常-点头",      # PROCESSING
    3: "cbt1-咖啡-喝",   # EXECUTING
    4: "cbt1-得意",      # SUCCESS
    5: "cbt1-尴尬",      # FAILURE
    6: "cbt1-绝望",      # CRITICAL
    7: "cbt1-看纸",      # DISPLAY
    8: "cbt1-通常-1",    # IDLE
}

STATE_NAMES = {
    0: "BOOT",       1: "ANALYZING",  2: "PROCESSING",
    3: "EXECUTING",  4: "SUCCESS",    5: "FAILURE",
    6: "CRITICAL",   7: "DISPLAY",    8: "IDLE",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Windows API
# ═══════════════════════════════════════════════════════════════════════════════

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_LAYERED = 0x00080000

user32 = ctypes.windll.user32

def _get_pygame_hwnd():
    try:
        info = pygame.display.get_wm_info()
        return info.get('window', 0)
    except Exception:
        return 0

def set_always_on_top(hwnd=None):
    if hwnd is None:
        hwnd = _get_pygame_hwnd()
    if hwnd and hwnd != 0:
        hwnd_val = ctypes.c_void_p(hwnd)
        user32.SetWindowPos(
            hwnd_val, ctypes.c_void_p(HWND_TOPMOST),
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        return True
    return False

def set_tool_window(hwnd=None):
    if hwnd is None:
        hwnd = _get_pygame_hwnd()
    if hwnd and hwnd != 0:
        hwnd_val = ctypes.c_void_p(hwnd)
        exstyle = user32.GetWindowLongW(hwnd_val, GWL_EXSTYLE)
        new_exstyle = (exstyle & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd_val, GWL_EXSTYLE, new_exstyle)
        user32.SetWindowPos(
            hwnd_val, None, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED
        )
        return True
    return False

# Monitor enumeration
MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)

def detect_mini_display():
    monitors = []
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        monitors.append({
            'x': rect.left, 'y': rect.top,
            'w': rect.right - rect.left, 'h': rect.bottom - rect.top,
            'area': (rect.right - rect.left) * (rect.bottom - rect.top)
        })
        return True
    enum_proc = MonitorEnumProc(callback)
    user32.EnumDisplayMonitors(None, None, enum_proc, 0)

    if not monitors:
        return None
    primary = monitors[0]
    candidates = [m for m in monitors if m['area'] < primary['area'] * 0.5]
    if candidates:
        mini = min(candidates, key=lambda m: m['area'])
        return (mini['x'], mini['y'], mini['w'], mini['h'])
    if primary['w'] <= 800 and primary['h'] <= 600:
        return (primary['x'], primary['y'], primary['w'], primary['h'])
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# GIF 动画管理器
# ═══════════════════════════════════════════════════════════════════════════════

class GIFAnimation:
    """加载和管理 GIF 动画帧"""

    def __init__(self, base_path, state_id):
        self.frames = []
        self.durations = []  # 每帧持续时间(毫秒)
        self.current_frame = 0
        self.elapsed = 0
        # 状态7 (DISPLAY/看纸) 不循环，停在最后一帧
        self.loop = (state_id != 7)

        prefix = STATE_ASSETS.get(state_id, "cbt1-通常")
        self._load_gif(base_path, prefix, state_id)

    def _load_gif(self, base_path, prefix, state_id):
        """加载 GIF 文件"""
        # 查找匹配的 GIF 文件
        pattern = os.path.join(base_path, f"{prefix}*.gif")
        files = glob.glob(pattern)

        if not files:
            print(f"[warn] No GIF found for state {state_id} ({prefix}), using default")
            # 使用通常作为后备
            if prefix != "cbt1-通常":
                return self._load_gif(base_path, "cbt1-通常", state_id)
            return

        # 优先选择 -2 (完整说话动画) 或 -动作 版本
        gif_file = None
        for f in files:
            if "-2.gif" in f or "-动作" in f:
                gif_file = f
                break
        if not gif_file:
            gif_file = files[0]

        print(f"[display] Loading: {os.path.basename(gif_file)}")

        try:
            gif = Image.open(gif_file)

            # 提取所有帧
            frame_index = 0
            while True:
                # 转换为 RGBA
                frame = gif.convert('RGBA')

                # 转换为 pygame Surface
                mode = frame.mode
                size = frame.size
                data = frame.tobytes()

                pygame_surface = pygame.image.fromstring(data, size, mode)

                # 缩放以适应屏幕
                scale_w = SCREEN_W / size[0]
                scale_h = SCREEN_H / size[1]
                scale = min(scale_w, scale_h)
                new_size = (int(size[0] * scale), int(size[1] * scale))

                pygame_surface = pygame.transform.scale(pygame_surface, new_size)
                self.frames.append(pygame_surface)

                # 获取帧持续时间
                duration = gif.info.get('duration', 100)  # 默认 100ms
                self.durations.append(duration)

                frame_index += 1

                try:
                    gif.seek(frame_index)
                except EOFError:
                    break

            print(f"[display] Loaded {len(self.frames)} frames")

        except Exception as e:
            print(f"[error] Failed to load GIF: {e}")

    def update(self, dt):
        """更新动画，dt 是秒"""
        if not self.frames:
            return

        self.elapsed += dt * 1000  # 转为毫秒

        # 检查是否需要切换帧
        while self.elapsed >= self.durations[self.current_frame]:
            self.elapsed -= self.durations[self.current_frame]
            self.current_frame += 1

            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1

    def get_frame(self):
        """获取当前帧"""
        if not self.frames:
            return None
        return self.frames[self.current_frame]

    def draw(self, screen, center_x=None, center_y=None):
        """在屏幕上绘制当前帧"""
        frame = self.get_frame()
        if frame is None:
            return

        rect = frame.get_rect()
        if center_x is None:
            center_x = SCREEN_W // 2
        if center_y is None:
            center_y = SCREEN_H // 2

        rect.center = (center_x, center_y)
        screen.blit(frame, rect)


# ═══════════════════════════════════════════════════════════════════════════════
# 应用状态
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AppState:
    current: int = 0
    prev: int = 0
    msg: str = ""
    elapsed: float = 0.0
    animations: dict = field(default_factory=dict)
    state_enter_time: float = 0.0  # 进入当前状态的时间
    min_display_time: float = 0.3  # 最少停留0.3秒，响应更快
    auto_return_at: float = -1.0   # 自动切回待机的时间点，-1表示不切
    auto_return_to: int = 8        # 自动切回的目标状态（默认IDLE）

    # 哪些状态在N秒后自动切回IDLE
    AUTO_RETURN_STATES: dict = field(default_factory=lambda: {
        4: 2.0,  # SUCCESS → IDLE after 2s
        5: 3.0,  # FAILURE → IDLE after 3s
        6: 4.0,  # CRITICAL → IDLE after 4s
    })

    def can_change_state(self) -> bool:
        """检查是否可以切换状态（已停留至少min_display_time秒）"""
        return (self.elapsed - self.state_enter_time) >= self.min_display_time

    def enter_state(self, state_id: int):
        """进入新状态"""
        if state_id != self.current:
            self.prev = self.current
            self.current = state_id
            self.state_enter_time = self.elapsed
            # 设置自动回待机计时器
            delay = self.AUTO_RETURN_STATES.get(state_id, -1)
            if delay > 0:
                self.auto_return_at = self.elapsed + delay
            else:
                self.auto_return_at = -1.0

    def check_auto_return(self):
        """检查是否需要自动切回待机，返回True表示发生了切换"""
        if self.auto_return_at > 0 and self.elapsed >= self.auto_return_at:
            self.auto_return_at = -1.0
            target = self.auto_return_to
            print(f"[display] Auto-return: {STATE_NAMES[self.current]} -> {STATE_NAMES[target]}")
            self.prev = self.current
            self.current = target
            self.state_enter_time = self.elapsed
            return True
        return False

    def get_animation(self, state_id):
        if state_id not in self.animations:
            self.animations[state_id] = GIFAnimation(ASSET_PATH, state_id)
        return self.animations[state_id]


# ═══════════════════════════════════════════════════════════════════════════════
# TCP 服务器
# ═══════════════════════════════════════════════════════════════════════════════

class TCPServer:
    def __init__(self, port):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('0.0.0.0', port))
        self.sock.listen(5)
        self.sock.setblocking(False)
        self.client = None
        self.buffer = b""

    def check(self, app):
        if self.client is None:
            try:
                self.client, addr = self.sock.accept()
                self.client.setblocking(False)
                print(f"[display] Client connected: {addr}")
            except BlockingIOError:
                pass
            return

        try:
            data = self.client.recv(4096)
            if data:
                self.buffer += data
                self._process_buffer(app)
            else:
                self.client.close()
                self.client = None
                self.buffer = b""
        except (BlockingIOError, ConnectionResetError):
            pass
        except Exception:
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
            self.client = None
            self.buffer = b""

    def _process_buffer(self, app):
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            if line.strip():
                self._handle_message(line.strip(), app)

    def _handle_message(self, data, app):
        try:
            msg = json.loads(data.decode('utf-8'))
            state = msg.get('state')
            target = None
            if isinstance(state, int) and 0 <= state <= 8:
                target = state
            elif isinstance(state, str):
                name_map = {v.lower(): k for k, v in STATE_NAMES.items()}
                target = name_map.get(state.lower())
            if target is not None:
                # 检查是否可以切换状态（至少停留2秒）
                if target != app.current:
                    if app.can_change_state():
                        print(f"[display] {STATE_NAMES[app.current]} -> {STATE_NAMES[target]}")
                        app.enter_state(target)
                    else:
                        remaining = app.min_display_time - (app.elapsed - app.state_enter_time)
                        print(f"[display] Delay {remaining:.1f}s: {STATE_NAMES[target]}")
            app.msg = msg.get('msg', '')
        except Exception as e:
            print(f"[display] Invalid message: {e}")

    def close(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
        try:
            self.sock.close()
        except:
            pass


def send_state(state, msg=""):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2)
        sock.connect(('127.0.0.1', TCP_PORT))
        sock.send((json.dumps({"state": state, "msg": msg}) + "\n").encode())
        print(f"Sent: state={state} ({STATE_NAMES.get(state, '?')}) msg='{msg}'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--pos', default='0,1440', help='monitor position x,y')
    args = p.parse_args()

    # 自动检测小屏幕
    if args.pos == '0,1440':
        mini = detect_mini_display()
        if mini:
            x, y, w, h = mini
            x = x + (w - SCREEN_W) // 2
            y = y + (h - SCREEN_H) // 2
            print(f"[display] Auto-detected mini display: {w}x{h}")
        else:
            x, y = 0, 1440
    else:
        x, y = map(int, args.pos.split(','))

    os.environ['SDL_VIDEO_WINDOW_POS'] = f'{x},{y}'

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.NOFRAME)
    pygame.display.set_caption("成步堂龙一")
    pygame.mouse.set_visible(False)

    # 设置窗口样式
    hwnd = _get_pygame_hwnd()
    set_tool_window(hwnd)
    set_always_on_top(hwnd)

    clock = pygame.time.Clock()
    app = AppState()

    # 加载背景图片
    print("[display] Loading backgrounds...")
    load_backgrounds()

    # 预加载所有动画
    print("[display] Loading animations...")
    for state_id in range(9):
        app.get_animation(state_id)

    tcp = TCPServer(TCP_PORT)
    print(f"[display] Listening on TCP 0.0.0.0:{TCP_PORT}")
    print(f"[display] Press Q or ESC to quit")

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        app.elapsed += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif pygame.K_0 <= event.key <= pygame.K_8:
                    app.current = event.key - pygame.K_0

        # 检查 TCP
        tcp.check(app)

        # 自动回待机
        app.check_auto_return()

        # 清屏
        screen.fill((0, 0, 0))

        # 第1层：绘制法庭背景（座位）
        draw_court_background(screen)

        # 获取并更新当前动画
        anim = app.get_animation(app.current)
        anim.update(dt)

        # 第2层：绘制CBT（缩放并定位到辩护席位置）
        frame = anim.get_frame()
        if frame:
            # 计算缩放比例，适应辩护席
            scale = 0.9
            new_width = int(frame.get_width() * scale)
            new_height = int(frame.get_height() * scale)
            scaled_frame = pygame.transform.scale(frame, (new_width, new_height))

            # 定位：站在辩护席后面（调整位置让脚被桌子遮挡）
            rect = scaled_frame.get_rect()
            rect.centerx = SCREEN_W // 2
            rect.centery = SCREEN_H * 0.65  # 再往下一点，让桌子遮挡下半身

            screen.blit(scaled_frame, rect)

        # 第3层：绘制法庭前景（桌子，遮挡CBT下半身）
        draw_court_foreground(screen)

        pygame.display.flip()

    tcp.close()
    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        if len(sys.argv) < 3:
            print("Usage: python display.py send <state> [message]")
            print(f"States: {STATE_NAMES}")
            sys.exit(1)
        sa = sys.argv[2]
        sm = sys.argv[3] if len(sys.argv) > 3 else ""
        try:
            sa = int(sa)
        except ValueError:
            pass
        send_state(sa, sm)
    else:
        main()
