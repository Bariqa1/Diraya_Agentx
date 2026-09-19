"""Comprehensive performance benchmark comparing MPS, CoreML/ANE, and Execution modes."""
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

img = cv2.imread("scratch_frame_test7.jpg")
if img is None:
    img = np.zeros((720, 1280, 3), dtype=np.uint8)

print("=" * 60)
print("DIRAYA HARDWARE ACCELERATION BENCHMARK (MacBook Pro M-Series)")
print("=" * 60)

# 1. Native PyTorch on Apple Silicon GPU (MPS)
print("\n--- 1. PyTorch on Apple Silicon GPU (MPS) ---")
m_person_mps = YOLO("models/yolo11n.pt")
m_ppe_mps = YOLO("models/PPE.pt")
m_fall_mps = YOLO("models/Fall.pt")

# Warm up MPS
_ = m_person_mps.predict(img, device="mps", verbose=False)
_ = m_ppe_mps.predict(img, device="mps", verbose=False)
_ = m_fall_mps.predict(img, device="mps", verbose=False)
if torch.backends.mps.is_available():
    torch.mps.synchronize()

t0 = time.perf_counter()
N = 15
for _ in range(N):
    _ = m_person_mps.predict(img, device="mps", verbose=False)
    _ = m_ppe_mps.predict(img, device="mps", verbose=False)
    _ = m_fall_mps.predict(img, device="mps", verbose=False)
    if torch.backends.mps.is_available():
        torch.mps.synchronize()
t_mps = (time.perf_counter() - t0) * 1000 / N
fps_mps = 1000.0 / t_mps
print(f"Latency per frame (3 models): {t_mps:.2f} ms | FPS: {fps_mps:.1f} FPS")

# 2. CoreML (.mlpackage) in Python
print("\n--- 2. CoreML / ANE (.mlpackage) ---")
try:
    m_person_cml = YOLO("models/yolo11n.mlpackage")
    m_ppe_cml = YOLO("models/PPE.mlpackage")
    m_fall_cml = YOLO("models/Fall.mlpackage")

    # Warm up CoreML
    _ = m_person_cml(img, verbose=False)
    _ = m_ppe_cml(img, verbose=False)
    _ = m_fall_cml(img, verbose=False)

    t0 = time.perf_counter()
    N_cml = 10
    for _ in range(N_cml):
        _ = m_person_cml(img, verbose=False)
        _ = m_ppe_cml(img, verbose=False)
        _ = m_fall_cml(img, verbose=False)
    t_cml = (time.perf_counter() - t0) * 1000 / N_cml
    fps_cml = 1000.0 / t_cml
    print(f"Latency per frame (3 models): {t_cml:.2f} ms | FPS: {fps_cml:.1f} FPS")
except Exception as e:
    t_cml = 0
    fps_cml = 0
    print(f"CoreML failed: {e}")

# 3. Parallel Pipelining (Decoupled Video Decode + GPU Inference)
print("\n--- 3. Pipelined Architecture (Async I/O + MPS Inference) ---")
import queue
import threading

frame_queue = queue.Queue(maxsize=10)
result_queue = queue.Queue(maxsize=10)
stop_event = threading.Event()

def producer():
    cap = cv2.VideoCapture("video_test/video_test7.mp4")
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break
        frame_queue.put(frame)
    cap.release()
    frame_queue.put(None)

def worker():
    while True:
        frame = frame_queue.get()
        if frame is None:
            break
        _ = m_person_mps.predict(frame, device="mps", verbose=False)
        _ = m_ppe_mps.predict(frame, device="mps", verbose=False)
        _ = m_fall_mps.predict(frame, device="mps", verbose=False)
        if torch.backends.mps.is_available():
            torch.mps.synchronize()
        result_queue.put(True)

t_pipe_start = time.perf_counter()
t_prod = threading.Thread(target=producer)
t_work = threading.Thread(target=worker)
t_prod.start()
t_work.start()

processed_count = 0
while True:
    res = result_queue.get()
    processed_count += 1
    if processed_count >= 100:  # Benchmark first 100 frames
        stop_event.set()
        break

t_pipe_total = time.perf_counter() - t_pipe_start
fps_pipe = processed_count / t_pipe_total
print(f"Processed {processed_count} frames in {t_pipe_total:.2f}s | Pipelined FPS: {fps_pipe:.1f} FPS")

print("\n" + "=" * 60)
print(f"SUMMARY COMPARISON:")
print(f"1. CoreML/ANE in Python: {fps_cml:.1f} FPS ({t_cml:.1f} ms)")
print(f"2. PyTorch on Apple Silicon GPU (MPS): {fps_mps:.1f} FPS ({t_mps:.1f} ms)")
print(f"3. Pipelined Video + MPS GPU: {fps_pipe:.1f} FPS ({1000.0/fps_pipe:.1f} ms)")
print("=" * 60)
