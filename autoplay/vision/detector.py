from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


def _imread_unicode(path: Path, flags: int = cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


@dataclass(slots=True)
class VisionRuntimeConfig:
    ui_roi: tuple[float, float, float, float]
    ui_left_roi: tuple[float, float, float, float]
    ui_gate_mode: str
    ground_roi: tuple[float, float, float, float]
    arc_roi: tuple[float, float, float, float]
    ui_feature_threshold: float
    ground_overlap_threshold: float
    arc_overlap_threshold: float


FEATURE_ROI_MAX_WIDTH = 420


@dataclass(slots=True)
class VisionMetrics:
    ui_feature_score: float = 0.0
    ui_good_matches: int = 0
    ui_inliers: int = 0
    ui_left_feature_score: float = 0.0
    ui_left_good_matches: int = 0
    ui_left_inliers: int = 0
    ui_pass: bool = False
    ground_overlap_ratio: float = 0.0
    ground_line_pixels: int = 0
    ground_note_pixels: int = 0
    ground_pass: bool = False
    arc_overlap_ratio: float = 0.0
    arc_cap_pixels: int = 0
    arc_note_pixels: int = 0
    arc_pass: bool = False
    last_arc_rect: tuple[int, int, int, int] | None = None


class VisionDetector:
    def __init__(self, ref_dir: Path, use_cuda: bool = True) -> None:
        self.ref_dir = ref_dir
        self.metrics = VisionMetrics()
        self.runtime = VisionRuntimeConfig(
            ui_roi=(0.66, 0.02, 0.995, 0.20),
            ui_left_roi=(0.005, 0.02, 0.34, 0.20),
            ui_gate_mode="weighted",
            ground_roi=(0.12, 1310 / 1440, 0.88, 1345 / 1440),
            arc_roi=(0.18, 0.22, 0.82, 0.80),
            ui_feature_threshold=0.08,
            ground_overlap_threshold=0.045,
            arc_overlap_threshold=0.44,
        )

        self.cuda_enabled = False
        self.cuda_canny = None
        if use_cuda:
            try:
                if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.cuda_enabled = True
                    self.cuda_canny = cv2.cuda.createCannyEdgeDetector(50, 150)
            except Exception:
                self.cuda_enabled = False

        self.ui_templates = self._load_ui_templates()
        self.ui_left_templates = self._load_ui_left_templates()
        self.arc_cap_template = self._load_arc_cap_template()

        self.orb = cv2.ORB_create(
            nfeatures=1100, fastThreshold=10, scaleFactor=1.15, nlevels=8
        )
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        self.ui_template_features: list[
            tuple[list, np.ndarray | None, tuple[int, int]]
        ] = []
        for tpl in self.ui_templates:
            gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
            kp, des = self.orb.detectAndCompute(gray, None)
            self.ui_template_features.append((kp, des, gray.shape[:2]))

        self.ui_left_template_features: list[
            tuple[list, np.ndarray | None, tuple[int, int]]
        ] = []
        for tpl in self.ui_left_templates:
            gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
            kp, des = self.orb.detectAndCompute(gray, None)
            self.ui_left_template_features.append((kp, des, gray.shape[:2]))

    def set_runtime(self, runtime: VisionRuntimeConfig) -> None:
        self.runtime = runtime

    def _load_ui_templates(self) -> list[np.ndarray]:
        templates: list[np.ndarray] = []
        for name in ("uiright.png", "uiright_2.png", "uiright-real.png"):
            img = _imread_unicode(self.ref_dir / name, cv2.IMREAD_COLOR)
            if img is not None:
                templates.append(img)
        return templates

    def _load_ui_left_templates(self) -> list[np.ndarray]:
        templates: list[np.ndarray] = []
        for name in ("uileft.png", "uileft_2.png", "pause.png"):
            img = _imread_unicode(self.ref_dir / name, cv2.IMREAD_COLOR)
            if img is not None:
                templates.append(img)
        return templates

    def _load_arc_cap_template(self) -> np.ndarray | None:
        return _imread_unicode(
            self.ref_dir / "Playfield" / "Note" / "arc_cap.png",
            cv2.IMREAD_UNCHANGED,
        )

    def _roi_rect(
        self, frame: np.ndarray, roi: tuple[float, float, float, float]
    ) -> tuple[int, int, int, int]:
        h, w = frame.shape[:2]
        x0 = int(w * roi[0])
        y0 = int(h * roi[1])
        x1 = int(w * roi[2])
        y1 = int(h * roi[3])
        x0, x1 = sorted((max(0, x0), min(w, x1)))
        y0, y1 = sorted((max(0, y0), min(h, y1)))
        return x0, y0, x1, y1

    def _canny(self, gray: np.ndarray) -> np.ndarray:
        if self.cuda_enabled and self.cuda_canny is not None:
            try:
                gpu = cv2.cuda_GpuMat()
                gpu.upload(gray)
                return self.cuda_canny.detect(gpu).download()
            except Exception:
                pass
        return cv2.Canny(gray, 50, 150)

    def _match_feature_score(
        self,
        roi: np.ndarray,
        template_features: list[tuple[list, np.ndarray | None, tuple[int, int]]],
    ) -> tuple[float, int, int]:
        if roi.shape[1] > FEATURE_ROI_MAX_WIDTH:
            scale = FEATURE_ROI_MAX_WIDTH / float(roi.shape[1])
            roi = cv2.resize(
                roi,
                (FEATURE_ROI_MAX_WIDTH, max(1, int(roi.shape[0] * scale))),
                interpolation=cv2.INTER_AREA,
            )

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        kp_f, des_f = self.orb.detectAndCompute(gray, None)
        if des_f is None or len(kp_f) < 8:
            return 0.0, 0, 0

        best_score = 0.0
        best_good = 0
        best_inliers = 0
        for kp_t, des_t, _shape in template_features:
            if des_t is None or len(kp_t) < 8:
                continue

            knn = self.matcher.knnMatch(des_t, des_f, k=2)
            good = []
            for pair in knn:
                if len(pair) != 2:
                    continue
                m, n = pair
                if m.distance < 0.72 * n.distance:
                    good.append(m)

            inliers = 0
            if len(good) >= 8:
                src = np.float32([kp_t[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst = np.float32([kp_f[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                _h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 2.5)
                if mask is not None:
                    inliers = int(mask.sum())

            denom = max(len(kp_t), 1)
            score = (0.55 * len(good) + 0.95 * inliers) / float(denom)
            if score > best_score:
                best_score = score
                best_good = len(good)
                best_inliers = inliers
        return best_score, best_good, best_inliers

    def detect_ui_panel(self, frame: np.ndarray) -> bool:
        mode = self.runtime.ui_gate_mode
        x0, y0, x1, y1 = self._roi_rect(frame, self.runtime.ui_roi)
        right_roi = frame[y0:y1, x0:x1]

        right_score, right_good, right_inliers = 0.0, 0, 0
        if right_roi.size > 0 and mode in {"right", "weighted"}:
            right_score, right_good, right_inliers = self._match_feature_score(
                right_roi,
                self.ui_template_features,
            )

        left_score, left_good, left_inliers = 0.0, 0, 0
        lx0, ly0, lx1, ly1 = self._roi_rect(frame, self.runtime.ui_left_roi)
        left_roi = frame[ly0:ly1, lx0:lx1]
        if (
            left_roi.size > 0
            and self.ui_left_template_features
            and mode in {"left", "weighted"}
        ):
            left_score, left_good, left_inliers = self._match_feature_score(
                left_roi,
                self.ui_left_template_features,
            )

        self.metrics.ui_feature_score = right_score
        self.metrics.ui_good_matches = right_good
        self.metrics.ui_inliers = right_inliers
        self.metrics.ui_left_feature_score = left_score
        self.metrics.ui_left_good_matches = left_good
        self.metrics.ui_left_inliers = left_inliers

        th = self.runtime.ui_feature_threshold
        if mode == "right":
            passed = right_score >= th
        elif mode == "left":
            passed = left_score >= th
        else:
            fused = 0.75 * right_score + 0.25 * left_score
            passed = (right_score >= th) or (left_score >= th) or (fused >= th)

        self.metrics.ui_pass = passed
        return passed

    def detect_ground_overlap(self, frame: np.ndarray) -> bool:
        x0, y0, x1, y1 = self._roi_rect(frame, self.runtime.ground_roi)
        roi = frame[y0:y1, x0:x1]
        if roi.size == 0:
            self.metrics.ground_pass = False
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edge = self._canny(gray)
        lines = cv2.HoughLinesP(
            edge,
            1,
            np.pi / 180,
            threshold=35,
            minLineLength=max(12, int(roi.shape[1] * 0.35)),
            maxLineGap=8,
        )

        line_mask = np.zeros(gray.shape, dtype=np.uint8)
        if lines is not None:
            for entry in lines:
                x_a, y_a, x_b, y_b = entry[0]
                cv2.line(line_mask, (x_a, y_a), (x_b, y_b), 255, 2)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        note_mask = ((hsv[:, :, 1] > 85) & (hsv[:, :, 2] > 105)).astype(np.uint8) * 255

        overlap = cv2.bitwise_and(line_mask, note_mask)
        line_pixels = int(cv2.countNonZero(line_mask))
        note_pixels = int(cv2.countNonZero(note_mask))
        overlap_pixels = int(cv2.countNonZero(overlap))
        ratio = overlap_pixels / float(max(1, line_pixels))

        self.metrics.ground_line_pixels = line_pixels
        self.metrics.ground_note_pixels = note_pixels
        self.metrics.ground_overlap_ratio = ratio
        self.metrics.ground_pass = ratio >= self.runtime.ground_overlap_threshold
        return self.metrics.ground_pass

    def detect_arc_overlap(self, frame: np.ndarray) -> bool:
        if self.arc_cap_template is None:
            self.metrics.arc_pass = False
            return False

        x0, y0, x1, y1 = self._roi_rect(frame, self.runtime.arc_roi)
        roi = frame[y0:y1, x0:x1]
        if roi.size == 0:
            self.metrics.arc_pass = False
            return False

        if self.arc_cap_template.ndim == 3 and self.arc_cap_template.shape[2] == 4:
            cap_bgr = self.arc_cap_template[:, :, :3]
            cap_alpha = self.arc_cap_template[:, :, 3]
        else:
            cap_bgr = self.arc_cap_template
            cap_alpha = np.ones(cap_bgr.shape[:2], dtype=np.uint8) * 255

        best_score = -1.0
        best_rect: tuple[int, int, int, int] | None = None
        best_alpha: np.ndarray | None = None
        for scale in (0.45, 0.55, 0.65, 0.75, 0.9, 1.0, 1.15):
            tpl = cv2.resize(
                cap_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR
            )
            alp = cv2.resize(
                cap_alpha, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR
            )
            th, tw = tpl.shape[:2]
            if th < 10 or tw < 10 or th >= roi.shape[0] or tw >= roi.shape[1]:
                continue
            score_map = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
            _minv, maxv, _minl, maxl = cv2.minMaxLoc(score_map)
            if maxv > best_score:
                best_score = float(maxv)
                best_rect = (maxl[0], maxl[1], maxl[0] + tw, maxl[1] + th)
                best_alpha = alp

        if best_rect is None or best_alpha is None:
            self.metrics.arc_pass = False
            return False

        cap_mask = np.zeros(roi.shape[:2], dtype=np.uint8)
        bx0, by0, bx1, by1 = best_rect
        cap_mask[by0:by1, bx0:bx1] = (best_alpha > 20).astype(np.uint8) * 255

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        arc_mask = ((hsv[:, :, 1] > 60) & (hsv[:, :, 2] > 80)).astype(np.uint8) * 255

        overlap = cv2.bitwise_and(cap_mask, arc_mask)
        cap_pixels = int(cv2.countNonZero(cap_mask))
        arc_pixels = int(cv2.countNonZero(arc_mask))
        overlap_pixels = int(cv2.countNonZero(overlap))
        ratio = overlap_pixels / float(max(1, cap_pixels))

        self.metrics.arc_cap_pixels = cap_pixels
        self.metrics.arc_note_pixels = arc_pixels
        self.metrics.arc_overlap_ratio = ratio
        self.metrics.arc_pass = ratio >= self.runtime.arc_overlap_threshold
        self.metrics.last_arc_rect = best_rect
        return self.metrics.arc_pass

    def render_overlay(
        self, frame: np.ndarray, stage: str, decode_fps: float | None
    ) -> np.ndarray:
        overlay = frame.copy()
        ui = self._roi_rect(frame, self.runtime.ui_roi)
        ui_left = self._roi_rect(frame, self.runtime.ui_left_roi)
        ground = self._roi_rect(frame, self.runtime.ground_roi)
        arc = self._roi_rect(frame, self.runtime.arc_roi)

        cv2.rectangle(overlay, (ui[0], ui[1]), (ui[2], ui[3]), (0, 220, 255), 2)
        cv2.rectangle(
            overlay,
            (ui_left[0], ui_left[1]),
            (ui_left[2], ui_left[3]),
            (220, 180, 40),
            2,
        )
        cv2.rectangle(
            overlay, (ground[0], ground[1]), (ground[2], ground[3]), (80, 255, 80), 2
        )
        cv2.rectangle(overlay, (arc[0], arc[1]), (arc[2], arc[3]), (255, 120, 80), 2)

        if self.metrics.last_arc_rect is not None:
            ax0, ay0, ax1, ay1 = self.metrics.last_arc_rect
            cv2.rectangle(
                overlay,
                (arc[0] + ax0, arc[1] + ay0),
                (arc[0] + ax1, arc[1] + ay1),
                (255, 255, 0),
                2,
            )

        lines = [
            f"stage={stage}",
            f"fps={decode_fps:.1f}" if decode_fps is not None else "fps=n/a",
            f"ui pass={self.metrics.ui_pass} mode={self.runtime.ui_gate_mode} right={self.metrics.ui_feature_score:.3f} left={self.metrics.ui_left_feature_score:.3f}",
            f"ground pass={self.metrics.ground_pass} overlap={self.metrics.ground_overlap_ratio:.3f}",
            f"arc pass={self.metrics.arc_pass} overlap={self.metrics.arc_overlap_ratio:.3f}",
            f"cuda={self.cuda_enabled}",
        ]
        text_metrics = [
            cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.68, 2)[0]
            for text in lines
        ]
        max_w = max((size[0] for size in text_metrics), default=200)
        x = max(10, overlay.shape[1] - max_w - 22)
        y = max(26, overlay.shape[0] - 24 * len(lines) - 14)
        for text in lines:
            cv2.putText(
                overlay,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                (0, 0, 0),
                4,
                cv2.LINE_AA,
            )
            cv2.putText(
                overlay,
                text,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                (30, 250, 255),
                2,
                cv2.LINE_AA,
            )
            y += 24
        return overlay
