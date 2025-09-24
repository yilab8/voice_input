# 語音輸入熱鍵工具

這是一套受 [WISPR Flow] 啟發的 Windows 語音輸入輔助程式。使用者只要按下單一全域熱鍵（`Ctrl + ⊞ Win`）即可啟動或停止麥克風錄音，並透過 Whisper 引擎將語音轉為文字，再自動貼到目前作用中的應用程式中。

專案結構採用模組化與自動化測試，方便日後持續開發與維護。

## 功能特色

- 透過 `Ctrl + Win` 全域熱鍵控制「按住說話」式的錄音流程。
- 使用 [sounddevice] 擷取音訊並交給 [faster-whisper] 辨識，在安靜環境搭配 `medium` 或 `large-v2` 模型可達 95% 以上的辨識率。
- 正規化後的文字會自動複製到剪貼簿並貼上到目前的游標位置，可視需求關閉其中任一功能。
- 觸發錄音時會記錄當前作用視窗，在完成辨識後自動將焦點帶回原視窗並輸入文字，確保任何應用程式都能順暢接收內容。
- 錄音、語音辨識與文字輸出的元件皆可獨立測試與替換，方便注入模擬物件。

## 系統需求

- Windows 10/11（全域鍵盤監聽依賴 `keyboard` 套件，在 Windows 上支援最佳）。
- Python 3.10 或更新版本。
- 麥克風需具備良好的訊噪比，建議使用外接 USB 麥克風以提升準確度。
- 若要即時運行大型 Whisper 模型，可搭配支援 CUDA 11+ 的 GPU（選配）。

核心依賴已在 `pyproject.toml` 中列出：

- `faster-whisper`：語音轉文字。
- `sounddevice` 與 PortAudio：麥克風錄音。
- `keyboard`：註冊全域熱鍵。
- `pyperclip`：存取剪貼簿。
- `numpy`：高效率的音訊資料處理。

> **提示：** 在 Windows 上首次安裝 `sounddevice` 或 `faster-whisper` 時，可能需要先安裝 [Microsoft Visual C++ Redistributable] 才能順利載入。

## 快速開始

1. **切換到專案資料夾：**
   ```powershell
   cd C:\Users\<你的帳號>\Documents\GitHub\voice_input
   ```
   若你將專案放在其他路徑，請改成實際位置；之後的指令都必須在專案根目錄（能看到 `pyproject.toml` 的資料夾）執行。
2. **安裝套件（不需建立虛擬環境）：**
   ```powershell
   py -3.10 -m pip install --upgrade pip
   py -3.10 -m pip install --user .
   # 若要以可編輯模式進行開發或執行測試
   py -3.10 -m pip install --user -e .[dev]
   ```
   以上指令會把執行檔安裝到 `%APPDATA%\Python\Python310\Scripts`，請確認該路徑已加入
   `PATH`，或以完整路徑呼叫 `voice-input.exe`。如果腳本資料夾尚未加入 `PATH`，可改用
   `py -3.10 -m voice_input` 來啟動。
3. **預先下載想使用的 Whisper 模型（非必要，但可避免第一次啟動等待）：**
   ```powershell
   python -m faster_whisper.download medium --output_dir %LOCALAPPDATA%\voice-input-models
   ```
   若硬體足夠，可將 `medium` 改成 `large-v2` 以獲得最佳準確度。
4. **啟動應用程式：**
   ```powershell
   voice-input
   # 或者使用 Python 直接啟動
   python -m voice_input
   ```

當主控台顯示 `Hold ctrl+windows to record speech. Release to transcribe. Press Ctrl+C to exit.` 後，即可開始使用：

- 按住 `Ctrl + ⊞ Win` 開始錄音。
- 對著麥克風清楚說話。
- 放開熱鍵結束錄音，辨識出的文字會複製到剪貼簿並貼到目前游標位置。
- 在主控台視窗按 `Ctrl + C` 可結束程式。

## 設定說明

預設值定義於 `voice_input/config.py`，常用調整如下：

- `WhisperConfig.model_size`：`medium` 在效能與準確度間取得良好平衡；若有高效能 GPU 可改用 `large-v2`，準確率可達 95% 以上。
- `WhisperConfig.compute_type`：可設定為 `float16` 或 `int8_float16` 以善用現代 GPU。
- `HotkeyConfig.hotkey`：依個人習慣修改全域熱鍵（例如 `alt+space`）。
- `HotkeyConfig.suppress`：預設為 `True`，在 Windows 上會攔截熱鍵以避免彈出開始功能表；若不希望攔截可設為 `False`。
- `RecordingConfig.sample_rate`：預設 16 kHz；若麥克風支援更高取樣率，可提高此值，錄音模組會自動降頻給 Whisper。
- `AppConfig.insert_text` / `AppConfig.copy_to_clipboard`：若想手動處理貼上或剪貼簿，可關閉自動行為。
- `AppConfig.focus_active_window`：預設為 `True`，會在辨識完成後把焦點帶回按下熱鍵時的視窗；若系統上有自訂視窗管理邏輯，可將此項改為 `False`。

可依需求複製 `src/voice_input/__main__.py` 或撰寫啟動腳本，於建立 `VoiceInputApp` 前調整 `AppConfig`。

## 發佈與打包

若要提供單一執行檔給 Windows 測試者，可在啟用的虛擬環境中安裝 [PyInstaller] 並執行：

```powershell
py -3.10 -m pip install --user pyinstaller
pyinstaller -F -w -n VoiceInputApp .\src\voice_input\__main__.py --collect-all faster_whisper --collect-all sounddevice
```

完成後可在 `dist/VoiceInputApp.exe` 找到輸出的可執行檔。

## 測試

建議在每個開發階段結束時執行測試：

```powershell
py -3.10 -m pytest
```

測試套件會模擬硬體相關相依性，因此在任何平台上都能快速運行。若缺少可選套件（如 `numpy`），相關測試會自動跳過。

## 後續規劃

- 新增小型狀態覆蓋層或系統匣圖示，提供錄音中的視覺回饋。
- 支援將設定持久化為 `yaml`/`json` 檔，方便非開發者使用。
- 整合噪音抑制（例如 RNNoise）以改善嘈雜環境下的辨識率。
- 支援喚醒詞觸發，作為熱鍵以外的替代方案。

[WISPR Flow]: https://github.com/wispr-ai/wispr-flow
[sounddevice]: https://python-sounddevice.readthedocs.io/
[faster-whisper]: https://github.com/guillaumekln/faster-whisper
[Microsoft Visual C++ Redistributable]: https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist
[PyInstaller]: https://pyinstaller.org/
