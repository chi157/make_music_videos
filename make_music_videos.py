import librosa
import numpy as np
import pysrt
from moviepy import VideoClip, AudioFileClip
from PIL import Image, ImageDraw, ImageFont, ImageFile
from tkinter import Tk, filedialog
import os
import glob
import traceback

# ================= 設定區 =================
# 使用檔案選擇對話框
print("請選擇檔案...")

# 初始化 tkinter（隱藏主視窗）
root = Tk()
root.withdraw()
root.attributes('-topmost', True)

# 選擇音樂檔案
print("\n1. 請選擇音樂檔案 (MP3)")
AUDIO_FILE = filedialog.askopenfilename(
    title="選擇音樂檔案",
    filetypes=[("音樂檔案", "*.mp3 *.wav *.m4a"), ("所有檔案", "*.*")]
)

if not AUDIO_FILE:
    print("未選擇音樂檔案，程式結束")
    exit()

print(f"已選擇音樂: {os.path.basename(AUDIO_FILE)}")

# 選擇歌詞檔案
print("\n2. 請選擇歌詞檔案 (SRT)")
SRT_FILE = filedialog.askopenfilename(
    title="選擇歌詞檔案",
    filetypes=[("字幕檔案", "*.srt"), ("所有檔案", "*.*")]
)

if not SRT_FILE:
    print("未選擇歌詞檔案，程式結束")
    exit()

print(f"已選擇歌詞: {os.path.basename(SRT_FILE)}")

# 自動使用資料夾內的字體檔案
local_fonts = glob.glob(os.path.join(os.getcwd(), "*.ttf"))
if local_fonts:
    FONT_FILE = local_fonts[0]
    print(f"\n使用資料夾內字體: {os.path.basename(FONT_FILE)}")
else:
    FONT_FILE = None
    print("\n未找到 TTF 字體檔案，使用預設字體")

# 自動使用音檔名稱作為歌曲名稱
SONG_TITLE = os.path.splitext(os.path.basename(AUDIO_FILE))[0]
print(f"歌曲名稱: {SONG_TITLE}")

# 選擇輸出位置
print("\n3. 請選擇影片輸出位置")
OUTPUT_FILE = filedialog.asksaveasfilename(
    title="儲存影片",
    defaultextension=".mp4",
    filetypes=[("MP4 影片", "*.mp4"), ("所有檔案", "*.*")],
    initialfile=f"{SONG_TITLE}.mp4"
)

if not OUTPUT_FILE:
    OUTPUT_FILE = f"{SONG_TITLE}.mp4"
    print(f"使用預設輸出檔名: {OUTPUT_FILE}")
else:
    print(f"輸出檔案: {os.path.basename(OUTPUT_FILE)}")

root.destroy()

FONT_PATH = FONT_FILE if FONT_FILE else "msjh.ttc"  # 使用選擇/資料夾內的 TTF，否則使用預設字體

VIDEO_SIZE = (1920, 1080)     # 影片解析度 (1080p)
FPS = 30                      # 每秒幾格
BAR_COUNT = 120               # 畫面要有幾根音頻柱子
BAR_COLOR = (90, 90, 173)     # 柱子顏色 #5A5AAD
BG_COLOR = (227, 242, 253)    # 背景顏色 #E3F2FD 淺藍
CURRENT_LYRICS_COLOR = (72, 72, 145)  # 當前歌詞顏色 #484891
OTHER_LYRICS_COLOR = (72, 72, 145)  # 其他歌詞顏色 #484891
FONT_SIZE = 38               # 統一字體大小
CURRENT_FONT_SIZE = 55       # 當前歌詞字體大小
BG_IMAGE_PATH = "background.png"  # 背景圖片路徑（放在專案資料夾）
OVERLAY_ALPHA = 0.7          # 黑色遮罩透明度
TEXT_STROKE_WIDTH = 0.7        # 文字白邊寬度
OTHER_TEXT_STROKE_WIDTH = 0.4  # 其他文字白邊寬度
TEXT_STROKE_COLOR = (255, 255, 255)
OTHER_LYRICS_ALPHA = 50     # 非當前歌詞透明度 (0-255) 降低透明度讓當前歌詞更突顯
# =========================================

ImageFile.LOAD_TRUNCATED_IMAGES = True

print("1. 正在載入音訊與分析頻譜... (這可能需要幾秒鐘)")
# 載入音訊
y, sr = librosa.load(AUDIO_FILE, sr=None)

# 計算短時距傅立葉變換 (STFT) -> 得到頻譜
# n_fft 決定了頻率的解析度，hop_length 決定了時間的密度
hop_length = 512
D = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_length))
DB = librosa.amplitude_to_db(D, ref=np.max) # 轉成對數刻度(分貝)，比較符合人耳聽感

# 載入字幕
subs = pysrt.open(SRT_FILE)
print(f"✓ 字幕載入成功: {len(subs)} 句歌詞")

# 預先載入字體與背景，避免每幀重複初始化
def try_load_fonts(font_path):
    """嘗試載入並測試字體，成功回傳字體物件，失敗回傳 None"""
    try:
        print(f"正在嘗試載入字體: {font_path}")
        c_font = ImageFont.truetype(font_path, FONT_SIZE)
        c_font_current = ImageFont.truetype(font_path, CURRENT_FONT_SIZE)
        e_font = ImageFont.truetype(font_path, int(FONT_SIZE * 0.65))
        e_font_current = ImageFont.truetype(font_path, int(CURRENT_FONT_SIZE * 0.65))
        t_font = ImageFont.truetype(font_path, 84)
        s_font = ImageFont.truetype(font_path, 45)
        
        # 強制渲染測試：畫一張小圖來觸發潛在的錯誤 (如 OSError: too many function definitions)
        dummy_img = Image.new("RGB", (100, 100))
        dummy_draw = ImageDraw.Draw(dummy_img)
        dummy_draw.text((10, 10), "測試渲染Test", font=c_font)
        dummy_draw.text((10, 50), "測試渲染Test", font=e_font)
        
        return c_font, c_font_current, e_font, e_font_current, t_font, s_font
    except Exception as e:
        print(f"⚠ 字體 {font_path} 測試失敗: {e}")
        return None

# 1. 先嘗試預定的 FONT_PATH
fonts = try_load_fonts(FONT_PATH)

# 2. 如果失敗且不是微軟正黑體，則嘗試微軟正黑體
if fonts is None and "msjh" not in FONT_PATH.lower():
    print("嘗試切換至系統預設微軟正黑體 (msjh.ttc)...")
    FONT_PATH = "msjh.ttc"
    fonts = try_load_fonts(FONT_PATH)

if fonts:
    CHINESE_FONT, CHINESE_FONT_CURRENT, ENGLISH_FONT, ENGLISH_FONT_CURRENT, TITLE_FONT, SINGER_FONT = fonts
    print(f"✓ 字體最終確認: {os.path.basename(FONT_PATH)}")
else:
    print(f"✗ 致命錯誤: 無法載入任何可用字體。請確認 {FONT_PATH} 或 msjh.ttc 是否存在。")
    exit(1)

BG_IMAGE = None
if BG_IMAGE_PATH and os.path.exists(BG_IMAGE_PATH):
    try:
        BG_IMAGE = Image.open(BG_IMAGE_PATH).convert("RGB").resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"背景圖片載入失敗: {e}")
        BG_IMAGE = None

# 用來記錄最後顯示的歌詞索引，避免空白時段消失
last_valid_index = 0

# 歌詞換行輔助函數（移到外部避免重複定義）
# 使用简化的换行逻辑，避免频繁调用 textbbox
def wrap_chinese_text_simple(text, max_chars_per_line=20):
    """将中文文本根据字符数自动换行（简化版，避免调用textbbox）"""
    if not text or len(text) <= max_chars_per_line:
        return [text] if text else []

    mid = len(text) // 2
    split_pos = mid
    for offset in range(len(text) // 3):
        if mid + offset < len(text) and text[mid + offset] in '，。、！？ 　':
            split_pos = mid + offset + 1
            break
        elif mid - offset >= 0 and text[mid - offset] in '，。、！？ 　':
            split_pos = mid - offset + 1
            break

    line1 = text[:split_pos].strip()
    line2 = text[split_pos:].strip()
    return [line for line in [line1, line2] if line]

def wrap_english_text_simple(text, max_chars_per_line=30):
    """将英文文本根据单词自动换行（简化版，避免调用textbbox）"""
    if not text:
        return []
    
    words = text.split()
    if len(' '.join(words)) <= max_chars_per_line:
        return [text]
    
    lines = []
    current = ""
    for word in words:
        test_line = (current + " " + word).strip()
        if len(test_line) <= max_chars_per_line:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    return lines if lines else [text]

def draw_text_with_spacing(draw, xy, text, font, fill, stroke_width, stroke_fill, spacing=1, anchor="mm"):
    """
    繪製帶有字間距的文字。
    目前僅完整支援 anchor="mm" (中心對齊)。
    """
    if not text:
        return
        
    if anchor != "mm":
        # 如果不是 mm，回退到普通繪製（或根據需要實作其他對齊）
        draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill, anchor=anchor)
        return

    # 計算總寬度
    total_width = 0
    char_widths = []
    for char in text:
        # textlength 回傳浮點數，累積計算
        w = draw.textlength(char, font=font)
        char_widths.append(w)
        total_width += w
    
    # 加上間距總和
    total_width += spacing * (len(text) - 1) if len(text) > 1 else 0
    
    # 計算起始 X (xy[0] 是中心 x)
    start_x = xy[0] - total_width / 2
    y = xy[1] # xy[1] 是中心 y
    
    current_x = start_x
    for i, char in enumerate(text):
        # 使用 "lm" (Left-Middle) 讓文字垂直置中於 y，水平從 current_x 開始
        draw.text((current_x, y), char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill, anchor="lm")
        current_x += char_widths[i] + spacing

def make_frame(t):
    """
    這是核心函數：MoviePy 會傳入時間 t (秒)，我們要回傳當下的畫面圖片 (numpy array)
    """
    global last_valid_index
    
    # --- A. 建立背景 ---
    if BG_IMAGE is not None:
        img = BG_IMAGE.copy().convert("RGBA")
    else:
        img = Image.new('RGBA', VIDEO_SIZE, BG_COLOR + (255,))

    # 疊加 70% 黑色遮罩
    overlay = Image.new('RGBA', VIDEO_SIZE, (0, 0, 0, int(255 * OVERLAY_ALPHA)))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    
    w, h = VIDEO_SIZE
    
    # --- B. 繪製圓形音頻視覺化 ---
    frame_index = int(t * sr / hop_length)
    
    if frame_index < DB.shape[1]:
        freqs = DB[:100, frame_index]
        
        # 確保生成正好 BAR_COUNT 個柱子
        bars = []
        for i in range(BAR_COUNT):
            idx = int(i * len(freqs) / BAR_COUNT)
            bars.append(freqs[idx])
        
        # 圓形參數
        center_x = w // 4  # 圓心在左側1/4處
        center_y = h // 2
        base_radius = 120  # 基礎半徑
        max_bar_length = 150  # 最大柱子長度（增加）
        
        # 繪製圓形頻譜
        for i, val in enumerate(bars):
            # 計算角度（360度分成BAR_COUNT份）
            angle = (i / BAR_COUNT) * 2 * np.pi
            
            # 柱子高度（增加倍數讓動態更明顯）
            bar_height = np.clip((val + 80) * 2.5, 0, max_bar_length)
            gradient_ratio = 0 if max_bar_length == 0 else min(1.0, bar_height / max_bar_length)
            bar_color = tuple(
                int(BAR_COLOR[c] + (255 - BAR_COLOR[c]) * gradient_ratio)
                for c in range(3)
            )
            
            # 計算柱子的起點和終點
            start_x = center_x + base_radius * np.cos(angle)
            start_y = center_y + base_radius * np.sin(angle)
            end_x = center_x + (base_radius + bar_height) * np.cos(angle)
            end_y = center_y + (base_radius + bar_height) * np.sin(angle)
            
            # 繪製柱子（使用較粗的線條）
            draw.line([(start_x, start_y), (end_x, end_y)], fill=bar_color, width=5)
        
        # 在中心畫一個圓形（白色背景）
        draw.ellipse([center_x - base_radius, center_y - base_radius, 
                      center_x + base_radius, center_y + base_radius], 
                     fill=(255, 255, 255), outline=BAR_COLOR, width=4)
        
        # 在圓形中心繪製歌曲名稱
        try:
            # 使用中心锚点简化居中
            draw.text(
                (center_x, center_y),
                SONG_TITLE,
                font=TITLE_FONT,
                fill=BAR_COLOR,
                stroke_width=TEXT_STROKE_WIDTH,
                stroke_fill=TEXT_STROKE_COLOR,
                anchor="mm"  # 中心锚点
            )
        except Exception as e:
            if not hasattr(make_frame, '_title_error_logged'):
                print(f"⚠ 標題渲染錯誤: {e}")
                traceback.print_exc()
                make_frame._title_error_logged = True

    # --- C. 繪製滾動式歌詞 - 右半邊 ---
    # 找出當前時間對應的字幕索引
    current_index = -1
    for i, sub in enumerate(subs):
        start_sec = sub.start.ordinal / 1000.0
        end_sec = sub.end.ordinal / 1000.0
        if start_sec <= t <= end_sec:
            current_index = i
            break
    
    # 如果沒有當前歌詞（空白時段），使用最後一次有效的索引
    if current_index == -1:
        for i, sub in enumerate(subs):
            start_sec = sub.start.ordinal / 1000.0
            if start_sec <= t:
                last_valid_index = i
        current_index = last_valid_index
    else:
        last_valid_index = current_index
    
    if current_index >= 0 and current_index < len(subs):
        try:
            # 設定顯示參數
            display_count = 3
            center_pos = 1
            
            start_idx = max(0, current_index - center_pos)
            end_idx = min(len(subs), start_idx + display_count)
            
            if end_idx - start_idx < display_count:
                start_idx = max(0, end_idx - display_count)

            # 歌詞區域 - 右半邊的中心區域
            lyrics_box_left = w // 2
            lyrics_box_width = w // 2 - 80
            # 整體往左移 100px (原本是置中於右半邊)
            lyrics_center_x = (lyrics_box_left + lyrics_box_width // 2) - 150
            
            # --- 動態排版計算 (避免重疊) ---
            visible_items = []
            
            # 1. 先計算每句歌詞的高度與內容
            for i in range(start_idx, end_idx):
                text = subs[i].text
                lines = text.split('\n')
                chinese_text = lines[0] if len(lines) > 0 else ""
                english_text = lines[1] if len(lines) > 1 else ""
                
                is_current = (i == current_index)
                
                # 自動換行
                chinese_lines = wrap_chinese_text_simple(chinese_text, max_chars_per_line=15)
                english_lines = wrap_english_text_simple(english_text, max_chars_per_line=35)
                
                # 行高設定
                if is_current:
                    c_lh = CURRENT_FONT_SIZE + 15
                    e_lh = int(CURRENT_FONT_SIZE * 0.65) + 12
                else:
                    c_lh = FONT_SIZE + 12
                    e_lh = int(FONT_SIZE * 0.65) + 8
                
                block_gap = 10 if chinese_lines and english_lines else 0
                block_height = len(chinese_lines) * c_lh + block_gap + len(english_lines) * e_lh
                
                visible_items.append({
                    'index': i,
                    'is_current': is_current,
                    'chinese_lines': chinese_lines,
                    'english_lines': english_lines,
                    'c_lh': c_lh,
                    'e_lh': e_lh,
                    'block_height': block_height,
                    'block_gap': block_gap
                })

            # 2. 計算 Y 軸位置 (以當前歌詞為錨點)
            current_item_idx = -1
            for idx, item in enumerate(visible_items):
                if item['is_current']:
                    current_item_idx = idx
                    break
            
            # 如果列表裡沒有當前歌詞 (邊界情況)，就預設中間那個是主要位置
            if current_item_idx == -1:
                current_item_idx = len(visible_items) // 2

            # 固定當前歌詞的中心位置
            base_ref_y = h // 2 + 75  # 稍微偏下
            margin = 80  # 區塊之間的間距 (增加間距避免重疊)

            # --- 滑動動畫計算 ---
            global_y_offset = 0
            # 只有在非第一句，且上一句也在顯示列表內時才做動畫
            if current_index > 0 and current_item_idx > 0:
                 start_sec = subs[current_index].start.ordinal / 1000.0
                 dt = t - start_sec
                 anim_duration = 0.5  # 動畫持續 0.5 秒
                 
                 if 0 <= dt < anim_duration:
                     curr_item = visible_items[current_item_idx]
                     prev_item = visible_items[current_item_idx - 1]
                     
                     # 計算從 "上一句置中" 到 "這一句置中" 的距離
                     # 在上一句置中時，這一句的位置應該在 Center + dist
                     stack_dist = (curr_item['block_height'] / 2) + margin + (prev_item['block_height'] / 2)
                     
                     # Cubic Ease Out: 快速滑動後減速
                     progress = dt / anim_duration
                     ease = 1 - (1 - progress) ** 3
                     global_y_offset = stack_dist * (1 - ease)
            
            ref_y = base_ref_y + global_y_offset

            # 初始化位置陣列
            positions = [0] * len(visible_items)
            if visible_items:
                positions[current_item_idx] = ref_y
                
                # 往上推算 (前一句)
                for k in range(current_item_idx - 1, -1, -1):
                    curr = visible_items[k]
                    next_item = visible_items[k+1]
                    # 上一句中心 = 下一句中心 - 下一句半高 - 間距 - 上一句半高
                    positions[k] = positions[k+1] - next_item['block_height']/2 - margin - curr['block_height']/2
                
                # 往下推算 (後一句)
                for k in range(current_item_idx + 1, len(visible_items)):
                    curr = visible_items[k]
                    prev_item = visible_items[k-1]
                    # 下一句中心 = 上一句中心 + 上一句半高 + 間距 + 下一句半高
                    positions[k] = positions[k-1] + prev_item['block_height']/2 + margin + curr['block_height']/2

            # 3. 繪製
            for item, y_pos in zip(visible_items, positions):
                i = item['index']
                block_height = item['block_height']
                c_lh = item['c_lh']
                e_lh = item['e_lh']
                chinese_lines = item['chinese_lines']
                english_lines = item['english_lines']
                block_gap = item['block_gap']
                
                block_top = y_pos - block_height / 2
                
                # 決定顏色
                if item['is_current']:
                    color = CURRENT_LYRICS_COLOR
                    stroke_color = TEXT_STROKE_COLOR
                    current_stroke_width = TEXT_STROKE_WIDTH
                else:
                    color = OTHER_LYRICS_COLOR
                    stroke_color = TEXT_STROKE_COLOR
                    current_stroke_width = OTHER_TEXT_STROKE_WIDTH
                    
                    # 變暗透明
                    dim_factor = 0.5
                    color = (int(color[0]*dim_factor), int(color[1]*dim_factor), int(color[2]*dim_factor), OTHER_LYRICS_ALPHA)
                    stroke_color = (int(stroke_color[0]*dim_factor), int(stroke_color[1]*dim_factor), int(stroke_color[2]*dim_factor), OTHER_LYRICS_ALPHA)

                # 繪製中文區塊
                for idx, line in enumerate(chinese_lines):
                    x = lyrics_center_x
                    y = block_top + idx * c_lh
                    
                    if item['is_current']:
                         # 當前歌詞：模擬粗體 + 白邊
                        draw_text_with_spacing(draw, (x, y), line, font=CHINESE_FONT_CURRENT, fill=color, stroke_width=3, stroke_fill=stroke_color, spacing=5, anchor="mm")
                        draw_text_with_spacing(draw, (x, y), line, font=CHINESE_FONT_CURRENT, fill=color, stroke_width=1, stroke_fill=color, spacing=5, anchor="mm")
                    else:
                        draw_text_with_spacing(draw, (x, y), line, font=CHINESE_FONT, fill=color, stroke_width=current_stroke_width, stroke_fill=stroke_color, spacing=5, anchor="mm")

                # 英文顏色
                if item['is_current']:
                    e_color = color
                else:
                    e_base = OTHER_LYRICS_COLOR
                    e_color = (min(255, e_base[0]+40), min(255, e_base[1]+40), min(255, e_base[2]+40), OTHER_LYRICS_ALPHA)
                
                # 繪製英文區塊
                e_start_y = block_top + len(chinese_lines) * c_lh + block_gap
                for idx, line in enumerate(english_lines):
                    y = e_start_y + idx * e_lh
                    
                    if item['is_current']:
                        draw_text_with_spacing(draw, (lyrics_center_x, y), line, font=ENGLISH_FONT_CURRENT, fill=e_color, stroke_width=3, stroke_fill=stroke_color, spacing=2, anchor="mm")
                        draw_text_with_spacing(draw, (lyrics_center_x, y), line, font=ENGLISH_FONT_CURRENT, fill=e_color, stroke_width=1, stroke_fill=e_color, spacing=2, anchor="mm")
                    else:
                        draw_text_with_spacing(draw, (lyrics_center_x, y), line, font=ENGLISH_FONT, fill=e_color, stroke_width=current_stroke_width, stroke_fill=stroke_color, spacing=2, anchor="mm")
                
        except Exception as e:
            # 只在第一次錯誤時打印，避免高頻打印
            if not hasattr(make_frame, '_error_logged'):
                print(f"⚠ 歌詞渲染錯誤: {e}")
                traceback.print_exc()
                make_frame._error_logged = True

    # --- D. 演唱者標記（右下角紅色區域） ---
    try:
        singer_text = "演唱者：chi"
        padding = 30
        # 使用右下角锚点
        x = w - padding
        y = h - padding

        # 1. 繪製底部白邊 (寬度 = 粗體寬度 0.6 + 白邊 0.3 = 0.9)
        draw.text(
            (x, y),
            singer_text,
            font=SINGER_FONT,
            fill=OTHER_LYRICS_COLOR,
            stroke_width=0.9,
            stroke_fill=TEXT_STROKE_COLOR,
            anchor="rb"  # 右下角锚点
        )
        # 2. 繪製上層文字 (模擬微粗體，寬度 0.6，顏色同字體)
        draw.text(
            (x, y),
            singer_text,
            font=SINGER_FONT,
            fill=OTHER_LYRICS_COLOR,
            stroke_width=0.6,
            stroke_fill=OTHER_LYRICS_COLOR,
            anchor="rb"  # 右下角锚点
        )
    except Exception as e:
        if not hasattr(make_frame, '_singer_error_logged'):
            print(f"⚠ 演唱者渲染錯誤: {e}")
            traceback.print_exc()
            make_frame._singer_error_logged = True

    return np.array(img.convert("RGB"))

# ================= 執行輸出 =================
print("2. 開始合成影片... (這會花一點時間，取決於電腦效能)")

# 建立影片物件
video = VideoClip(make_frame, duration=librosa.get_duration(y=y, sr=sr))
# 加上音軌
audio = AudioFileClip(AUDIO_FILE)
video = video.with_audio(audio)

# 寫入檔案
video.write_videofile(OUTPUT_FILE, fps=FPS, codec='libx264', audio_codec='aac', bitrate="8000k", preset="medium")
print(f"完成！影片已存為 {OUTPUT_FILE}")