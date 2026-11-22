"""UI-кит HouseCheck AI: карточки, кнопки, кольца, анимации, тосты, адаптивная сетка."""

from __future__ import annotations

import hashlib
import math
import random

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer,
    QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

import icons
from theme_tokens import T


# ───────────────────────── helpers ─────────────────────────

def C(key_or_hex: str, alpha: int | None = None) -> QColor:
    value = T.get(key_or_hex, key_or_hex)
    color = QColor(value)
    if alpha is not None:
        color.setAlpha(alpha)
    return color


_FAMILIES: list[str] | None = None


def _families() -> list[str]:
    global _FAMILIES
    if _FAMILIES is None:
        from PySide6.QtGui import QFontDatabase
        installed = set(QFontDatabase.families())
        wanted = ["Poppins", "Nunito", "Inter", "SF Pro Display", "Segoe UI Variable Display", "Segoe UI", "Helvetica Neue", "Arial"]
        _FAMILIES = [f for f in wanted if f in installed] or [QFont().defaultFamily()]
    return _FAMILIES


def font(size: int = 13, weight: int = 400) -> QFont:
    f = QFont()
    f.setFamilies(_families())
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    return f


def label(text: str = "", size: int = 13, color: str = "text", weight: int = 400, wrap: bool = True) -> QLabel:
    w = QLabel(text)
    w.setWordWrap(wrap)
    w.setFont(font(size, weight))
    w.setStyleSheet(f"color:{T.get(color, color)};background:transparent;")
    return w


def score_color(score: int | None) -> str:
    if not score:
        return T["text_soft"]
    if score >= 80:
        return T["positive"]
    if score >= 65:
        return T["accent"]
    if score >= 50:
        return T["warning"]
    return T["danger"]


def money(value: object, suffix: str = " ₸") -> str:
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        n = 0
    if not n:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + " млн" + suffix
    return f"{n:,}".replace(",", " ") + suffix


def later(ms: int, fn) -> None:
    """singleShot, безопасный к удалению виджета до срабатывания."""
    def run():
        try:
            fn()
        except RuntimeError:
            pass
    QTimer.singleShot(ms, run)


def fade_in(widget: QWidget, delay: int = 0, duration: int = 380) -> None:
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def done():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
    anim.finished.connect(done)
    later(delay, anim.start)


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


class _Hover:
    """Плавный прогресс наведения 0..1 для виджетов, которые рисуют себя сами."""

    def _init_hover(self, duration: int = 180):
        self._hover = 0.0
        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(duration)
        self._hover_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hover_anim.valueChanged.connect(self._set_hover)
        self.setAttribute(Qt.WA_Hover, True)

    def _set_hover(self, v):
        self._hover = float(v)
        self.update()

    def _animate_hover(self, target: float):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()


# ───────────────────────── Card ─────────────────────────

class Card(QFrame, _Hover):
    """Белая карточка с большим радиусом и мягкой тенью. variant: surface|muted|dark|accent|outline|glass."""

    clicked = Signal()
    PAD = 10

    def __init__(self, variant: str = "surface", radius: int = 24, clickable: bool = False, hover: bool = True, parent=None):
        super().__init__(parent)
        self.variant = variant
        self.radius = radius
        self.clickable = clickable
        self.hoverable = hover or clickable
        self.selected = False
        self._init_hover(220)
        if clickable:
            self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._inner = QVBoxLayout(self)
        p = self.PAD
        self._inner.setContentsMargins(p + 18, p + 16, p + 18, p + 18)
        self._inner.setSpacing(10)

    def layout_(self) -> QVBoxLayout:
        return self._inner

    def set_padding(self, l, t, r, b):
        p = self.PAD
        self._inner.setContentsMargins(p + l, p + t, p + r, p + b)

    def enterEvent(self, e):
        if self.hoverable:
            self._animate_hover(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.hoverable:
            self._animate_hover(0.0)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.clickable and e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def body_rect(self) -> QRectF:
        p = self.PAD
        lift = 3 * self._hover
        return QRectF(p, p - lift, self.width() - 2 * p, self.height() - 2 * p)

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.body_rect()
        if self.variant == "glass":
            path = QPainterPath(); path.addRoundedRect(r, self.radius, self.radius)
            painter.fillPath(path, QColor(255, 255, 255, int(14 + 22 * self._hover)))
            return
        dark_theme = QColor(T["bg"]).lightness() < 100
        # мягкая многослойная тень
        base_alpha = 10 if not dark_theme else 26
        layers = 9
        for i in range(layers, 0, -1):
            spread = i * (1.2 + 0.5 * self._hover)
            alpha = int(base_alpha * (1 - i / (layers + 1)) * (1 + 0.9 * self._hover))
            sh = r.adjusted(-spread * 0.6, -spread * 0.2 + 4 + 3 * self._hover, spread * 0.6, spread + 2 * self._hover)
            path = QPainterPath()
            path.addRoundedRect(sh, self.radius + spread * 0.5, self.radius + spread * 0.5)
            painter.fillPath(path, C("shadow", max(0, min(255, alpha))))
        path = QPainterPath()
        path.addRoundedRect(r, self.radius, self.radius)
        if self.variant == "dark":
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, C("nav2"))
            g.setColorAt(1, C("nav"))
            painter.fillPath(path, g)
        elif self.variant == "accent":
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, C("accent_glow"))
            g.setColorAt(1, C("accent"))
            painter.fillPath(path, g)
        elif self.variant == "muted":
            painter.fillPath(path, C("surface_muted"))
        else:
            painter.fillPath(path, C("surface"))
        if self.variant in ("surface", "muted", "outline"):
            border = QColor(C("border"))
            if self.selected:
                border = C("accent")
            elif self._hover > 0:
                a = C("accent")
                border = QColor(
                    int(border.red() + (a.red() - border.red()) * self._hover * 0.6),
                    int(border.green() + (a.green() - border.green()) * self._hover * 0.6),
                    int(border.blue() + (a.blue() - border.blue()) * self._hover * 0.6),
                )
            painter.setPen(QPen(border, 2 if self.selected else 1))
            painter.drawPath(path)
        if self.variant in ("dark", "accent"):
            # декоративные блики
            painter.setClipPath(path)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 18))
            painter.drawEllipse(QPointF(r.right() - 30, r.top() + 20), 90, 90)
            painter.setBrush(QColor(255, 255, 255, 10))
            painter.drawEllipse(QPointF(r.right() - 110, r.bottom() + 10), 70, 70)


# ───────────────────────── Buttons ─────────────────────────

class Button(QPushButton, _Hover):
    """Кнопка-пилюля. variant: primary|secondary|ghost|dark|danger|soft|white."""

    def __init__(self, text: str = "", variant: str = "secondary", icon_name: str | None = None, size: str = "md", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.icon_name = icon_name
        self.size_name = size
        self._press = 0.0
        self._init_hover()
        self._press_anim = QVariantAnimation(self)
        self._press_anim.setDuration(120)
        self._press_anim.valueChanged.connect(lambda v: (setattr(self, "_press", float(v)), self.update()))
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(font({"sm": 12, "md": 13, "lg": 15}[size], 600))
        self.setFlat(True)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setFixedHeight({"sm": 32, "md": 40, "lg": 50}[size])

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        h = {"sm": 32, "md": 40, "lg": 50}[self.size_name]
        pad = {"sm": 14, "md": 18, "lg": 24}[self.size_name]
        w = fm.horizontalAdvance(self.text()) + pad * 2
        if self.icon_name:
            w += 18 + (8 if self.text() else 0)
        if not self.text():
            w = h
        return QSize(w, h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def enterEvent(self, e):
        self._animate_hover(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._animate_hover(0.0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._press_anim.stop(); self._press_anim.setStartValue(self._press); self._press_anim.setEndValue(1.0); self._press_anim.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_anim.stop(); self._press_anim.setStartValue(self._press); self._press_anim.setEndValue(0.0); self._press_anim.start()
        super().mouseReleaseEvent(e)

    def _colors(self):
        v, h = self.variant, self._hover
        if v == "primary":
            bg = _mix(C("accent"), C("accent_hover"), h); fg = C("white"); border = None
        elif v == "dark":
            bg = _mix(C("nav"), C("nav2"), h); fg = C("white"); border = None
        elif v == "danger":
            bg = _mix(C("danger_soft"), C("danger"), h); fg = _mix(C("danger"), C("white"), h); border = None
        elif v == "ghost":
            bg = C("accent_soft", int(200 * h)); fg = _mix(C("text"), C("accent"), h); border = None
        elif v == "soft":
            bg = _mix(C("accent_soft"), C("accent"), h * 0.25); fg = C("accent"); border = None
        elif v == "white":
            bg = QColor(255, 255, 255, int(40 + 60 * h)); fg = C("white"); border = None
        else:
            bg = _mix(C("surface"), C("surface_muted"), h); fg = C("text"); border = _mix(C("border"), C("accent"), h)
        return bg, fg, border

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg, fg, border = self._colors()
        if not self.isEnabled():
            p.setOpacity(0.45)
        scale = 1 - 0.04 * self._press
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        cx, cy = r.center().x(), r.center().y()
        r = QRectF(cx - r.width() * scale / 2, cy - r.height() * scale / 2, r.width() * scale, r.height() * scale)
        radius = r.height() / 2
        if self.variant == "primary" and self._hover > 0:
            glow = C("accent", int(60 * self._hover))
            for i in range(1, 5):
                path = QPainterPath(); path.addRoundedRect(r.adjusted(-i, -i + 2, i, i + 2), radius + i, radius + i)
                p.fillPath(path, QColor(glow.red(), glow.green(), glow.blue(), int(glow.alpha() / (i + 1))))
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path, bg)
        if border is not None:
            p.setPen(QPen(border, 1.2))
            p.drawPath(path)
        p.setPen(fg)
        p.setFont(self.font())
        fm = QFontMetrics(self.font())
        text = self.text()
        tw = fm.horizontalAdvance(text)
        isz = 18 if self.size_name != "sm" else 15
        gap = 8 if text and self.icon_name else 0
        total = tw + (isz + gap if self.icon_name else 0)
        x = r.center().x() - total / 2
        if self.icon_name:
            icons.paint(p, self.icon_name, fg.name(), QRectF(x, r.center().y() - isz / 2, isz, isz))
            x += isz + gap
        if text:
            p.drawText(QRectF(x, r.top(), tw + 2, r.height()), Qt.AlignVCenter | Qt.AlignLeft, text)


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


class IconButton(Button):
    def __init__(self, icon_name: str, tooltip: str = "", variant: str = "secondary", size: str = "md", parent=None):
        super().__init__("", variant, icon_name, size, parent)
        self.setToolTip(tooltip)
        h = {"sm": 32, "md": 40, "lg": 50}[size]
        self.setFixedSize(h, h)


class Chip(QPushButton, _Hover):
    """Переключаемая пилюля-фильтр."""

    def __init__(self, text: str, checked: bool = False, icon_name: str | None = None, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setChecked(checked)
        self._on = 1.0 if checked else 0.0
        self._init_hover()
        self._on_anim = QVariantAnimation(self)
        self._on_anim.setDuration(200)
        self._on_anim.valueChanged.connect(lambda v: (setattr(self, "_on", float(v)), self.update()))
        self.toggled.connect(self._toggled)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(font(12, 600))
        self.setFixedHeight(34)

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        return QSize(fm.horizontalAdvance(self.text()) + 30 + (22 if self.icon_name else 0), 34)

    def _toggled(self, on):
        self._on_anim.stop(); self._on_anim.setStartValue(self._on); self._on_anim.setEndValue(1.0 if on else 0.0); self._on_anim.start()

    def enterEvent(self, e): self._animate_hover(1.0); super().enterEvent(e)
    def leaveEvent(self, e): self._animate_hover(0.0); super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath(); path.addRoundedRect(r, r.height() / 2, r.height() / 2)
        bg = _mix(_mix(C("surface"), C("surface_muted"), self._hover), C("nav"), self._on)
        p.fillPath(path, bg)
        if self._on < 1:
            p.setPen(QPen(_mix(C("border"), C("accent"), self._hover * 0.7), 1)); p.drawPath(path)
        fg = _mix(C("text"), C("white"), self._on)
        x = r.left() + 15
        if self.icon_name:
            icons.paint(p, self.icon_name, fg.name(), QRectF(x, r.center().y() - 8, 16, 16)); x += 22
        p.setPen(fg); p.setFont(self.font())
        p.drawText(QRectF(x, r.top(), r.width(), r.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())


class Segmented(QWidget):
    """Сегментированный переключатель с анимированной подложкой."""

    changed = Signal(int)

    def __init__(self, options: list[str], index: int = 0, icons_list: list[str] | None = None, dark: bool = False, parent=None):
        super().__init__(parent)
        self.options = options
        self.icons_list = icons_list
        self.index = index
        self.dark = dark
        self._pos = float(index)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_pos", float(v)), self.update()))
        self.setFont(font(12, 600))
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        fm = QFontMetrics(self.font())
        self._seg_w = max(fm.horizontalAdvance(o) for o in options) + (40 if icons_list else 28) if any(options) else 38
        self.setFixedWidth(int(self._seg_w * len(options) + 8))

    def set_index(self, i: int, emit: bool = True):
        if i == self.index:
            return
        self._anim.stop(); self._anim.setStartValue(self._pos); self._anim.setEndValue(float(i)); self._anim.start()
        self.index = i
        if emit:
            self.changed.emit(i)

    def mousePressEvent(self, e):
        i = int((e.position().x() - 4) // self._seg_w)
        if 0 <= i < len(self.options):
            self.set_index(i)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        path = QPainterPath(); path.addRoundedRect(r, r.height() / 2, r.height() / 2)
        p.fillPath(path, QColor(255, 255, 255, 22) if self.dark else C("surface_muted"))
        if not self.dark:
            p.setPen(QPen(C("border"), 1)); p.drawPath(path)
        knob = QRectF(4 + self._pos * self._seg_w, 4, self._seg_w, r.height() - 8)
        kp = QPainterPath(); kp.addRoundedRect(knob, knob.height() / 2, knob.height() / 2)
        p.fillPath(kp, C("accent"))
        p.setFont(self.font())
        for i, text in enumerate(self.options):
            seg = QRectF(4 + i * self._seg_w, 4, self._seg_w, r.height() - 8)
            active = 1 - min(1.0, abs(self._pos - i))
            fg = _mix(C("nav_muted") if self.dark else C("text_muted"), C("white"), active)
            p.setPen(fg)
            if self.icons_list:
                tw = QFontMetrics(self.font()).horizontalAdvance(text)
                total = 16 + (6 + tw if text else 0)
                x = seg.center().x() - total / 2
                icons.paint(p, self.icons_list[i], fg.name(), QRectF(x, seg.center().y() - 8, 16, 16))
                if text:
                    p.drawText(QRectF(x + 22, seg.top(), tw + 4, seg.height()), Qt.AlignVCenter, text)
            else:
                p.drawText(seg, Qt.AlignCenter, text)


# ───────────────────────── Data visuals ─────────────────────────

class ScoreRing(QWidget):
    """Анимированное кольцо индекса комфорта."""

    def __init__(self, size: int = 110, thickness: int = 10, caption: str = "", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.thickness = thickness
        self.caption = caption
        self.value = 0
        self._shown = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1100)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_shown", float(v)), self.update()))
        self.on_dark = False

    def set_value(self, value: int | None, animate: bool = True):
        self.value = int(value or 0)
        if animate:
            self._anim.stop(); self._anim.setStartValue(0.0); self._anim.setEndValue(float(self.value)); self._anim.start()
        else:
            self._shown = float(self.value); self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        t = self.thickness
        r = QRectF(t / 2 + 1, t / 2 + 1, self.width() - t - 2, self.height() - t - 2)
        track = QColor(255, 255, 255, 40) if self.on_dark else C("grid")
        p.setPen(QPen(track, t, Qt.SolidLine, Qt.RoundCap)); p.drawEllipse(r)
        color = QColor(score_color(self.value))
        if self.value:
            g = QPen(color, t, Qt.SolidLine, Qt.RoundCap)
            p.setPen(g)
            p.drawArc(r, 90 * 16, int(-self._shown / 100 * 360 * 16))
        p.setPen(C("white") if self.on_dark else C("text"))
        p.setFont(font(int(self.width() * 0.30), 800))
        txt = str(int(round(self._shown))) if self.value else "—"
        if self.caption:
            p.drawText(QRectF(0, -self.height() * 0.06, self.width(), self.height()), Qt.AlignCenter, txt)
            p.setFont(font(max(9, int(self.width() * 0.09)), 600))
            p.setPen(C("nav_muted") if self.on_dark else C("text_muted"))
            p.drawText(QRectF(0, self.height() * 0.58, self.width(), 20), Qt.AlignHCenter | Qt.AlignTop, self.caption)
        else:
            p.drawText(self.rect(), Qt.AlignCenter, txt)


class MeterBar(QWidget):
    """Строка категории: иконка, название, анимированная полоса, значение."""

    def __init__(self, title: str, icon_name: str = "sparkle", parent=None):
        super().__init__(parent)
        self.title = title
        self.icon_name = icon_name
        self.value = 0
        self._shown = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(900)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_shown", float(v)), self.update()))
        self.setFixedHeight(34)
        self.setMinimumWidth(220)

    def set_value(self, value: int, delay: int = 0):
        self.value = int(value or 0)
        self._anim.stop(); self._anim.setStartValue(0.0); self._anim.setEndValue(float(self.value))
        later(delay, self._anim.start)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        h = self.height()
        icons.paint(p, self.icon_name, T["text_muted"], QRectF(0, h / 2 - 9, 18, 18))
        p.setFont(font(12, 600)); p.setPen(C("text"))
        p.drawText(QRectF(28, 0, 130, h), Qt.AlignVCenter, self.title)
        bar = QRectF(160, h / 2 - 4, self.width() - 160 - 44, 8)
        path = QPainterPath(); path.addRoundedRect(bar, 4, 4); p.fillPath(path, C("grid"))
        if self.value:
            fill = QRectF(bar.left(), bar.top(), bar.width() * self._shown / 100, bar.height())
            g = QLinearGradient(fill.topLeft(), fill.topRight())
            col = QColor(score_color(self.value))
            light = QColor(col); light.setAlpha(150)
            g.setColorAt(0, light); g.setColorAt(1, col)
            fp = QPainterPath(); fp.addRoundedRect(fill, 4, 4); p.fillPath(fp, g)
        p.setFont(font(13, 800)); p.setPen(C("text"))
        p.drawText(QRectF(self.width() - 40, 0, 40, h), Qt.AlignVCenter | Qt.AlignRight, str(int(self._shown)) if self.value else "—")


class Stars(QWidget):
    def __init__(self, rating: float = 0, size: int = 14, parent=None):
        super().__init__(parent)
        self.rating = rating
        self.sz = size
        self.setFixedSize(size * 5 + 8, size + 2)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        for i in range(5):
            filled = self.rating >= i + 0.5
            name = "star_fill" if filled else "star"
            color = "#F5A524" if filled else T["border_strong"]
            icons.paint(p, name, color, QRectF(i * (self.sz + 2), 1, self.sz, self.sz), 1.6)


class Avatar(QWidget):
    PALETTE = ["#F28A3C", "#5B8DEF", "#3FA77A", "#7B6CF6", "#E0584B", "#D9822B", "#2BB3C0"]

    def __init__(self, name: str, size: int = 38, parent=None):
        super().__init__(parent)
        self.name = name or "?"
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        idx = int(hashlib.md5(self.name.encode()).hexdigest(), 16) % len(self.PALETTE)
        col = QColor(self.PALETTE[idx])
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0, col.lighter(125)); g.setColorAt(1, col)
        p.setBrush(g); p.setPen(Qt.NoPen); p.drawEllipse(self.rect())
        parts = [x for x in self.name.replace(".", " ").split() if x]
        initials = "".join(x[0] for x in parts[:2]).upper() or "?"
        p.setPen(QColor("#FFFFFF")); p.setFont(font(int(self.height() * 0.38), 700))
        p.drawText(self.rect(), Qt.AlignCenter, initials)


class Badge(QLabel):
    def __init__(self, text: str, bg: str = "accent_soft", fg: str = "accent", size: int = 11, parent=None):
        super().__init__(text, parent)
        self.setFont(font(size, 700))
        self.setStyleSheet(f"background:{T.get(bg, bg)};color:{T.get(fg, fg)};border-radius:10px;padding:3px 10px;")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


class IconBubble(QWidget):
    def __init__(self, icon_name: str, bg: str = "accent_soft", fg: str = "accent", size: int = 44, parent=None):
        super().__init__(parent)
        self.icon_name, self.bg, self.fg = icon_name, bg, fg
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()), self.width() * 0.32, self.width() * 0.32)
        p.fillPath(path, C(self.bg))
        s = self.width() * 0.5
        icons.paint(p, self.icon_name, T.get(self.fg, self.fg), QRectF((self.width() - s) / 2, (self.height() - s) / 2, s, s))


class CountLabel(QLabel):
    """Число, которое «набегает» при показе."""

    def __init__(self, value: float = 0, size: int = 30, color: str = "text", suffix: str = "", decimals: int = 0, parent=None):
        super().__init__(parent)
        self.suffix, self.decimals = suffix, decimals
        self.setFont(font(size, 800))
        self.setStyleSheet(f"color:{T.get(color, color)};background:transparent;")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1200)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._render)
        self.set_value(value)

    def _render(self, v):
        v = float(v)
        self.setText((f"{v:.{self.decimals}f}" if self.decimals else f"{int(round(v)):,}".replace(",", " ")) + self.suffix)

    def set_value(self, value: float):
        self._anim.stop(); self._anim.setStartValue(0.0); self._anim.setEndValue(float(value)); self._anim.start()


# ───────────────────────── Cover art ─────────────────────────

_cover_cache: dict[tuple, QPixmap] = {}
SKIES = [
    ("#FFD3A8", "#F28A3C", "#7A3E1C"), ("#BFE3FF", "#5B8DEF", "#1E3A78"), ("#DCD2FF", "#7B6CF6", "#2E2470"),
    ("#C5F2DD", "#3FA77A", "#164A35"), ("#3D4E85", "#17233F", "#0A0F1F"), ("#FFC9C2", "#E0584B", "#5E1E18"),
]


def cover_pixmap(name: str, w: int, h: int, dpr: float = 2.0) -> QPixmap:
    key = (name, w, h, dpr)
    if key in _cover_cache:
        return _cover_cache[key]
    seed = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    rnd = random.Random(seed)
    top, mid, deep = SKIES[seed % len(SKIES)]
    px = QPixmap(int(w * dpr), int(h * dpr)); px.setDevicePixelRatio(dpr); px.fill(Qt.transparent)
    p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, w * 0.3, h)
    g.setColorAt(0, QColor(top)); g.setColorAt(1, QColor(mid))
    p.fillRect(QRectF(0, 0, w, h), g)
    night = top.startswith("#3D")
    # солнце / луна
    sx, sy, sr = w * rnd.uniform(0.62, 0.86), h * rnd.uniform(0.18, 0.34), h * 0.13
    rg = QRadialGradient(QPointF(sx, sy), sr * 3)
    rg.setColorAt(0, QColor(255, 250, 230, 160)); rg.setColorAt(1, QColor(255, 250, 230, 0))
    p.setPen(Qt.NoPen); p.setBrush(rg); p.drawEllipse(QPointF(sx, sy), sr * 3, sr * 3)
    p.setBrush(QColor("#FFF6DA" if not night else "#E9ECFF")); p.drawEllipse(QPointF(sx, sy), sr, sr)
    # облака
    p.setBrush(QColor(255, 255, 255, 70))
    for _ in range(3):
        cx, cy = rnd.uniform(0, w), rnd.uniform(h * 0.1, h * 0.4)
        for k in range(3):
            p.drawEllipse(QPointF(cx + k * 16, cy + (k % 2) * 4), 18, 10)
    # дальний план
    far = QColor(deep); far.setAlpha(70)
    p.setBrush(far)
    x = -10
    while x < w:
        bw = rnd.uniform(26, 48); bh = rnd.uniform(h * 0.25, h * 0.5)
        p.drawRect(QRectF(x, h - bh, bw, bh)); x += bw + rnd.uniform(2, 10)
    # ближний план со светящимися окнами
    near = QColor(deep); near.setAlpha(215)
    x = rnd.uniform(-20, 0)
    while x < w:
        bw = rnd.uniform(34, 62); bh = rnd.uniform(h * 0.38, h * 0.78)
        rect = QRectF(x, h - bh, bw, bh)
        path = QPainterPath(); path.addRoundedRect(rect.adjusted(0, 0, 0, 10), 5, 5)
        p.fillPath(path, near)
        win = QColor("#FFE6A8"); win.setAlpha(210)
        for wy in range(int(rect.top() + 10), int(h - 8), 11):
            for wx in range(int(rect.left() + 6), int(rect.right() - 6), 9):
                if rnd.random() < (0.45 if not night else 0.6):
                    p.fillRect(QRectF(wx, wy, 4, 5), win)
        x += bw + rnd.uniform(4, 12)
    # дымка снизу
    fog = QLinearGradient(0, h * 0.7, 0, h)
    fog.setColorAt(0, QColor(0, 0, 0, 0)); fog.setColorAt(1, QColor(0, 0, 0, 70))
    p.fillRect(QRectF(0, 0, w, h), fog)
    p.end()
    _cover_cache[key] = px
    return px


class Cover(QWidget):
    def __init__(self, name: str, height: int = 150, radius: int = 18, parent=None):
        super().__init__(parent)
        self.name = name
        self.radius = radius
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, cover_pixmap(self.name, max(1, self.width()), max(1, self.height())))


# ───────────────────────── Inputs ─────────────────────────

class SearchBox(QFrame, _Hover):
    """Поле поиска с иконкой и подсказкой горячей клавиши."""

    def __init__(self, placeholder: str = "", hint: str = "", height: int = 44, parent=None):
        super().__init__(parent)
        self._init_hover()
        self.hint = hint
        self.setFixedHeight(height)
        lay = QHBoxLayout(self); lay.setContentsMargins(44, 0, 14 + (44 if hint else 0), 0)
        self.edit = QLineEdit(); self.edit.setObjectName("bare"); self.edit.setPlaceholderText(placeholder)
        self.edit.setFont(font(14, 500))
        self.edit.installEventFilter(self)
        lay.addWidget(self.edit)
        self._focus = 0.0

    def eventFilter(self, obj, e):
        if obj is self.edit and e.type() in (e.Type.FocusIn, e.Type.FocusOut):
            self._animate_hover(1.0 if e.type() == e.Type.FocusIn else 0.0)
        return False

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath(); path.addRoundedRect(r, r.height() / 2, r.height() / 2)
        if self._hover > 0:
            for i in range(1, 5):
                gp = QPainterPath(); gp.addRoundedRect(r.adjusted(-i, -i, i, i), r.height() / 2 + i, r.height() / 2 + i)
                p.fillPath(gp, C("accent", int(28 * self._hover / i)))
        p.fillPath(path, C("field"))
        p.setPen(QPen(_mix(C("border"), C("accent"), self._hover), 1.5)); p.drawPath(path)
        icons.paint(p, "search", _mix(C("text_soft"), C("accent"), self._hover).name(), QRectF(16, r.center().y() - 9, 18, 18))
        if self.hint:
            hr = QRectF(r.right() - 50, r.center().y() - 12, 40, 24)
            hp = QPainterPath(); hp.addRoundedRect(hr, 8, 8); p.fillPath(hp, C("surface_muted"))
            p.setPen(C("text_muted")); p.setFont(font(11, 700)); p.drawText(hr, Qt.AlignCenter, self.hint)


# ───────────────────────── Layout & transitions ─────────────────────────

class ResponsiveGrid(QWidget):
    """Сетка карточек: число колонок зависит от ширины."""

    def __init__(self, min_width: int = 300, spacing: int = 6, parent=None):
        super().__init__(parent)
        self.min_width = min_width
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(spacing)
        self.items: list[QWidget] = []
        self._cols = 0

    def set_items(self, widgets: list[QWidget], animate: bool = True):
        clear_layout(self.grid)
        self.items = widgets
        self._cols = 0
        self._relayout()
        if animate:
            for i, w in enumerate(widgets[:24]):
                fade_in(w, delay=40 * i, duration=420)

    def _relayout(self):
        cols = max(1, (self.width() or 900) // self.min_width)
        if cols == self._cols:
            return
        self._cols = cols
        for w in self.items:
            self.grid.removeWidget(w)
        for i, w in enumerate(self.items):
            self.grid.addWidget(w, i // cols, i % cols)
        for c in range(8):
            self.grid.setColumnStretch(c, 1 if c < cols else 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()


class AnimatedStack(QStackedWidget):
    """Стек страниц с плавным переходом: старая страница растворяется, новая выезжает снизу."""

    def go(self, widget: QWidget):
        old = self.currentWidget()
        if widget is old:
            return
        if old is None or not self.isVisible():
            self.setCurrentWidget(widget)
            return
        shot = old.grab()
        overlay = QLabel(self)
        overlay.setPixmap(shot)
        overlay.setGeometry(self.rect())
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setCurrentWidget(widget)
        overlay.show(); overlay.raise_()
        eff = QGraphicsOpacityEffect(overlay); overlay.setGraphicsEffect(eff)
        fade = QPropertyAnimation(eff, b"opacity", overlay)
        fade.setDuration(220); fade.setStartValue(1.0); fade.setEndValue(0.0); fade.setEasingCurve(QEasingCurve.OutQuad)
        fade.finished.connect(overlay.deleteLater)
        fade.start()
        target = widget.geometry()
        slide = QPropertyAnimation(widget, b"pos", widget)
        slide.setDuration(360); slide.setStartValue(target.topLeft() + QPoint(0, 26)); slide.setEndValue(target.topLeft())
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.finished.connect(lambda: widget.setGeometry(target))
        slide.start()


# ───────────────────────── Toasts ─────────────────────────

class Toast(QWidget):
    KIND = {"info": ("sparkle", "accent"), "ok": ("check", "positive"), "warn": ("shield", "warning"), "error": ("close", "danger")}

    def __init__(self, host: QWidget, text: str, kind: str = "info"):
        super().__init__(host)
        self.text = text
        self.kind = kind
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        f = font(13, 600)
        self.setFont(f)
        fm = QFontMetrics(f)
        self.resize(min(460, fm.horizontalAdvance(text) + 76), 52)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -4)
        for i in range(1, 6):
            sp = QPainterPath(); sp.addRoundedRect(r.adjusted(-i * 0.4, i, i * 0.4, i), 18, 18)
            p.fillPath(sp, QColor(0, 0, 0, 10))
        path = QPainterPath(); path.addRoundedRect(r, 18, 18)
        p.fillPath(path, QColor("#17233F"))
        icon_name, color = self.KIND.get(self.kind, self.KIND["info"])
        p.setBrush(QColor(T[color])); p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(r.left() + 12, r.center().y() - 14, 28, 28))
        icons.paint(p, icon_name, "#FFFFFF", QRectF(r.left() + 18, r.center().y() - 8, 16, 16))
        p.setPen(QColor("#FFFFFF")); p.setFont(self.font())
        p.drawText(r.adjusted(52, 0, -12, 0), Qt.AlignVCenter | Qt.TextSingleLine, self.text)


_active_toasts: list[Toast] = []


def toast(host: QWidget, text: str, kind: str = "info", ms: int = 2600) -> None:
    if host is None:
        return
    t = Toast(host, text, kind)
    _active_toasts[:] = [x for x in _active_toasts if _alive(x)]
    y = 72 + sum(x.height() + 8 for x in _active_toasts)
    end = QPoint(host.width() - t.width() - 24, y)
    t.move(end + QPoint(40, 0)); t.show(); t.raise_()
    _active_toasts.append(t)
    eff = QGraphicsOpacityEffect(t); eff.setOpacity(0); t.setGraphicsEffect(eff)
    a1 = QPropertyAnimation(t, b"pos", t); a1.setDuration(380); a1.setStartValue(t.pos()); a1.setEndValue(end); a1.setEasingCurve(QEasingCurve.OutBack); a1.start()
    a2 = QPropertyAnimation(eff, b"opacity", t); a2.setDuration(260); a2.setStartValue(0.0); a2.setEndValue(1.0); a2.start()

    def hide():
        if not _alive(t):
            return
        a3 = QPropertyAnimation(eff, b"opacity", t); a3.setDuration(300); a3.setStartValue(1.0); a3.setEndValue(0.0)
        a3.finished.connect(lambda: (_active_toasts.remove(t) if t in _active_toasts else None, t.deleteLater()))
        a3.start()
    later(ms, hide)


def _alive(w) -> bool:
    try:
        w.isVisible()
        return True
    except RuntimeError:
        return False


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background:{T['border']};")


def hbox(*widgets, spacing: int = 10, margins=(0, 0, 0, 0), stretch_at: int | None = None) -> QHBoxLayout:
    lay = QHBoxLayout(); lay.setSpacing(spacing); lay.setContentsMargins(*margins)
    for i, w in enumerate(widgets):
        if w is None:
            lay.addStretch(1)
        elif isinstance(w, int):
            lay.addSpacing(w)
        elif hasattr(w, "addWidget") and not isinstance(w, QWidget):
            lay.addLayout(w, 1 if stretch_at == i else 0)
        else:
            lay.addWidget(w, 1 if stretch_at == i else 0)
    return lay


def vbox(*widgets, spacing: int = 8, margins=(0, 0, 0, 0)) -> QVBoxLayout:
    lay = QVBoxLayout(); lay.setSpacing(spacing); lay.setContentsMargins(*margins)
    for w in widgets:
        if w is None:
            lay.addStretch(1)
        elif isinstance(w, int):
            lay.addSpacing(w)
        elif hasattr(w, "addWidget") and not isinstance(w, QWidget):
            lay.addLayout(w)
        else:
            lay.addWidget(w)
    return lay
