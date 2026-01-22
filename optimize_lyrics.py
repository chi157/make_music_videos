"""
SRT 歌詞優化工具
可以重新組織歌詞的斷句，讓顯示更自然
"""

import pysrt
from tkinter import Tk, filedialog
import os
import re

def optimize_lyrics_basic(srt_file, output_file):
    """
    基礎優化：合併短句、智能斷句
    """
    subs = pysrt.open(srt_file, encoding='utf-8')
    optimized_subs = pysrt.SubRipFile()
    
    i = 0
    while i < len(subs):
        current_sub = subs[i]
        text = current_sub.text.strip()
        
        # 如果當前句太短（少於6個字），嘗試與下一句合併
        if len(text) < 6 and i + 1 < len(subs):
            next_sub = subs[i + 1]
            # 檢查時間間隔是否很近（小於0.5秒）
            time_gap = (next_sub.start.ordinal - current_sub.end.ordinal) / 1000.0
            
            # 只有當時間間隔很短且合併後不會太長時才合併
            combined_text = text + ' ' + next_sub.text.strip()
            if time_gap < 0.5 and len(combined_text) <= 30:
                # 合併兩句，保持原有時間範圍
                new_sub = pysrt.SubRipItem(
                    index=len(optimized_subs) + 1,
                    start=current_sub.start,
                    end=next_sub.end,
                    text=combined_text
                )
                optimized_subs.append(new_sub)
                i += 2
                continue
        
        # 如果句子太長（超過25個字），進行智能斷句
        if len(text) > 25:
            # 尋找最佳斷句點
            mid = len(text) // 2
            split_pos = mid
            
            # 優先在標點符號處斷句
            found_split = False
            for offset in range(min(len(text) // 3, 10)):
                if mid + offset < len(text) and text[mid + offset] in '，。、！？ 　':
                    split_pos = mid + offset + 1
                    found_split = True
                    break
                elif mid - offset >= 0 and text[mid - offset] in '，。、！？ 　':
                    split_pos = mid - offset + 1
                    found_split = True
                    break
            
            # 只有找到合適的斷句點才分割
            if found_split:
                # 計算時間分割點（根據字數比例分配時間）
                duration = current_sub.end.ordinal - current_sub.start.ordinal
                ratio = split_pos / len(text)
                split_time = current_sub.start.ordinal + int(duration * ratio)
            
            # 創建兩個字幕項
            text1 = text[:split_pos].strip()
            text2 = text[split_pos:].strip()
            
            if text1:
                sub1 = pysrt.SubRipItem(
                    index=len(optimized_subs) + 1,
                    start=current_sub.start,
                    end=pysrt.SubRipTime(milliseconds=split_time),
                    text=text1
                )
                optimized_subs.append(sub1)
            
            if text2:
                sub2 = pysrt.SubRipItem(
                    index=len(optimized_subs) + 1,
                    start=pysrt.SubRipTime(milliseconds=split_time),
                    end=current_sub.end,
                    text=text2
                )
                optimized_subs.append(sub2)
            
            i += 1
            continue
        
        # 保持原樣
        new_sub = pysrt.SubRipItem(
            index=len(optimized_subs) + 1,
            start=current_sub.start,
            end=current_sub.end,
            text=text
        )
        optimized_subs.append(new_sub)
        
        i += 1
    
    # 重新編號
    for idx, sub in enumerate(optimized_subs, 1):
        sub.index = idx
    
    # 儲存
    optimized_subs.save(output_file, encoding='utf-8')
    print(f"\n✅ 優化完成！")
    print(f"原始歌詞數: {len(subs)}")
    print(f"優化後歌詞數: {len(optimized_subs)}")
    print(f"已儲存至: {output_file}")
    print("\n📝 優化原則:")
    print("  - 保持原有時間軸，確保歌詞與演唱同步")
    print("  - 合併過短的句子（< 6字且間隔 < 0.5秒）")
    print("  - 分割過長的句子（> 25字）於標點符號處")
    print("  - 時間分配根據字數比例自動調整")


def optimize_lyrics_local_gpt(srt_file, output_file, api_url="http://localhost:1234/v1", reference_lyrics_file=None):
    """
    使用本地 GPT 模型優化斷句
    支援 LM Studio, Ollama, vLLM 等本地模型
    可選參考歌詞文件（已標註標點符號）
    """
    try:
        import requests
        import json
        
        # 讀取原始字幕
        subs = pysrt.open(srt_file, encoding='utf-8')
        
        # 準備歌詞文本和時間資訊
        lyrics_with_time = []
        for sub in subs:
            start_time = sub.start.ordinal / 1000.0
            end_time = sub.end.ordinal / 1000.0
            lyrics_with_time.append({
                "text": sub.text,
                "start": start_time,
                "end": end_time,
                "duration": end_time - start_time
            })
        
        # 準備提示詞
        lyrics_text = '\n'.join([f"{i+1}. {item['text']} (時長: {item['duration']:.1f}秒)" 
                                  for i, item in enumerate(lyrics_with_time)])
        
        # 如果有參考歌詞文件，讀取內容
        reference_section = ""
        if reference_lyrics_file and os.path.exists(reference_lyrics_file):
            with open(reference_lyrics_file, 'r', encoding='utf-8') as f:
                reference_text = f.read().strip()
            reference_section = f"""

【參考歌詞】（已標註標點符號，請按照這個版本的斷句和標點來優化）：
{reference_text}

請根據參考歌詞的斷句方式，將原始歌詞重新分割，保持時間軸的準確性。
"""
        
        prompt = f"""請將參考歌詞按斷句方式分行輸出。

【參考歌詞】：
{reference_text}

🚨 重要規則：
1. 嚴格按照參考歌詞的斷句（標點符號、換行）來分割
2. 完全保留原文，一個字都不能改（包括標點符號）
3. 每個句號、問號、驚嘆號後換行
4. 每個逗號可以考慮換行（如果句子太長）
5. 只輸出歌詞，每行一句，不要添加序號

請直接輸出分行後的歌詞：
"""
        
        print("正在使用本地 GPT 模型優化歌詞...")
        print(f"API 端點: {api_url}")
        
        # 調用本地模型 API
        response = requests.post(
            f"{api_url}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "qwen2.5",
                "messages": [
                    {"role": "system", "content": "你是一個專業的歌詞編輯。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"回應: {response.text}")
            return
        
        result = response.json()
        optimized_text = result['choices'][0]['message']['content']
        
        # 解析優化後的歌詞
        optimized_lines = []
        for line in optimized_text.split('\n'):
            line = line.strip()
            # 移除可能的序號
            line = re.sub(r'^\d+[\.\、]\s*', '', line)
            # 移除可能的標點符號開頭
            line = re.sub(r'^[，。、！？：；]\s*', '', line)
            if line and len(line) > 2:  # 過濾掉太短的行
                optimized_lines.append(line)
        
        print(f"\n優化後得到 {len(optimized_lines)} 句歌詞")
        
        if len(optimized_lines) == 0:
            print("❌ 沒有獲得有效的優化結果")
            return
        
        # 智能時間分配：結合精確匹配和字符映射
        optimized_subs = pysrt.SubRipFile()
        
        # 步驟1: 建立原始 SRT 的字符到時間映射
        char_time_map = []  # 每個字符對應的時間
        original_subs_dict = {}  # 用於精確匹配：完整文本 -> 原始字幕項列表
        
        for sub in subs:
            raw_text = sub.text.strip()
            text = sub.text.replace('\n', '').strip()
            # 去除標點符號，只保留實際歌詞文字
            clean_text = re.sub(r'[，。、！？：；\s]', '', text)
            
            # 建立文本到字幕的映射（用於精確匹配）
            original_subs_dict.setdefault(raw_text, []).append(sub)
            
            duration = sub.end.ordinal - sub.start.ordinal
            
            # 為每個字符分配時間（線性插值）
            for i, char in enumerate(clean_text):
                char_start = sub.start.ordinal + int(duration * i / max(1, len(clean_text)))
                char_end = sub.start.ordinal + int(duration * (i + 1) / max(1, len(clean_text)))
                
                char_time_map.append({
                    'char': char,
                    'start': char_start,
                    'end': char_end
                })
        
        # 步驟2: 檢查字符數量
        optimized_chars = []
        for line in optimized_lines:
            clean_line = re.sub(r'[，。、！？：；\s]', '', line.strip())
            optimized_chars.extend(list(clean_line))
        
        print(f"\n📊 字符匹配分析:")
        print(f"  原始 SRT 字符數: {len(char_time_map)}")
        print(f"  優化歌詞字符數: {len(optimized_chars)}")
        print(f"  原始 SRT 句數: {len(subs)}")
        
        # 步驟3: 為每句優化後的歌詞分配時間
        char_index = 0
        exact_matches = 0
        
        for i, line in enumerate(optimized_lines):
            line_text = line.strip()
            if not line_text:
                continue
            
            # 計算這句歌詞的純文字
            line_clean = re.sub(r'[，。、！？：；\s]', '', line_text)
            line_char_count = len(line_clean)
            
            if line_char_count == 0:
                continue
            
            # 嘗試精確匹配：如果這句歌詞在原始 SRT 中完全相同
            if line_text in original_subs_dict and original_subs_dict[line_text]:
                # 找到完全匹配！使用原始 SRT 的時間
                matched_sub = original_subs_dict[line_text].pop(0)
                start_time = matched_sub.start.ordinal
                end_time = matched_sub.end.ordinal
                exact_matches += 1
                
                # 更新字符索引（跳過這些字符）
                char_index += line_char_count
                
                match_indicator = "✓ 精確匹配"
            else:
                # 沒有完全匹配，使用字符映射
                start_idx = char_index
                end_idx = min(char_index + line_char_count - 1, len(char_time_map) - 1)
                
                # 處理超出範圍的情況
                if start_idx >= len(char_time_map):
                    if len(optimized_subs) > 0:
                        last_sub = optimized_subs[-1]
                        avg_duration = 2000
                        start_time = last_sub.end.ordinal
                        end_time = start_time + avg_duration
                    else:
                        start_time = subs[0].start.ordinal
                        end_time = subs[-1].end.ordinal
                    match_indicator = "⚠ 超出範圍"
                else:
                    start_time = char_time_map[start_idx]['start']
                    
                    if end_idx < len(char_time_map):
                        end_time = char_time_map[end_idx]['end']
                    else:
                        end_time = char_time_map[-1]['end']
                    
                    if end_time <= start_time:
                        end_time = start_time + 500
                    
                    match_indicator = "○ 字符映射"
                
                # 更新字符索引
                char_index = end_idx + 1
            
            # 創建字幕項
            sub = pysrt.SubRipItem(
                index=i + 1,
                start=pysrt.SubRipTime(milliseconds=int(start_time)),
                end=pysrt.SubRipTime(milliseconds=int(end_time)),
                text=line_text
            )
            optimized_subs.append(sub)
            
            # 顯示進度
            duration_sec = (end_time - start_time) / 1000.0
            print(f"  {i+1}. {line_text[:18]}... → {duration_sec:.1f}秒 ({line_char_count}字) {match_indicator}")
        
        print(f"\n✨ 精確匹配: {exact_matches}/{len(optimized_lines)} 句")
        
        def clean_punctuation(text):
            if not text:
                return text
            # 逗點類標點改成空白
            text = re.sub(r"[，,、]", " ", text)
            # 移除其他標點符號
            text = re.sub(r"[。！？：；·…—\-\(\)\[\]{}『』「」《》〈〉\\/\.\!?]", "", text)
            # 合併多餘空白
            text = re.sub(r"\s+", " ", text).strip()
            return text

        # 為每句歌詞添加英文翻譯
        print(f"\n🌍 正在生成英文翻譯...")
        print(f"💡 使用英文模型以確保語法正確性...")
        
        translated_subs = pysrt.SubRipFile()
        
        # 準備所有歌詞的上下文
        all_lyrics = [sub.text for sub in optimized_subs]
        context_text = "\n".join([f"{i+1}. {text}" for i, text in enumerate(all_lyrics)])
        
        for i, sub in enumerate(optimized_subs):
            chinese_text = sub.text
            
            # 調用 API 進行翻譯（使用英文模型）
            try:
                # 簡化 prompt，直接要求翻譯
                translate_prompt = f"""Translate this Chinese lyric to English. Keep it poetic and natural for singing:

{chinese_text}

English translation (one line only):"""
                
                translate_response = requests.post(
                    f"{api_url}/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "model": "llama3.1",
                        "messages": [
                            {"role": "system", "content": "You are a professional translator. Translate Chinese lyrics to English concisely. Output ONLY the English translation, no explanations."},
                            {"role": "user", "content": translate_prompt}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 100
                    },
                    timeout=30
                )
                
                if translate_response.status_code == 200:
                    english_text = translate_response.json()['choices'][0]['message']['content'].strip()
                    
                    # 清理多餘的說明文字
                    # 移除常見的前綴
                    english_text = re.sub(r'^(Here\'s|Here is|Translation:|English translation:?|Line \d+:)\s*', '', english_text, flags=re.IGNORECASE)
                    # 移除引號
                    english_text = english_text.strip('"\'')
                    # 只取第一行（如果有多行說明）
                    english_text = english_text.split('\n')[0].strip()
                    
                    # 如果還是包含說明性文字，嘗試提取實際翻譯
                    if 'translation' in english_text.lower() or 'here' in english_text.lower():
                        # 嘗試找到冒號後面的內容
                        if ':' in english_text:
                            english_text = english_text.split(':', 1)[1].strip().strip('"\'')
                    
                    # 移除中文原文（如果AI重複了）
                    if chinese_text in english_text:
                        english_text = english_text.replace(chinese_text, '').strip()
                    
                    # 保留中文原文 + 添加英文翻譯
                    combined_text = f"{chinese_text}\n{english_text}"
                    print(f"  {i+1}/{len(optimized_subs)}: ✓ ({chinese_text[:10]}...)")
                else:
                    # 翻譯失敗，只保留中文原文
                    combined_text = chinese_text
                    print(f"  {i+1}/{len(optimized_subs)}: ✗ (失敗，保留原文)")
                    
            except Exception as e:
                combined_text = chinese_text
                print(f"  {i+1}/{len(optimized_subs)}: ✗")
            
            # 最終輸出：移除標點符號（逗點改空白）
            combined_text = "\n".join([clean_punctuation(line) for line in combined_text.split("\n") if line.strip()])

            # 創建新的字幕項
            new_sub = pysrt.SubRipItem(
                index=i + 1,
                start=sub.start,
                end=sub.end,
                text=combined_text
            )
            translated_subs.append(new_sub)
        
        translated_subs.save(output_file, encoding='utf-8')
        print(f"\n✅ 優化和翻譯完成！已儲存至: {output_file}")
        print(f"📊 總共 {len(translated_subs)} 句歌詞（中英雙語）")
        print(f"🎯 使用模型: qwen2.5 (斷句優化) + llama3.1 (英文翻譯)")
        
    except ImportError:
        print("❌ 需要安裝 requests 套件: pip install requests")
    except requests.exceptions.ConnectionError:
        print(f"❌ 無法連接到本地模型 API: {api_url}")
        print("請確認本地模型服務正在運行")
    except Exception as e:
        print(f"❌ 本地模型優化失敗: {e}")


def optimize_lyrics_ai(srt_file, output_file):
    """
    AI 優化：使用 OpenAI API 來優化斷句
    需要設定 OPENAI_API_KEY 環境變數
    """
    try:
        import openai
        import json
        
        # 檢查 API Key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ 未設定 OPENAI_API_KEY 環境變數")
            print("請先設定: set OPENAI_API_KEY=your-api-key")
            return
        
        openai.api_key = api_key
        
        # 讀取原始字幕
        subs = pysrt.open(srt_file, encoding='utf-8')
        
        # 準備歌詞文本
        lyrics_text = '\n'.join([sub.text for sub in subs])
        
        print("正在使用 AI 優化歌詞斷句...")
        
        # 調用 OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一個專業的歌詞編輯。請將歌詞重新斷句，使每句長度適中（10-25字），符合演唱節奏和語意完整性。"},
                {"role": "user", "content": f"請優化以下歌詞的斷句，每行一句，保持原有順序：\n\n{lyrics_text}"}
            ]
        )
        
        optimized_text = response.choices[0].message.content
        optimized_lines = [line.strip() for line in optimized_text.split('\n') if line.strip()]
        
        # 重新分配時間軸
        total_duration = subs[-1].end.ordinal - subs[0].start.ordinal
        time_per_line = total_duration // len(optimized_lines)
        
        optimized_subs = pysrt.SubRipFile()
        for i, line in enumerate(optimized_lines):
            start_time = subs[0].start.ordinal + i * time_per_line
            end_time = start_time + time_per_line
            
            sub = pysrt.SubRipItem(
                index=i + 1,
                start=pysrt.SubRipTime(milliseconds=start_time),
                end=pysrt.SubRipTime(milliseconds=end_time),
                text=line
            )
            optimized_subs.append(sub)
        
        optimized_subs.save(output_file, encoding='utf-8')
        print(f"\n✅ AI 優化完成！已儲存至: {output_file}")
        
    except ImportError:
        print("❌ 需要安裝 openai 套件: pip install openai")
    except Exception as e:
        print(f"❌ AI 優化失敗: {e}")


def main():
    print("=" * 60)
    print("SRT 歌詞優化與翻譯工具")
    print("=" * 60)
    
    # 初始化檔案選擇器
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    # 步驟 1: 選擇音樂檔案
    print("\n步驟 1/3: 請選擇音樂檔案...")
    audio_file = filedialog.askopenfilename(
        title="選擇音樂檔案",
        filetypes=[("音樂檔案", "*.mp3 *.wav *.m4a *.flac"), ("所有檔案", "*.*")]
    )
    
    if not audio_file:
        print("❌ 未選擇音樂檔案，程式結束")
        return
    
    print(f"✅ 已選擇音樂: {os.path.basename(audio_file)}")
    
    # 步驟 2: 選擇原始 SRT 檔案
    print("\n步驟 2/3: 請選擇原始 SRT 歌詞檔案...")
    input_file = filedialog.askopenfilename(
        title="選擇原始 SRT 歌詞檔案",
        filetypes=[("字幕檔案", "*.srt"), ("所有檔案", "*.*")]
    )
    
    if not input_file:
        print("❌ 未選擇 SRT 檔案，程式結束")
        return
    
    print(f"✅ 已選擇 SRT: {os.path.basename(input_file)}")
    
    # 步驟 3: 選擇參考歌詞文件（必須）
    print("\n步驟 3/3: 請選擇參考歌詞檔案（已標註標點符號，無時間標註）...")
    reference_file = filedialog.askopenfilename(
        title="選擇參考歌詞檔案（已標註標點）",
        filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")]
    )
    
    if not reference_file:
        print("❌ 未選擇參考檔案，程式結束")
        return
    
    print(f"✅ 已選擇參考歌詞: {os.path.basename(reference_file)}")
    
    # 使用本地 GPT 模型優化
    api_url = "http://localhost:11434/v1"
    print(f"\n🤖 使用本地 GPT 模型 (Ollama): {api_url}")
    print(f"🎵 音樂檔案: {os.path.basename(audio_file)}")
    
    # 設定輸出檔案名稱
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_優化.srt"
    
    # 執行優化和翻譯
    optimize_lyrics_local_gpt(input_file, output_file, api_url, reference_file)
    
    root.destroy()


if __name__ == "__main__":
    main()
