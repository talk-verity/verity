"use client";
import { useEffect, useRef, useState } from "react";

export function useVoiceRecorder(onRecorded: (blob: Blob) => void, onError: (message: string) => void) {
  const [isRecording, setRecording] = useState(false);
  const [starting, setStarting] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const context = useRef<AudioContext | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(false);
  const startingRef = useRef(false);
  const callbacks = useRef({ onRecorded, onError });
  useEffect(() => { callbacks.current = { onRecorded, onError }; });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current) {
        recorder.current.onstop = null;
        recorder.current.ondataavailable = null;
        if (recorder.current.state !== "inactive") recorder.current.stop();
      }
      stream.current?.getTracks().forEach(track => track.stop());
      void context.current?.close();
    };
  }, []);
  function stop() {
    if (timer.current) clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
    setRecording(false);
  }
  async function start() {
    if (startingRef.current || recorder.current?.state === "recording") return;
    startingRef.current = true;
    setStarting(true);
    try {
      if (!context.current || context.current.state === "closed") context.current = new AudioContext();
      await context.current.resume();
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) { media.getTracks().forEach(track => track.stop()); return; }
      stream.current = media;
      const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(type => MediaRecorder.isTypeSupported(type));
      const rec = new MediaRecorder(media, { ...(mimeType ? { mimeType } : {}), audioBitsPerSecond: 64000 });
      recorder.current = rec;
      const chunks: Blob[] = [];
      let bytes = 0;
      rec.ondataavailable = event => {
        chunks.push(event.data);
        bytes += event.data.size;
        if (bytes > 3.5 * 1024 * 1024 && rec.state === "recording") stop();
      };
      rec.onstop = () => {
        media.getTracks().forEach(track => track.stop());
        stream.current = null;
        if (timer.current) clearTimeout(timer.current);
        if (!mounted.current) return;
        setRecording(false);
        const blob = new Blob(chunks, { type: rec.mimeType });
        if (blob.size > 4 * 1024 * 1024) {
          callbacks.current.onError("Recording is too large. Please record a shorter response.");
          return;
        }
        callbacks.current.onRecorded(blob);
      };
      rec.onerror = () => { callbacks.current.onError("Recording failed. Please try again."); stop(); };
      rec.start(1000);
      setRecording(true);
      timer.current = setTimeout(stop, 115000);
    } catch {
      stream.current?.getTracks().forEach(track => track.stop());
      if (mounted.current) callbacks.current.onError("Could not start recording. Check microphone permissions.");
    } finally {
      startingRef.current = false;
      if (mounted.current) setStarting(false);
    }
  }
  async function play(base64: string) {
    const ctx = context.current;
    if (!ctx || ctx.state === "closed") return;
    const bytes = Uint8Array.from(atob(base64), char => char.charCodeAt(0));
    const audio = await ctx.decodeAudioData(bytes.buffer);
    if (!mounted.current) return;
    const source = ctx.createBufferSource();
    source.buffer = audio;
    source.connect(ctx.destination);
    source.start();
  }
  return { isRecording, starting, start, stop, play };
}
