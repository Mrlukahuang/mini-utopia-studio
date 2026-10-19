class_name MiniUtopiaFamilyVoiceRecorder
extends Node

signal voice_ready(media_type: String, bytes: PackedByteArray)
signal voice_failed

## Web-only, explicitly tapped mic: one sentence per current Director shot.
## No autoplay, voice cache, access token, URL upload or console payload.
var _callback_ref: JavaScriptObject
var recording := false


func start_on_user_tap() -> bool:
    if recording or not OS.has_feature("web"):
        return false
    recording = true
    _callback_ref = JavaScriptBridge.create_callback(_on_browser_result)
    var window := JavaScriptBridge.get_interface("window")
    window.__miniUtopiaVoiceResult = _callback_ref
    JavaScriptBridge.eval("""
(async () => {
  const done = window.__miniUtopiaVoiceResult;
  if (window.__miniUtopiaVoiceActive ||
      !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia ||
      !window.MediaRecorder || !window.isSecureContext) {
    done("failed"); return;
  }
  window.__miniUtopiaVoiceActive = true;
  let stream = null;
  try {
    // Safari prefers mp4/AAC. Chrome supports WebM/Opus.
    const mime = ["audio/mp4", "audio/webm"].find(
      t => MediaRecorder.isTypeSupported(t));
    if (!mime) throw new Error("unsupported");
    stream = await navigator.mediaDevices.getUserMedia({audio:true, video:false});
    const recorder = new MediaRecorder(stream, {mimeType:mime});
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      window.__miniUtopiaVoiceActive = false;
      window.__miniUtopiaVoiceStop = null;
      const blob = new Blob(chunks, {type:mime});
      if (!blob.size || blob.size > 1500000) {
        done("failed"); return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const value = String(reader.result || "");
        if (!value.includes(",")) { done("failed"); return; }
        done("ready|" + mime + "|" + value.split(",")[1]);
      };
      reader.onerror = () => done("failed");
      reader.readAsDataURL(blob);
    };
    recorder.onerror = () => {
      stream.getTracks().forEach(t => t.stop());
      window.__miniUtopiaVoiceActive = false;
      window.__miniUtopiaVoiceStop = null;
      done("failed");
    };
    window.__miniUtopiaVoiceStop = () => {
      if (recorder.state === "recording") recorder.stop();
    };
    recorder.start();
    setTimeout(() => {
      if (recorder.state === "recording") recorder.stop();
    }, 9000);
  } catch (_) {
    if (stream) stream.getTracks().forEach(t => t.stop());
    window.__miniUtopiaVoiceActive = false;
    window.__miniUtopiaVoiceStop = null;
    done("failed");
  }
})();
""", true)
    return true


func _on_browser_result(args: Array) -> void:
    recording = false
    if args.is_empty():
        voice_failed.emit()
        return
    var result := String(args[0])
    if not result.begins_with("ready|"):
        voice_failed.emit()
        return
    var second := result.find("|", 6)
    if second < 0:
        voice_failed.emit()
        return
    var mime := result.substr(6, second - 6)
    var data := Marshalls.base64_to_raw(result.substr(second + 1))
    if mime not in ["audio/mp4", "audio/webm"] or data.is_empty() or data.size() > 1500000:
        voice_failed.emit()
        return
    voice_ready.emit(mime, data)


func _exit_tree() -> void:
    if OS.has_feature("web"):
        JavaScriptBridge.eval("""
if (window.__miniUtopiaVoiceStop) window.__miniUtopiaVoiceStop();
window.__miniUtopiaVoiceResult = null;
""", true)
    recording = false
    _callback_ref = null
