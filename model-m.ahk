; AutoHotkey script to remap Model-M keyboard on Windows
; The Right Ctrl key is the modifier key

; Set Caps Lock to Windows key
CapsLock::LWin

; Reload Caps Lock behaviour with
RControl & CapsLock::CapsLock

; Volume control
RControl & F1::Volume_Mute
RControl & F2::Volume_Down
RControl & F3::Volume_Up

; Media control
RControl & F5::Media_Prev
RControl & F6::Media_Play_Pause
RControl & F7::Media_Stop
RControl & F8::Media_Next
