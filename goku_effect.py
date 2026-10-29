"""Goku mode: two fingers on the forehead teleport the person out of (and back into) the frame."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from vanish_sound import SOUND_PATH


APP_DIR = Path(__file__).resolve().parent
FACE_MODEL = APP_DIR / "face_landmarker.task"
TELEPORT_SOUND_PATH = APP_DIR / "assets" / "vanish-dbz.mp3"

HOLD_SECONDS = 1.0
HOLD_GRACE_SECONDS = 0.25
RELEASE_SECONDS = 0.4
CHECK_INTERVAL_SECONDS = 0.06
FACE_MEMORY_MS = 1500
FADE_SECONDS = 0.7
LINGER_SECONDS = 0.4
EFFECT_SECONDS = FADE_SECONDS + LINGER_SECONDS
SOUND_LEAD_SECONDS = 0.3  # the sound starts this long before the visual effect


def sound_path() -> Path:
    """vanish-dbz.mp3 if present in assets, otherwise the Naruto sound."""
    return TELEPORT_SOUND_PATH if TELEPORT_SOUND_PATH.is_file() else SOUND_PATH


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def two_fingers_pose(points: np.ndarray) -> bool:
    """Index and middle straight and together, ring and pinky folded (image coordinates)."""
    wrist = points[0]
    scale = _distance(wrist, points[9])
    if scale < 1e-6:
        return False
    for base in (5, 9):  # index, middle: tip clearly farther from the wrist than the PIP joint
        if _distance(points[base + 3], wrist) < _distance(points[base + 1], wrist) * 1.15:
            return False
    for base in (13, 17):  # ring, pinky: tip stays close to the palm
        if _distance(points[base + 3], wrist) > _distance(points[base], wrist) * 1.4:
            return False
    return _distance(points[8], points[12]) < scale * 0.55


def tips_on_forehead(points: np.ndarray, forehead: np.ndarray, face_width: float) -> bool:
    tips = (points[8] + points[12]) / 2.0
    return _distance(tips, forehead) < face_width * 0.6


class GokuTracker:
    """Face + hand landmarks; reports whether two fingers are held against the forehead."""

    def __init__(self, hands: vision.HandLandmarker, face: vision.FaceLandmarker):
        self.hands = hands
        self.face = face
        self.forehead: np.ndarray | None = None
        self.face_width = 0.0
        self.face_seen_ms = 0
        self.status = "no_face"

    def pose_on_forehead(self, image: mp.Image, timestamp_ms: int) -> bool:
        faces = self.face.detect_for_video(image, timestamp_ms)
        if faces.face_landmarks:
            marks = faces.face_landmarks[0]
            size = np.array([image.width, image.height], dtype=np.float32)
            point = lambda index: np.array([marks[index].x, marks[index].y], dtype=np.float32) * size
            self.forehead = (point(10) + point(151)) / 2.0
            self.face_width = _distance(point(234), point(454))
            self.face_seen_ms = timestamp_ms
        # A raised hand can hide the face from the tracker: keep the last forehead briefly.
        if self.forehead is None or timestamp_ms - self.face_seen_ms > FACE_MEMORY_MS:
            self.status = "no_face"
            return False

        hands = self.hands.detect_for_video(image, timestamp_ms)
        if not hands.hand_landmarks:
            self.status = "no_hand"
            return False
        size = np.array([image.width, image.height], dtype=np.float32)
        for landmarks in hands.hand_landmarks:
            points = np.array([(p.x, p.y) for p in landmarks], dtype=np.float32) * size
            if not two_fingers_pose(points):
                self.status = "pose_not_matching"
            elif not tips_on_forehead(points, self.forehead, self.face_width):
                self.status = "fingers_away_from_forehead"
            else:
                self.status = "ok"
                return True
        return False

    def close(self) -> None:
        try:
            self.hands.close()
        finally:
            self.face.close()


def create_tracker(hand_model: Path) -> GokuTracker:
    for model in (hand_model, FACE_MODEL):
        if not model.is_file():
            raise RuntimeError(f"Modello non trovato: {model}")
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(hand_model)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.35,
        min_hand_presence_confidence=0.35,
        min_tracking_confidence=0.45,
    ))
    try:
        face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(FACE_MODEL)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.4,
            min_face_presence_confidence=0.4,
            min_tracking_confidence=0.4,
        ))
    except Exception:
        hands.close()
        raise
    return GokuTracker(hands, face)


def _smoothstep(edge0: float, edge1: float, value: float) -> float:
    x = min(max((value - edge0) / (edge1 - edge0), 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def render_goku(
    frame: np.ndarray,
    background: np.ndarray,
    mask: np.ndarray | None,
    age: float,
    reverse: bool = False,
) -> np.ndarray:
    """Fade the silhouette with animated vertical lines; reverse=True plays it backwards."""
    s = EFFECT_SECONDS - age if reverse else age
    s = min(max(s, 0.0), EFFECT_SECONDS)
    if mask is None:
        mask = np.zeros(frame.shape[:2], dtype=np.float32)

    person = mask * (1.0 - _smoothstep(0.3, 1.0, s / FADE_SECONDS))
    alpha = person[:, :, None]
    output = (frame.astype(np.float32) * alpha
              + background.astype(np.float32) * (1.0 - alpha))

    intensity = min(1.0, s / 0.2) * (1.0 - max(0.0, s - FADE_SECONDS) / LINGER_SECONDS)
    points = cv2.findNonZero((mask > 0.05).astype(np.uint8))
    if intensity > 0.01 and points is not None:
        x, y, w, h = cv2.boundingRect(points)
        pad = 40
        left, top = max(0, x - pad), max(0, y - pad)
        right, bottom = min(frame.shape[1], x + w + pad), min(frame.shape[0], y + h + pad)
        area = np.s_[top:bottom, left:right]

        rng = np.random.default_rng(int(age * 24))  # lines re-roll ~24 times per second
        lines = np.zeros((bottom - top, right - left), dtype=np.float32)
        for _ in range(45):
            line_x = int(rng.integers(0, right - left))
            length = int(rng.uniform(0.4, 1.0) * (bottom - top))
            start = int(rng.integers(0, max(1, (bottom - top) - length + 1)))
            cv2.line(lines, (line_x, start), (line_x, start + length),
                     float(rng.uniform(0.5, 1.0)), int(rng.integers(1, 4)), cv2.LINE_AA)

        # Lines hug the silhouette (dilated) instead of covering the whole frame.
        region = cv2.GaussianBlur(
            cv2.dilate((mask[area] > 0.1).astype(np.uint8), np.ones((31, 31), np.uint8)).astype(np.float32),
            (0, 0), 8.0,
        )
        strength = (lines * region * 0.85 * intensity)[:, :, None]
        gray = np.array((140, 140, 140), dtype=np.float32)
        output[area] = output[area] * (1.0 - strength) + gray * strength
    return np.clip(output, 0, 255).astype(np.uint8)


class GokuSession:
    """Phases: visible -> vanishing -> gone -> appearing -> visible, driven by the held gesture."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.phase = "visible"
        self.started = 0.0
        self.hold_started: float | None = None
        self.last_seen = float("-inf")
        self.last_check = float("-inf")
        self.armed = True  # must lower the hand between two teleports
        self.mask: np.ndarray | None = None
        self.mask_at = float("-inf")

    def _update_hold(self, pose: bool, now: float, sound) -> None:
        if not pose:
            if self.hold_started is not None and now - self.last_seen > HOLD_GRACE_SECONDS:
                print("[Goku] Gesto interrotto: il conto alla rovescia riparte da capo.")
                self.hold_started = None
            if now - self.last_seen > RELEASE_SECONDS:
                self.armed = True
            return
        self.last_seen = now
        if not self.armed:
            return
        if self.hold_started is None:
            self.hold_started = now
            print(f"[Goku] Gesto riconosciuto: tieni la posa {HOLD_SECONDS:g} secondo.")
        if now - self.hold_started >= HOLD_SECONDS:
            vanishing = self.phase == "visible"
            self.phase = "vanishing" if vanishing else "appearing"
            self.started = now + SOUND_LEAD_SECONDS
            self.hold_started = None
            self.armed = False
            self.mask_at = float("-inf")
            sound.play()
            print("[Goku] Teletrasporto!" if vanishing else "[Goku] Ritorno!")

    def step(self, frame, background, now, elapsed_ms, tracker, get_mask, sound,
             debug: bool = False) -> np.ndarray:
        if self.phase in ("visible", "gone") and now - self.last_check >= CHECK_INTERVAL_SECONDS:
            self.last_check = now
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            pose = tracker.pose_on_forehead(image, elapsed_ms)
            if debug:
                print(f"[Goku] stato={tracker.status}, posa={pose}")
            self._update_hold(pose, now, sound)

        if self.phase in ("vanishing", "appearing"):
            if now - self.mask_at >= 0.05:
                self.mask = get_mask(frame, elapsed_ms)
                self.mask_at = now
            age = now - self.started
            if age >= EFFECT_SECONDS:
                self.phase = "gone" if self.phase == "vanishing" else "visible"
            else:
                return render_goku(frame, background, self.mask, age, self.phase == "appearing")
        return background.copy() if self.phase == "gone" else frame
